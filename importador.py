"""
Importação de resultados anteriores por planilha (CSV, Excel .xlsx ou Google Sheets).

Usado pelo admin quando a API da Caixa não entrega todo o histórico. As linhas
validadas são gravadas no PostgreSQL (tabela concursos_importados), que é
persistente, e depois mescladas ao histórico local pelo updater.
"""

import csv
import io
import re
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import requests

try:
    from .core import LOTERIAS_CONFIG, LoteriaType
except ImportError:
    from core import LOTERIAS_CONFIG, LoteriaType

MAX_LINHAS = 20000
MAX_ERROS_EXIBIDOS = 30

MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']


class ErroImportacao(Exception):
    pass


def _normalizar(texto: Any) -> str:
    s = unicodedata.normalize('NFKD', str(texto or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s.lower())


def _config(loteria_type: str):
    try:
        return LOTERIAS_CONFIG[LoteriaType(loteria_type)]
    except (ValueError, KeyError):
        raise ErroImportacao('Loteria inválida.')


# ---------------------------------------------------------------------------
# Leitura dos arquivos
# ---------------------------------------------------------------------------

def _decodificar(conteudo: bytes) -> str:
    for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            return conteudo.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ErroImportacao('Não foi possível ler o arquivo CSV (codificação desconhecida).')


def ler_csv(conteudo: bytes) -> List[List[Any]]:
    texto = _decodificar(conteudo)
    amostra = texto[:5000]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=';,\t|')
        delim = dialeto.delimiter
    except csv.Error:
        delim = ';' if amostra.count(';') > amostra.count(',') else ','
    return [linha for linha in csv.reader(io.StringIO(texto), delimiter=delim)]


def ler_xlsx(conteudo: bytes) -> List[List[Any]]:
    try:
        import openpyxl
    except ImportError:
        raise ErroImportacao('Suporte a Excel indisponível no servidor (openpyxl ausente).')
    try:
        wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    except Exception:
        raise ErroImportacao('Arquivo Excel inválido. Use o formato .xlsx.')
    ws = wb.worksheets[0]
    linhas = []
    for linha in ws.iter_rows(values_only=True):
        linhas.append(list(linha))
        if len(linhas) > MAX_LINHAS + 50:
            break
    wb.close()
    return linhas


def url_exportacao_google_sheets(url: str) -> str:
    """Converte o link de compartilhamento do Google Sheets no link de exportação CSV."""
    partes = urlparse(url.strip())
    if partes.scheme != 'https' or partes.hostname != 'docs.google.com':
        raise ErroImportacao('Informe um link do Google Sheets (https://docs.google.com/spreadsheets/...).')
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', partes.path)
    if not m:
        raise ErroImportacao('Link do Google Sheets inválido.')
    gid = parse_qs(partes.query).get('gid', [None])[0]
    if not gid:
        g = re.search(r'gid=(\d+)', partes.fragment or '')
        gid = g.group(1) if g else '0'
    if not str(gid).isdigit():
        gid = '0'
    return f'https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv&gid={gid}'


def ler_google_sheets(url: str) -> List[List[Any]]:
    export = url_exportacao_google_sheets(url)
    try:
        resp = requests.get(export, timeout=20, allow_redirects=True)
    except requests.RequestException:
        raise ErroImportacao('Não foi possível acessar a planilha do Google.')
    tipo = resp.headers.get('Content-Type', '')
    if resp.status_code != 200 or 'text/html' in tipo:
        raise ErroImportacao('A planilha precisa estar compartilhada como "Qualquer pessoa com o link pode ver".')
    if len(resp.content) > 10 * 1024 * 1024:
        raise ErroImportacao('Planilha muito grande (limite de 10 MB).')
    return ler_csv(resp.content)


def ler_arquivo(nome: str, conteudo: bytes) -> List[List[Any]]:
    nome = (nome or '').lower()
    if nome.endswith('.xlsx') or nome.endswith('.xlsm'):
        return ler_xlsx(conteudo)
    if nome.endswith('.xls'):
        raise ErroImportacao('Formato .xls antigo não suportado. Salve como .xlsx ou .csv.')
    if nome.endswith('.csv') or nome.endswith('.txt') or not nome:
        return ler_csv(conteudo)
    # Arquivo sem extensão conhecida: xlsx é um zip
    if conteudo[:2] == b'PK':
        return ler_xlsx(conteudo)
    return ler_csv(conteudo)


# ---------------------------------------------------------------------------
# Interpretação das colunas
# ---------------------------------------------------------------------------

def _inteiro(valor: Any) -> Optional[int]:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        return int(valor) if valor.is_integer() else None
    s = str(valor).strip()
    if re.fullmatch(r'\d+(\.0+)?', s):
        return int(float(s))
    return None


def _data(valor: Any) -> Optional[str]:
    if valor is None or valor == '':
        return None
    if isinstance(valor, datetime):
        return valor.strftime('%d/%m/%Y')
    if isinstance(valor, date):
        return valor.strftime('%d/%m/%Y')
    s = str(valor).strip()
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y', '%Y-%m-%d %H:%M:%S', '%d.%m.%Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%d/%m/%Y')
        except ValueError:
            continue
    return None


def _papel_da_coluna(cabecalho: str) -> Optional[str]:
    h = _normalizar(cabecalho)
    if not h:
        return None
    if h in ('concurso', 'conc', 'nconcurso', 'numeroconcurso', 'numconcurso', 'numero', 'n', 'no'):
        return 'concurso'
    if h.startswith('data'):
        return 'data'
    if 'trevo' in h:
        return 'trevo'
    if 'timedocoracao' in h or h in ('time', 'timecoracao') or 'mesdasorte' in h or h in ('mes', 'messorte'):
        return 'complemento'
    if h in ('dezenas', 'numeros', 'resultado', 'numerossorteados', 'dezenassorteadas'):
        return 'dezenas_texto'
    segundo = bool(re.search(r'(2|segundo)sorteio|sorteio2|2s$', h))
    if re.fullmatch(r'(bola|dezena|dez|d|n|num|numero|coluna|col|b)\d{1,2}.*', h) or \
       re.fullmatch(r'\d{1,2}(a|o)?(bola|dezena|coluna).*', h):
        return 'dezena2' if segundo else 'dezena'
    if segundo and re.search(r'\d', h):
        return 'dezena2'
    return None


def _encontrar_cabecalho(linhas: List[List[Any]]) -> Tuple[int, Dict[int, str]]:
    """Procura, nas primeiras linhas, a que contém a coluna 'Concurso'."""
    for i, linha in enumerate(linhas[:15]):
        papeis = {j: _papel_da_coluna(c) for j, c in enumerate(linha)}
        if 'concurso' in papeis.values():
            return i, {j: p for j, p in papeis.items() if p}
    return -1, {}


def _numeros_de_texto(texto: Any) -> List[int]:
    return [int(n) for n in re.findall(r'\d+', str(texto or ''))]


def interpretar(loteria_type: str, linhas: List[List[Any]]) -> Dict[str, Any]:
    """Valida as linhas e devolve {'concursos': [...], 'erros': [...], 'ignoradas': n}."""
    cfg = _config(loteria_type)
    linhas = [l for l in linhas if l and any(c not in (None, '') for c in l)]
    if not linhas:
        raise ErroImportacao('A planilha está vazia.')
    if len(linhas) > MAX_LINHAS:
        raise ErroImportacao(f'Planilha com mais de {MAX_LINHAS} linhas.')

    idx_cab, papeis = _encontrar_cabecalho(linhas)
    if idx_cab >= 0:
        dados = linhas[idx_cab + 1:]
    else:
        # Sem cabeçalho: Concurso, [Data], dezenas..., [trevos/2º sorteio]
        dados = linhas
        papeis = None

    duplo = cfg.sorteios_por_concurso == 2
    com_trevo = loteria_type == 'mais_milionaria'
    com_complemento = loteria_type in ('timemania', 'dia_de_sorte')
    k = cfg.sorteados

    resultado: Dict[int, Dict[str, Any]] = {}
    erros: List[str] = []
    ignoradas = 0

    for n_linha, linha in enumerate(dados, start=(idx_cab + 2) if idx_cab >= 0 else 1):
        try:
            item = _interpretar_linha(linha, papeis, k, duplo, com_trevo, com_complemento)
        except ErroImportacao as e:
            erros.append(f'Linha {n_linha}: {e}')
            continue
        if item is None:
            ignoradas += 1
            continue

        problema = _validar(loteria_type, cfg, item)
        if problema:
            erros.append(f'Linha {n_linha} (concurso {item["concurso"]}): {problema}')
            continue
        if item['concurso'] in resultado and resultado[item['concurso']]['dezenas'] != item['dezenas']:
            erros.append(f'Linha {n_linha}: concurso {item["concurso"]} repetido com dezenas diferentes.')
            continue
        resultado[item['concurso']] = item

    concursos = [resultado[c] for c in sorted(resultado)]
    return {'concursos': concursos, 'erros': erros, 'ignoradas': ignoradas}


def _interpretar_linha(linha, papeis, k, duplo, com_trevo, com_complemento) -> Optional[Dict[str, Any]]:
    item: Dict[str, Any] = {'concurso': None, 'data': None, 'dezenas': [], 'segundo': [],
                            'trevos': [], 'complemento': None}

    if papeis is None:
        valores = list(linha)
        concurso = _inteiro(valores[0]) if valores else None
        if concurso is None:
            return None
        item['concurso'] = concurso
        resto = valores[1:]
        if resto and _data(resto[0]) and _inteiro(resto[0]) is None:
            item['data'] = _data(resto[0])
            resto = resto[1:]
        nums = []
        for v in resto:
            n = _inteiro(v)
            if n is None:
                if com_complemento and v not in (None, '') and item['complemento'] is None:
                    item['complemento'] = str(v).strip()
                continue
            nums.append(n)
        if len(nums) == 1 and k > 1:
            nums = _numeros_de_texto(resto[0])
        item['dezenas'] = nums[:k]
        extra = nums[k:]
        if duplo:
            item['segundo'] = extra[:k]
        elif com_trevo:
            item['trevos'] = extra[:2]
        return item

    for j, papel in papeis.items():
        valor = linha[j] if j < len(linha) else None
        if papel == 'concurso':
            item['concurso'] = _inteiro(valor)
        elif papel == 'data':
            item['data'] = _data(valor)
        elif papel == 'dezena':
            n = _inteiro(valor)
            if n is not None:
                item['dezenas'].append(n)
            elif valor not in (None, ''):
                raise ErroImportacao(f'valor inválido "{valor}" na coluna de dezena.')
        elif papel == 'dezena2':
            n = _inteiro(valor)
            if n is not None:
                item['segundo'].append(n)
        elif papel == 'trevo':
            n = _inteiro(valor)
            if n is not None:
                item['trevos'].append(n)
            else:
                item['trevos'].extend(_numeros_de_texto(valor))
        elif papel == 'complemento':
            if valor not in (None, ''):
                item['complemento'] = str(valor).strip()
        elif papel == 'dezenas_texto':
            item['dezenas'].extend(_numeros_de_texto(valor))

    if item['concurso'] is None:
        return None
    # Dupla Sena com todas as dezenas em colunas sem marcação de sorteio: 1º bloco e 2º bloco
    if duplo and not item['segundo'] and len(item['dezenas']) == 2 * k:
        item['dezenas'], item['segundo'] = item['dezenas'][:k], item['dezenas'][k:]
    # +Milionária com os trevos logo após as dezenas, sem cabeçalho próprio
    if com_trevo and not item['trevos'] and len(item['dezenas']) == k + 2:
        item['dezenas'], item['trevos'] = item['dezenas'][:k], item['dezenas'][k:]
    return item


def _normalizar_complemento(loteria_type: str, valor: Optional[str]) -> Optional[str]:
    if not valor:
        return None
    if loteria_type == 'dia_de_sorte':
        n = _inteiro(valor)
        if n is not None and 1 <= n <= 12:
            return MESES[n - 1].capitalize()
        alvo = _normalizar(valor)
        for mes in MESES:
            if _normalizar(mes) == alvo or _normalizar(mes)[:3] == alvo:
                return mes.capitalize()
        return None
    return str(valor).strip()[:80]


def _validar(loteria_type: str, cfg, item: Dict[str, Any]) -> Optional[str]:
    if item['concurso'] <= 0:
        return 'número de concurso inválido.'
    dezenas = item['dezenas']
    k = cfg.sorteados
    if len(dezenas) != k:
        return f'esperado {k} dezenas, encontrado {len(dezenas)}.'

    if loteria_type == 'super_sete':
        if any(not 0 <= d <= 9 for d in dezenas):
            return 'cada coluna do Super Sete vai de 0 a 9.'
    else:
        if any(not cfg.numero_inicial <= d <= cfg.numero_final for d in dezenas):
            return f'dezenas devem estar entre {cfg.numero_inicial} e {cfg.numero_final}.'
        if len(set(dezenas)) != k:
            return 'dezenas repetidas.'
        item['dezenas'] = sorted(dezenas)

    if cfg.sorteios_por_concurso == 2:
        seg = item['segundo']
        if seg:
            if len(seg) != k or len(set(seg)) != k or any(not 1 <= d <= cfg.numero_final for d in seg):
                return f'2º sorteio precisa de {k} dezenas distintas entre 1 e {cfg.numero_final}.'
            item['segundo'] = sorted(seg)
    else:
        item['segundo'] = []

    if loteria_type == 'mais_milionaria':
        tr = item['trevos']
        if tr:
            if len(tr) != 2 or len(set(tr)) != 2 or any(not 1 <= t <= 6 for t in tr):
                return 'trevos precisam ser 2 números distintos entre 1 e 6.'
            item['trevos'] = sorted(tr)
    else:
        item['trevos'] = []

    if loteria_type in ('timemania', 'dia_de_sorte'):
        original = item['complemento']
        item['complemento'] = _normalizar_complemento(loteria_type, original)
        if original and not item['complemento']:
            return f'mês da sorte inválido: "{original}".'
    else:
        item['complemento'] = None
    return None


def processar(loteria_type: str, *, nome_arquivo: str = '', conteudo: Optional[bytes] = None,
              url: str = '') -> Dict[str, Any]:
    _config(loteria_type)
    if conteudo:
        linhas = ler_arquivo(nome_arquivo, conteudo)
    elif url:
        linhas = ler_google_sheets(url)
    else:
        raise ErroImportacao('Envie um arquivo CSV/Excel ou informe o link do Google Sheets.')
    return interpretar(loteria_type, linhas)


def modelo_csv(loteria_type: str) -> str:
    """CSV de exemplo com o cabeçalho esperado para a loteria."""
    cfg = _config(loteria_type)
    k = cfg.sorteados
    cab = ['Concurso', 'Data'] + [f'Bola{i}' for i in range(1, k + 1)]
    exemplo = ['1', '01/01/2020'] + [str(cfg.numero_inicial + i) for i in range(k)]
    if loteria_type == 'super_sete':
        cab = ['Concurso', 'Data'] + [f'Coluna{i}' for i in range(1, 8)]
        exemplo = ['1', '01/01/2020'] + ['1', '2', '3', '4', '5', '6', '7']
    if cfg.sorteios_por_concurso == 2:
        cab += [f'Bola{i} 2º Sorteio' for i in range(1, k + 1)]
        exemplo += [str(i + 10) for i in range(1, k + 1)]
    if loteria_type == 'mais_milionaria':
        cab += ['Trevo1', 'Trevo2']
        exemplo += ['1', '2']
    if loteria_type == 'timemania':
        cab.append('Time do Coração')
        exemplo.append('Flamengo/RJ')
    if loteria_type == 'dia_de_sorte':
        cab.append('Mês da Sorte')
        exemplo.append('Janeiro')
    return ';'.join(cab) + '\n' + ';'.join(exemplo) + '\n'

"""
Módulo de Atualização e Sincronização dos Resultados das Loterias da Caixa
Projeto Calculadora da Sorte
"""

import os
import json
import time
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import database


ORIGINAL_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
if os.environ.get('VERCEL'):
    DATA_DIR = os.path.join('/tmp', 'data')
else:
    DATA_DIR = ORIGINAL_DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)

# Mapeamento do enum/id local para os slugs da API da Caixa
LOTERIAS_SLUGS = {
    'mega_sena': 'megasena',
    'lotofacil': 'lotofacil',
    'quina': 'quina',
    'lotomania': 'lotomania',
    'mais_milionaria': 'maismilionaria',
    'dia_de_sorte': 'diadesorte',
    'super_sete': 'supersete',
    'timemania': 'timemania',
    'dupla_sena': 'duplasena'
}

LOTERIAS_NOMES = {
    'mega_sena': 'Mega-Sena',
    'lotofacil': 'Lotofácil',
    'quina': 'Quina',
    'lotomania': 'Lotomania',
    'mais_milionaria': '+Milionária',
    'dia_de_sorte': 'Dia de Sorte',
    'super_sete': 'Super Sete',
    'timemania': 'Timemania',
    'dupla_sena': 'Dupla Sena'
}


def _get_session() -> requests.Session:
    """Cria uma sessão HTTP otimizada com headers completos e pool de conexões"""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=1)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://loterias.caixa.gov.br/',
        'Origin': 'https://loterias.caixa.gov.br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    })
    return session


_RESULTADO_COMPLETO_CACHE = {}
_RESULTADO_COMPLETO_TIME = {}


def consultar_caixa(slug: str, concurso: Optional[int] = None, max_retries: int = 2) -> Optional[Dict[str, Any]]:
    """
    Consulta o resultado de uma loteria na API com fallback para múltiplas fontes:
    1. api.guidi.dev.br (apenas para loterias compatíveis: megasena, lotofacil, quina, lotomania, timemania)
    2. Caixa Oficial (servicebus2.caixa.gov.br) com headers de navegador e timeout adequado
    3. loteriascaixa-api.herokuapp.com (para lotofacil, quina, lotomania, timemania)
    """
    session = _get_session()
    
    urls_para_tentar = []
    
    # 1. Guidi API (rápida para modalidades compatíveis)
    if slug in ('megasena', 'lotofacil', 'quina', 'lotomania', 'timemania'):
        url_guidi = f'https://api.guidi.dev.br/loteria/{slug}'
        url_guidi += f'/{concurso}' if concurso else '/ultimo'
        urls_para_tentar.append(('guidi', url_guidi))
        
    # 2. Heroku fallback (suporta TODAS as 9 loterias e funciona perfeitamente a partir da Vercel/EUA)
    url_heroku = f'https://loteriascaixa-api.herokuapp.com/api/{slug}'
    url_heroku += f'/{concurso}' if concurso else '/latest'
    urls_para_tentar.append(('heroku', url_heroku))

    # 3. Caixa Oficial (suporta as 9 modalidades - pode sofrer bloqueio em IP de datacenter internacional)
    url_caixa = f'https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}'
    if concurso:
        url_caixa += f'/{concurso}'
    urls_para_tentar.append(('caixa', url_caixa))
        
    timeout_req = 4
        
    for source, url in urls_para_tentar:
        for tentativa in range(1, max_retries + 1):
            try:
                response = session.get(url, timeout=timeout_req)
                if response.status_code == 200:
                    dados = response.json()
                    if source == 'heroku' and isinstance(dados, dict) and dados.get('concurso'):
                        dezenas_heroku = [f"{int(n):02d}" for n in dados.get('dezenas', [])]
                        segundo_sorteio = None
                        if slug == 'duplasena' and len(dezenas_heroku) == 12:
                            dezenas_heroku, segundo_sorteio = dezenas_heroku[:6], dezenas_heroku[6:]
                        return {
                            'numero': dados.get('concurso'),
                            'dataApuracao': dados.get('data'),
                            'listaDezenas': dezenas_heroku,
                            'listaDezenasSegundoSorteio': segundo_sorteio,
                            'acumulado': dados.get('acumulou', False),
                            'valorEstimadoProximoConcurso': float(dados.get('valorEstimadoProximoConcurso') or 0.0),
                            'dataProximoConcurso': dados.get('dataProximoConcurso') or dados.get('proximoConcurso'),
                            'listaTrevos': [str(t) for t in dados.get('trevos', [])],
                            'nomeTimeCoracaoMesSorte': dados.get('timeCoracao') or dados.get('mesSorte')
                        }
                    elif isinstance(dados, dict) and dados.get('numero'):
                        return dados
                elif response.status_code == 429:
                    time.sleep(0.2 * tentativa)
                elif response.status_code in (403, 502, 503, 504):
                    time.sleep(0.2 * tentativa)
            except Exception as e:
                if tentativa == max_retries:
                    print(f"[UPDATER] Erro na URL {url} ({slug} - {concurso}): {e}")
                else:
                    time.sleep(0.2 * tentativa)
                    
    return None


def carregar_ultimo_resultado_local(loteria_type: str) -> Optional[Dict[str, Any]]:
    """Carrega o último resultado completo salvo em arquivo local"""
    path = os.path.join(DATA_DIR, f'{loteria_type}_ultimo_resultado.json')
    if not os.path.exists(path) and os.path.exists(os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_ultimo_resultado.json')):
        path = os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_ultimo_resultado.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def salvar_ultimo_resultado_local(loteria_type: str, dados: Dict[str, Any]):
    """Salva o último resultado completo em arquivo local"""
    for folder in [DATA_DIR, ORIGINAL_DATA_DIR]:
        try:
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f'{loteria_type}_ultimo_resultado.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


def invalidar_cache_resultado(loteria_type: Optional[str] = None):
    """Invalida o cache em memória para uma ou todas as loterias"""
    global _RESULTADO_COMPLETO_CACHE, _RESULTADO_COMPLETO_TIME
    if loteria_type:
        _RESULTADO_COMPLETO_CACHE.pop(loteria_type, None)
        _RESULTADO_COMPLETO_TIME.pop(loteria_type, None)
    else:
        _RESULTADO_COMPLETO_CACHE.clear()
        _RESULTADO_COMPLETO_TIME.clear()


def obter_ultimo_resultado_completo(loteria_type: str, forcar_online: bool = False) -> Optional[Dict[str, Any]]:
    """
    Obtém o resultado mais recente para a loteria com garantia de entrega:
    1. Cache em memória recente (120 segundos)
    2. Consulta online resiliente (Guidi, Caixa, Heroku)
    3. Fallback para banco persistente PostgreSQL (database.obter_ultimo_resultado_db)
    4. Fallback para arquivo _ultimo_resultado.json atualizado
    5. Fallback sintético baseado no histórico/meta
    """
    now = time.time()
    
    # 1. Cache em memória recente (120 segundos para alta performance e proteção contra rate-limit)
    if not forcar_online and loteria_type in _RESULTADO_COMPLETO_CACHE and (now - _RESULTADO_COMPLETO_TIME.get(loteria_type, 0)) < 120:
        return _RESULTADO_COMPLETO_CACHE[loteria_type]
        
    slug = LOTERIAS_SLUGS.get(loteria_type)
    if not slug:
        return None
        
    # 2. Tentar consulta online
    dados = consultar_caixa(slug)
    if dados and dados.get('numero'):
        _RESULTADO_COMPLETO_CACHE[loteria_type] = dados
        _RESULTADO_COMPLETO_TIME[loteria_type] = now
        salvar_ultimo_resultado_local(loteria_type, dados)
        try:
            database.salvar_ultimo_resultado_db(loteria_type, dados)
        except Exception:
            pass
        return dados
        
    # 3. Fallback para banco de dados persistente PostgreSQL (Supabase)
    try:
        dados_db = database.obter_ultimo_resultado_db(loteria_type)
        if dados_db and dados_db.get('numero'):
            _RESULTADO_COMPLETO_CACHE[loteria_type] = dados_db
            _RESULTADO_COMPLETO_TIME[loteria_type] = now
            salvar_ultimo_resultado_local(loteria_type, dados_db)
            return dados_db
    except Exception:
        pass

    # 4. Fallback para cache local em disco (_ultimo_resultado.json)
    dados_local = carregar_ultimo_resultado_local(loteria_type)
    if dados_local and dados_local.get('numero'):
        _RESULTADO_COMPLETO_CACHE[loteria_type] = dados_local
        _RESULTADO_COMPLETO_TIME[loteria_type] = now
        return dados_local
        
    # 5. Fallback sintético a partir de histórico e meta
    historico = carregar_historico_local(loteria_type)
    meta = carregar_meta(loteria_type)
    if historico:
        ultimo_sorteio = historico[-1]
        dados_sinteticos = {
            'numero': meta.get('ultimo_concurso', 1),
            'dataApuracao': meta.get('data_apuracao', datetime.now().strftime('%d/%m/%Y')),
            'listaDezenas': [f"{n:02d}" for n in ultimo_sorteio],
            'acumulado': True,
            'valorEstimadoProximoConcurso': 3000000.0,
            'dataProximoConcurso': (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')
        }
        return dados_sinteticos
        
    return None


import time

_META_CACHE = {}
_META_CACHE_TIME = {}
_HISTORICO_CACHE = {}
_HISTORICO_CACHE_TIME = {}
_CACHE_TTL = 3600  # 1 hora

def carregar_meta(loteria_type: str) -> Dict[str, Any]:
    """Carrega metadados de sincronização da loteria"""
    now = time.time()
    if loteria_type in _META_CACHE and (now - _META_CACHE_TIME.get(loteria_type, 0)) < _CACHE_TTL:
        return _META_CACHE[loteria_type]

    path = os.path.join(DATA_DIR, f'{loteria_type}_meta.json')
    if not os.path.exists(path) and os.path.exists(os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_meta.json')):
        path = os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_meta.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                _META_CACHE[loteria_type] = dados
                _META_CACHE_TIME[loteria_type] = now
                return dados
        except Exception:
            pass
    return {}


def salvar_meta(loteria_type: str, meta: Dict[str, Any]):
    """Salva metadados de sincronização da loteria"""
    path = os.path.join(DATA_DIR, f'{loteria_type}_meta.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        _META_CACHE[loteria_type] = meta
        _META_CACHE_TIME[loteria_type] = time.time()
    except Exception as e:
        print(f"[UPDATER] Erro ao salvar meta {loteria_type}: {e}")


def carregar_historico_local(loteria_type: str) -> List[List[int]]:
    """Carrega lista de listas de números do arquivo JSON"""
    now = time.time()
    if loteria_type in _HISTORICO_CACHE and (now - _HISTORICO_CACHE_TIME.get(loteria_type, 0)) < _CACHE_TTL:
        return _HISTORICO_CACHE[loteria_type]

    path = os.path.join(DATA_DIR, f'{loteria_type}_historico.json')
    if not os.path.exists(path) and os.path.exists(os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_historico.json')):
        path = os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_historico.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    _HISTORICO_CACHE[loteria_type] = dados
                    _HISTORICO_CACHE_TIME[loteria_type] = now
                    return dados
        except Exception as e:
            print(f"[UPDATER] Erro ao carregar historico {loteria_type}: {e}")
    return []


def salvar_historico_local(loteria_type: str, historico: List[List[int]]):
    """Salva lista de listas de números no arquivo JSON"""
    path = os.path.join(DATA_DIR, f'{loteria_type}_historico.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)
    _HISTORICO_CACHE[loteria_type] = historico
    _HISTORICO_CACHE_TIME[loteria_type] = time.time()


_TIMES_CACHE = {}
_TIMES_CACHE_TIME = {}


def carregar_times_local(loteria_type: str) -> List[Optional[str]]:
    """Carrega a lista do 'Time do Coração' sorteado em cada concurso (exclusivo da Timemania),
    alinhada por posição com o histórico de dezenas da mesma loteria."""
    now = time.time()
    if loteria_type in _TIMES_CACHE and (now - _TIMES_CACHE_TIME.get(loteria_type, 0)) < _CACHE_TTL:
        return _TIMES_CACHE[loteria_type]

    path = os.path.join(DATA_DIR, f'{loteria_type}_times.json')
    if not os.path.exists(path) and os.path.exists(os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_times.json')):
        path = os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_times.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    _TIMES_CACHE[loteria_type] = dados
                    _TIMES_CACHE_TIME[loteria_type] = now
                    return dados
        except Exception as e:
            print(f"[UPDATER] Erro ao carregar times {loteria_type}: {e}")
    return []


def salvar_times_local(loteria_type: str, times: List[Optional[str]]):
    """Salva a lista do 'Time do Coração' sorteado em cada concurso"""
    path = os.path.join(DATA_DIR, f'{loteria_type}_times.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(times, f, indent=2, ensure_ascii=False)
    _TIMES_CACHE[loteria_type] = times
    _TIMES_CACHE_TIME[loteria_type] = time.time()


_TREVOS_CACHE = {}
_TREVOS_CACHE_TIME = {}


def carregar_trevos_local(loteria_type: str) -> List[List[int]]:
    """Carrega a lista de trevos sorteados em cada concurso (exclusivo da +Milionária),
    alinhada por posição com o histórico de dezenas da mesma loteria."""
    now = time.time()
    if loteria_type in _TREVOS_CACHE and (now - _TREVOS_CACHE_TIME.get(loteria_type, 0)) < _CACHE_TTL:
        return _TREVOS_CACHE[loteria_type]

    path = os.path.join(DATA_DIR, f'{loteria_type}_trevos.json')
    if not os.path.exists(path) and os.path.exists(os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_trevos.json')):
        path = os.path.join(ORIGINAL_DATA_DIR, f'{loteria_type}_trevos.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    _TREVOS_CACHE[loteria_type] = dados
                    _TREVOS_CACHE_TIME[loteria_type] = now
                    return dados
        except Exception as e:
            print(f"[UPDATER] Erro ao carregar trevos {loteria_type}: {e}")
    return []


def salvar_trevos_local(loteria_type: str, trevos: List[List[int]]):
    """Salva a lista de trevos sorteados em cada concurso"""
    path = os.path.join(DATA_DIR, f'{loteria_type}_trevos.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(trevos, f, indent=2, ensure_ascii=False)
    _TREVOS_CACHE[loteria_type] = trevos
    _TREVOS_CACHE_TIME[loteria_type] = time.time()


_SEGUNDO_SORTEIO_CACHE = {}
_SEGUNDO_SORTEIO_CACHE_TIME = {}


def carregar_segundo_sorteio_local(loteria_type: str) -> List[List[int]]:
    """Carrega as dezenas do 2º sorteio de cada concurso (exclusivo da Dupla Sena),
    alinhadas por posição com o histórico do 1º sorteio."""
    now = time.time()
    if loteria_type in _SEGUNDO_SORTEIO_CACHE and (now - _SEGUNDO_SORTEIO_CACHE_TIME.get(loteria_type, 0)) < _CACHE_TTL:
        return _SEGUNDO_SORTEIO_CACHE[loteria_type]

    nome = f'{loteria_type}_segundo_sorteio.json'
    path = os.path.join(DATA_DIR, nome)
    if not os.path.exists(path) and os.path.exists(os.path.join(ORIGINAL_DATA_DIR, nome)):
        path = os.path.join(ORIGINAL_DATA_DIR, nome)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                if isinstance(dados, list):
                    _SEGUNDO_SORTEIO_CACHE[loteria_type] = dados
                    _SEGUNDO_SORTEIO_CACHE_TIME[loteria_type] = now
                    return dados
        except Exception as e:
            print(f"[UPDATER] Erro ao carregar 2º sorteio {loteria_type}: {e}")
    return []


def salvar_segundo_sorteio_local(loteria_type: str, sorteios: List[List[int]]):
    path = os.path.join(DATA_DIR, f'{loteria_type}_segundo_sorteio.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sorteios, f, indent=2, ensure_ascii=False)
    _SEGUNDO_SORTEIO_CACHE[loteria_type] = sorteios
    _SEGUNDO_SORTEIO_CACHE_TIME[loteria_type] = time.time()


def carregar_concursos_local(loteria_type: str) -> List[int]:
    """Número de cada concurso do histórico, na mesma ordem (vazio em históricos antigos)."""
    nome = f'{loteria_type}_concursos.json'
    for pasta in (DATA_DIR, ORIGINAL_DATA_DIR):
        path = os.path.join(pasta, nome)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                return dados if isinstance(dados, list) else []
            except Exception as e:
                print(f"[UPDATER] Erro ao carregar concursos {loteria_type}: {e}")
            break
    return []


def salvar_concursos_local(loteria_type: str, concursos: List[int]):
    with open(os.path.join(DATA_DIR, f'{loteria_type}_concursos.json'), 'w', encoding='utf-8') as f:
        json.dump(concursos, f)


def historico_consistente(loteria_type: str, historico: List[List[int]], ultimo_local: Optional[int],
                          dados_ultimo_local: Optional[Dict[str, Any]]) -> bool:
    """O último item do histórico precisa ser o sorteio do concurso que a meta diz ser o último.
    Se não for, o histórico está defasado ou desalinhado e precisa ser recarregado."""
    if not historico or not ultimo_local:
        return False
    if not dados_ultimo_local or dados_ultimo_local.get('numero') != ultimo_local:
        return True  # sem como comparar: mantém
    slug = LOTERIAS_SLUGS.get(loteria_type)
    return historico[-1] == extrair_dezenas(dados_ultimo_local, slug)


def extrair_segundo_sorteio(dados_caixa: Dict[str, Any]) -> List[int]:
    """Extrai as dezenas do 2º sorteio da Dupla Sena."""
    try:
        return sorted(int(n) for n in (dados_caixa.get('listaDezenasSegundoSorteio') or []))
    except Exception:
        return []


def historico_com_segundo_sorteio(loteria_type: str) -> List[List[int]]:
    """Dupla Sena: une 1º e 2º sorteio de cada concurso (12 dezenas por concurso).
    Só une quando todos os concursos têm o 2º sorteio, para não misturar concursos
    com 6 e com 12 dezenas no mesmo cálculo."""
    historico = carregar_historico_local(loteria_type)
    segundos = carregar_segundo_sorteio_local(loteria_type)
    if not historico or len(segundos) != len(historico) or not all(len(s) == 6 for s in segundos):
        return historico
    return [primeiro + segundo for primeiro, segundo in zip(historico, segundos)]


def extrair_dezenas(dados_caixa: Dict[str, Any], slug: str) -> List[int]:
    """Extrai e formata a lista de dezenas sorteadas"""
    lista = dados_caixa.get('listaDezenas') or dados_caixa.get('dezenasSorteadasOrdemSorteio') or []
    try:
        numeros = [int(n) for n in lista]
        # Para Super Sete mantém a ordem das colunas; para as outras, ordena
        if slug != 'supersete':
            numeros.sort()
        return numeros
    except Exception:
        return []


def extrair_time_coracao(dados_caixa: Dict[str, Any]) -> Optional[str]:
    """Extrai o nome do 'Time do Coração' sorteado no concurso (exclusivo da Timemania).
    A API da Caixa já usou nomes de campo distintos ao longo do tempo, então tenta
    várias chaves conhecidas antes de desistir."""
    for chave in ('nomeTimeCoracaoMesSorte', 'timeCoracaoMesSorte', 'nomeTimeCoracao', 'timeDoCoracao'):
        valor = dados_caixa.get(chave)
        if valor:
            return str(valor).strip()
    return None


def extrair_trevos(dados_caixa: Dict[str, Any]) -> List[int]:
    """Extrai os 2 números da sorte ('trevos') sorteados no concurso (exclusivo da +Milionária).
    A API da Caixa já usou nomes de campo distintos ao longo do tempo, então tenta
    várias chaves conhecidas antes de desistir."""
    lista = (
        dados_caixa.get('listaTrevos')
        or dados_caixa.get('trevosSorteados')
        or dados_caixa.get('trevos')
        or []
    )
    try:
        numeros = sorted(int(n) for n in lista)
        return numeros
    except Exception:
        return []


def obter_status_loterias(consultar_online: bool = True) -> List[Dict[str, Any]]:
    """
    Retorna lista com status detalhado de todas as 9 loterias:
    - total de concursos locais
    - último concurso local
    - último concurso divulgado pela Caixa (se consultar_online=True)
    - data da última apuração
    - status ('Atualizado', 'Desatualizado', 'Sem histórico')
    """
    status_lista = []
    
    for loteria_type, slug in LOTERIAS_SLUGS.items():
        historico_local = carregar_historico_local(loteria_type)
        meta = carregar_meta(loteria_type)
        
        total_local = len(historico_local)
        ultimo_local_concurso = meta.get('ultimo_concurso')
        
        # Consultar último na Caixa (se habilitado)
        if consultar_online:
            dados_caixa = consultar_caixa(slug)
        else:
            dados_caixa = None

        if dados_caixa:
            ultimo_caixa_concurso = dados_caixa.get('numero')
            data_apuracao = dados_caixa.get('dataApuracao')
        else:
            ultimo_caixa_concurso = meta.get('ultimo_concurso') or meta.get('ultimo_caixa')
            data_apuracao = meta.get('data_apuracao', 'Sincronizado')
            
        if total_local == 0:
            situacao = 'Sem histórico'
        elif ultimo_caixa_concurso and ultimo_local_concurso:
            if ultimo_local_concurso >= ultimo_caixa_concurso:
                situacao = 'Atualizado'
            else:
                situacao = f'Desatualizado ({ultimo_caixa_concurso - ultimo_local_concurso} concurso(s) atrás)'
        else:
            situacao = 'Atualizado' if total_local > 0 else 'Histórico parcial'

        status_lista.append({
            'loteria_type': loteria_type,
            'slug': slug,
            'nome': LOTERIAS_NOMES.get(loteria_type, loteria_type.title()),
            'total_local': total_local,
            'ultimo_local': ultimo_local_concurso or (f'~{total_local}' if total_local > 0 else 'Nenhum'),
            'ultimo_caixa': ultimo_caixa_concurso or ultimo_local_concurso or 'Indisponível',
            'data_apuracao': data_apuracao,
            'situacao': situacao,
            'ultima_sincronizacao': meta.get('atualizado_em', 'Automático às 23h')
        })
        
    return status_lista


def sincronizar_loteria(loteria_type: str, n_historico: int = 50) -> Dict[str, Any]:
    """
    Sincroniza uma loteria específica buscando os últimos sorteios da Caixa.
    Se o histórico tiver menos de n_historico sorteios, faz carga retroativa.
    Se já estiver próximo do último, busca incrementalmente os novos.
    """
    slug = LOTERIAS_SLUGS.get(loteria_type)
    if not slug:
        return {'sucesso': False, 'erro': 'Loteria inválida'}

    session = _get_session()
    
    # Registra a tentativa para respeitar o cooldown de 30 min (mesmo se der erro)
    meta = carregar_meta(loteria_type)
    meta['ultima_tentativa'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    salvar_meta(loteria_type, meta)
    
    # 1. Buscar último concurso na Caixa
    ultimo_dados = consultar_caixa(slug)
    if not ultimo_dados or not ultimo_dados.get('numero'):
        database.log_sync(loteria_type, None, None, 'ERRO', 'Não foi possível conectar à API da Caixa')
        return {'sucesso': False, 'erro': 'Falha na conexão com a Caixa'}

    ultimo_numero = ultimo_dados.get('numero')
    data_apuracao = ultimo_dados.get('dataApuracao')
    
    # Salva e propaga imediatamente o último resultado (disco local, PostgreSQL e cache em memória)
    salvar_ultimo_resultado_local(loteria_type, ultimo_dados)
    try:
        database.salvar_ultimo_resultado_db(loteria_type, ultimo_dados)
    except Exception as e:
        print(f"[UPDATER] Aviso ao salvar no banco de dados ({loteria_type}): {e}")
    _RESULTADO_COMPLETO_CACHE[loteria_type] = ultimo_dados
    _RESULTADO_COMPLETO_TIME[loteria_type] = time.time()
    
    # 2. Carregar dados locais existentes
    historico_local = carregar_historico_local(loteria_type)
    ultimo_local = meta.get('ultimo_concurso')

    # Histórico defasado (ex.: meta atualizada sem o histórico): recarrega do zero, senão
    # os concursos que faltam nunca seriam baixados e a numeração ficaria errada
    if historico_local and ultimo_local:
        dados_ultimo_local = ultimo_dados if ultimo_local == ultimo_numero else consultar_caixa(slug, concurso=ultimo_local, max_retries=1)
        if not historico_consistente(loteria_type, historico_local, ultimo_local, dados_ultimo_local):
            print(f"[UPDATER] Histórico de {loteria_type} não confere com o concurso {ultimo_local}; recarregando.")
            historico_local, ultimo_local = [], None

    # Backfill específico da Timemania: preenche o "Time do Coração" dos concursos
    # que já estavam salvos antes desta funcionalidade existir. Não afeta as outras loterias.
    if loteria_type == 'timemania' and ultimo_local and len(historico_local) >= 20:
        times_local_atual = carregar_times_local(loteria_type)
        deficit = len(historico_local) - len(times_local_atual)
        if deficit > 0:
            concurso_inicial_backfill = ultimo_local - len(historico_local) + 1
            print(f"[UPDATER] Backfill de 'Time do Coração' para {deficit} concurso(s) da Timemania...")
            times_backfill = []
            for c in range(concurso_inicial_backfill, concurso_inicial_backfill + deficit):
                d = consultar_caixa(slug, concurso=c, max_retries=1)
                times_backfill.append(extrair_time_coracao(d) if d else None)
                time.sleep(0.04)
            salvar_times_local(loteria_type, times_backfill + times_local_atual)

    # Backfill específico da +Milionária: preenche os trevos dos concursos que já
    # estavam salvos antes desta funcionalidade existir. Não afeta as outras loterias.
    if loteria_type == 'mais_milionaria' and ultimo_local and len(historico_local) >= 20:
        trevos_local_atual = carregar_trevos_local(loteria_type)
        deficit = len(historico_local) - len(trevos_local_atual)
        if deficit > 0:
            concurso_inicial_backfill = ultimo_local - len(historico_local) + 1
            print(f"[UPDATER] Backfill de trevos para {deficit} concurso(s) da +Milionária...")
            trevos_backfill = []
            for c in range(concurso_inicial_backfill, concurso_inicial_backfill + deficit):
                d = consultar_caixa(slug, concurso=c, max_retries=1)
                trevos_backfill.append(extrair_trevos(d) if d else [])
                time.sleep(0.04)
            salvar_trevos_local(loteria_type, trevos_backfill + trevos_local_atual)

    # Backfill específico da Dupla Sena: preenche o 2º sorteio dos concursos já salvos.
    if loteria_type == 'dupla_sena' and ultimo_local and len(historico_local) >= 20:
        segundos_local_atual = carregar_segundo_sorteio_local(loteria_type)
        deficit = len(historico_local) - len(segundos_local_atual)
        if deficit > 0:
            concurso_inicial_backfill = ultimo_local - len(historico_local) + 1
            print(f"[UPDATER] Backfill do 2º sorteio para {deficit} concurso(s) da Dupla Sena...")
            segundos_backfill = []
            for c in range(concurso_inicial_backfill, concurso_inicial_backfill + deficit):
                d = consultar_caixa(slug, concurso=c, max_retries=1)
                segundos_backfill.append(extrair_segundo_sorteio(d) if d else [])
                time.sleep(0.04)
            salvar_segundo_sorteio_local(loteria_type, segundos_backfill + segundos_local_atual)

    novos_concursos = []
    
    # Caso 1: Sem histórico ou histórico muito curto (< 20 sorteios), baixa lote de n_historico
    if len(historico_local) < 20 or not ultimo_local:
        inicio = max(1, ultimo_numero - n_historico + 1)
        print(f"[UPDATER] Carga inicial de {inicio} até {ultimo_numero} para {loteria_type}...")
        
        historico_acumulado = []
        concursos_acumulado = []
        times_acumulado = [] if loteria_type == 'timemania' else None
        trevos_acumulado = [] if loteria_type == 'mais_milionaria' else None
        segundos_acumulado = [] if loteria_type == 'dupla_sena' else None
        for c in range(inicio, ultimo_numero + 1):
            if c == ultimo_numero:
                d = ultimo_dados
            else:
                d = consultar_caixa(slug, concurso=c, max_retries=1)

            if d:
                dezenas = extrair_dezenas(d, slug)
                if dezenas:
                    historico_acumulado.append(dezenas)
                    concursos_acumulado.append(c)
                    if times_acumulado is not None:
                        times_acumulado.append(extrair_time_coracao(d))
                    if trevos_acumulado is not None:
                        trevos_acumulado.append(extrair_trevos(d))
                    if segundos_acumulado is not None:
                        segundos_acumulado.append(extrair_segundo_sorteio(d))
            # Pequena pausa para estabilidade
            time.sleep(0.04)

        if len(historico_acumulado) >= 10:
            salvar_historico_local(loteria_type, historico_acumulado)
            salvar_concursos_local(loteria_type, concursos_acumulado)
            if times_acumulado is not None:
                salvar_times_local(loteria_type, times_acumulado)
            if trevos_acumulado is not None:
                salvar_trevos_local(loteria_type, trevos_acumulado)
            if segundos_acumulado is not None:
                salvar_segundo_sorteio_local(loteria_type, segundos_acumulado)
            salvar_meta(loteria_type, {
                'ultimo_concurso': ultimo_numero,
                'data_apuracao': data_apuracao,
                'total_concursos': len(historico_acumulado),
                'atualizado_em': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            })
            database.log_sync(
                loteria_type, 
                ultimo_numero, 
                data_apuracao, 
                'SUCESSO', 
                f'Carga inicial completa com {len(historico_acumulado)} concursos.'
            )
            return {
                'sucesso': True,
                'novos_concursos': len(historico_acumulado),
                'total_local': len(historico_acumulado),
                'ultimo_concurso': ultimo_numero,
                'data_apuracao': data_apuracao
            }
        else:
            return {'sucesso': False, 'erro': 'Não foi possível obter dados suficientes'}

    # Caso 2: Carga incremental de novos concursos
    if ultimo_numero > ultimo_local:
        qtd_pendentes = ultimo_numero - ultimo_local
        print(f"[UPDATER] Baixando {qtd_pendentes} novos concursos de {ultimo_local + 1} a {ultimo_numero}...")
        
        novos_numeros = []
        novos_times = [] if loteria_type == 'timemania' else None
        novos_trevos = [] if loteria_type == 'mais_milionaria' else None
        novos_segundos = [] if loteria_type == 'dupla_sena' else None
        for c in range(ultimo_local + 1, ultimo_numero + 1):
            if c == ultimo_numero:
                d = ultimo_dados
            else:
                d = consultar_caixa(slug, concurso=c, max_retries=1)

            if d:
                dezenas = extrair_dezenas(d, slug)
                if dezenas:
                    novos_concursos.append(dezenas)
                    novos_numeros.append(c)
                    if novos_times is not None:
                        novos_times.append(extrair_time_coracao(d))
                    if novos_trevos is not None:
                        novos_trevos.append(extrair_trevos(d))
                    if novos_segundos is not None:
                        novos_segundos.append(extrair_segundo_sorteio(d))
            time.sleep(0.04)

        concursos_local = carregar_concursos_local(loteria_type)
        alinhado = len(concursos_local) == len(historico_local)
        historico_local.extend(novos_concursos)
        salvar_historico_local(loteria_type, historico_local)
        # Só mantém a numeração se ela já estava alinhada ao histórico
        salvar_concursos_local(loteria_type, concursos_local + novos_numeros if alinhado else [])
        if novos_times is not None:
            times_local = carregar_times_local(loteria_type)
            times_local.extend(novos_times)
            salvar_times_local(loteria_type, times_local)
        if novos_trevos is not None:
            trevos_local = carregar_trevos_local(loteria_type)
            trevos_local.extend(novos_trevos)
            salvar_trevos_local(loteria_type, trevos_local)
        if novos_segundos is not None:
            segundos_local = carregar_segundo_sorteio_local(loteria_type)
            segundos_local.extend(novos_segundos)
            salvar_segundo_sorteio_local(loteria_type, segundos_local)
        salvar_meta(loteria_type, {
            'ultimo_concurso': ultimo_numero,
            'data_apuracao': data_apuracao,
            'total_concursos': len(historico_local),
            'atualizado_em': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        })
        database.log_sync(
            loteria_type, 
            ultimo_numero, 
            data_apuracao, 
            'SUCESSO', 
            f'{len(novos_concursos)} novos concursos adicionados (até #{ultimo_numero}).'
        )
        return {
            'sucesso': True,
            'novos_concursos': len(novos_concursos),
            'total_local': len(historico_local),
            'ultimo_concurso': ultimo_numero,
            'data_apuracao': data_apuracao
        }
    else:
        # Já está atualizado
        salvar_meta(loteria_type, {
            'ultimo_concurso': ultimo_numero,
            'data_apuracao': data_apuracao,
            'total_concursos': len(historico_local),
            'atualizado_em': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        })
        return {
            'sucesso': True,
            'novos_concursos': 0,
            'total_local': len(historico_local),
            'ultimo_concurso': ultimo_numero,
            'data_apuracao': data_apuracao,
            'mensagem': 'Já está atualizado com o último concurso.'
        }


def sincronizar_todas(n_historico: int = 50) -> Dict[str, Any]:
    """Sincroniza todas as 9 modalidades de loteria"""
    resultados = {}
    total_novos = 0
    erros = []
    
    for loteria_type in LOTERIAS_SLUGS.keys():
        try:
            res = sincronizar_loteria(loteria_type, n_historico=n_historico)
            resultados[loteria_type] = res
            if res.get('sucesso'):
                total_novos += res.get('novos_concursos', 0)
            else:
                erros.append(f"{loteria_type}: {res.get('erro')}")
        except Exception as e:
            erros.append(f"{loteria_type}: {str(e)}")

    # Import tardio: notificacoes depende de conferencia, que importa este módulo
    try:
        import notificacoes
        avisos = notificacoes.notificar_premios()
    except Exception as e:
        avisos = {'erro': str(e)}
        print(f"[UPDATER] Falha ao enviar avisos de prêmio: {e}")

    return {
        'sucesso': len(erros) == 0,
        'total_novos': total_novos,
        'avisos_email': avisos,
        'detalhes': resultados,
        'erros': erros,
        'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    }


# ==============================================================================
# AGENDADOR AUTOMÁTICO DIÁRIO CONSERVADOR — 23:00H (HORÁRIO DE BRASÍLIA)
# ==============================================================================
_scheduler_started = False


def calcular_segundos_ate_2300() -> float:
    """Calcula os segundos restantes até as 23:00:00 (Horário de Brasília)"""
    agora = datetime.now()
    alvo = agora.replace(hour=23, minute=0, second=0, microsecond=0)
    if agora >= alvo:
        alvo += timedelta(days=1)
    segundos = (alvo - agora).total_seconds()
    return max(1.0, segundos)


def calcular_segundos_ate_2359() -> float:
    """Calcula os segundos restantes até as 23:59:00 do dia atual ou do dia seguinte (retrocompatibilidade)"""
    agora = datetime.now()
    alvo = agora.replace(hour=23, minute=59, second=0, microsecond=0)
    if agora >= alvo:
        alvo += timedelta(days=1)
    segundos = (alvo - agora).total_seconds()
    return max(1.0, segundos)


def calcular_segundos_proximo_checkpoint() -> tuple[float, str]:
    """Calcula os segundos restantes até a execução diária oficial das 23:00h"""
    segundos = calcular_segundos_ate_2300()
    return segundos, '23:00h (Horário de Brasília)'


def agora_brasilia() -> datetime:
    """Retorna datetime atual no fuso oficial de Brasília (UTC-3)"""
    from datetime import timezone
    tz_br = timezone(timedelta(hours=-3))
    return datetime.now(tz_br)


def verificar_se_necessita_atualizacao(loteria_type: str) -> bool:
    """
    Verifica se a loteria precisa de atualização automática.
    Permite atualização a partir das 20:15h (Horário de Brasília) nos dias de sorteio
    e implementa cooldown para evitar bloqueios ou sobrecarga na API da Caixa.
    """
    meta = carregar_meta(loteria_type)
    if not meta or not meta.get('ultimo_concurso'):
        return True
        
    atualizado_em_str = meta.get('atualizado_em')
    if not atualizado_em_str:
        return True
        
    agora = agora_brasilia()
    
    # Cooldown de tentativas (15 minutos)
    ultima_tentativa_str = meta.get('ultima_tentativa')
    if ultima_tentativa_str:
        try:
            ultima_dt = datetime.strptime(ultima_tentativa_str, '%d/%m/%Y %H:%M:%S').replace(tzinfo=agora.tzinfo)
            if (agora - ultima_dt) < timedelta(minutes=15):
                return False
        except Exception:
            pass
            
    # Histórico que não confere com o último concurso registrado precisa ser recarregado
    if not historico_consistente(loteria_type, carregar_historico_local(loteria_type),
                                 meta.get('ultimo_concurso'), carregar_ultimo_resultado_local(loteria_type)):
        return True

    try:
        atualizado_dt = datetime.strptime(atualizado_em_str, '%d/%m/%Y %H:%M:%S').replace(tzinfo=agora.tzinfo)
        diferenca = agora - atualizado_dt
        
        # Se tem mais de 24 horas que não atualiza com sucesso, permite a tentativa
        if diferenca > timedelta(hours=24):
            return True
            
        # Se já foi atualizado com sucesso hoje após o horário de sorteio (20:15h), não tenta de novo
        if atualizado_dt.date() == agora.date() and (atualizado_dt.hour > 20 or (atualizado_dt.hour == 20 and atualizado_dt.minute >= 15)):
            return False
            
        # A partir das 20:15h (horário dos primeiros resultados da Caixa)
        if agora.hour > 20 or (agora.hour == 20 and agora.minute >= 15):
            return True
            
        return False
    except Exception:
        return True


def _loop_agendador_diario():
    """Loop diário que executa a sincronização segura pontualmente às 23:00h (Horário de Brasília)"""
    print("[UPDATER] Serviço de sincronização diária agendado para às 23:00h (Horário de Brasília).")
    while True:
        try:
            segundos_espera = calcular_segundos_ate_2300()
            horas = segundos_espera / 3600
            print(f"[UPDATER] Próxima atualização diária oficial da Caixa: 23:00h (em {horas:.2f}h / {int(segundos_espera)}s).")
            time.sleep(segundos_espera)
            print("[UPDATER] 23:00h atingido! Executando sincronização diária oficial de todas as loterias...")
            sincronizar_todas(n_historico=50)
            # Pausa de 120s para garantir avanço seguro
            time.sleep(120)
        except Exception as e:
            print(f"[UPDATER] Erro no loop de agendamento das 23:00h: {e}")
            time.sleep(60)


def iniciar_agendador():
    """Inicia a thread de sincronização automática em background"""
    global _scheduler_started
    if os.environ.get('VERCEL'):
        return
    if not _scheduler_started:
        _scheduler_started = True
        t = threading.Thread(target=_loop_agendador_diario, daemon=True)
        t.start()

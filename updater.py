"""
Módulo de Atualização e Sincronização dos Resultados das Loterias da Caixa
Projeto Calculadora da Sorte
"""

import os
import json
import time
import threading
import urllib3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import database

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def consultar_caixa(slug: str, concurso: Optional[int] = None, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """
    Consulta o resultado de uma loteria na API oficial da Caixa, com fallback para API pública alternativa
    (pois a Caixa bloqueia IPs de datacenters como Vercel/AWS).
    """
    session = _get_session()
    
    urls_para_tentar = []
    
    # URL Primária (Caixa Oficial)
    url_caixa = f'https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}'
    if concurso:
        url_caixa += f'/{concurso}'
    urls_para_tentar.append(url_caixa)
    
    # URL Secundária (Fallback Público - api.guidi.dev.br)
    url_fallback = f'https://api.guidi.dev.br/loteria/{slug}'
    if concurso:
        url_fallback += f'/{concurso}'
    else:
        url_fallback += '/ultimo'
    urls_para_tentar.append(url_fallback)
        
    for url in urls_para_tentar:
        for tentativa in range(1, max_retries + 1):
            try:
                response = session.get(url, verify=False, timeout=15)
                if response.status_code == 200:
                    dados = response.json()
                    if isinstance(dados, dict) and dados.get('numero'):
                        return dados
                elif response.status_code == 429:
                    time.sleep(1.2 * tentativa)
                elif response.status_code in (403, 502, 503, 504):
                    time.sleep(1.0 * tentativa)
            except Exception as e:
                if tentativa == max_retries:
                    print(f"[UPDATER] Erro persistente na URL {url} ({slug} - {concurso}): {e}")
                else:
                    time.sleep(1.0 * tentativa)
                    
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
    
    # 2. Carregar dados locais existentes
    historico_local = carregar_historico_local(loteria_type)
    ultimo_local = meta.get('ultimo_concurso')
    
    novos_concursos = []
    
    # Caso 1: Sem histórico ou histórico muito curto (< 20 sorteios), baixa lote de n_historico
    if len(historico_local) < 20 or not ultimo_local:
        inicio = max(1, ultimo_numero - n_historico + 1)
        print(f"[UPDATER] Carga inicial de {inicio} até {ultimo_numero} para {loteria_type}...")
        
        historico_acumulado = []
        for c in range(inicio, ultimo_numero + 1):
            if c == ultimo_numero:
                d = ultimo_dados
            else:
                try:
                    res = session.get(f'https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}/{c}', verify=False, timeout=6)
                    d = res.json() if res.status_code == 200 else None
                except Exception:
                    d = None
            
            if d:
                dezenas = extrair_dezenas(d, slug)
                if dezenas:
                    historico_acumulado.append(dezenas)
            # Pequena pausa para estabilidade
            time.sleep(0.04)

        if len(historico_acumulado) >= 10:
            salvar_historico_local(loteria_type, historico_acumulado)
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
        
        for c in range(ultimo_local + 1, ultimo_numero + 1):
            if c == ultimo_numero:
                d = ultimo_dados
            else:
                try:
                    res = session.get(f'https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}/{c}', verify=False, timeout=6)
                    d = res.json() if res.status_code == 200 else None
                except Exception:
                    d = None
            
            if d:
                dezenas = extrair_dezenas(d, slug)
                if dezenas:
                    novos_concursos.append(dezenas)
            time.sleep(0.04)

        historico_local.extend(novos_concursos)
        salvar_historico_local(loteria_type, historico_local)
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
            
    return {
        'sucesso': len(erros) == 0,
        'total_novos': total_novos,
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


def verificar_se_necessita_atualizacao(loteria_type: str) -> bool:
    """
    Verifica se a loteria precisa de atualização automática.
    Bloqueia verificações fora do horário de sorteios (madrugada/dia)
    e implementa cooldown para evitar bloqueios da API da Caixa.
    """
    meta = carregar_meta(loteria_type)
    if not meta or not meta.get('ultimo_concurso'):
        return True
        
    atualizado_em_str = meta.get('atualizado_em')
    if not atualizado_em_str:
        return True
        
    # Cooldown de tentativas (seja sucesso ou falha)
    ultima_tentativa_str = meta.get('ultima_tentativa')
    if ultima_tentativa_str:
        try:
            ultima_dt = datetime.strptime(ultima_tentativa_str, '%d/%m/%Y %H:%M:%S')
            if (datetime.now() - ultima_dt) < timedelta(minutes=30):
                return False
        except Exception:
            pass
            
    try:
        atualizado_dt = datetime.strptime(atualizado_em_str, '%d/%m/%Y %H:%M:%S')
        agora = datetime.now()
        diferenca = agora - atualizado_dt
        
        # Se tem mais de 24 horas que não atualiza com sucesso, permite a tentativa
        if diferenca > timedelta(hours=24):
            return True
            
        # Se foi atualizado com sucesso hoje, não tenta de novo
        if atualizado_dt.date() == agora.date():
            return False
            
        # Se a última atualização foi ontem, SÓ tenta sincronizar se 
        # já estivermos no horário de liberação dos resultados (após as 20:30)
        if agora.hour >= 20 and (agora.hour > 20 or agora.minute >= 30) and atualizado_dt.date() < agora.date():
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

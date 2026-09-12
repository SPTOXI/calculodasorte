"""
Módulo de Sincronização e Persistência em Nuvem (Vercel Blob Storage)
Projeto Calculadora da Sorte

Garante a persistência contínua do banco de dados SQLite entre instâncias
serverless (AWS Lambda / Vercel Functions), evitando perda de usuários e dados cadastrais.
Implementação estritamente compatível com o protocolo oficial REST da Vercel (@vercel/blob v12).
"""

import os
import sys
import time
import logging
import urllib.parse
from typing import Optional, Dict, Any

logger = logging.getLogger('blob_storage')

_CACHED_TOKEN = None
_CACHED_BLOB_URLS: Dict[str, str] = {}
_LAST_UPLOAD_TIME: Optional[float] = None
_LAST_DOWNLOAD_TIME: Optional[float] = None
_LAST_STORAGE_ERROR: Optional[str] = None


def get_blob_token() -> Optional[str]:
    """Obtém o token de leitura e escrita do Vercel Blob a partir do ambiente ou arquivos locais"""
    global _CACHED_TOKEN
    if _CACHED_TOKEN:
        return _CACHED_TOKEN

    # 1. Variáveis de ambiente padrão da Vercel
    for key in ('BLOB_READ_WRITE_TOKEN', 'VERCEL_BLOB_READ_WRITE_TOKEN'):
        token = os.environ.get(key)
        if token and token.strip():
            _CACHED_TOKEN = token.strip()
            return _CACHED_TOKEN

    # 2. Varredura por qualquer variável com formato de token Vercel Blob
    for k, v in os.environ.items():
        if ('BLOB' in k.upper() or k.upper().endswith('_READ_WRITE_TOKEN')) and isinstance(v, str):
            if v.strip().startswith('vercel_blob_rw_'):
                _CACHED_TOKEN = v.strip()
                return _CACHED_TOKEN

    # 3. Fallback para .env e .env.local em desenvolvimento local
    env_local_paths = [
        os.path.join(os.path.dirname(__file__), '.env.local'),
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.getcwd(), '.env.local'),
        os.path.join(os.getcwd(), '.env')
    ]
    for p in env_local_paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('#') or not line:
                            continue
                        if line.startswith('BLOB_READ_WRITE_TOKEN=') or line.startswith('VERCEL_BLOB_READ_WRITE_TOKEN='):
                            val = line.split('=', 1)[1].strip(' "\'')
                            if val:
                                _CACHED_TOKEN = val
                                return _CACHED_TOKEN
            except Exception:
                pass

    return None


def get_store_id(token: Optional[str] = None) -> str:
    """Extrai o identificador único da store a partir do token da Vercel"""
    t = token or get_blob_token() or ""
    parts = t.split('_')
    # Formato padrão: vercel_blob_rw_<storeId>_<secret>
    if len(parts) >= 4 and parts[0] == 'vercel' and parts[1] == 'blob':
        return parts[3]
    return ""


def get_api_url() -> str:
    """Retorna a URL base da API REST do Vercel Blob"""
    base = os.environ.get('VERCEL_BLOB_API_URL') or os.environ.get('NEXT_PUBLIC_VERCEL_BLOB_API_URL')
    if base and base.strip():
        return base.strip().rstrip('/')
    return "https://vercel.com/api/blob"


def upload_blob(src_path: str, blob_name: str, timeout: float = 10.0) -> bool:
    """
    Envia um arquivo local (ex: /tmp/data/database.db) para o Vercel Blob Storage.
    Utiliza o protocolo REST oficial da Vercel com substituição atômica e sufixo randômico desativado.
    """
    global _LAST_UPLOAD_TIME, _LAST_STORAGE_ERROR
    token = get_blob_token()
    if not token:
        _LAST_STORAGE_ERROR = "Token BLOB_READ_WRITE_TOKEN não configurado no ambiente."
        return False

    if not os.path.exists(src_path) or os.path.getsize(src_path) == 0:
        _LAST_STORAGE_ERROR = f"Arquivo de origem {src_path} não existe ou está vazio."
        return False

    import requests

    store_id = get_store_id(token)
    api_url = get_api_url()
    content_type = 'application/x-sqlite3' if src_path.endswith('.db') else 'application/octet-stream'

    headers = {
        'authorization': f'Bearer {token}',
        'x-api-version': '12',
        'x-vercel-blob-access': 'public',
        'x-add-random-suffix': '0',
        'x-allow-overwrite': '1',
        'content-type': content_type
    }
    if store_id:
        headers['x-vercel-blob-store-id'] = store_id

    # Endpoint oficial de upload: /?pathname={blob_name}
    encoded_name = urllib.parse.quote(blob_name)
    url = f"{api_url}/?pathname={encoded_name}"

    try:
        with open(src_path, 'rb') as f:
            data = f.read()

        headers['x-content-length'] = str(len(data))
        res = requests.put(url, data=data, headers=headers, timeout=timeout)

        if res.status_code == 200:
            _LAST_UPLOAD_TIME = time.time()
            _LAST_STORAGE_ERROR = None
            try:
                res_data = res.json()
                dl_url = res_data.get('downloadUrl') or res_data.get('url')
                if dl_url:
                    _CACHED_BLOB_URLS[blob_name] = dl_url
            except Exception:
                pass
            print(f"[BLOB] Base {blob_name} enviada para nuvem com sucesso ({len(data)} bytes).")
            return True
        else:
            _LAST_STORAGE_ERROR = f"HTTP {res.status_code}: {res.text[:150]}"
            print(f"[BLOB] Erro ao enviar {blob_name}: {_LAST_STORAGE_ERROR}")
            return False
    except Exception as e:
        _LAST_STORAGE_ERROR = f"Exceção no upload: {str(e)}"
        print(f"[BLOB] Exceção ao enviar {blob_name}: {e}")
        return False


def get_blob_url(blob_name: str, timeout: float = 6.0) -> Optional[str]:
    """
    Localiza a URL de download do blob através da API de listagem da Vercel ou do cache local.
    """
    global _LAST_STORAGE_ERROR
    # 1. Verifica cache em memória
    if blob_name in _CACHED_BLOB_URLS:
        return _CACHED_BLOB_URLS[blob_name]

    token = get_blob_token()
    if not token:
        return None

    import requests

    store_id = get_store_id(token)
    api_url = get_api_url()
    encoded_prefix = urllib.parse.quote(blob_name)
    list_url = f"{api_url}?prefix={encoded_prefix}&limit=5"

    headers = {
        'authorization': f'Bearer {token}',
        'x-api-version': '12'
    }
    if store_id:
        headers['x-vercel-blob-store-id'] = store_id

    try:
        res = requests.get(list_url, headers=headers, timeout=timeout)
        if res.status_code == 200:
            data = res.json()
            blobs = data.get('blobs', [])
            for b in blobs:
                if b.get('pathname') == blob_name or b.get('pathname', '').endswith(blob_name):
                    dl_url = b.get('downloadUrl') or b.get('url')
                    if dl_url:
                        _CACHED_BLOB_URLS[blob_name] = dl_url
                        return dl_url
        else:
            _LAST_STORAGE_ERROR = f"List API HTTP {res.status_code}: {res.text[:100]}"
    except Exception as e:
        _LAST_STORAGE_ERROR = f"Exceção ao listar blob: {str(e)}"

    # Fallback determinístico caso o storeId seja conhecido
    if store_id:
        predictable_url = f"https://{store_id}.public.blob.vercel-storage.com/{blob_name}"
        return predictable_url

    return None


def download_blob(blob_name: str, dest_path: str, timeout: float = 10.0) -> bool:
    """
    Baixa o arquivo do Vercel Blob para o caminho local (ex: /tmp/data/database.db).
    Garante gravação atômica para integridade absoluta do arquivo SQLite.
    """
    global _LAST_DOWNLOAD_TIME, _LAST_STORAGE_ERROR
    token = get_blob_token()
    if not token:
        _LAST_STORAGE_ERROR = "Token BLOB_READ_WRITE_TOKEN não configurado no ambiente."
        return False

    dl_url = get_blob_url(blob_name, timeout=timeout)
    if not dl_url:
        _LAST_STORAGE_ERROR = f"URL de download para {blob_name} não foi encontrada na nuvem."
        return False

    import requests

    headers = {
        'authorization': f'Bearer {token}'
    }

    try:
        res = requests.get(dl_url, headers=headers, timeout=timeout)
        if res.status_code == 200 and len(res.content) > 0:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            temp_path = f"{dest_path}.tmp_{os.getpid()}"
            with open(temp_path, 'wb') as f:
                f.write(res.content)
            # Substituição atômica no filesystem
            os.replace(temp_path, dest_path)
            _LAST_DOWNLOAD_TIME = time.time()
            _LAST_STORAGE_ERROR = None
            print(f"[BLOB] Base {blob_name} baixada da nuvem com sucesso ({len(res.content)} bytes).")
            return True
        elif res.status_code == 404:
            _LAST_STORAGE_ERROR = f"Arquivo {blob_name} ainda não existe no bucket da nuvem (404)."
            return False
        else:
            _LAST_STORAGE_ERROR = f"HTTP {res.status_code} ao baixar: {res.text[:100]}"
            print(f"[BLOB] Erro ao baixar {blob_name}: {_LAST_STORAGE_ERROR}")
            return False
    except Exception as e:
        _LAST_STORAGE_ERROR = f"Exceção ao baixar blob: {str(e)}"
        print(f"[BLOB] Exceção ao baixar {blob_name}: {e}")
        return False


def get_storage_status() -> Dict[str, Any]:
    """
    Retorna diagnóstico estruturado da persistência em nuvem para exibição no painel admin
    """
    token = get_blob_token()
    configured = bool(token)
    is_vercel = bool(os.environ.get('VERCEL'))
    store_id = get_store_id(token) if configured else ""

    if configured:
        backend_name = "Vercel Blob Storage"
        status_code = "conectado"
        mensagem = f"Conectado à nuvem (Store ID: {store_id[:6]}...)" if store_id else "Conectado ao Vercel Blob Storage."
    elif is_vercel:
        backend_name = "Vercel Efêmero (Alerta)"
        status_code = "aviso_vercel"
        mensagem = (
            "Atenção: BLOB_READ_WRITE_TOKEN não configurado no painel da Vercel. "
            "Os cadastros podem ser perdidos entre diferentes contêineres e dispositivos. "
            "Crie um Blob Store no menu Storage da Vercel para ativar a sincronização contínua."
        )
    else:
        backend_name = "SQLite Local (Desenvolvimento)"
        status_code = "local"
        mensagem = "Ambiente local. Banco persistido no disco local."

    return {
        'configured': configured,
        'is_vercel': is_vercel,
        'backend': backend_name,
        'status': status_code,
        'store_id': store_id,
        'last_upload': _LAST_UPLOAD_TIME,
        'last_download': _LAST_DOWNLOAD_TIME,
        'last_error': _LAST_STORAGE_ERROR,
        'mensagem': mensagem
    }


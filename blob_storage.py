"""
Módulo de Sincronização e Persistência em Nuvem (Vercel Blob Storage)
Projeto Calculadora da Sorte

Garante a persistência contínua do banco de dados SQLite entre instâncias
serverless (AWS Lambda / Vercel Functions), evitando perda de usuários e dados cadastrais.
"""

import os
import sys
import time
import logging
from typing import Optional

logger = logging.getLogger('blob_storage')

_CACHED_TOKEN = None

def get_blob_token() -> Optional[str]:
    """Obtém o token de leitura e escrita do Vercel Blob"""
    global _CACHED_TOKEN
    if _CACHED_TOKEN:
        return _CACHED_TOKEN

    token = os.environ.get('BLOB_READ_WRITE_TOKEN')
    if token:
        _CACHED_TOKEN = token.strip()
        return _CACHED_TOKEN

    # Fallback para .env.local em desenvolvimento local
    env_local_paths = [
        os.path.join(os.path.dirname(__file__), '.env.local'),
        os.path.join(os.getcwd(), '.env.local')
    ]
    for p in env_local_paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('BLOB_READ_WRITE_TOKEN='):
                            val = line.split('=', 1)[1].strip(' "\'')
                            if val:
                                _CACHED_TOKEN = val
                                return _CACHED_TOKEN
            except Exception:
                pass

    return None


def download_blob(blob_name: str, dest_path: str, timeout: float = 5.0) -> bool:
    """
    Baixa um arquivo do Vercel Blob para o caminho local (ex: /tmp/data/database.db).
    Retorna True em caso de sucesso.
    """
    token = get_blob_token()
    if not token:
        return False

    import requests

    headers = {
        'authorization': f'Bearer {token}',
        'x-api-version': '7'
    }

    url = f'https://blob.vercel-storage.com/{blob_name}'
    try:
        res = requests.get(url, headers=headers, timeout=timeout)
        if res.status_code == 200 and len(res.content) > 0:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            temp_path = f"{dest_path}.tmp_{os.getpid()}"
            with open(temp_path, 'wb') as f:
                f.write(res.content)
            # Substituição atômica no filesystem
            os.replace(temp_path, dest_path)
            print(f"[BLOB] Base {blob_name} baixada com sucesso ({len(res.content)} bytes).")
            return True
        elif res.status_code == 404:
            # Arquivo ainda não existe no bucket
            return False
        else:
            print(f"[BLOB] Erro ao baixar {blob_name}: HTTP {res.status_code} - {res.text[:100]}")
            return False
    except Exception as e:
        print(f"[BLOB] Exceção ao baixar {blob_name}: {e}")
        return False


def upload_blob(src_path: str, blob_name: str, timeout: float = 6.0) -> bool:
    """
    Envia um arquivo local (ex: /tmp/data/database.db) para o Vercel Blob.
    Garante gravação privada, atômica e substituição imediata da versão anterior.
    """
    token = get_blob_token()
    if not token:
        return False

    if not os.path.exists(src_path) or os.path.getsize(src_path) == 0:
        return False

    import requests

    content_type = 'application/x-sqlite3' if src_path.endswith('.db') else 'application/octet-stream'

    headers = {
        'authorization': f'Bearer {token}',
        'x-api-version': '7',
        'x-vercel-blob-access': 'private',
        'x-add-random-suffix': '0',
        'x-allow-overwrite': '1',
        'content-type': content_type
    }

    url = f'https://blob.vercel-storage.com/{blob_name}'
    try:
        with open(src_path, 'rb') as f:
            data = f.read()

        res = requests.put(url, data=data, headers=headers, timeout=timeout)
        if res.status_code == 200:
            print(f"[BLOB] Base {blob_name} sincronizada na nuvem com sucesso ({len(data)} bytes).")
            return True
        else:
            print(f"[BLOB] Erro ao enviar {blob_name}: HTTP {res.status_code} - {res.text[:100]}")
            return False
    except Exception as e:
        print(f"[BLOB] Exceção ao enviar {blob_name}: {e}")
        return False

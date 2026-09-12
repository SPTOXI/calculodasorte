"""
Teste de Integração de Persistência e Sincronização entre Instâncias Serverless (Mobile vs Desktop)
Projeto Calculadora da Sorte
"""

import os
import shutil
import tempfile
import unittest
import http.server
import threading
import json
import urllib.parse
from werkzeug.security import check_password_hash

import blob_storage
import database


class MockVercelBlobServer:
    def __init__(self):
        self.store = {}
        self.server = http.server.HTTPServer(('127.0.0.1', 0), self._make_handler())
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _make_handler(self):
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_PUT(self):
                parsed = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed.query)
                pathname = qs.get('pathname', [''])[0]
                length = int(self.headers.get('content-length', 0))
                body = self.rfile.read(length)
                outer.store[pathname] = body

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                resp = {
                    'url': f'http://127.0.0.1:{outer.port}/blobs/{pathname}',
                    'downloadUrl': f'http://127.0.0.1:{outer.port}/blobs/{pathname}?download=1',
                    'pathname': pathname,
                    'contentType': 'application/x-sqlite3',
                    'size': len(body)
                }
                self.wfile.write(json.dumps(resp).encode('utf-8'))

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path.startswith('/blobs/'):
                    name = parsed.path.replace('/blobs/', '')
                    if name in outer.store:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/octet-stream')
                        self.end_headers()
                        self.wfile.write(outer.store[name])
                    else:
                        self.send_response(404)
                        self.end_headers()
                elif parsed.path == '/' or parsed.path == '':
                    qs = urllib.parse.parse_qs(parsed.query)
                    prefix = qs.get('prefix', [''])[0]
                    blobs = []
                    for k, v in outer.store.items():
                        if k.startswith(prefix):
                            blobs.append({
                                'url': f'http://127.0.0.1:{outer.port}/blobs/{k}',
                                'downloadUrl': f'http://127.0.0.1:{outer.port}/blobs/{k}?download=1',
                                'pathname': k,
                                'size': len(v)
                            })
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'blobs': blobs, 'hasMore': False}).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()

        return Handler

    def stop(self):
        self.server.shutdown()


class TestCrossDevicePersistence(unittest.TestCase):

    def setUp(self):
        self.mock_server = MockVercelBlobServer()
        self.orig_data_dir = database.DATA_DIR
        self.orig_db_path = database.DB_PATH

        self.test_token = 'vercel_blob_rw_cloudsync_testsecret99'
        os.environ['BLOB_READ_WRITE_TOKEN'] = self.test_token
        os.environ['VERCEL_BLOB_API_URL'] = f'http://127.0.0.1:{self.mock_server.port}'
        blob_storage._CACHED_TOKEN = self.test_token
        blob_storage._CACHED_BLOB_URLS.clear()

        # Configurar diretórios temporários separados para Container A (Mobile) e Container B (Desktop)
        self.mobile_dir = tempfile.mkdtemp(prefix='container_mobile_')
        self.desktop_dir = tempfile.mkdtemp(prefix='container_desktop_')

    def tearDown(self):
        self.mock_server.stop()
        database.DATA_DIR = self.orig_data_dir
        database.DB_PATH = self.orig_db_path
        os.environ.pop('BLOB_READ_WRITE_TOKEN', None)
        os.environ.pop('VERCEL_BLOB_API_URL', None)
        blob_storage._CACHED_TOKEN = None
        blob_storage._CACHED_BLOB_URLS.clear()
        shutil.rmtree(self.mobile_dir, ignore_errors=True)
        shutil.rmtree(self.desktop_dir, ignore_errors=True)

    def test_mobile_registration_persists_to_desktop(self):
        """
        Cenário real relatado pelo usuário:
        1. Usuário acessa pelo mobile (Contêiner A), cadastra com e-mail misto e espaços (Carlos.Apostador@Email.com )
        2. Contêiner A persiste localmente e sincroniza com o Vercel Blob
        3. Usuário acessa pelo desktop (Contêiner B, que nasce sem esse usuário localmente)
        4. Contêiner B busca usuário por e-mail, sincroniza da nuvem e autentica com sucesso
        """
        # =========================================================================
        # PASSO 1: SIMULAR INSTÂNCIA MOBILE (Contêiner A)
        # =========================================================================
        database.DATA_DIR = self.mobile_dir
        database.DB_PATH = os.path.join(self.mobile_dir, 'database.db')
        database.init_db()

        mobile_email_input = "  Carlos.Apostador@Email.com  "
        mobile_password = "MinhaSenha123"
        mobile_name = "Carlos Apostador Mobile"

        created_user = database.create_user(
            email=mobile_email_input,
            password=mobile_password,
            name=mobile_name,
            role='user',
            plan='free',
            credits=1
        )

        self.assertIsNotNone(created_user)
        self.assertEqual(created_user['email'], 'carlos.apostador@email.com')
        self.assertEqual(created_user['name'], mobile_name)
        self.assertEqual(created_user['credits'], 1)

        # Verificar se o Vercel Blob recebeu a versão atualizada
        self.assertIn('database.db', self.mock_server.store)
        cloud_bytes = self.mock_server.store['database.db']
        self.assertGreater(len(cloud_bytes), 0)

        # =========================================================================
        # PASSO 2: SIMULAR INSTÂNCIA DESKTOP (Contêiner B com filesystem efêmero)
        # =========================================================================
        database.DATA_DIR = self.desktop_dir
        database.DB_PATH = os.path.join(self.desktop_dir, 'database.db')
        
        # O Contêiner B inicializa apenas com o banco inicial limpo
        database.init_db()

        # O usuário entra no desktop e digita seu e-mail em minúsculas
        desktop_login_email = "carlos.apostador@email.com"

        # get_user_by_email deve detectar ausência local e acionar sync_db_from_cloud(force=True)
        desktop_user = database.get_user_by_email(desktop_login_email)

        self.assertIsNotNone(
            desktop_user, 
            "O usuário cadastrado no mobile DEVE ser localizado no desktop após sincronização da nuvem!"
        )
        self.assertEqual(desktop_user['email'], 'carlos.apostador@email.com')
        self.assertEqual(desktop_user['name'], mobile_name)
        self.assertTrue(check_password_hash(desktop_user['password_hash'], mobile_password))

        # Verificar se o painel administrativo no desktop lista o usuário
        all_users = database.get_all_users()
        emails_list = [u['email'] for u in all_users]
        self.assertIn('carlos.apostador@email.com', emails_list)

    def test_case_insensitive_and_whitespace_login(self):
        """Valida busca com maiúsculas/minúsculas divergentes entre mobile e desktop"""
        database.DATA_DIR = self.mobile_dir
        database.DB_PATH = os.path.join(self.mobile_dir, 'database.db')
        database.init_db()

        database.create_user(
            email="maria.sorte@gmail.com",
            password="senha_secreta",
            name="Maria Sorte"
        )

        # Busca com maiúsculas no desktop
        u1 = database.get_user_by_email("MARIA.SORTE@GMAIL.COM")
        self.assertIsNotNone(u1)
        self.assertEqual(u1['email'], "maria.sorte@gmail.com")

        # Busca com espaços acidentais
        u2 = database.get_user_by_email("   Maria.Sorte@gmail.com  ")
        self.assertIsNotNone(u2)
        self.assertEqual(u2['email'], "maria.sorte@gmail.com")


if __name__ == '__main__':
    unittest.main()

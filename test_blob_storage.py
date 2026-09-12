"""
Testes Unitários para o Módulo de Persistência em Nuvem (Vercel Blob Storage)
Calculadora da Sorte
"""

import os
import tempfile
import unittest
import http.server
import threading
import json
import urllib.parse
from unittest.mock import patch

import blob_storage


class MockVercelBlobServer:
    def __init__(self):
        self.store = {}
        self.requests_log = []

        handler_cls = self._make_handler()
        self.server = http.server.HTTPServer(('127.0.0.1', 0), handler_cls)
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

                outer.requests_log.append({
                    'method': 'PUT',
                    'path': self.path,
                    'headers': dict(self.headers),
                    'body_len': len(body)
                })

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
                outer.requests_log.append({
                    'method': 'GET',
                    'path': self.path,
                    'headers': dict(self.headers)
                })

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


class TestBlobStorage(unittest.TestCase):

    def setUp(self):
        self.mock_server = MockVercelBlobServer()
        blob_storage._CACHED_TOKEN = None
        blob_storage._CACHED_BLOB_URLS.clear()
        self.test_token = 'vercel_blob_rw_teststore99_secrettoken12345'
        os.environ['BLOB_READ_WRITE_TOKEN'] = self.test_token
        os.environ['VERCEL_BLOB_API_URL'] = f'http://127.0.0.1:{self.mock_server.port}'

    def tearDown(self):
        self.mock_server.stop()
        os.environ.pop('BLOB_READ_WRITE_TOKEN', None)
        os.environ.pop('VERCEL_BLOB_API_URL', None)
        blob_storage._CACHED_TOKEN = None
        blob_storage._CACHED_BLOB_URLS.clear()

    def test_token_and_store_id_parsing(self):
        token = blob_storage.get_blob_token()
        self.assertEqual(token, self.test_token)
        store_id = blob_storage.get_store_id(token)
        self.assertEqual(store_id, 'teststore99')

    def test_upload_and_download_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, 'database.db')
            with open(src_file, 'wb') as f:
                f.write(b'SQLite format 3\x00DummyDatabaseContentForTesting')

            # 1. Upload
            success = blob_storage.upload_blob(src_file, 'database.db')
            self.assertTrue(success, "Upload to mock Vercel Blob should succeed")

            # Verify request made to mock server
            put_reqs = [r for r in self.mock_server.requests_log if r['method'] == 'PUT']
            self.assertEqual(len(put_reqs), 1)
            self.assertEqual(put_reqs[0]['headers'].get('x-api-version'), '12')
            self.assertEqual(put_reqs[0]['headers'].get('x-vercel-blob-access'), 'public')
            self.assertEqual(put_reqs[0]['headers'].get('x-vercel-blob-store-id'), 'teststore99')

            # 2. Download to a different path
            dest_file = os.path.join(tmpdir, 'restored_database.db')
            dl_success = blob_storage.download_blob('database.db', dest_file)
            self.assertTrue(dl_success, "Download from mock Vercel Blob should succeed")
            self.assertTrue(os.path.exists(dest_file))

            with open(dest_file, 'rb') as f:
                content = f.read()
            self.assertEqual(content, b'SQLite format 3\x00DummyDatabaseContentForTesting')

    def test_storage_status_diagnostics(self):
        status = blob_storage.get_storage_status()
        self.assertTrue(status['configured'])
        self.assertEqual(status['backend'], 'Vercel Blob Storage')
        self.assertEqual(status['store_id'], 'teststore99')


if __name__ == '__main__':
    unittest.main()

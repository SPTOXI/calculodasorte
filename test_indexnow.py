#!/usr/bin/env python3
"""
Testes unitários para a funcionalidade de submissão do IndexNow.
Verifica rotas de validação, arquivos de chave, extração de sitemaps,
divisão em lotes e envio à API.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import database
database.init_db = MagicMock()
import app as flask_app
from scripts.submit_indexnow import (
    DEFAULT_KEY,
    DEFAULT_HOST,
    extract_urls_from_xml,
    chunk_list,
    submit_batch_to_indexnow,
)


class TestIndexNow(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.app.test_client()
        self.project_root = Path(__file__).parent

    def test_flask_indexnow_key_route(self):
        # Arrange
        route = f"/{DEFAULT_KEY}.txt"

        # Act
        response = self.client.get(route)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(response.data.decode("utf-8").strip(), DEFAULT_KEY)

    def test_key_files_exist_on_disk(self):
        # Arrange & Act
        root_key_file = self.project_root / f"{DEFAULT_KEY}.txt"
        static_key_file = self.project_root / "static" / f"{DEFAULT_KEY}.txt"

        # Assert
        self.assertTrue(root_key_file.exists(), "Chave deve existir na raiz do projeto")
        self.assertEqual(root_key_file.read_text(encoding="utf-8").strip(), DEFAULT_KEY)

        self.assertTrue(static_key_file.exists(), "Chave deve existir em static/")
        self.assertEqual(static_key_file.read_text(encoding="utf-8").strip(), DEFAULT_KEY)

    def test_package_json_contains_indexnow_submit_script(self):
        # Arrange
        package_json_path = self.project_root / "package.json"

        # Act
        self.assertTrue(package_json_path.exists(), "package.json deve existir na raiz")
        with open(package_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Assert
        scripts = data.get("scripts", {})
        self.assertIn("indexnow:submit", scripts)
        self.assertIn("submit_indexnow.mjs", scripts["indexnow:submit"])

    def test_extract_urls_from_xml(self):
        # Arrange
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://www.calculodasorte.com.br/</loc>
          </url>
          <url>
            <loc>https://www.calculodasorte.com.br/lotofacil</loc>
          </url>
        </urlset>"""

        # Act
        urls = extract_urls_from_xml(sample_xml)

        # Assert
        self.assertEqual(len(urls), 2)
        self.assertIn("https://www.calculodasorte.com.br/", urls)
        self.assertIn("https://www.calculodasorte.com.br/lotofacil", urls)

    def test_chunk_list(self):
        # Arrange
        items = list(range(25))

        # Act
        chunks = chunk_list(items, 10)

        # Assert
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 10)
        self.assertEqual(len(chunks[1]), 10)
        self.assertEqual(len(chunks[2]), 5)

    @patch("urllib.request.urlopen")
    def test_submit_batch_to_indexnow_success_200(self, mock_urlopen):
        # Arrange
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        # Act
        result = submit_batch_to_indexnow(
            endpoint="https://api.indexnow.org/indexnow",
            host=DEFAULT_HOST,
            key=DEFAULT_KEY,
            key_location=f"https://{DEFAULT_HOST}/{DEFAULT_KEY}.txt",
            batch=["https://www.calculodasorte.com.br/"],
            batch_index=1,
            total_batches=1,
        )

        # Assert
        self.assertTrue(result)

    @patch("urllib.request.urlopen")
    def test_submit_batch_to_indexnow_success_202(self, mock_urlopen):
        # Arrange
        mock_resp = MagicMock()
        mock_resp.status = 202
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        # Act
        result = submit_batch_to_indexnow(
            endpoint="https://api.indexnow.org/indexnow",
            host=DEFAULT_HOST,
            key=DEFAULT_KEY,
            key_location=f"https://{DEFAULT_HOST}/{DEFAULT_KEY}.txt",
            batch=["https://www.calculodasorte.com.br/"],
            batch_index=1,
            total_batches=1,
        )

        # Assert
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()

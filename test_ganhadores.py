"""Testes das páginas e do armazenamento de ganhadores por cidade."""

import tempfile
import unittest
from unittest.mock import patch

from app import app
import ganhadores
import updater


class TestExtracao(unittest.TestCase):

    def test_formato_caixa(self):
        dados = {'numero': 10, 'listaMunicipioUFGanhadores': [
            {'municipio': 'SÃO JOSÉ DOS CAMPOS', 'uf': 'SP', 'ganhadores': 2},
            {'municipio': 'CANAL ELETRONICO', 'uf': '--', 'ganhadores': 1}]}
        self.assertEqual(ganhadores.extrair_ganhadores(dados), [
            {'municipio': 'SÃO JOSÉ DOS CAMPOS', 'uf': 'SP', 'ganhadores': 2},
            {'municipio': 'CANAL ELETRONICO', 'uf': '--', 'ganhadores': 1}])

    def test_formato_lista_completa(self):
        dados = {'concurso': 5, 'localGanhadores': [{'municipio': 'Curitiba', 'uf': 'pr', 'ganhadores': 1}]}
        self.assertEqual(ganhadores.extrair_ganhadores(dados),
                         [{'municipio': 'CURITIBA', 'uf': 'PR', 'ganhadores': 1}])

    def test_sem_campo_retorna_none(self):
        self.assertIsNone(ganhadores.extrair_ganhadores({'numero': 1}))

    def test_slug_e_nome(self):
        self.assertEqual(ganhadores.slugify('SÃO JOSÉ DOS CAMPOS'), 'sao-jose-dos-campos')
        self.assertEqual(ganhadores._nome_cidade('SÃO JOSÉ DOS CAMPOS'), 'São José dos Campos')


class TestRegistroEPaginas(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(updater, 'DATA_DIR', self.tmp.name),
                        patch.object(updater, 'ORIGINAL_DATA_DIR', self.tmp.name)]
        for p in self.patches:
            p.start()
        ganhadores._CACHE.clear()
        self.client = app.test_client()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        ganhadores._CACHE.clear()
        self.tmp.cleanup()

    def test_registrar_nao_duplica(self):
        dados = {'numero': 7, 'dataApuracao': '01/01/2026',
                 'listaMunicipioUFGanhadores': [{'municipio': 'RECIFE', 'uf': 'PE', 'ganhadores': 1}]}
        self.assertTrue(ganhadores.registrar('quina', dados))
        self.assertFalse(ganhadores.registrar('quina', dados))
        self.assertEqual(ganhadores.agregados('quina')['ufs']['PE']['ganhadores'], 1)

    def test_paginas(self):
        ganhadores.registrar('quina', {'numero': 7, 'dataApuracao': '01/01/2026',
                                       'listaMunicipioUFGanhadores': [{'municipio': 'RECIFE', 'uf': 'PE', 'ganhadores': 2}]})
        self.assertEqual(self.client.get('/ganhadores/quina').status_code, 200)
        self.assertEqual(self.client.get('/ganhadores/quina/pe').status_code, 200)
        r = self.client.get('/ganhadores/quina/pe/recife')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Recife (PE) teve 2 ganhadores', r.get_data(as_text=True))
        self.assertEqual(self.client.get('/ganhadores/quina/sp').status_code, 404)
        self.assertEqual(self.client.get('/ganhadores/quina/pe/olinda').status_code, 404)
        self.assertEqual(self.client.get('/ganhadores/mega-sena').status_code, 404)  # sem dados
        self.assertIn('/ganhadores/quina/pe/recife', self.client.get('/sitemap-ganhadores.xml').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()

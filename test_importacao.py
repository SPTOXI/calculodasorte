"""Importação de resultados anteriores por planilha (admin)."""

import io
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import openpyxl

import database
import importador
import updater
from app import app


class TestInterpretacao(unittest.TestCase):

    def test_csv_com_cabecalho_da_caixa(self):
        csv = ('Concurso;Data do Sorteio;Bola1;Bola2;Bola3;Bola4;Bola5;Bola6;Ganhadores 6 acertos;Cidade / UF\n'
               '1;11/03/1996;41;5;4;52;30;33;0;\n'
               '2;18/03/1996;9;39;37;49;43;41;1;PARANA\n')
        res = importador.interpretar('mega_sena', importador.ler_csv(csv.encode('cp1252')))
        self.assertEqual(res['erros'], [])
        self.assertEqual([c['concurso'] for c in res['concursos']], [1, 2])
        self.assertEqual(res['concursos'][0]['dezenas'], [4, 5, 30, 33, 41, 52])
        self.assertEqual(res['concursos'][0]['data'], '11/03/1996')

    def test_sem_cabecalho_e_dezenas_invalidas(self):
        csv = '10,01/02/2020,1,2,3,4,5,6\n11,02/02/2020,1,2,3,4,5,61\n12,03/02/2020,1,1,3,4,5,6\n'
        res = importador.interpretar('mega_sena', importador.ler_csv(csv.encode()))
        self.assertEqual([c['concurso'] for c in res['concursos']], [10])
        self.assertEqual(len(res['erros']), 2)

    def test_dupla_sena_doze_dezenas(self):
        cab = ';'.join(['Concurso'] + [f'Bola{i}' for i in range(1, 7)] * 2)
        linha = ';'.join(['5'] + [str(n) for n in [6, 5, 4, 3, 2, 1, 11, 12, 13, 14, 15, 16]])
        res = importador.interpretar('dupla_sena', importador.ler_csv(f'{cab}\n{linha}\n'.encode()))
        c = res['concursos'][0]
        self.assertEqual(c['dezenas'], [1, 2, 3, 4, 5, 6])
        self.assertEqual(c['segundo'], [11, 12, 13, 14, 15, 16])

    def test_modelo_de_cada_loteria_e_valido(self):
        for loteria in updater.LOTERIAS_SLUGS:
            res = importador.interpretar(loteria, importador.ler_csv(importador.modelo_csv(loteria).encode()))
            self.assertEqual(res['erros'], [], loteria)
            self.assertEqual(len(res['concursos']), 1, loteria)
        self.assertEqual(importador.interpretar('mais_milionaria', importador.ler_csv(
            importador.modelo_csv('mais_milionaria').encode()))['concursos'][0]['trevos'], [1, 2])

    def test_mes_da_sorte_e_super_sete(self):
        csv = 'Concurso;Bola1;Bola2;Bola3;Bola4;Bola5;Bola6;Bola7;Mês da Sorte\n1;1;2;3;4;5;6;7;3\n2;1;2;3;4;5;6;7;Smarch\n'
        res = importador.interpretar('dia_de_sorte', importador.ler_csv(csv.encode()))
        self.assertEqual(res['concursos'][0]['complemento'], 'Março')
        self.assertEqual(len(res['erros']), 1)

        csv = 'Concurso;Coluna1;Coluna2;Coluna3;Coluna4;Coluna5;Coluna6;Coluna7\n1;9;0;9;1;1;2;3\n'
        res = importador.interpretar('super_sete', importador.ler_csv(csv.encode()))
        self.assertEqual(res['concursos'][0]['dezenas'], [9, 0, 9, 1, 1, 2, 3])

    def test_xlsx(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['Resultados Quina'])
        ws.append(['Concurso', 'Data Sorteio', 'Bola1', 'Bola2', 'Bola3', 'Bola4', 'Bola5'])
        ws.append([1, '13/03/1994', 25, 45, 60, 76, 79])
        buf = io.BytesIO()
        wb.save(buf)
        res = importador.interpretar('quina', importador.ler_arquivo('quina.xlsx', buf.getvalue()))
        self.assertEqual(res['concursos'][0]['dezenas'], [25, 45, 60, 76, 79])

    def test_link_google_sheets(self):
        self.assertEqual(
            importador.url_exportacao_google_sheets('https://docs.google.com/spreadsheets/d/abc_123/edit#gid=77'),
            'https://docs.google.com/spreadsheets/d/abc_123/export?format=csv&gid=77')
        with self.assertRaises(importador.ErroImportacao):
            importador.url_exportacao_google_sheets('https://evil.example.com/spreadsheets/d/abc')


class TestImportacaoAdmin(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.copiar_dados_originais(updater.ORIGINAL_DATA_DIR)
        self.patches = [patch.object(updater, 'DATA_DIR', self.tmp),
                        patch.object(updater, 'ORIGINAL_DATA_DIR', self.tmp)]
        for p in self.patches:
            p.start()
        for cache in (updater._HISTORICO_CACHE, updater._META_CACHE):
            cache.pop('quina', None)
        updater._IMPORTADOS_MESCLADOS.discard('quina')
        database.excluir_concursos_importados('quina')

        self.client = app.test_client()
        admin = database.get_user_by_email('silvio.luis.morais@gmail.com')
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['id']

    def copiar_dados_originais(self, origem):
        self.origem = origem
        for arq in os.listdir(origem):
            if arq.startswith('quina_'):
                shutil.copy(os.path.join(origem, arq), self.tmp)

    def tearDown(self):
        database.excluir_concursos_importados('quina')
        for p in self.patches:
            p.stop()
        for cache in (updater._HISTORICO_CACHE, updater._META_CACHE):
            cache.pop('quina', None)
        shutil.rmtree(self.tmp)

    def _enviar(self, confirmar):
        csv = 'Concurso;Bola1;Bola2;Bola3;Bola4;Bola5\n1;25;45;60;76;79\n2;13;30;58;63;64\n'
        return self.client.post('/api/admin/importar-resultados', data={
            'loteria': 'quina', 'confirmar': '1' if confirmar else '0',
            'arquivo': (io.BytesIO(csv.encode()), 'quina.csv')}, content_type='multipart/form-data')

    def test_previa_importacao_e_desfazer(self):
        antes = len(updater.carregar_historico_local('quina'))
        previa = self._enviar(False).get_json()
        self.assertTrue(previa['previa'])
        self.assertEqual(previa['comparacao']['novos'], 2)
        self.assertEqual(len(updater.carregar_historico_local('quina')), antes)

        res = self._enviar(True).get_json()
        self.assertEqual(res['adicionados'], 2)
        historico = updater.carregar_historico_local('quina')
        self.assertEqual(len(historico), antes + 2)
        self.assertEqual(historico[0], [25, 45, 60, 76, 79])
        self.assertEqual(updater.carregar_concursos_local('quina')[:2], [1, 2])

        # Instância nova (cold start no Vercel): os importados voltam do banco
        self.copiar_dados_originais(self.origem)
        for arq in ('quina_concursos.json',):
            caminho = os.path.join(self.tmp, arq)
            if not os.path.exists(os.path.join(self.origem, arq)) and os.path.exists(caminho):
                os.remove(caminho)
        updater._IMPORTADOS_MESCLADOS.discard('quina')
        updater._HISTORICO_CACHE.pop('quina', None)
        self.assertEqual(len(updater.carregar_historico_local('quina')), antes + 2)

        resumo = self.client.get('/api/admin/importar-resultados/resumo').get_json()
        quina = next(l for l in resumo['loterias'] if l['loteria'] == 'quina')
        self.assertEqual(quina['importados']['total'], 2)

        self.assertEqual(self.client.delete('/api/admin/importar-resultados/quina').get_json()['removidos'], 2)
        self.assertEqual(len(updater.carregar_historico_local('quina')), antes)

    def test_somente_admin(self):
        cliente = app.test_client()
        res = cliente.post('/api/admin/importar-resultados', data={'loteria': 'quina'})
        self.assertIn(res.status_code, (302, 401, 403))


if __name__ == '__main__':
    unittest.main()

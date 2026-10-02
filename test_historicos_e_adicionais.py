import unittest
import json
import os
from unittest.mock import patch, MagicMock

os.environ.setdefault('SECRET_KEY', 'test-secret-key')

with patch('database.init_db'), patch('updater.iniciar_agendador'):
    from app import app
    import updater
    import conferencia
    import database

class TestHistoricosEAdicionais(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_local_data_companion_files(self):
        """Testa se os arquivos complementares existem e carregam dados estruturados"""
        trevos = updater.carregar_trevos_local('mais_milionaria')
        self.assertGreater(len(trevos), 0, "Deveria haver histórico de trevos para +Milionária")
        self.assertEqual(len(trevos[0]), 2, "Cada concurso de +Milionária deve ter 2 trevos")

        meses = updater.carregar_times_local('dia_de_sorte')
        self.assertGreater(len(meses), 0, "Deveria haver histórico de meses para Dia de Sorte")
        self.assertIsInstance(meses[0], str)

        times = updater.carregar_times_local('timemania')
        self.assertGreater(len(times), 0, "Deveria haver histórico de times para Timemania")
        self.assertIsInstance(times[0], str)

        segundo = updater.carregar_segundo_sorteio_local('dupla_sena')
        self.assertGreater(len(segundo), 0, "Deveria haver histórico do 2º sorteio para Dupla Sena")
        self.assertEqual(len(segundo[0]), 6, "Cada 2º sorteio da Dupla Sena deve ter 6 números")

    def test_conferencia_mais_milionaria_com_trevos(self):
        """Testa se a conferência de +Milionária avalia e retorna trevos corretamente"""
        jogos = [[1, 2, 3, 4, 5, 6]]
        trevos_jogos = [[1, 2]]
        sorteio_dezenas = [1, 2, 3, 4, 5, 6]
        sorteio_trevos = [1, 2]

        resultado, premiacoes = conferencia.conferir_jogos(
            loteria_type='mais_milionaria',
            jogos=jogos,
            sorteio=sorteio_dezenas,
            segundo_sorteio=None,
            trevos_sorteio=sorteio_trevos,
            trevos_jogos=trevos_jogos
        )
        self.assertEqual(len(resultado), 1)
        item = resultado[0]
        self.assertEqual(item['qtd_acertos'], 6)
        self.assertEqual(item['trevos'], [1, 2])
        self.assertEqual(item['trevos_acertados'], 2)
        self.assertIn('🏆', item['rotulo_premio'])

    def test_conferencia_dia_de_sorte_e_timemania_complementos(self):
        """Testa a conferência de Mês da Sorte e Time do Coração"""
        # Dia de Sorte
        resultado, premiacoes = conferencia.conferir_jogos(
            loteria_type='dia_de_sorte',
            jogos=[[1, 2, 3, 4, 5, 6, 7]],
            sorteio=[1, 2, 3, 10, 11, 12, 13],
            complemento_sorteio='Janeiro',
            complementos_jogos=['Janeiro']
        )
        item = resultado[0]
        self.assertTrue(item['acertou_complemento'])
        self.assertEqual(item['complemento'], 'Janeiro')
        self.assertIn('Mês da Sorte', item['rotulo_premio'])

        # Timemania
        resultado_time, premiacoes_time = conferencia.conferir_jogos(
            loteria_type='timemania',
            jogos=[[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]],
            sorteio=[1, 2, 3, 11, 12, 13, 14],
            complemento_sorteio='FLAMENGO/RJ',
            complementos_jogos=['Flamengo / RJ']
        )
        item_time = resultado_time[0]
        self.assertTrue(item_time['acertou_complemento'])
        self.assertIn('Time do Coração', item_time['rotulo_premio'])

    @patch('database.sync_db_to_cloud')
    @patch('database.get_db_connection')
    def test_database_salvar_e_listar_trevos_e_complementos(self, mock_db_conn, mock_sync):
        """Testa serialização e recuperação de trevos e complementos em database.py"""
        mock_conn = MagicMock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn

        # Simular retorno do cursor para salvar
        cursor_mock = MagicMock()
        cursor_mock.fetchone.return_value = {'id': 77}
        mock_conn.cursor.return_value = cursor_mock

        aposta_id = database.salvar_aposta(
            loteria_type='mais_milionaria',
            modalidade='manual',
            jogos=[[1, 2, 3, 4, 5, 6]],
            dezenas_por_jogo=6,
            user_id=1,
            trevos=[[3, 4]],
            complementos=None,
            titulo='Aposta Teste Trevos'
        )
        self.assertEqual(aposta_id, 77)

        # Simular listagem
        mock_conn.execute.return_value.fetchall.return_value = [
            {
                'id': 77,
                'loteria_type': 'mais_milionaria',
                'modalidade': 'manual',
                'jogos_json': json.dumps([[1, 2, 3, 4, 5, 6]]),
                'dezenas_por_jogo': 6,
                'trevos_json': json.dumps([[3, 4]]),
                'complementos_json': None,
                'quantidade_jogos': 1,
                'titulo': 'Aposta Teste Trevos',
                'created_at': '2026-10-02 12:00:00'
            }
        ]
        apostas = database.listar_apostas(loteria_type='mais_milionaria', user_id=1)
        self.assertEqual(len(apostas), 1)
        self.assertEqual(apostas[0]['trevos'], [[3, 4]])

    def test_api_carregar_historico_returns_adicionais(self):
        """Verifica se /api/carregar-historico retorna trevos e complementos"""
        res_mil = self.app.get('/api/carregar-historico/mais_milionaria')
        data_mil = json.loads(res_mil.data)
        self.assertIn('trevos', data_mil)
        self.assertGreater(len(data_mil['trevos']), 0)

        res_dia = self.app.get('/api/carregar-historico/dia_de_sorte')
        data_dia = json.loads(res_dia.data)
        self.assertIn('complementos', data_dia)
        self.assertGreater(len(data_dia['complementos']), 0)

        res_time = self.app.get('/api/carregar-historico/timemania')
        data_time = json.loads(res_time.data)
        self.assertIn('complementos', data_time)
        self.assertGreater(len(data_time['complementos']), 0)

    def test_download_jogos_com_trevos_e_complementos(self):
        """Verifica se o download em .txt e .md inclui trevos e complementos"""
        payload = {
            'jogos': [[1, 2, 3, 4, 5, 6]],
            'trevos': [[2, 5]],
            'complementos': []
        }
        res_txt = self.app.post('/download/jogos/mais_milionaria/txt',
                                data=json.dumps(payload),
                                content_type='application/json')
        txt = res_txt.data.decode('utf-8')
        self.assertIn('Trevos: [ 2 5 ]', txt)

        res_md = self.app.post('/download/jogos/mais_milionaria/md',
                               data=json.dumps(payload),
                               content_type='application/json')
        md = res_md.data.decode('utf-8')
        self.assertIn('Trevos da Sorte 🍀', md)
        self.assertIn('🍀 2, 5', md)

        # Testar download timemania com Time do Coração
        payload_time = {
            'jogos': [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]],
            'trevos': [],
            'complementos': ['FLAMENGO/RJ']
        }
        res_time_txt = self.app.post('/download/jogos/timemania/txt',
                                     data=json.dumps(payload_time),
                                     content_type='application/json')
        txt_time = res_time_txt.data.decode('utf-8')
        self.assertIn('Time: FLAMENGO/RJ', txt_time)

    @patch('database.get_user_by_id', return_value={'id': 10, 'email': 'test@example.com', 'is_blocked': 0, 'role': 'user'})
    @patch('database.check_user_access', return_value={'tem_acesso': True})
    @patch('database.consume_user_credit')
    @patch('database.salvar_aposta')
    @patch('app._acesso_bloqueado', return_value=None)
    def test_api_fechamento_mais_milionaria_gera_trevos(self, mock_bloq, mock_salvar, mock_credit, mock_access, mock_user):
        """Verifica se api_fechamento para +Milionária gera trevos e os retorna"""
        mock_salvar.return_value = 88
        with self.app.session_transaction() as sess:
            sess['user_id'] = 10
            sess['user_email'] = 'test@example.com'

        payload = {
            'grupo': [1, 2, 3, 4, 5, 6, 7, 8],
            'dezenas_por_jogo': 6,
            'condicao': 6,
            'garantia': 4
        }
        res = self.app.post('/api/fechamento/mais_milionaria',
                            data=json.dumps(payload),
                            content_type='application/json')
        data = json.loads(res.data)
        self.assertTrue(data.get('sucesso'))
        self.assertIn('trevos', data)
        self.assertIsNotNone(data['trevos'])
        self.assertEqual(len(data['trevos']), len(data['jogos']))
        mock_salvar.assert_called_once()
        _, kwargs = mock_salvar.call_args
        self.assertIsNotNone(kwargs.get('trevos'))

    @patch('database.salvar_aposta')
    def test_api_salvar_apostas_preenche_trevos_e_complementos(self, mock_salvar):
        """Verifica se api_salvar_apostas preenche trevos e complementos padrão se omitidos"""
        mock_salvar.return_value = 99
        with self.app.session_transaction() as sess:
            sess['user_id'] = 10

        # +Milionária sem trevos enviados
        res_mil = self.app.post('/api/apostas/salvar',
                                data=json.dumps({
                                    'loteria_type': 'mais_milionaria',
                                    'jogos': [[1, 2, 3, 4, 5, 6]],
                                    'modalidade': 'manual'
                                }),
                                content_type='application/json')
        self.assertEqual(res_mil.status_code, 200)
        _, kwargs = mock_salvar.call_args
        self.assertIsNotNone(kwargs.get('trevos'))
        self.assertEqual(len(kwargs['trevos']), 1)
        self.assertEqual(len(kwargs['trevos'][0]), 2)

if __name__ == '__main__':
    unittest.main()

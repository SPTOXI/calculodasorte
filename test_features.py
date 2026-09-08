"""
Testes Automatizados para as Novas Funcionalidades:
- Agendamento 23:59h
- Download de Histórico (.md e .txt)
- Geração de Múltiplos Jogos Inteligentes
- Exportação de Apostas (.md e .txt)
- Endpoint Cron do Vercel
"""

import unittest
import json
from app import app
import updater

class TestNovasFuncionalidades(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_01_calculo_segundos_2359(self):
        """Testa o cálculo do tempo até 23:59h"""
        segundos = updater.calcular_segundos_ate_2359()
        self.assertGreater(segundos, 0)
        self.assertLessEqual(segundos, 86400)
        print(f"[TESTE] Segundos restantes até 23:59h: {segundos:.0f}s ({segundos/3600:.2f}h)")

    def test_02_download_historico_md_e_txt(self):
        """Testa o download do histórico oficial em .md e .txt"""
        # Download MD
        res_md = self.client.get('/download/historico/mega_sena/md')
        self.assertEqual(res_md.status_code, 200)
        self.assertIn('attachment', res_md.headers.get('Content-Disposition', ''))
        self.assertIn('.md', res_md.headers.get('Content-Disposition', ''))
        texto_md = res_md.get_data(as_text=True)
        self.assertIn('# Histórico Oficial de Sorteios', texto_md)
        self.assertIn('| Concurso Histórico |', texto_md)

        # Download TXT
        res_txt = self.client.get('/download/historico/mega_sena/txt')
        self.assertEqual(res_txt.status_code, 200)
        self.assertIn('attachment', res_txt.headers.get('Content-Disposition', ''))
        self.assertIn('.txt', res_txt.headers.get('Content-Disposition', ''))
        texto_txt = res_txt.get_data(as_text=True)
        self.assertIn('HISTÓRICO OFICIAL DE SORTEIOS', texto_txt)
        self.assertIn('Concurso #', texto_txt)

    def test_03_gerar_multiplos_jogos_api(self):
        """Testa a geração de múltiplos palpites baseados no modelo canônico"""
        res = self.client.post('/api/gerar-multiplos-jogos/mega_sena',
            data=json.dumps({
                'quantidade_jogos': 7,
                'dezenas_por_jogo': 6
            }),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['sucesso'])
        self.assertEqual(len(data['jogos']), 7)
        self.assertEqual(data['dezenas_por_jogo'], 6)

        # Garantir que todos os 7 jogos são distintos
        jogos_tuplas = [tuple(j) for j in data['jogos']]
        self.assertEqual(len(set(jogos_tuplas)), 7, "Todos os jogos gerados devem ser únicos")

        for j in data['jogos']:
            self.assertEqual(len(j), 6)
            for n in j:
                self.assertTrue(1 <= n <= 60)

    def test_04_download_jogos_export(self):
        """Testa exportação dos palpites em .md e .txt"""
        jogos_exemplo = [
            [8, 17, 24, 43, 47, 58],
            [1, 13, 25, 35, 39, 51]
        ]

        # Export MD
        res_md = self.client.post('/download/jogos/mega_sena/md',
            data=json.dumps({'jogos': jogos_exemplo}),
            content_type='application/json'
        )
        self.assertEqual(res_md.status_code, 200)
        self.assertIn('attachment', res_md.headers.get('Content-Disposition', ''))
        self.assertIn('.md', res_md.headers.get('Content-Disposition', ''))
        texto_md = res_md.get_data(as_text=True)
        self.assertIn('# Palpites Gerados', texto_md)
        self.assertIn('08, 17, 24, 43, 47, 58', texto_md)

        # Export TXT
        res_txt = self.client.post('/download/jogos/mega_sena/txt',
            data=json.dumps({'jogos': jogos_exemplo}),
            content_type='application/json'
        )
        self.assertEqual(res_txt.status_code, 200)
        self.assertIn('attachment', res_txt.headers.get('Content-Disposition', ''))
        self.assertIn('.txt', res_txt.headers.get('Content-Disposition', ''))
        texto_txt = res_txt.get_data(as_text=True)
        self.assertIn('PALPITES GERADOS', texto_txt)
        self.assertIn('08 17 24 43 47 58', texto_txt)

    def test_05_cron_endpoint(self):
        """Testa se a rota do cron diário responde corretamente"""
        res = self.client.get('/api/cron/atualizar')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('sucesso', data)

    def test_06_salvar_e_listar_apostas_usuario(self):
        """Testa salvar apostas no banco SQLite e listar apostas da sessão"""
        jogos_teste = [
            [4, 12, 25, 33, 41, 58],
            [2, 10, 20, 30, 40, 50]
        ]
        # Salvar aposta
        res_salvar = self.client.post('/api/apostas/salvar',
            data=json.dumps({
                'loteria_type': 'mega_sena',
                'modalidade': 'fechamento',
                'jogos': jogos_teste,
                'titulo': 'Teste Automatizado Unitário'
            }),
            content_type='application/json'
        )
        self.assertEqual(res_salvar.status_code, 200)
        dados_salvos = res_salvar.get_json()
        self.assertTrue(dados_salvos['sucesso'])
        aposta_id = dados_salvos['aposta_id']
        self.assertGreater(aposta_id, 0)

        # Listar apostas
        res_listar = self.client.get('/api/apostas/listar/mega_sena')
        self.assertEqual(res_listar.status_code, 200)
        dados_lista = res_listar.get_json()
        self.assertTrue(dados_lista['sucesso'])
        self.assertGreaterEqual(dados_lista['total'], 1)
        ids = [a['id'] for a in dados_lista['apostas']]
        self.assertIn(aposta_id, ids)

        return aposta_id

    def test_07_conferir_aposta_com_caixa(self):
        """Testa o endpoint de conferência automática contra o último sorteio da Caixa"""
        aposta_id = self.test_06_salvar_e_listar_apostas_usuario()
        res_conf = self.client.get(f'/api/apostas/conferir/{aposta_id}')
        self.assertEqual(res_conf.status_code, 200)
        dados_conf = res_conf.get_json()
        self.assertTrue(dados_conf['sucesso'])
        self.assertIn('concurso_numero', dados_conf)
        self.assertIn('dezenas_sorteadas', dados_conf)
        self.assertIn('jogos_conferidos', dados_conf)
        self.assertGreater(len(dados_conf['jogos_conferidos']), 0)

    def test_08_excluir_aposta_usuario(self):
        """Testa a exclusão de uma aposta salva"""
        aposta_id = self.test_06_salvar_e_listar_apostas_usuario()
        res_del = self.client.delete(f'/api/apostas/{aposta_id}')
        self.assertEqual(res_del.status_code, 200)
        dados_del = res_del.get_json()
        self.assertTrue(dados_del['sucesso'])


if __name__ == '__main__':
    unittest.main()


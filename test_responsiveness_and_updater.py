"""
Testes de Responsividade do Admin/Usuário e Robustez da API da Caixa
Projeto Calculadora da Sorte
"""

import re
import unittest
import json
from app import app
import updater
import database


class TestResponsividadeEUpdater(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_email'] = 'silvio.luis.morais@gmail.com'
            sess['user_role'] = 'admin'

    def test_01_viewport_meta_em_todos_templates(self):
        """Verifica se todos os templates HTML possuem a tag viewport para responsividade mobile"""
        rotas_autenticadas = ['/dashboard', '/analise/mega_sena', '/admin', '/planos']
        for rota in rotas_autenticadas:
            res = self.client.get(rota)
            self.assertEqual(res.status_code, 200, f"Falha na rota {rota}")
            self.assertIn('name="viewport"', res.text, f"Viewport ausente em {rota}")
            self.assertIn('width=device-width', res.text, f"Width=device-width ausente em {rota}")

        # Rotas públicas sem sessão ativa
        anon_client = app.test_client()
        for rota in ['/login', '/cadastro']:
            res = anon_client.get(rota)
            self.assertEqual(res.status_code, 200, f"Falha na rota {rota}")
            self.assertIn('name="viewport"', res.text, f"Viewport ausente em {rota}")

    def test_02_responsividade_admin_css_e_classes(self):
        """Verifica se as correções de responsividade do painel admin estão presentes no HTML e CSS"""
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 200)
        html = res.text
        html = html + '\n' + re.sub(r'\s+', '', html)

        # Verifica contenção de overflow global no body/html
        self.assertIn('overflow-x:hidden', html)
        self.assertIn('max-width:100vw', html)

        # Verifica correção do seletor de abas
        self.assertIn('.tabs-header{', html)
        self.assertIn('overflow-x:auto', html)
        self.assertIn('-webkit-overflow-scrolling:touch', html)

        # Verifica classes de apoio responsivo
        self.assertIn('mobile-table-hint', html)
        self.assertIn('user-info', html)
        self.assertIn('user-nav-actions', html)
        self.assertIn('table-responsive', html)
        self.assertIn('overscroll-behavior-x:contain', html)

        # Verifica classes especiais para colunas em telas menores
        self.assertIn('col-detalhes', html)
        self.assertIn('col-txid', html)

        # Verifica min-width em tabelas para evitar compressão
        self.assertIn('min-width:650px', html)

        # Verifica suporte a múltiplos breakpoints mobile e tablet
        self.assertIn('(max-width:1024px)', html)
        self.assertIn('(max-width:768px)', html)
        self.assertIn('(max-width:480px)', html)
        self.assertIn('(max-width:360px)', html)

    def test_03_responsividade_area_usuario(self):
        """Verifica a responsividade da área de análise do usuário"""
        res = self.client.get('/analise/mega_sena')
        self.assertEqual(res.status_code, 200)
        html = res.text
        html = html + '\n' + re.sub(r'\s+', '', html)

        # Volante e bolas
        self.assertIn('volante-grid', html)
        self.assertIn('volante-bola', html)

        # Tabela de números
        self.assertIn('tabela-numeros', html)
        self.assertIn('min-width:500px', html)

        # Drawer e chat flutuante IA
        self.assertIn('ai-chat-floating-btn', html)
        self.assertIn('ai-chat-panel', html)

    def test_04_agendador_diario_2300_caixa(self):
        """Verifica os cálculos do agendador diário oficial das 23:00h da Caixa"""
        segundos, nome = updater.calcular_segundos_proximo_checkpoint()
        self.assertGreater(segundos, 0)
        self.assertIsInstance(nome, str)
        self.assertIn('23:00', nome)

        seg_2300 = updater.calcular_segundos_ate_2300()
        self.assertGreater(seg_2300, 0)
        self.assertLessEqual(seg_2300, 86400)

        # Retrocompatibilidade com teste antigo
        seg_2359 = updater.calcular_segundos_ate_2359()
        self.assertGreater(seg_2359, 0)
        self.assertLessEqual(seg_2359, 86400)

    def test_05_verificacao_staleness_sob_demanda(self):
        """Verifica função de detecção inteligente de necessidade de atualização"""
        # Para uma loteria existente
        necessita = updater.verificar_se_necessita_atualizacao('mega_sena')
        self.assertIsInstance(necessita, bool)

        # Para loteria inexistente
        necessita_fake = updater.verificar_se_necessita_atualizacao('loteria_fantasma_xyz')
        self.assertTrue(necessita_fake)

    def test_06_vercel_json_cron_2300_brasilia(self):
        """Verifica se o vercel.json está configurado para 23:00h de Brasília (02:00 UTC)"""
        with open('vercel.json', 'r', encoding='utf-8') as f:
            vconf = json.load(f)

        crons = vconf.get('crons', [])
        self.assertEqual(len(crons), 1)

        schedule = crons[0].get('schedule')
        # 02:00 UTC = 23:00 BRT (Horário de Brasília)
        self.assertEqual(schedule, '0 2 * * *')

    def test_07_api_carregar_historico_com_metadados(self):
        """Verifica endpoint /api/carregar-historico com auto-sincronização opcional"""
        res = self.client.get('/api/carregar-historico/mega_sena')
        self.assertEqual(res.status_code, 200)
        dados = res.get_json()
        self.assertIn('historico', dados)
        self.assertIn('concursos_count', dados)
        self.assertIn('meta', dados)
        self.assertGreater(dados['concursos_count'], 0)

    def test_08_bloqueio_sincronizacao_usuario_padrao(self):
        """Verifica que a função 'Sincronizar Agora' está indisponível para o usuário padrão"""
        # Cliente autenticado como usuário padrão (role='user')
        u_comum = database.get_user_by_email('usuario.comum@email.com')
        if not u_comum:
            u_comum = database.create_user('usuario.comum@email.com', '123456', 'Usuario Comum', role='user')
        user_client = app.test_client()
        with user_client.session_transaction() as sess:
            sess['user_id'] = u_comum['id']
            sess['user_email'] = u_comum['email']
            sess['user_role'] = 'user'

        # 1. No HTML da página de análise, o botão 'Sincronizar Agora' NÃO deve ser renderizado para usuário padrão
        res_page = user_client.get('/analise/mega_sena')
        self.assertEqual(res_page.status_code, 200)
        self.assertNotIn('sincronizarComCaixaAgora()', res_page.text)
        self.assertNotIn('Sincronizar Agora', res_page.text)

        # 2. No endpoint de API, usuário comum recebe 403 Forbidden
        res_api = user_client.post('/api/sincronizar/mega_sena')
        self.assertEqual(res_api.status_code, 403)
        dados_api = res_api.get_json()
        self.assertFalse(dados_api.get('sucesso'))
        self.assertIn('apenas para administradores', dados_api.get('erro', ''))

        # 3. Administrador possui acesso ao botão e ao endpoint
        res_admin_page = self.client.get('/analise/mega_sena')
        self.assertEqual(res_admin_page.status_code, 200)
        self.assertIn('sincronizarComCaixaAgora()', res_admin_page.text)
        self.assertIn('Sincronizar Agora (Admin)', res_admin_page.text)

    def test_09_remocao_gerar_50_jogos_teste(self):
        """Verifica que o botão desnecessário 'Gerar 50 Jogos de Teste' foi removido da interface"""
        res = self.client.get('/analise/mega_sena')
        self.assertEqual(res.status_code, 200)
        html = res.text
        html = html + '\n' + re.sub(r'\s+', '', html)

        # Botão redundante não deve existir no HTML
        self.assertNotIn('Gerar 50 Jogos de Teste', html)
        self.assertNotIn('gerarDadosExemplo()', html)

        # Deve manter os botões essenciais da aba Meus Números
        self.assertIn('Avaliar Meus Jogos', html)
        self.assertIn('Salvar no Histórico Pessoal', html)

    def test_10_admin_ssr_usuarios_e_pagamentos_renderizados_imediatamente(self):
        """Garante que usuários cadastrados e pagamentos são renderizados no HTML do /admin imediatamente"""
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 200)
        html = res.text
        html = html + '\n' + re.sub(r'\s+', '', html)

        # 1. Usuário admin padrão deve estar renderizado na tabela de usuários
        self.assertIn('silvio.luis.morais@gmail.com', html)
        self.assertIn('badge-info', html)

        # 2. Pagamentos devem estar renderizados na tabela de pagamentos
        self.assertTrue('VIP Mensal' in html or 'Recarga Avulsa' in html or 'R$' in html)

        # 3. Badges de contadores no cabeçalho das abas
        self.assertIn('badge-total-usuarios', html)
        self.assertIn('badge-total-pagamentos', html)

    def test_11_admin_responsividade_cards_mobile_e_metricas(self):
        """Valida que o admin possui suporte a visualização mobile em cartões e barra de métricas"""
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 200)
        html = res.text
        html = html + '\n' + re.sub(r'\s+', '', html)

        # 1. Barra de métricas em tempo real
        self.assertIn('metrics-grid', html)
        self.assertIn('Receita Confirmada', html)

        # 2. Tabela no formato cartão responsivo para telas pequenas
        self.assertIn('responsive-card-table', html)
        self.assertIn('data-label="E-mail"', html)
        self.assertIn('data-label="Valor"', html)

        # 3. Campos de busca instantânea
        self.assertIn('busca-usuarios', html)
        self.assertIn('busca-pagamentos', html)


if __name__ == '__main__':
    unittest.main()


"""
Testes automatizados para a precificação e checkout da análise por R$ 1,00.
Valida:
1. templates/cadastro.html com texto exato exigido
2. database.create_user com credits=0 padrão
3. database.approve_payment adicionando crédito para tipo 'analise'
4. /cadastro com credits=0 e redirecionamento de boas-vindas
5. /api/checkout/pix com valor R$ 1,00 para tipo 'analise'
6. /api/checkout/infinitepay com valor R$ 1,00 (100 centavos) para tipo 'analise'
7. Ausência de referências a análise grátis/cortesia nas páginas principais
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import re
import json

os.environ.setdefault('SECRET_KEY', 'test-secret-key')

with patch('database.init_db'), patch('updater.iniciar_agendador'):
    from app import app, PRECO_ANALISE
    import database


class TestCheckoutAnalise(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_texto_cadastro_html(self):
        """Verifica se o texto exato exigido está presente em templates/cadastro.html"""
        with open('templates/cadastro.html', 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        # O HTML contém a formatação exata dentro do badge de bônus
        self.assertIn("<strong>Bônus:</strong> Pague 1 real por análise completa gratuita ao se cadastrar!", conteudo)
        self.assertNotIn("Ganhe 1 análise completa gratuita ao se cadastrar!", conteudo)

        # Validando também o texto sem tags
        texto_limpo = re.sub(r'<[^>]+>', '', conteudo)
        self.assertIn("Bônus: Pague 1 real por análise completa gratuita ao se cadastrar!", texto_limpo)

    def test_02_preco_analise_constante(self):
        """Verifica a constante de preço da análise avulsa"""
        self.assertEqual(PRECO_ANALISE, 1.00)

    @patch('database.record_login')
    @patch('database.get_user_by_email', return_value=None)
    @patch('database.create_user')
    def test_03_fluxo_cadastro_cria_usuario_com_zero_creditos(self, mock_create, mock_get, mock_rec):
        """Verifica que o cadastro cria usuário com credits=0 e redireciona com bônus de 1 real"""
        mock_create.return_value = {
            'id': 100,
            'email': 'novo@usuario.com',
            'name': 'Novo Usuario',
            'role': 'user',
            'credits': 0,
            'is_blocked': 0
        }

        with self.client:
            res = self.client.post('/cadastro', data={
                'nome': 'Novo Usuario',
                'email': 'novo@usuario.com',
                'password': 'Password123!',
                'confirm_password': 'Password123!',
                'termos_lgpd': '1',
                'plano_desejado': 'analise'
            }, follow_redirects=False)

            self.assertEqual(res.status_code, 302)
            self.assertIn('/planos', res.headers.get('Location', ''))
            mock_create.assert_called_once()
            _, kwargs = mock_create.call_args
            self.assertEqual(kwargs.get('credits'), 0)

    @patch('database.sync_db_to_cloud')
    @patch('database.add_user_credits')
    @patch('database.activate_vip_plan')
    @patch('database.get_payment_by_id')
    @patch('database.get_db_connection')
    def test_04_approve_payment_analise_concede_1_credito(self, mock_db_conn, mock_get_payment, mock_vip, mock_add_credits, mock_sync):
        """Verifica se a aprovação de pagamento 'analise' concede 1 crédito"""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        # Simular pagamento tipo 'analise'
        mock_get_payment.return_value = {
            'id': 1,
            'user_id': 42,
            'tipo': 'analise',
            'status': 'pendente'
        }

        resultado = database.approve_payment(payment_id=1)
        self.assertTrue(resultado)
        mock_add_credits.assert_called_with(42, amount=1)
        mock_vip.assert_not_called()

        mock_add_credits.reset_mock()
        # Simular pagamento tipo 'credito'
        mock_get_payment.return_value = {
            'id': 2,
            'user_id': 42,
            'tipo': 'credito',
            'status': 'pendente'
        }
        resultado = database.approve_payment(payment_id=2)
        self.assertTrue(resultado)
        mock_add_credits.assert_called_with(42, amount=1)

    @patch('database.create_payment')
    @patch('database.get_user_by_id')
    def test_05_checkout_pix_analise(self, mock_get_user, mock_create_pay):
        """Verifica geração de checkout PIX para 1 análise (R$ 1,00)"""
        mock_get_user.return_value = {
            'id': 10,
            'email': 'cliente@teste.com',
            'nome': 'Cliente Teste',
            'is_blocked': 0
        }
        mock_create_pay.return_value = {
            'id': 123,
            'valor': 1.00,
            'tipo': 'analise',
            'pix_copia_cola': '00020126580014br.gov.bcb.pix...',
            'pix_qr_code_base64': 'data:image/png;base64,abc'
        }

        with self.client.session_transaction() as sess:
            sess['user_id'] = 10
            sess['email'] = 'cliente@teste.com'
            sess['role'] = 'user'

        res = self.client.post('/api/checkout/pix', json={
            'tipo': 'analise'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('sucesso'))
        self.assertEqual(data.get('valor'), 1.00)
        self.assertEqual(data.get('tipo'), 'analise')
        mock_create_pay.assert_called_with(user_id=10, tipo='analise', valor=1.00, loteria_type=None)

    @patch('requests.post')
    @patch('database.create_payment')
    @patch('database.get_user_by_id')
    def test_06_checkout_infinitepay_analise(self, mock_get_user, mock_create_pay, mock_requests_post):
        """Verifica geração de link InfinitePay para análise avulsa por R$ 1,00 (100 centavos)"""
        mock_get_user.return_value = {
            'id': 10,
            'email': 'cliente@teste.com',
            'nome': 'Cliente Teste',
            'telefone': '11999999999',
            'is_blocked': 0
        }
        mock_create_pay.return_value = {
            'id': 456,
            'valor': 1.00,
            'tipo': 'analise'
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'url': 'https://pay.infinitepay.io/checkout/teste-123'
        }
        mock_requests_post.return_value = mock_resp

        with self.client.session_transaction() as sess:
            sess['user_id'] = 10
            sess['email'] = 'cliente@teste.com'
            sess['role'] = 'user'

        res = self.client.post('/api/checkout/infinitepay', json={
            'tipo': 'analise'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('sucesso'))
        self.assertEqual(data.get('checkout_url'), 'https://pay.infinitepay.io/checkout/teste-123')

        mock_requests_post.assert_called_once()
        _, post_kwargs = mock_requests_post.call_args
        payload = post_kwargs.get('json', {})
        items = payload.get('items', [])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get('price'), 100) # R$ 1,00 em centavos (100)
        self.assertIn('1 Análise Completa (R$ 1,00)', items[0].get('description'))

    def test_07_templates_verificacao_sem_cortesia(self):
        """Verifica que templates principais não oferecem mais análise grátis ou cortesia no cadastro"""
        arquivos = [
            'templates/minha_conta.html',
            'templates/landing.html',
            'templates/index.html',
            'templates/planos.html',
            'templates/dashboard_base.html',
            'templates/login.html'
        ]
        termos_proibidos = [
            '1 Análise Grátis',
            'Ganhe 1 análise completa gratuita',
            'CRÉDITO(S) DE CORTESIA',
            'Degustação Grátis'
        ]

        for arq in arquivos:
            with open(arq, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            for termo in termos_proibidos:
                self.assertNotIn(termo, conteudo, f"Termo proibido '{termo}' encontrado no arquivo {arq}")


if __name__ == '__main__':
    unittest.main()

"""
Script de Testes Automatizados Completo para o Sistema
Calculadora da Sorte: Autenticação, CRUD de Usuários, Sincronização Caixa e Modelo Estatístico
"""

import os
import json
import unittest
from werkzeug.security import check_password_hash

import database
import updater
from app import app

class TestCalculadoraDaSorte(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        database.init_db()

    def test_01_admin_seed(self):
        """Verifica se o usuário admin foi gerado com as credenciais especificadas"""
        admin = database.get_user_by_email('silvio.luis.morais@gmail.com')
        self.assertIsNotNone(admin, "Admin deve existir no banco de dados")
        self.assertEqual(admin['role'], 'admin')
        self.assertTrue(check_password_hash(admin['password_hash'], '123456'), "Senha inicial deve ser 123456")
        self.assertEqual(admin['must_change_password'], 1, "Deve requerer troca de senha no primeiro login")

    def test_02_login_and_auth(self):
        """Testa o fluxo de login web e cookies de sessão"""
        # Senha incorreta
        res = self.client.post('/login', data={
            'email': 'silvio.luis.morais@gmail.com',
            'password': 'errada'
        }, follow_redirects=True)
        self.assertIn('E-mail ou senha incorretos', res.get_data(as_text=True))

        # Senha correta
        res = self.client.post('/login', data={
            'email': 'silvio.luis.morais@gmail.com',
            'password': '123456'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Painel Admin', res.get_data(as_text=True))

    def test_03_usuario_crud_and_block(self):
        """Testa o CRUD de usuários e a trava de bloqueio"""
        # 1. Login como admin
        self.client.post('/login', data={
            'email': 'silvio.luis.morais@gmail.com',
            'password': '123456'
        })

        # 2. Criar novo usuário
        novo_email = 'teste.operador@loteria.com'
        res = self.client.post('/api/admin/usuarios', 
            data=json.dumps({'email': novo_email, 'password': 'senha_operador', 'role': 'user'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 201)
        user_data = res.get_json()
        user_id = user_data['id']
        self.assertEqual(user_data['email'], novo_email)

        # 3. Editar usuário
        res = self.client.put(f'/api/admin/usuarios/{user_id}',
            data=json.dumps({'email': 'teste.alterado@loteria.com', 'role': 'admin'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['email'], 'teste.alterado@loteria.com')

        # 4. Bloquear usuário
        res = self.client.post(f'/api/admin/usuarios/{user_id}/bloquear')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['bloqueado'])

        # Verificar se usuário bloqueado não consegue fazer login
        client_bloqueado = app.test_client()
        res = client_bloqueado.post('/login', data={
            'email': 'teste.alterado@loteria.com',
            'password': 'senha_operador'
        }, follow_redirects=True)
        self.assertIn('bloqueada', res.get_data(as_text=True))

        # 5. Desbloquear usuário
        res = self.client.post(f'/api/admin/usuarios/{user_id}/bloquear')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json()['bloqueado'])

        # 6. Excluir usuário
        res = self.client.delete(f'/api/admin/usuarios/{user_id}')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['sucesso'])

        # Verificar que usuário foi deletado
        self.assertIsNone(database.get_user_by_id(user_id))

    def test_04_protecao_auto_exclusao_e_bloqueio(self):
        """Verifica que o admin não pode bloquear ou excluir a si mesmo"""
        self.client.post('/login', data={
            'email': 'silvio.luis.morais@gmail.com',
            'password': '123456'
        })
        admin = database.get_user_by_email('silvio.luis.morais@gmail.com')

        # Tentar se auto-bloquear
        res = self.client.post(f'/api/admin/usuarios/{admin["id"]}/bloquear')
        self.assertEqual(res.status_code, 400)
        self.assertIn('não pode bloquear', res.get_json()['erro'])

        # Tentar se auto-excluir
        res = self.client.delete(f'/api/admin/usuarios/{admin["id"]}')
        self.assertEqual(res.status_code, 400)
        self.assertIn('não pode excluir', res.get_json()['erro'])

    def test_05_alterar_propria_senha(self):
        """Testa alteração de senha após o primeiro login"""
        self.client.post('/login', data={
            'email': 'silvio.luis.morais@gmail.com',
            'password': '123456'
        })

        res = self.client.post('/admin/alterar-senha',
            data=json.dumps({'nova_senha': 'admin_nova_senha_2026'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)

        # Confirmar no banco
        admin = database.get_user_by_email('silvio.luis.morais@gmail.com')
        self.assertTrue(check_password_hash(admin['password_hash'], 'admin_nova_senha_2026'))
        self.assertEqual(admin['must_change_password'], 0)

        # Restaurar senha original de teste para consistência
        database.update_password(admin['id'], '123456')
        database.set_must_change_password(admin['id'], 1)

    def test_06_loterias_status_e_sincronizacao(self):
        """Testa a rota de status e a sincronização com a Caixa"""
        self.client.post('/login', data={
            'email': 'silvio.luis.morais@gmail.com',
            'password': '123456'
        })

        # Testar status
        res = self.client.get('/api/admin/loterias/status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('status', data)
        self.assertEqual(len(data['status']), 9, "Deve cobrir as 9 modalidades de loteria")

        # Testar sincronização de uma modalidade (Lotofácil)
        res = self.client.post('/api/admin/loterias/sincronizar/lotofacil')
        self.assertEqual(res.status_code, 200)
        sync_res = res.get_json()
        self.assertTrue(sync_res['sucesso'])
        self.assertGreater(sync_res['total_local'], 0)

        # Testar endpoint de análise com os dados sincronizados
        res_analise = self.client.post('/api/analise/lotofacil', 
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(res_analise.status_code, 200)
        analise_json = res_analise.get_json()
        self.assertIn('estatisticas_gerais', analise_json)
        self.assertIn('validacao_camada7', analise_json)


if __name__ == '__main__':
    unittest.main()

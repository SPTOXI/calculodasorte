"""Anúncio de bolões na Hero da landing e do painel, e rodapé legal condicional."""

import unittest
import uuid
from unittest.mock import patch

import app as app_module
import database
from app import app


class TestHeroBoloes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()
        sufixo = uuid.uuid4().hex[:8]
        cls.admin = database.create_user(f'admh-{sufixo}@teste.com', 'senha123', role='admin')
        cls.user = database.create_user(f'usrh-{sufixo}@teste.com', 'senha123')
        with patch('conferencia.proximo_concurso', return_value=3000):
            aposta = database.salvar_aposta('quina', 'fechamento', [[1, 2, 3, 4, 5]] * 4, 5,
                                            user_id=cls.admin['id'], concurso_alvo=3000)
            client = app.test_client()
            with client.session_transaction() as s:
                s['user_id'] = cls.admin['id']
            app_module._rate_limits.clear()
            r = client.post('/api/boloes', json={'aposta_id': aposta, 'total_cotas': 4, 'titulo': 'Bolão Quina Destaque'})
        assert r.status_code == 201, r.get_json()

    def setUp(self):
        self.client = app.test_client()

    def tearDown(self):
        database.save_bolao_config({'ativo': False})
        app_module._cache_bolao_cfg['cfg'] = None

    def _ativar(self, ativo: bool):
        database.save_bolao_config({'ativo': ativo})
        app_module._cache_bolao_cfg['cfg'] = None

    def _logar(self, user_id):
        with self.client.session_transaction() as s:
            s['user_id'] = user_id

    def test_modulo_desligado_nao_anuncia_e_mantem_rodape(self):
        self._ativar(False)
        html = self.client.get('/').get_data(as_text=True)
        self.assertNotIn('Novidade: Gestão de Bolões', html)
        self.assertIn('NÃO comercializamos bilhetes ou bolões', html)

    def test_modulo_ativo_anuncia_com_destaques_e_ajusta_rodape(self):
        self._ativar(True)
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('Novidade: Gestão de Bolões', html)
        self.assertIn('class="bh-card"', html)  # cartões dos bolões mais perto de esgotar
        self.assertIn('por cota', html)
        self.assertIn('Ver grupos de bolão abertos', html)
        self.assertIn('href="/boloes"', html)
        self.assertNotIn('NÃO comercializamos bilhetes ou bolões', html)
        self.assertIn('gerenciamos grupos de bolão', html)
        self.assertIn('lotéricas parceiras', html)

    def test_painel_do_usuario_mostra_anuncio_quando_ativo(self):
        self._logar(self.user['id'])
        self._ativar(False)
        self.assertNotIn('Novidade: Gestão de Bolões', self.client.get('/dashboard').get_data(as_text=True))
        self._ativar(True)
        self.assertIn('Novidade: Gestão de Bolões', self.client.get('/dashboard').get_data(as_text=True))

    def test_admin_pre_visualiza_landing_com_modulo_desligado(self):
        self._ativar(False)
        self._logar(self.admin['id'])
        self.assertEqual(self.client.get('/').status_code, 302)  # sem o parâmetro, vai para o painel
        html = self.client.get('/?preview=boloes').get_data(as_text=True)
        self.assertIn('Novidade: Gestão de Bolões', html)

    def test_usuario_comum_nao_usa_pre_visualizacao(self):
        self._ativar(False)
        self._logar(self.user['id'])
        self.assertEqual(self.client.get('/?preview=boloes').status_code, 302)


if __name__ == '__main__':
    unittest.main()

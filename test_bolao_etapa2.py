"""Etapa 2 dos bolões: organizador cria bolão a partir de um fechamento salvo e a vitrine lista os abertos."""

import json
import unittest
import uuid
from unittest.mock import patch

import bolao
import database
from app import app
from core import LOTERIAS_CONFIG, LoteriaType

MEGA = LOTERIAS_CONFIG[LoteriaType.MEGA_SENA]


class TestValidacaoJogos(unittest.TestCase):

    def test_valida_e_ordena(self):
        self.assertEqual(bolao.validar_jogos(MEGA, [[6, 5, 4, 3, 2, 1]]), [[1, 2, 3, 4, 5, 6]])

    def test_rejeita_invalidos(self):
        for jogos in ([], None, [[1, 2, 3, 4, 5, 61]], [[1, 1, 2, 3, 4, 5]], [['1', 2, 3, 4, 5, 6]], [[True, 2, 3, 4, 5, 6]]):
            with self.assertRaises(ValueError, msg=jogos):
                bolao.validar_jogos(MEGA, jogos)

    def test_permissoes(self):
        ativo, inativo = {'ativo': True}, {'ativo': False}
        self.assertTrue(bolao.pode_organizar({'role': 'admin'}, inativo))
        self.assertTrue(bolao.pode_organizar({'role': 'organizador'}, ativo))
        self.assertFalse(bolao.pode_organizar({'role': 'organizador'}, inativo))
        self.assertFalse(bolao.pode_organizar({'role': 'user'}, ativo))
        self.assertFalse(bolao.pode_organizar({'role': 'organizador', 'is_blocked': 1}, ativo))
        self.assertFalse(bolao.pode_organizar(None, ativo))


class TestFluxoOrganizador(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()
        sufixo = uuid.uuid4().hex[:8]
        cls.org = database.create_user(f'org-{sufixo}@teste.com', 'senha123', role='user')
        database.update_user(cls.org['id'], role='organizador')
        cls.outro = database.create_user(f'outro-{sufixo}@teste.com', 'senha123')
        database.save_bolao_config({'ativo': True, 'taxa_tipo': 'percentual', 'taxa_valor': '20',
                                    'min_cotas': 2, 'max_cotas': 50})

    @classmethod
    def tearDownClass(cls):
        database.save_bolao_config({'ativo': False})

    def setUp(self):
        self.client = app.test_client()
        self._logar(self.org['id'])
        self.proximo = patch('conferencia.proximo_concurso', return_value=3000)
        self.proximo.start()
        self.aposta_id = database.salvar_aposta('mega_sena', 'fechamento', [[1, 2, 3, 4, 5, 6, 7]] * 3, 7,
                                                user_id=self.org['id'], concurso_alvo=3000)

    def tearDown(self):
        self.proximo.stop()

    def _logar(self, user_id):
        with self.client.session_transaction() as s:
            s['user_id'] = user_id

    def _post(self, url, dados=None):
        return self.client.post(url, data=json.dumps(dados or {}), content_type='application/json')

    def test_preview_usa_taxa_do_admin(self):
        r = self._post('/api/boloes/preview', {'aposta_id': self.aposta_id, 'total_cotas': 10})
        self.assertEqual(r.status_code, 200, r.get_json())
        d = r.get_json()
        # 3 jogos de 7 números na Mega = 3 x R$ 42,00 = R$ 126,00 + 20% = R$ 151,20 / 10
        self.assertEqual(d['custo_caixa'], 126.0)
        self.assertEqual(d['taxa_servico'], 25.2)
        self.assertEqual(d['valor_cota'], 15.12)
        self.assertEqual(d['concurso'], 3000)

    def test_cliente_nao_define_preco(self):
        r = self._post('/api/boloes', {'aposta_id': self.aposta_id, 'total_cotas': 10,
                                       'valor_cota': 0.01, 'taxa_valor': 0, 'jogos': [[1, 2, 3, 4, 5, 6]]})
        self.assertEqual(r.status_code, 201, r.get_json())
        b = database.get_bolao(r.get_json()['bolao_id'], com_jogos=True)
        self.assertEqual(float(b['valor_cota']), 15.12)
        self.assertEqual(len(b['jogos']), 3)

    def test_cria_lista_e_fecha(self):
        r = self._post('/api/boloes', {'aposta_id': self.aposta_id, 'total_cotas': 12, 'titulo': 'Bolão da Firma'})
        self.assertEqual(r.status_code, 201, r.get_json())
        bolao_id = r.get_json()['bolao_id']

        b = database.get_bolao(bolao_id)
        self.assertEqual(b['cotas_disponiveis'], 12)
        self.assertEqual(b['status'], 'aberto')
        self.assertIn(bolao_id, [x['id'] for x in database.listar_boloes_abertos()])

        vitrine = self.client.get('/boloes').get_data(as_text=True)
        self.assertIn('Bolão da Firma', vitrine)
        self.assertIn('12 de 12', vitrine)
        detalhe = self.client.get(f'/boloes/{bolao_id}')
        self.assertEqual(detalhe.status_code, 200)
        self.assertIn('Prestação de contas', detalhe.get_data(as_text=True))
        self.assertEqual(self.client.get('/organizador').status_code, 200)

        self._logar(self.outro['id'])
        self.assertEqual(self._post(f'/api/boloes/{bolao_id}/fechar').status_code, 403)
        self._logar(self.org['id'])
        self.assertEqual(self._post(f'/api/boloes/{bolao_id}/fechar').status_code, 200)
        self.assertEqual(database.get_bolao(bolao_id)['status'], 'fechado')
        self.assertNotIn(bolao_id, [x['id'] for x in database.listar_boloes_abertos()])

    def test_usuario_comum_nao_cria(self):
        self._logar(self.outro['id'])
        self.assertEqual(self._post('/api/boloes', {'aposta_id': self.aposta_id, 'total_cotas': 10}).status_code, 403)

    def test_nao_usa_aposta_de_outro(self):
        alheia = database.salvar_aposta('mega_sena', 'fechamento', [[1, 2, 3, 4, 5, 6]], 6,
                                        user_id=self.outro['id'], concurso_alvo=3000)
        self.assertEqual(self._post('/api/boloes', {'aposta_id': alheia, 'total_cotas': 10}).status_code, 404)

    def test_concurso_ja_sorteado(self):
        antiga = database.salvar_aposta('mega_sena', 'fechamento', [[1, 2, 3, 4, 5, 6]], 6,
                                        user_id=self.org['id'], concurso_alvo=2990)
        r = self._post('/api/boloes', {'aposta_id': antiga, 'total_cotas': 10})
        self.assertEqual(r.status_code, 400)
        self.assertIn('já foi sorteado', r.get_json()['erro'])

    def test_cotas_fora_da_faixa(self):
        self.assertEqual(self._post('/api/boloes', {'aposta_id': self.aposta_id, 'total_cotas': 51}).status_code, 400)

    def test_loteria_nao_suportada(self):
        sete = database.salvar_aposta('super_sete', 'manual', [[1, 2, 3, 4, 5, 6, 7]], 7,
                                      user_id=self.org['id'], concurso_alvo=3000)
        self.assertEqual(self._post('/api/boloes', {'aposta_id': sete, 'total_cotas': 10}).status_code, 400)

    def test_modulo_desligado_esconde_vitrine_e_bloqueia_organizador(self):
        database.save_bolao_config({'ativo': False})
        try:
            self.assertEqual(self.client.get('/boloes').status_code, 302)
            self.assertEqual(self.client.get('/api/boloes').status_code, 404)
            self.assertEqual(self._post('/api/boloes', {'aposta_id': self.aposta_id, 'total_cotas': 10}).status_code, 403)
        finally:
            database.save_bolao_config({'ativo': True})


if __name__ == '__main__':
    unittest.main()

"""Testes da precificação de bolões (etapa 1) e das rotas de configuração do admin."""

import json
import unittest
from decimal import Decimal
from unittest.mock import patch

import bolao
from core import LOTERIAS_CONFIG, LoteriaType

LOTOFACIL = LOTERIAS_CONFIG[LoteriaType.LOTOFACIL]
MEGA = LOTERIAS_CONFIG[LoteriaType.MEGA_SENA]


def _cfg(**kw):
    return bolao.normalizar_config({'taxa_tipo': 'percentual', 'taxa_valor': '20', **kw})


class TestPrecificacao(unittest.TestCase):

    def test_custo_jogo_usa_tabela_caixa(self):
        self.assertEqual(bolao.custo_jogo(LOTOFACIL, 15), Decimal('3.5'))
        self.assertEqual(bolao.custo_jogo(LOTOFACIL, 16), Decimal('56.0'))
        self.assertEqual(bolao.custo_jogo(MEGA, 7), Decimal('42.0'))

    def test_exemplo_lotofacil_percentual(self):
        jogos = [list(range(1, 17))] * 10
        p = bolao.calcular_precos(LOTOFACIL, jogos, 12, _cfg())
        self.assertEqual(p['custo_caixa'], Decimal('560.00'))
        self.assertEqual(p['taxa_servico'], Decimal('112.00'))
        self.assertEqual(p['custo_total'], Decimal('672.00'))
        self.assertEqual(p['valor_cota'], Decimal('56.00'))
        self.assertEqual(p['sobra_arredondamento'], Decimal('0'))

    def test_taxa_fixa(self):
        p = bolao.calcular_precos(MEGA, [[1, 2, 3, 4, 5, 6]] * 10, 4, _cfg(taxa_tipo='fixa', taxa_valor='50'))
        self.assertEqual(p['custo_total'], Decimal('110.00'))
        self.assertEqual(p['valor_cota'], Decimal('27.50'))

    def test_arredonda_cota_para_cima(self):
        p = bolao.calcular_precos(MEGA, [[1, 2, 3, 4, 5, 6]] * 5, 7, _cfg(taxa_valor='0'))
        # R$ 30,00 / 7 = 4,2857... -> 4,29; a arrecadação nunca fica abaixo do custo
        self.assertEqual(p['valor_cota'], Decimal('4.29'))
        self.assertGreaterEqual(p['arrecadacao_maxima'], p['custo_total'])
        self.assertEqual(p['sobra_arredondamento'], Decimal('0.03'))

    def test_valida_cotas_e_jogos(self):
        cfg = _cfg(min_cotas=2, max_cotas=10)
        with self.assertRaises(ValueError):
            bolao.calcular_precos(MEGA, [[1, 2, 3, 4, 5, 6]], 11, cfg)
        with self.assertRaises(ValueError):
            bolao.calcular_precos(MEGA, [[1, 2, 3, 4, 5, 6]], 1, cfg)
        with self.assertRaises(ValueError):
            bolao.calcular_precos(MEGA, [[1, 2, 3]], 5, cfg)
        with self.assertRaises(ValueError):
            bolao.calcular_precos(MEGA, [], 5, cfg)


class TestConfig(unittest.TestCase):

    def test_padrao_quando_vazio_ou_invalido(self):
        self.assertEqual(bolao.carregar_config(None), bolao.CONFIG_PADRAO)
        self.assertEqual(bolao.carregar_config('{"taxa_tipo": "x"}'), bolao.CONFIG_PADRAO)
        self.assertEqual(bolao.carregar_config('lixo'), bolao.CONFIG_PADRAO)

    def test_rejeita_valores_invalidos(self):
        for dados in ({'taxa_valor': '101'}, {'taxa_valor': '-1'}, {'taxa_valor': 'abc'},
                      {'min_cotas': 10, 'max_cotas': 5}, {'minutos_reserva': 0}, {'taxa_tipo': 'outro'}):
            with self.assertRaises(ValueError, msg=dados):
                bolao.normalizar_config(dados)

    def test_taxa_fixa_pode_passar_de_100(self):
        self.assertEqual(bolao.normalizar_config({'taxa_tipo': 'fixa', 'taxa_valor': '150'})['taxa_valor'], '150.00')

    def test_ignora_chaves_desconhecidas(self):
        self.assertNotIn('hack', bolao.normalizar_config({'hack': 1}))


ADMIN = {'id': 1, 'role': 'admin', 'is_blocked': 0, 'must_change_password': 0, 'email': 'a@a'}
USER = {**ADMIN, 'role': 'user'}


class TestRotasAdmin(unittest.TestCase):

    def setUp(self):
        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()
        with self.client.session_transaction() as s:
            s['user_id'] = 1

    def _post(self, url, dados):
        return self.client.post(url, data=json.dumps(dados), content_type='application/json')

    @patch('database.get_user_by_id', return_value=USER)
    def test_usuario_comum_nao_acessa(self, _):
        self.assertNotEqual(self._post('/api/admin/boloes/config', {'taxa_valor': '5'}).status_code, 200)

    @patch('database.set_setting', return_value=True)
    @patch('database.get_setting', return_value=None)
    @patch('database.get_user_by_id', return_value=ADMIN)
    def test_admin_salva_taxa(self, _u, _g, set_setting):
        r = self._post('/api/admin/boloes/config', {'taxa_tipo': 'percentual', 'taxa_valor': '15', 'ativo': True})
        self.assertEqual(r.status_code, 200)
        salvo = json.loads(set_setting.call_args[0][1])
        self.assertEqual(salvo['taxa_valor'], '15.00')
        self.assertTrue(salvo['ativo'])

    @patch('database.get_setting', return_value=None)
    @patch('database.get_user_by_id', return_value=ADMIN)
    def test_admin_config_invalida(self, *_):
        self.assertEqual(self._post('/api/admin/boloes/config', {'taxa_valor': '200'}).status_code, 400)

    @patch('database.get_setting', return_value=None)
    @patch('database.get_user_by_id', return_value=ADMIN)
    def test_simulador(self, *_):
        r = self._post('/api/admin/boloes/simular', {'loteria_type': 'lotofacil', 'dezenas_por_jogo': 16,
                                                      'quantidade_jogos': 10, 'total_cotas': 12,
                                                      'config': {'taxa_valor': '20'}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['valor_cota'], 56.0)
        r = self._post('/api/admin/boloes/simular', {'loteria_type': 'xyz'})
        self.assertEqual(r.status_code, 400)


if __name__ == '__main__':
    unittest.main()

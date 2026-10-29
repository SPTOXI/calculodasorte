"""Etapa 3 dos bolões: compra de cota via Pix (InfinitePay), reserva com prazo e bilhete com hash."""

import json
import re
import threading
import unittest
import uuid
from unittest.mock import MagicMock, patch

import database
import app as app_module
from app import app


def _link_ok(*_a, **_k):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {'url': 'https://checkout.infinitepay.io/teste'}
    return resp


def _confirmacao(pago=True, valor=1512):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {'success': True, 'paid': pago, 'amount': valor}
    return resp


class TestCompraCota(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()
        sufixo = uuid.uuid4().hex[:8]
        cls.org = database.create_user(f'org3-{sufixo}@teste.com', 'senha123')
        database.update_user(cls.org['id'], role='organizador')
        cls.comprador = database.create_user(f'comp-{sufixo}@teste.com', 'senha123', name='Maria Souza')
        cls.outro = database.create_user(f'comp2-{sufixo}@teste.com', 'senha123')
        database.save_bolao_config({'ativo': True, 'taxa_tipo': 'percentual', 'taxa_valor': '20',
                                    'min_cotas': 2, 'max_cotas': 50, 'minutos_reserva': 15})

    @classmethod
    def tearDownClass(cls):
        database.save_bolao_config({'ativo': False})

    def setUp(self):
        app_module._rate_limits.clear()
        self.client = app.test_client()
        self._logar(self.org['id'])
        with patch('conferencia.proximo_concurso', return_value=3000):
            aposta = database.salvar_aposta('mega_sena', 'fechamento', [[1, 2, 3, 4, 5, 6, 7]] * 3, 7,
                                            user_id=self.org['id'], concurso_alvo=3000)
            r = self._post('/api/boloes', {'aposta_id': aposta, 'total_cotas': 2})
        self.assertEqual(r.status_code, 201, r.get_json())
        self.bolao_id = r.get_json()['bolao_id']  # 2 cotas de R$ 75,60
        self._logar(self.comprador['id'])

    def _logar(self, user_id):
        with self.client.session_transaction() as s:
            s['user_id'] = user_id

    def _post(self, url, dados=None):
        return self.client.post(url, data=json.dumps(dados or {}), content_type='application/json')

    def _comprar(self, aceite=True):
        with patch('app.requests.post', side_effect=_link_ok) as link:
            r = self._post(f'/api/boloes/{self.bolao_id}/comprar', {'aceite_termos': aceite})
        return r, link

    def _webhook(self, payment_id, pago=True, valor=7560):
        with patch('app.requests.post', return_value=_confirmacao(pago, valor)):
            return self._post('/api/webhook/infinitepay', {'order_nsu': str(payment_id),
                                                          'transaction_nsu': 'tx1', 'invoice_slug': 'slug1'})

    def test_exige_aceite_dos_termos(self):
        r, link = self._comprar(aceite=False)
        self.assertEqual(r.status_code, 400)
        link.assert_not_called()
        self.assertEqual(database.get_bolao(self.bolao_id)['cotas_disponiveis'], 2)

    def test_compra_reserva_e_gera_checkout_com_valor_da_cota(self):
        r, link = self._comprar()
        self.assertEqual(r.status_code, 200, r.get_json())
        d = r.get_json()
        self.assertEqual(d['cota_numero'], 1)
        self.assertEqual(link.call_args.kwargs['json']['items'][0]['price'], 7560)
        self.assertIn(f'/boloes/{self.bolao_id}', link.call_args.kwargs['json']['redirect_url'])
        b = database.get_bolao(self.bolao_id)
        self.assertEqual((b['cotas_disponiveis'], b['cotas_vendidas'], b['cotas_pagas']), (1, 1, 0))
        pagamento = database.get_payment_by_id(d['payment_id'])
        self.assertEqual((pagamento['tipo'], pagamento['bolao_id']), ('cota_bolao', self.bolao_id))

    def test_repetir_compra_reaproveita_reserva(self):
        r1, _ = self._comprar()
        r2, _ = self._comprar()
        self.assertEqual(r1.get_json()['payment_id'], r2.get_json()['payment_id'])
        self.assertEqual(database.get_bolao(self.bolao_id)['cotas_disponiveis'], 1)

    def test_webhook_confirmado_gera_bilhete(self):
        pid = self._comprar()[0].get_json()['payment_id']
        self.assertEqual(self._webhook(pid).status_code, 200)

        cotas = database.listar_cotas_usuario(self.comprador['id'], self.bolao_id)
        self.assertEqual(cotas[0]['status'], 'paga')
        hash_bilhete = cotas[0]['hash_bilhete']
        self.assertRegex(hash_bilhete, r'^[0-9a-f]{64}$')

        pagina = self.client.get(f'/bilhete/{hash_bilhete}')
        self.assertEqual(pagina.status_code, 200)
        html = pagina.get_data(as_text=True)
        self.assertIn('Maria', html)
        self.assertNotIn('Souza', html)  # só o primeiro nome do titular é público
        self.assertIn('1 de 2', html)
        self.assertEqual(len(re.findall(r'[0-9a-f]{64}', html)), 2)  # hash + impressão dos jogos

        # webhook repetido não gera outro bilhete
        self._webhook(pid)
        self.assertEqual(database.listar_cotas_usuario(self.comprador['id'], self.bolao_id)[0]['hash_bilhete'], hash_bilhete)
        self.assertIn('Ver bilhete', self.client.get('/minhas-cotas').get_data(as_text=True))

    def test_webhook_nao_confirmado_nao_libera(self):
        pid = self._comprar()[0].get_json()['payment_id']
        self.assertEqual(self._webhook(pid, pago=False).status_code, 400)
        self.assertEqual(self._webhook(pid, valor=100).status_code, 400)  # pagou menos que a cota
        self.assertEqual(database.listar_cotas_usuario(self.comprador['id'], self.bolao_id)[0]['status'], 'reservada')

    def test_bilhete_inexistente(self):
        self.assertEqual(self.client.get('/bilhete/' + 'a' * 64).status_code, 404)
        self.assertEqual(self.client.get('/bilhete/xyz').status_code, 404)

    def test_esgota_e_reserva_vencida_volta_a_venda(self):
        self._comprar()
        self._logar(self.outro['id'])
        self.assertEqual(self._comprar()[0].status_code, 200)
        self._logar(self.org['id'])
        self.assertEqual(self._comprar()[0].status_code, 409)  # 2 de 2 reservadas

        with database.get_db_connection() as conn:
            conn.execute("UPDATE bolao_cotas SET reservada_ate = NOW() - INTERVAL '1 minute' WHERE bolao_id = %s AND user_id = %s",
                         (self.bolao_id, self.outro['id']))
        r, _ = self._comprar()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['cota_numero'], 2)

    def test_pagamento_apos_reserva_vencida_pega_outra_cota_livre(self):
        pid = self._comprar()[0].get_json()['payment_id']
        with database.get_db_connection() as conn:
            conn.execute("UPDATE bolao_cotas SET reservada_ate = NOW() - INTERVAL '1 minute' WHERE bolao_id = %s",
                         (self.bolao_id,))
        database.get_bolao(self.bolao_id)  # libera as reservas vencidas
        self._webhook(pid)
        cotas = database.listar_cotas_usuario(self.comprador['id'], self.bolao_id)
        self.assertEqual([c['status'] for c in cotas], ['paga'])

    def test_bolao_fechado_nao_vende(self):
        database.update_bolao_status(self.bolao_id, 'fechado')
        self.assertEqual(self._comprar()[0].status_code, 400)

    def test_compras_simultaneas_nao_vendem_a_mesma_cota(self):
        usuarios = [database.create_user(f'par-{uuid.uuid4().hex[:8]}@teste.com', 'senha123') for _ in range(4)]
        cotas, erros = [], []

        def reservar(u):
            try:
                c = database.reservar_cota(self.bolao_id, u['id'], 15)
                if c:
                    cotas.append(c['numero'])
            except Exception as e:
                erros.append(e)

        threads = [threading.Thread(target=reservar, args=(u,)) for u in usuarios]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(erros, [])
        self.assertEqual(sorted(cotas), [1, 2])


if __name__ == '__main__':
    unittest.main()

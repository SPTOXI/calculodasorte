"""Etapa 4 dos bolões: comprovante, prazo, cancelamento com reembolso, conferência e rateio do prêmio."""

import io
import json
import unittest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import app as app_module
import bolao
import boloes_rotina
import database
from app import app

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
PDF = b'%PDF-1.4\n' + b'x' * 100


def _link_ok(*_a, **_k):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {'url': 'https://checkout.infinitepay.io/teste'}
    return resp


class TestRegrasPuras(unittest.TestCase):

    def test_tipo_do_comprovante_pelos_bytes(self):
        self.assertEqual(bolao.tipo_do_comprovante(PNG), 'image/png')
        self.assertEqual(bolao.tipo_do_comprovante(PDF), 'application/pdf')
        self.assertEqual(bolao.tipo_do_comprovante(b'\xff\xd8\xff\xe0abc'), 'image/jpeg')
        self.assertIsNone(bolao.tipo_do_comprovante(b'<html><script>'))

    def test_rateio_arredonda_para_baixo(self):
        self.assertEqual(bolao.rateio_por_cota('1000', 3), Decimal('333.33'))
        with self.assertRaises(ValueError):
            bolao.rateio_por_cota('-1', 3)

    def test_prazo_a_partir_da_data_do_proximo_sorteio(self):
        dados = {'numero': 2999, 'dataProximoConcurso': '31/10/2026'}
        sorteio = bolao.data_do_sorteio(dados, 3000)
        self.assertEqual(sorteio, datetime(2026, 10, 31, 23, 0))  # 20h de Brasília
        self.assertEqual(bolao.calcular_prazo_comprovante(sorteio, 3), datetime(2026, 10, 31, 20, 0))
        self.assertIsNone(bolao.data_do_sorteio(dados, 3001))  # data só é conhecida para o próximo concurso
        self.assertIsNone(bolao.data_do_sorteio({'numero': 2999, 'dataProximoConcurso': ''}, 3000))


class TestFluxoEtapa4(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()
        sufixo = uuid.uuid4().hex[:8]
        cls.org = database.create_user(f'org4-{sufixo}@teste.com', 'senha123')
        database.update_user(cls.org['id'], role='organizador')
        cls.comprador = database.create_user(f'comp4-{sufixo}@teste.com', 'senha123', name='Ana Lima')
        cls.admin = database.create_user(f'adm4-{sufixo}@teste.com', 'senha123', role='admin')
        database.save_bolao_config({'ativo': True, 'taxa_tipo': 'percentual', 'taxa_valor': '20',
                                    'min_cotas': 2, 'max_cotas': 50, 'horas_comprovante': 3})

    @classmethod
    def tearDownClass(cls):
        database.save_bolao_config({'ativo': False})

    def setUp(self):
        app_module._rate_limits.clear()
        self.client = app.test_client()
        self._logar(self.org['id'])
        ultimo = {'numero': 2999, 'dataProximoConcurso': '31/10/2026'}
        with patch('conferencia.proximo_concurso', return_value=3000), \
                patch('updater.carregar_ultimo_resultado_local', return_value=ultimo):
            aposta = database.salvar_aposta('mega_sena', 'fechamento', [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]], 6,
                                            user_id=self.org['id'], concurso_alvo=3000)
            r = self._post('/api/boloes', {'aposta_id': aposta, 'total_cotas': 3})
        self.assertEqual(r.status_code, 201, r.get_json())
        self.bolao_id = r.get_json()['bolao_id']

    def _logar(self, user_id):
        with self.client.session_transaction() as s:
            s['user_id'] = user_id

    def _post(self, url, dados=None):
        return self.client.post(url, data=json.dumps(dados or {}), content_type='application/json')

    def _upload(self, conteudo, nome='comprovante.png'):
        return self.client.post(f'/api/boloes/{self.bolao_id}/comprovante',
                                data={'arquivo': (io.BytesIO(conteudo), nome)}, content_type='multipart/form-data')

    def _comprar_e_pagar(self, user):
        self._logar(user['id'])
        with patch('app.requests.post', side_effect=_link_ok):
            pid = self._post(f'/api/boloes/{self.bolao_id}/comprar', {'aceite_termos': True}).get_json()['payment_id']
        database.approve_payment(pid)
        return pid

    def test_prazo_definido_na_criacao(self):
        b = database.get_bolao(self.bolao_id)
        self.assertEqual(b['prazo_comprovante'], datetime(2026, 10, 31, 20, 0))
        self.assertIn('31/10/2026 17:00', self.client.get(f'/boloes/{self.bolao_id}').get_data(as_text=True))

    def test_comprovante_registra_bolao_e_libera_reservas(self):
        self._logar(self.comprador['id'])
        with patch('app.requests.post', side_effect=_link_ok):
            self._post(f'/api/boloes/{self.bolao_id}/comprar', {'aceite_termos': True})
        self._logar(self.org['id'])

        r = self._upload(PNG)
        self.assertEqual(r.status_code, 200, r.get_json())
        b = database.get_bolao(self.bolao_id)
        self.assertEqual(b['status'], 'registrado')
        self.assertEqual(b['comprovante_hash'], r.get_json()['comprovante_hash'])
        self.assertEqual(b['cotas_disponiveis'], 3)  # reserva não paga foi devolvida

        arquivo = self.client.get(f'/boloes/{self.bolao_id}/comprovante')
        self.assertEqual(arquivo.status_code, 200)
        self.assertEqual(arquivo.mimetype, 'image/png')
        self.assertEqual(arquivo.data, PNG)
        self.assertIn('inline', arquivo.headers['Content-Disposition'])

        # vendas encerradas depois do registro
        self._logar(self.comprador['id'])
        with patch('app.requests.post', side_effect=_link_ok):
            self.assertEqual(self._post(f'/api/boloes/{self.bolao_id}/comprar', {'aceite_termos': True}).status_code, 400)

    def test_comprovante_validacoes(self):
        self.assertEqual(self._upload(b'<html>nao</html>', 'x.png').status_code, 400)
        self.assertEqual(self._upload(PDF + b'0' * bolao.TAMANHO_MAX_COMPROVANTE, 'x.pdf').status_code, 400)
        self._logar(self.comprador['id'])
        self.assertEqual(self._upload(PNG).status_code, 404)  # não é o organizador

    def test_rotina_cancela_sem_comprovante_e_gera_reembolso(self):
        pid = self._comprar_e_pagar(self.comprador)
        with patch('notificacoes.email_configurado', return_value=True), \
                patch('notificacoes.enviar_email', return_value=True) as email:
            relatorio = boloes_rotina.executar(agora=datetime(2026, 10, 31, 20, 1))
        self.assertGreaterEqual(relatorio['cancelados'], 1)
        b = database.get_bolao(self.bolao_id)
        self.assertEqual(b['status'], 'cancelado')
        self.assertEqual(database.get_payment_by_id(pid)['status'], 'reembolso_pendente')
        self.assertEqual(database.listar_cotas_usuario(self.comprador['id'], self.bolao_id)[0]['status'], 'estornada')
        destinos = [c.args[0] for c in email.call_args_list]
        self.assertIn(self.comprador['email'], destinos)

        self.assertIn(pid, [r['id'] for r in database.listar_reembolsos_pendentes()])
        self._logar(self.admin['id'])
        self.assertEqual(self._post(f'/api/admin/reembolsos/{pid}/concluir').status_code, 200)
        self.assertEqual(database.get_payment_by_id(pid)['status'], 'reembolsado')
        self.assertIn('cancelado', self.client.get(f'/boloes/{self.bolao_id}').get_data(as_text=True))

    def test_rotina_alerta_uma_vez_perto_do_prazo(self):
        agora = datetime(2026, 10, 31, 8, 0)  # 12h antes do prazo
        with patch('notificacoes.email_configurado', return_value=True), \
                patch('notificacoes.enviar_email', return_value=True) as email:
            primeira = boloes_rotina.executar(agora=agora)
            enviados = email.call_count
            segunda = boloes_rotina.executar(agora=agora)
        self.assertGreaterEqual(primeira['alertas'], 1)
        self.assertEqual(segunda['alertas'], 0)
        self.assertEqual(email.call_count, enviados)  # não repete o alerta
        b = database.get_bolao(self.bolao_id)
        self.assertIsNotNone(b['alerta_prazo_em'])
        self.assertEqual(b['status'], 'aberto')

    def test_pagamento_confirmado_apos_cancelamento_vai_para_reembolso(self):
        self._logar(self.comprador['id'])
        with patch('app.requests.post', side_effect=_link_ok):
            pid = self._post(f'/api/boloes/{self.bolao_id}/comprar', {'aceite_termos': True}).get_json()['payment_id']
        database.cancelar_bolao(self.bolao_id, 'teste')
        database.approve_payment(pid)
        self.assertEqual(database.get_payment_by_id(pid)['status'], 'reembolso_pendente')

    def test_admin_cancelar_pelo_status_gera_reembolso(self):
        pid = self._comprar_e_pagar(self.comprador)
        self._logar(self.admin['id'])
        r = self._post(f'/api/admin/boloes/{self.bolao_id}/status', {'status': 'cancelado'})
        self.assertEqual(r.get_json()['reembolsos'], 1)
        self.assertEqual(database.get_payment_by_id(pid)['status'], 'reembolso_pendente')

    def test_conferencia_premiado_e_rateio(self):
        self._comprar_e_pagar(self.comprador)
        self._logar(self.org['id'])
        self.assertEqual(self._upload(PDF, 'c.pdf').status_code, 200)
        sorteio = {'status': 'conferido', 'concurso': 3000, 'data_apuracao': '31/10/2026',
                   'dezenas': [1, 2, 3, 4, 40, 50], 'segundo_sorteio': [], 'trevos': [], 'complemento': None}
        with patch('conferencia.sorteio_do_concurso', return_value=sorteio):
            relatorio = boloes_rotina.executar(agora=datetime(2026, 11, 1, 2, 0))
        self.assertGreaterEqual(relatorio['conferidos'], 1)
        b = database.get_bolao(self.bolao_id)
        self.assertEqual(b['status'], 'premiado')
        resultado = json.loads(b['resultado_json'])
        self.assertEqual(resultado['jogos'][0]['qtd_acertos'], 4)

        self._logar(self.admin['id'])
        r = self._post(f'/api/admin/boloes/{self.bolao_id}/premio', {'valor_premio': '1000,00'})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(r.get_json()['premio_por_cota'], 333.33)
        pagina = self.client.get(f'/boloes/{self.bolao_id}').get_data(as_text=True)
        self.assertIn('Bolão premiado', pagina)
        self.assertIn('R$ 333,33', pagina)

    def test_conferencia_nao_premiado(self):
        self._upload(PNG)
        sorteio = {'status': 'conferido', 'concurso': 3000, 'dezenas': [51, 52, 53, 54, 55, 56],
                   'segundo_sorteio': [], 'trevos': [], 'complemento': None}
        with patch('conferencia.sorteio_do_concurso', return_value=sorteio):
            boloes_rotina.executar(agora=datetime(2026, 11, 1, 2, 0))
        self.assertEqual(database.get_bolao(self.bolao_id)['status'], 'nao_premiado')
        self._logar(self.admin['id'])
        self.assertEqual(self._post(f'/api/admin/boloes/{self.bolao_id}/premio', {'valor_premio': '10'}).status_code, 400)

    def test_cron_inclui_rotina_dos_boloes(self):
        with patch('updater.sincronizar_todas', return_value={'sucesso': True}), \
                patch('boloes_rotina.executar', return_value={'conferidos': 0}) as rotina, \
                patch.dict('os.environ', {'CRON_SECRET': 'x'}):
            r = self.client.get('/api/cron/atualizar', headers={'Authorization': 'Bearer x'})
        self.assertEqual(r.get_json()['boloes'], {'conferidos': 0})
        rotina.assert_called_once()

    def test_painel_admin_renderiza(self):
        self._comprar_e_pagar(self.comprador)
        database.cancelar_bolao(self.bolao_id, 'teste')
        self._logar(self.admin['id'])
        html = self.client.get('/admin?aba=tab-boloes').get_data(as_text=True)
        self.assertIn('Reembolsos Pendentes', html)
        self.assertIn('Rodar rotina agora', html)


if __name__ == '__main__':
    unittest.main()

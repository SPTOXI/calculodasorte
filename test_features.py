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
from unittest.mock import patch, MagicMock
from app import app
import updater
import database

def _resposta_infinitepay(dados, status=200):
    resp = MagicMock(status_code=status)
    resp.json.return_value = dados
    return resp


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
        admin = database.get_user_by_email('silvio.luis.morais@gmail.com')
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['id']
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
        # A aposta concorre no próximo concurso: fica aguardando até o resultado sair
        if dados_conf.get('status') == 'aguardando':
            self.assertNotIn('jogos_conferidos', dados_conf)
        else:
            self.assertIn('dezenas_sorteadas', dados_conf)
            self.assertGreater(len(dados_conf['jogos_conferidos']), 0)

    def test_08_excluir_aposta_usuario(self):
        """Testa a exclusão de uma aposta salva"""
        # Salva aposta auxiliar para testar exclusão
        res_salvar = self.client.post('/api/apostas/salvar',
            data=json.dumps({
                'loteria_type': 'mega_sena',
                'modalidade': 'fechamento',
                'jogos': [[1, 2, 3, 4, 5, 6]],
                'titulo': 'Para Teste Exclusao'
            }),
            content_type='application/json'
        )
        aposta_id = res_salvar.get_json()['aposta_id']
        res_del = self.client.delete(f'/api/apostas/{aposta_id}')
        self.assertEqual(res_del.status_code, 200)
        dados_del = res_del.get_json()
        self.assertTrue(dados_del['sucesso'])

    def test_09_cadastro_novo_usuario_com_credito(self):
        """Testa cadastro de novo apostador com 1 crédito grátis de análise"""
        import uuid
        email_teste = f"apostador_{uuid.uuid4().hex[:8]}@teste.com"
        res = self.client.post('/cadastro', data={
            'nome': 'Apostador Teste',
            'email': email_teste,
            'password': 'senha123teste',
            'confirm_password': 'senha123teste',
            'termos_lgpd': 'on'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'dashboard', res.request.path.encode() or b'')

    def test_10_protecao_rotas_sem_login(self):
        """Testa que rotas privadas redirecionam para /login quando não autenticado"""
        anon_client = app.test_client()
        res = anon_client.get('/dashboard', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers.get('Location', ''))

    def test_11_checkout_pix_e_ativacao(self):
        """Testa criação de pedido PIX e ativação de plano"""
        import uuid
        import database
        email = f"vip_{uuid.uuid4().hex[:8]}@teste.com"
        user = database.create_user(email, 'senha123', name='VIP User')
        user_id = user['id']
        
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

        # Gerar PIX VIP R$ 49,90
        res_pix = self.client.post('/api/checkout/pix',
            data=json.dumps({'tipo': 'vip_mensal'}),
            content_type='application/json'
        )
        self.assertEqual(res_pix.status_code, 200)
        dados_pix = res_pix.get_json()
        self.assertTrue(dados_pix['sucesso'])
        self.assertEqual(dados_pix['valor'], 49.90)
        self.assertIn('pix_copia_cola', dados_pix)
        payment_id = dados_pix['payment_id']

        # O aviso do usuário não libera acesso: o PIX precisa ser conferido
        res_conf = self.client.post(f'/api/checkout/confirmar/{payment_id}')
        self.assertEqual(res_conf.status_code, 200)
        self.assertFalse(res_conf.get_json()['sucesso'])
        self.assertFalse(database.check_user_access(user_id)['is_vip'])

        # O administrador confere o extrato e aprova
        self.assertTrue(database.approve_payment(payment_id))
        res_conf = self.client.post(f'/api/checkout/confirmar/{payment_id}')
        self.assertEqual(res_conf.get_json()['novo_status'], 'aprovado')

        # Checar se usuário agora tem VIP ativo
        access = database.check_user_access(user_id)
        self.assertTrue(access['is_vip'])
        self.assertTrue(access['has_access'])

    def test_12_agente_ia_parecer_e_chat(self):
        """Testa parecer técnico e chat interativo com o Consultor IA (usando motor heurístico nativo)"""
        import uuid
        import database
        email = f"ia_{uuid.uuid4().hex[:8]}@teste.com"
        user = database.create_user(email, 'senha123', name='IA Tester')
        user_id = user['id']
        # Conta nova começa sem crédito; o teste é do parecer e do chat, não do paywall
        database.add_user_credits(user_id, 1)

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

        jogos = [
            [4, 11, 23, 38, 45, 59],
            [7, 14, 28, 35, 49, 52]
        ]
        # O parecer vem junto da geração (sem chamada extra de IA)
        res_gerar = self.client.post('/api/gerar-multiplos-jogos/mega_sena',
            data=json.dumps({'quantidade_jogos': 2, 'dezenas_por_jogo': 6}),
            content_type='application/json'
        )
        self.assertEqual(res_gerar.status_code, 200)
        self.assertIn('parecer', res_gerar.get_json())

        # Teste do chat
        res_chat = self.client.post('/api/ia/chat',
            data=json.dumps({
                'mensagem': 'Qual a melhor estratégia para o próximo concurso?',
                'loteria_type': 'mega_sena',
                'jogos_recentes': jogos
            }),
            content_type='application/json'
        )
        self.assertEqual(res_chat.status_code, 200)
        data_c = res_chat.get_json()
        self.assertTrue(data_c['sucesso'])
        self.assertIn('resposta', data_c)
        self.assertGreater(len(data_c['resposta']), 20)

    def test_13_paywall_creditos_esgotados(self):
        """Testa se o gerador bloqueia e retorna precisa_plano=True após créditos esgotados"""
        import uuid
        import database
        email = f"sem_credito_{uuid.uuid4().hex[:8]}@teste.com"
        user = database.create_user(email, 'senha123', name='Free User')
        user_id = user['id']

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

        # Consumir o único crédito de boas-vindas
        database.consume_user_credit(user_id)
        access = database.check_user_access(user_id)
        self.assertEqual(access['credits'], 0)
        self.assertFalse(access['has_access'])

        # Tentar gerar novo jogo deve ser barrado com 403
        res = self.client.post('/api/gerar-multiplos-jogos/mega_sena',
            data=json.dumps({'quantidade_jogos': 2, 'dezenas_por_jogo': 6}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertFalse(data['sucesso'])
        self.assertTrue(data.get('precisa_plano'))

    def test_14_infinitepay_checkout_e_webhook(self):
        """Testa geração de link InfinitePay (com handle silvio_morais_) e aprovação via Webhook"""
        import uuid
        import database
        email = f"infpay_{uuid.uuid4().hex[:8]}@teste.com"
        user = database.create_user(email, 'senha123', name='Cliente InfinitePay')
        user_id = user['id']

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

        # 1. Gerar link de checkout InfinitePay
        link = 'https://checkout.infinitepay.io/silvio_morais_/abc123'
        with patch('app.requests.post', return_value=_resposta_infinitepay({'url': link})):
            res_link = self.client.post('/api/checkout/infinitepay',
                data=json.dumps({'tipo': 'vip_mensal'}),
                content_type='application/json'
            )
        self.assertEqual(res_link.status_code, 200)
        data_link = res_link.get_json()
        self.assertTrue(data_link['sucesso'])
        self.assertIn('checkout.infinitepay.io/silvio_morais_', data_link['checkout_url'])
        payment_id = data_link['payment_id']
        webhook = json.dumps({
            'order_nsu': str(payment_id),
            'transaction_nsu': 'inf_tx_99998888',
            'capture_method': 'pix',
            'slug': 'calc-sorte-vip'
        })

        # 2. Webhook forjado (a InfinitePay não confirma o pagamento) é rejeitado
        with patch('app.requests.post', return_value=_resposta_infinitepay({'success': True, 'paid': False})):
            res_forjado = self.client.post('/api/webhook/infinitepay', data=webhook, content_type='application/json')
        self.assertEqual(res_forjado.status_code, 400)
        self.assertFalse(database.check_user_access(user_id)['is_vip'])

        # Pago com valor menor que o cobrado também é rejeitado
        with patch('app.requests.post', return_value=_resposta_infinitepay({'success': True, 'paid': True, 'amount': 100})):
            res_menor = self.client.post('/api/webhook/infinitepay', data=webhook, content_type='application/json')
        self.assertEqual(res_menor.status_code, 400)

        # Webhook legítimo: a InfinitePay confirma o pagamento
        with patch('app.requests.post', return_value=_resposta_infinitepay({'success': True, 'paid': True, 'amount': 4990})) as consulta:
            res_webhook = self.client.post('/api/webhook/infinitepay', data=webhook, content_type='application/json')
        self.assertEqual(consulta.call_args.args[0], 'https://api.checkout.infinitepay.io/payment_check')
        self.assertEqual(consulta.call_args.kwargs['json']['order_nsu'], str(payment_id))
        self.assertEqual(res_webhook.status_code, 200)
        self.assertTrue(res_webhook.get_json()['sucesso'])

        # 3. Verificar se o usuário agora tem plano VIP ativado
        access = database.check_user_access(user_id)
        self.assertTrue(access['is_vip'])
        self.assertTrue(access['has_access'])

        # 4. Checar rota de status
        res_status = self.client.get(f'/api/checkout/status/{payment_id}')
        self.assertEqual(res_status.status_code, 200)
        self.assertTrue(res_status.get_json()['is_approved'])

    def test_15_admin_gestao_pagamentos(self):
        """Testa listagem e aprovação manual de pagamentos no painel administrativo"""
        import uuid
        import database
        admin = database.get_user_by_email('silvio.luis.morais@gmail.com')
        self.assertIsNotNone(admin)

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['id']

        # Criar pagamento pendente auxiliar
        pagamento = database.create_payment(user_id=admin['id'], tipo='avulso', valor=5.00)
        p_id = pagamento['id']

        # Listar pagamentos
        res_list = self.client.get('/api/admin/pagamentos')
        self.assertEqual(res_list.status_code, 200)
        data_l = res_list.get_json()
        self.assertTrue(data_l['sucesso'])
        self.assertGreaterEqual(data_l['total'], 1)

        # Aprovar manualmente
        res_aprov = self.client.post(f'/api/admin/pagamentos/{p_id}/aprovar')
        self.assertEqual(res_aprov.status_code, 200)
        self.assertTrue(res_aprov.get_json()['sucesso'])

    def test_16_lgpd_paginas_institucionais(self):
        """Testa disponibilidade das páginas de Política de Privacidade e Termos de Uso (LGPD)"""
        # 1. Página de Privacidade
        res_priv = self.client.get('/privacidade')
        self.assertEqual(res_priv.status_code, 200)
        texto_priv = res_priv.get_data(as_text=True)
        self.assertIn('Política de Privacidade', texto_priv)
        self.assertIn('Lei nº 13.709/2018', texto_priv)
        self.assertIn('silvio.luis.morais@gmail.com', texto_priv)
        self.assertIn('Art. 18', texto_priv)

        # 2. Página de Termos
        res_termos = self.client.get('/termos')
        self.assertEqual(res_termos.status_code, 200)
        texto_termos = res_termos.get_data(as_text=True)
        self.assertIn('Termos de Uso', texto_termos)
        self.assertIn('Jogo Responsável', texto_termos)
        self.assertIn('18 anos', texto_termos)
        self.assertIn('R$ 5,00', texto_termos)

    def test_17_lgpd_cadastro_consentimento(self):
        """Testa validação de consentimento obrigatório LGPD no formulário de cadastro"""
        import uuid
        email_teste_sem_lgpd = f"sem_lgpd_{uuid.uuid4().hex[:6]}@teste.com"
        email_teste_com_lgpd = f"com_lgpd_{uuid.uuid4().hex[:6]}@teste.com"

        # 1. Tentar cadastro sem marcar o checkbox de termos LGPD (deve falhar)
        res_falha = self.client.post('/cadastro', data={
            'nome': 'Apostador Sem Consentimento',
            'email': email_teste_sem_lgpd,
            'password': 'senha1234teste',
            'confirm_password': 'senha1234teste'
            # 'termos_lgpd' omitido propositalmente
        })
        self.assertEqual(res_falha.status_code, 200)
        texto_falha = res_falha.get_data(as_text=True)
        self.assertIn('Você deve concordar com os Termos de Uso e Política de Privacidade (LGPD)', texto_falha)

        # 2. Cadastro com checkbox LGPD marcado (deve suceder)
        res_sucesso = self.client.post('/cadastro', data={
            'nome': 'Apostador Com Consentimento',
            'email': email_teste_com_lgpd,
            'password': 'senha1234teste',
            'confirm_password': 'senha1234teste',
            'termos_lgpd': 'on'
        }, follow_redirects=True)
        self.assertEqual(res_sucesso.status_code, 200)
        user_db = database.get_user_by_email(email_teste_com_lgpd)
        self.assertIsNotNone(user_db)
        self.assertIsNotNone(user_db.get('accepted_terms_at'), "accepted_terms_at deve ser gravado")

    def test_18_lgpd_portabilidade_e_exclusao(self):
        """Testa endpoints de Direitos do Titular LGPD: Exportação (Art. 18, V) e Eliminação (Art. 18, VI)"""
        import uuid
        email_titular = f"titular_lgpd_{uuid.uuid4().hex[:6]}@teste.com"
        user = database.create_user(email_titular, 'senha1234', 'Titular de Teste LGPD', accepted_terms=True)
        user_id = user['id']

        # Salvar aposta simulada
        database.salvar_aposta('mega_sena', 'manual', [[5, 10, 15, 20, 25, 30]], 6, user_id=user_id, titulo='Aposta do Titular')

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

        # 1. Portabilidade de dados (Art. 18, V)
        res_exp = self.client.get('/api/usuario/exportar-dados')
        self.assertEqual(res_exp.status_code, 200)
        data_exp = res_exp.get_json()
        self.assertIn('Relatório Oficial de Portabilidade', data_exp['lgpd_declaracao'])
        self.assertEqual(data_exp['titular']['email'], email_titular)
        self.assertNotIn('password_hash', data_exp['titular'], "Hashes confidenciais não devem vazar na portabilidade")
        self.assertEqual(data_exp['total_apostas_registradas'], 1)

        # 2. Eliminação dos dados / Esquecimento (Art. 18, VI)
        res_del = self.client.post('/api/usuario/excluir-conta')
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()['sucesso'])

        # Verificar se o usuário e suas apostas foram completamente eliminados do banco
        user_apos_exclusao = database.get_user_by_id(user_id)
        self.assertIsNone(user_apos_exclusao)
        apostas_apos = database.listar_apostas(user_id=user_id)
        self.assertEqual(len(apostas_apos), 0)

    def test_19_preco_unico_analise_avulsa(self):
        """Testa garantia de Preço Único de R$ 5,00 para qualquer análise avulsa"""
        import uuid
        email_pagador = f"pagador_{uuid.uuid4().hex[:6]}@teste.com"
        user = database.create_user(email_pagador, 'senha1234', 'Pagador Teste')
        with self.client.session_transaction() as sess:
            sess['user_id'] = user['id']

        # Mesmo solicitando outro valor, o backend deve padronizar rigorosamente para R$ 5,00
        res_pix = self.client.post('/api/checkout/pix',
            data=json.dumps({'tipo': 'avulso', 'valor': 2.50, 'loteria_type': 'quina'}),
            content_type='application/json'
        )
        self.assertEqual(res_pix.status_code, 200)
        data_pix = res_pix.get_json()
        self.assertEqual(data_pix['valor'], 5.00, "Preço único de análise avulsa deve ser estritamente R$ 5,00")

    def test_20_pix_emvco_e_crc16_validos(self):
        """Valida que o payload PIX Copia e Cola gerado atende estritamente à especificação BACEN / EMVCo"""
        import database
        chave = 'silvio.luis.morais@gmail.com'
        valor = 5.00
        pix = database.gerar_pix_copia_e_cola(chave, 'Calculo da Sorte', 'SAO PAULO', valor, 'CS123456')
        
        # 1. Verifica indicadores obrigatórios
        self.assertTrue(pix.startswith('00020101021126'))
        self.assertIn('010211', pix)
        self.assertIn('0014br.gov.bcb.pix', pix)
        self.assertIn(f"01{len(chave):02d}{chave}", pix)
        self.assertIn('5303986', pix) # BRL
        self.assertIn('54045.00', pix) # R$ 5.00
        self.assertIn('5802BR', pix)
        self.assertIn('6304', pix)
        
        # 2. Valida o checksum CRC-16/CCITT-FALSE
        payload_sem_crc = pix[:-4]
        crc_calculado = database.calcular_crc16_ccitt(payload_sem_crc)
        self.assertEqual(pix[-4:], crc_calculado, "Checksum CRC16 do PIX deve bater exatamente com o algoritmo oficial BACEN")

    def test_21_geracao_qrcode_svg_base64(self):
        """Valida a geração de QR Code vetorial SVG em base64 tanto na função direta quanto na rota /api/checkout/pix"""
        import database
        import uuid
        import base64

        # 1. Teste da função direta
        pix_code = "00020101021126500014br.gov.bcb.pix0128silvio.luis.morais@gmail.com52040000530398654045.005802BR5916Calculo da Sorte6009SAO PAULO62070503***6304F4C2"
        qr_uri = database.gerar_qrcode_pix_base64(pix_code)
        self.assertTrue(qr_uri.startswith('data:image/svg+xml;base64,'))
        base64_part = qr_uri.split(',', 1)[1]
        svg_content = base64.b64decode(base64_part).decode('utf-8')
        self.assertIn('<svg', svg_content)
        self.assertIn('</svg>', svg_content)

        # 2. Teste via rota /api/checkout/pix
        email = f"qrcode_user_{uuid.uuid4().hex[:6]}@teste.com"
        u = database.create_user(email, '123456', 'Tester QR')
        with self.client.session_transaction() as sess:
            sess['user_id'] = u['id']

        res = self.client.post('/api/checkout/pix',
            data=json.dumps({'tipo': 'avulso', 'valor': 5.00}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['sucesso'])
        self.assertIn('pix_qr_code_base64', data)
        self.assertTrue(data['pix_qr_code_base64'].startswith('data:image/svg+xml;base64,'))

    def test_22_fluxo_avulso_e_auto_aprovacao_retorno(self):
        """Valida que a compra do avulso de R$ 5,00 libera créditos após retorno de checkout ou confirmação"""
        import database
        import uuid

        email = f"avulso_{uuid.uuid4().hex[:6]}@teste.com"
        u = database.create_user(email, '123456', 'Avulso Tester', credits=0)
        user_id = u['id']

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

        # 1. Usuário começa sem créditos
        access_inicial = database.check_user_access(user_id)
        self.assertFalse(access_inicial['has_access'])
        self.assertEqual(access_inicial['credits'], 0)

        # 2. Criação do pagamento avulso
        pagamento = database.create_payment(user_id=user_id, tipo='avulso', valor=5.00)
        p_id = pagamento['id']
        self.assertEqual(pagamento['valor'], 5.00)
        self.assertEqual(pagamento['status'], 'pendente')

        # 3. Só o parâmetro checkout=sucesso na URL não libera acesso
        res_forjado = self.client.get(f'/api/checkout/status/{p_id}?checkout=sucesso')
        self.assertFalse(res_forjado.get_json()['is_approved'])
        self.assertFalse(database.check_user_access(user_id)['has_access'])

        # Outro usuário não consulta nem aprova este pagamento
        outro = database.create_user(f"outro_{uuid.uuid4().hex[:6]}@teste.com", '123456', 'Outro', credits=0)
        with self.client.session_transaction() as sess:
            sess['user_id'] = outro['id']
        self.assertEqual(self.client.get(f'/api/checkout/status/{p_id}').status_code, 404)
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

        # Retorno do checkout confirmado pela InfinitePay libera o acesso
        with patch('app.requests.post', return_value=_resposta_infinitepay({'success': True, 'paid': True, 'amount': 500})):
            res_status = self.client.get(f'/api/checkout/status/{p_id}?checkout=sucesso&transaction_nsu=tx1&slug=abc')
        self.assertEqual(res_status.status_code, 200)
        data_st = res_status.get_json()
        self.assertTrue(data_st['is_approved'])
        self.assertEqual(data_st['status'], 'aprovado')
        self.assertTrue(data_st['access']['has_access'])
        # A análise avulsa libera 24 h de acesso (plano vip_24h)
        self.assertEqual(data_st['access']['plan'], 'vip_24h')

        # 4. Gerar jogo dentro das 24 h não consome crédito
        database.consume_user_credit(user_id)
        self.assertTrue(database.check_user_access(user_id)['has_access'])

    def test_22b_avulso_libera_24h_e_nao_vira_mensal(self):
        """O avulso de R$ 5,00 libera 24 h (vip_24h), inclusive para quem tem mensal vencido"""
        import uuid
        from datetime import datetime, timedelta

        u = database.create_user(f"av24_{uuid.uuid4().hex[:6]}@teste.com", '123456', 'Avulso 24h', credits=0)
        pagamento = database.create_payment(user_id=u['id'], tipo='avulso', valor=5.00)
        self.assertTrue(database.approve_payment(pagamento['id']))
        access = database.check_user_access(u['id'])
        self.assertEqual(access['plan'], 'vip_24h')
        validade = datetime.strptime(access['expires_at'], '%Y-%m-%d %H:%M:%S')
        self.assertLess(validade, datetime.now() + timedelta(hours=25))

        with self.client.session_transaction() as sess:
            sess['user_id'] = u['id']
        html = self.client.get('/minha-conta').get_data(as_text=True)
        self.assertIn('ACESSO 24 HORAS', html)
        self.assertNotIn('PLANO VIP MENSAL', html)

        # Mensal vencido comprando avulso vira 24 h, não mensal
        v = database.create_user(f"venc_{uuid.uuid4().hex[:6]}@teste.com", '123456', 'Mensal vencido', credits=0)
        with database.get_db_connection() as conn:
            conn.execute("UPDATE users SET plan = 'vip_mensal', vip_expires_at = %s WHERE id = %s",
                         (datetime.now() - timedelta(days=3), v['id']))
            conn.commit()
        pagamento = database.create_payment(user_id=v['id'], tipo='avulso', valor=5.00)
        database.approve_payment(pagamento['id'])
        self.assertEqual(database.check_user_access(v['id'])['plan'], 'vip_24h')

        # Mensal vigente comprando avulso continua mensal
        m = database.create_user(f"mens_{uuid.uuid4().hex[:6]}@teste.com", '123456', 'Mensal vigente', credits=0)
        database.approve_payment(database.create_payment(user_id=m['id'], tipo='vip_mensal', valor=49.90)['id'])
        database.approve_payment(database.create_payment(user_id=m['id'], tipo='avulso', valor=5.00)['id'])
        self.assertEqual(database.check_user_access(m['id'])['plan'], 'vip_mensal')

    def test_22c_cron_exige_segredo(self):
        """Com CRON_SECRET definida, /api/cron/atualizar só aceita o Bearer correto"""
        import os
        with patch.dict(os.environ, {'CRON_SECRET': 'segredo-teste'}), \
                patch('app.updater.sincronizar_todas', return_value={'sucesso': True}) as sync:
            self.assertEqual(self.client.post('/api/cron/atualizar').status_code, 401)
            res = self.client.post('/api/cron/atualizar', headers={'Authorization': 'Bearer errado'})
            self.assertEqual(res.status_code, 401)
            sync.assert_not_called()
            res = self.client.post('/api/cron/atualizar', headers={'Authorization': 'Bearer segredo-teste'})
            self.assertEqual(res.status_code, 200)
            sync.assert_called_once()

    def test_23_api_unauthenticated_returns_json_not_html(self):
        """Garante que rotas /api/* retornem JSON 401 e nunca HTML (evitando SyntaxError: Unexpected token '<')"""
        # 1. /api/checkout/pix sem autenticação
        res_pix = self.client.post('/api/checkout/pix',
            data=json.dumps({'tipo': 'avulso', 'valor': 5.00}),
            content_type='application/json'
        )
        self.assertEqual(res_pix.status_code, 401)
        self.assertIn('application/json', res_pix.headers.get('Content-Type', ''))
        data_pix = res_pix.get_json()
        self.assertIsNotNone(data_pix)
        self.assertFalse(data_pix['sucesso'])
        self.assertTrue(data_pix['requer_login'])
        self.assertIn('Autenticação necessária', data_pix['erro'])

        # 2. /api/checkout/infinitepay sem autenticação
        res_inf = self.client.post('/api/checkout/infinitepay',
            data=json.dumps({'tipo': 'avulso', 'valor': 5.00}),
            content_type='application/json'
        )
        self.assertEqual(res_inf.status_code, 401)
        self.assertIn('application/json', res_inf.headers.get('Content-Type', ''))
        data_inf = res_inf.get_json()
        self.assertIsNotNone(data_inf)
        self.assertFalse(data_inf['sucesso'])
        self.assertTrue(data_inf['requer_login'])

        # 3. Rota de API inexistente deve retornar 404 JSON, nunca HTML
        res_404 = self.client.get('/api/rota_inexistente_de_teste')
        self.assertEqual(res_404.status_code, 404)
        self.assertIn('application/json', res_404.headers.get('Content-Type', ''))
        data_404 = res_404.get_json()
        self.assertIsNotNone(data_404)
        self.assertFalse(data_404['sucesso'])

        # 4. Rota HTML pública ou restrita sem API continua redirecionando normalmente
        res_dash = self.client.get('/dashboard')
        self.assertEqual(res_dash.status_code, 302)
        self.assertIn('/login', res_dash.headers.get('Location', ''))

    def test_24_pix_bacen_compliance_and_config(self):
        """Valida conformidade estrita do payload PIX com as normas do BACEN, normalização de chaves e endpoint admin"""
        import base64

        # 1. Normalização de chaves PIX
        self.assertEqual(database.normalizar_chave_pix(' 123.456.789-01 '), '12345678901')
        self.assertEqual(database.normalizar_chave_pix('(11) 98765-4321'), '+5511987654321')
        self.assertEqual(database.normalizar_chave_pix('5511987654321'), '+5511987654321')
        self.assertEqual(database.normalizar_chave_pix(' TESTE@DOMINIO.COM '), 'teste@dominio.com')
        self.assertEqual(
            database.normalizar_chave_pix('E8B2D5D4-7A3E-4B0F-9C1D-8F2E3A4B5C6D'),
            'e8b2d5d4-7a3e-4b0f-9c1d-8f2e3a4b5c6d'
        )

        # 2. Identificação dos tipos de chave
        self.assertEqual(database.identificar_tipo_chave_pix('user@site.com'), 'email')
        self.assertEqual(database.identificar_tipo_chave_pix('+5511987654321'), 'telefone')
        self.assertEqual(database.identificar_tipo_chave_pix('12345678901'), 'cpf')
        self.assertEqual(database.identificar_tipo_chave_pix('12345678000190'), 'cnpj')
        self.assertEqual(database.identificar_tipo_chave_pix('e8b2d5d4-7a3e-4b0f-9c1d-8f2e3a4b5c6d'), 'aleatoria')

        # 3. Geração do Copia e Cola conforme BACEN
        payload = database.gerar_pix_copia_e_cola(
            chave='silvio.luis.morais@gmail.com',
            nome='Calculo da Sorte',
            cidade='SAO PAULO',
            valor=5.00,
            txid='***'
        )
        self.assertTrue(payload.startswith('000201'), "Payload deve iniciar com Tag 000201")
        self.assertIn('010211', payload, "Payload deve conter Tag 010211 (QR Code Estático)")
        self.assertIn('0014br.gov.bcb.pix', payload, "Payload deve conter GUI do BACEN")
        self.assertIn('silvio.luis.morais@gmail.com', payload)
        self.assertIn('52040000', payload)
        self.assertIn('5303986', payload)
        self.assertIn('54045.00', payload)
        self.assertIn('5802BR', payload)
        self.assertIn('62070503***', payload, "Tag 62 deve conter txid *** para QR estático sem rejeição de chave")
        self.assertIn('6304', payload)
        
        # Validar integridade do CRC16
        crc_gerado = payload[-4:]
        corpo = payload[:-4]
        crc_calculado = database.calcular_crc16_ccitt(corpo)
        self.assertEqual(crc_gerado, crc_calculado, "Checksum CRC16-CCITT deve ser válido")

        # 4. Geração de QR Code vetorial com fundo branco e quiet zone
        qr_uri = database.gerar_qrcode_pix_base64(payload)
        self.assertTrue(qr_uri.startswith('data:image/svg+xml;base64,'))
        svg_decoded = base64.b64decode(qr_uri.replace('data:image/svg+xml;base64,', '')).decode('utf-8')
        self.assertIn('<svg', svg_decoded)
        self.assertIn('<rect width="100%" height="100%" fill="#ffffff"/>', svg_decoded)

        # 5. API Admin de Configuração do PIX (/api/admin/config-pix)
        # 5.1 Sem autenticação -> 401
        res_nao_auth = self.client.get('/api/admin/config-pix')
        self.assertEqual(res_nao_auth.status_code, 401)

        # 5.2 Com admin logado
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        res_get = self.client.get('/api/admin/config-pix')
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.get_json()
        self.assertTrue(data_get['sucesso'])
        self.assertIn('config', data_get)
        self.assertIn('amostra_qr', data_get)

        # 5.3 Salvar nova configuração via POST
        res_post = self.client.post('/api/admin/config-pix',
            data=json.dumps({
                'chave': '(11) 98765-4321',
                'beneficiario': 'SILVIO LUIS MORAIS',
                'cidade': 'SAO PAULO'
            }),
            content_type='application/json'
        )
        self.assertEqual(res_post.status_code, 200)
        data_post = res_post.get_json()
        self.assertTrue(data_post['sucesso'])
        self.assertEqual(data_post['config']['chave'], '+5511987654321')
        self.assertEqual(data_post['config']['tipo'], 'telefone')
        self.assertIn('+5511987654321', data_post['amostra_copia_cola'])


if __name__ == '__main__':
    unittest.main()




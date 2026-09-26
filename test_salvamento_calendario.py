"""Salvamento automático dos jogos gerados e calendário de sorteios."""

import json
import unittest
import uuid
from datetime import datetime
from unittest.mock import patch

import database
from app import app
from core import LOTERIAS_CONFIG, LoteriaType, proximo_sorteio


class TestSalvamentoAutomatico(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        user = database.create_user(f"auto_{uuid.uuid4().hex[:8]}@teste.com", 'senha123', 'Auto', credits=5)
        self.user_id = user['id']
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id

    def test_jogos_gerados_sao_salvos(self):
        res = self.client.post('/api/gerar-multiplos-jogos/mega_sena', json={'quantidade_jogos': 3, 'dezenas_por_jogo': 6})
        data = res.get_json()
        self.assertTrue(data['aposta_id'])
        aposta = database.obter_aposta(data['aposta_id'])
        self.assertEqual(aposta['user_id'], self.user_id)
        self.assertEqual(aposta['jogos'], data['jogos'])
        self.assertEqual(aposta['concurso_alvo'], data['concurso_alvo'])

    def test_mes_da_sorte_salvo_e_alterado(self):
        data = self.client.post('/api/gerar-multiplos-jogos/dia_de_sorte',
                                json={'quantidade_jogos': 2, 'dezenas_por_jogo': 7}).get_json()
        aposta = database.obter_aposta(data['aposta_id'])
        self.assertEqual(aposta['complementos'], data['complementos'])

        url = f"/api/apostas/{data['aposta_id']}/complementos"
        self.assertEqual(self.client.post(url, json={'complementos': ['Janeiro', 'Smarch']}).status_code, 400)
        res = self.client.post(url, json={'complementos': ['Janeiro', 'Dezembro']})
        self.assertTrue(res.get_json()['sucesso'])
        self.assertEqual(database.obter_aposta(data['aposta_id'])['complementos'], ['Janeiro', 'Dezembro'])

        # Outro usuário não altera
        outro = database.create_user(f"outro_{uuid.uuid4().hex[:8]}@teste.com", 'senha123', 'Outro')
        with self.client.session_transaction() as sess:
            sess['user_id'] = outro['id']
        self.assertEqual(self.client.post(url, json={'complementos': ['Maio', 'Maio']}).status_code, 404)

    def test_trevos_salvos_na_mais_milionaria(self):
        data = self.client.post('/api/gerar-multiplos-jogos/mais_milionaria',
                                json={'quantidade_jogos': 2, 'dezenas_por_jogo': 7, 'trevos_por_jogo': 3}).get_json()
        aposta = database.obter_aposta(data['aposta_id'])
        self.assertEqual(aposta['trevos'], data['trevos'])
        self.assertTrue(all(len(t) == 3 for t in aposta['trevos']))


class TestCalendario(unittest.TestCase):

    def test_dias_de_sorteio_2026(self):
        esperado = {
            LoteriaType.MEGA_SENA: {'terça', 'quinta', 'domingo'},
            LoteriaType.LOTOFACIL: {'domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta'},
            LoteriaType.QUINA: {'domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta'},
            LoteriaType.LOTOMANIA: {'segunda', 'quarta', 'sexta'},
            LoteriaType.MAIS_MILIONARIA: {'quarta', 'domingo'},
            LoteriaType.DIA_DE_SORTE: {'domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta'},
            LoteriaType.SUPER_SETE: {'segunda', 'quarta', 'sexta'},
            LoteriaType.TIMEMANIA: {'terça', 'quinta', 'domingo'},
            LoteriaType.DUPLA_SENA: {'segunda', 'quarta', 'sexta'},
        }
        for lt, dias in esperado.items():
            self.assertEqual(set(LOTERIAS_CONFIG[lt].dias_sorteio), dias, lt.value)
            self.assertNotIn('sábado', LOTERIAS_CONFIG[lt].dias_sorteio)

    def test_proximo_sorteio(self):
        mega = LOTERIAS_CONFIG[LoteriaType.MEGA_SENA]
        self.assertEqual(proximo_sorteio(mega, datetime(2026, 9, 26, 10))[1], 'Sorteia Amanhã, 11h')   # sábado
        self.assertEqual(proximo_sorteio(mega, datetime(2026, 9, 27, 11, 30))[1], 'Sorteia Hoje, 11h')  # domingo
        self.assertEqual(proximo_sorteio(mega, datetime(2026, 9, 27, 12, 30))[1], 'Sorteia Terça, 21h')
        dupla = LOTERIAS_CONFIG[LoteriaType.DUPLA_SENA]
        self.assertEqual(proximo_sorteio(dupla, datetime(2026, 9, 28, 20))[1], 'Sorteia Hoje, 21h')    # segunda


if __name__ == '__main__':
    unittest.main()

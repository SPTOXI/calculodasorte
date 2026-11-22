"""Testes dos baselines experimentais da Mega-Sena."""

import unittest

from ml_baselines import (
    PROBABILIDADE_UNIFORME,
    avaliar_walk_forward,
    normalizar_historico,
    prever_frequencia_historica,
    prever_uniforme,
)


class TestBaselinesMegaSena(unittest.TestCase):
    def setUp(self):
        self.historico = [
            [1, 2, 3, 4, 5, 6],
            [1, 7, 8, 9, 10, 11],
            [1, 12, 13, 14, 15, 16],
            [1, 17, 18, 19, 20, 21],
        ]

    def test_uniforme_tem_probabilidade_teorica(self):
        previsao = prever_uniforme()
        self.assertEqual(len(previsao), 60)
        self.assertTrue(all(p == PROBABILIDADE_UNIFORME for p in previsao.values()))
        self.assertAlmostEqual(sum(previsao.values()), 6.0)

    def test_frequencia_usa_apenas_historico_recebido(self):
        previsao = prever_frequencia_historica(self.historico[:2])
        self.assertEqual(previsao[1], 1.0)
        self.assertEqual(previsao[2], 0.5)
        self.assertEqual(previsao[12], 0.0)
        self.assertAlmostEqual(sum(previsao.values()), 6.0)

    def test_walk_forward_avalia_sufixo(self):
        resultado = avaliar_walk_forward(self.historico, minimo_treino=2)
        self.assertEqual(resultado["concursos_avaliados"], 2)
        self.assertEqual(resultado["status"], "avaliado")
        self.assertIn("brier_uniforme", resultado)
        self.assertIn("brier_frequencia_historica", resultado)

    def test_rejeita_concurso_invalido(self):
        with self.assertRaises(ValueError):
            normalizar_historico([[1, 2, 3, 4, 5, 60, 61]])

    def test_rejeita_repeticao(self):
        with self.assertRaises(ValueError):
            normalizar_historico([[1, 2, 3, 4, 5, 5]])

    def test_rejeita_historico_curto_para_walk_forward(self):
        with self.assertRaises(ValueError):
            avaliar_walk_forward(self.historico, minimo_treino=4)


if __name__ == "__main__":
    unittest.main()

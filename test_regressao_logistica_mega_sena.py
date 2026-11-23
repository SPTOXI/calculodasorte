"""Testes da regressão logística experimental da Mega-Sena."""
import unittest

from regressao_logistica_mega_sena import construir_features_por_origem


class TestFeaturesLogisticas(unittest.TestCase):
    def setUp(self):
        self.historico = [
            [1, 2, 3, 4, 5, 6],
            [1, 7, 8, 9, 10, 11],
            [2, 12, 13, 14, 15, 16],
            [1, 17, 18, 19, 20, 21],
            [3, 22, 23, 24, 25, 26],
            [1, 27, 28, 29, 30, 31],
            [4, 32, 33, 34, 35, 36],
        ]

    def test_features_usam_apenas_passado(self):
        X, y = construir_features_por_origem(
            self.historico, min_historico=3, janelas=(2, 3)
        )
        # Origem 3: dezena 1 apareceu uma vez nos dois concursos anteriores.
        self.assertAlmostEqual(X[0][0, 0], 0.5)
        self.assertEqual(int(y[0][0]), 1)
        # A identidade da dezena 1 ocupa a primeira coluna one-hot após
        # duas janelas + frequência total + gap.
        self.assertEqual(X[0][0, 4], 1.0)

    def test_formato_das_matrizes(self):
        X, y = construir_features_por_origem(
            self.historico, min_historico=3, janelas=(2, 3)
        )
        self.assertEqual(X[0].shape, (60, 64))
        self.assertEqual(y[0].shape, (60,))


if __name__ == "__main__":
    unittest.main()

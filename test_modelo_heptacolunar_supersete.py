"""
Testes unitários e de integração para o Modelo Canônico 4.0 Heptacolunar do Super Sete (MCOSS 4.0).
Validações de topologia em Z_10^7, cota modular <= 5, dispersão das 7 colunas e variantes canônicas.
"""

import unittest
from modelo_super_sete import ModeloHeptacolunarSuperSete, ColunaSuperSete


class TestModeloHeptacolunarSuperSete(unittest.TestCase):
    def setUp(self):
        self.modelo = ModeloHeptacolunarSuperSete

    def test_topologia_colunas_z10_7(self):
        """Valida que o Super Sete possui exatamente 7 colunas com dígitos de 0 a 9."""
        self.assertEqual(len(self.modelo.COLUNAS), 7)
        self.assertEqual(self.modelo.TOTAL_COLUNAS, 7)
        for col in self.modelo.COLUNAS:
            self.assertEqual(len(col.digitos), 10)
            self.assertEqual(list(col.digitos), list(range(10)))
            self.assertEqual(col.centro_par, 4)
            self.assertEqual(col.centro_impar, 5)
        self.assertEqual(self.modelo.BASE_PURA, [4, 5, 4, 5, 4, 5, 4])

    def test_cota_analitica_modular_maxima(self):
        """Garante que a distância cíclica máxima em Z_10 é menor ou igual a 5."""
        for a in range(10):
            for b in range(10):
                dist = self.modelo.distancia_modular_10(a, b)
                self.assertLessEqual(
                    dist, 5,
                    f"Distância entre {a} e {b} foi {dist} > 5"
                )

    def test_variantes_canonicas_heptacolunares(self):
        """Valida a estrutura e integridade das 5 variantes canônicas."""
        variantes = self.modelo.gerar_variantes_canonicas()
        self.assertEqual(len(variantes), 5)

        # Base Pura
        base = variantes[0]
        self.assertEqual(base.digitos, [4, 5, 4, 5, 4, 5, 4])
        self.assertEqual(base.pares, 4)
        self.assertEqual(base.impares, 3)
        self.assertEqual(base.soma, 31)

        # Alpha (Moda e Soma 31)
        alpha = variantes[1]
        self.assertEqual(len(alpha.digitos), 7)
        self.assertEqual(alpha.soma, 31)
        self.assertEqual(alpha.pares, 4)
        self.assertEqual(alpha.impares, 3)
        self.assertGreaterEqual(alpha.digitos_distintos, 5)

        # Gamma (Máxima diversidade: 7 dígitos distintos)
        gamma = variantes[3]
        self.assertEqual(len(set(gamma.digitos)), 7)
        self.assertEqual(gamma.digitos_distintos, 7)

        # Todas as variantes
        for v in variantes:
            self.assertEqual(len(v.digitos), 7)
            for d in v.digitos:
                self.assertTrue(0 <= d <= 9)

    def test_calculo_dispersao_heptacolunar_completa(self):
        """Valida o cálculo de dispersão heptacolunar e métricas de aderência."""
        jogo = [4, 5, 4, 5, 4, 5, 4]
        sorteio_ref = [6, 0, 2, 1, 1, 4, 9]

        res = self.modelo.calcular_dispersao_heptacolunar(jogo, sorteio_ref)
        self.assertTrue(res["valido"])
        self.assertTrue(res["disponivel"])
        self.assertEqual(res["modelo"], "MCOSS 4.0")
        self.assertEqual(res["geometria"], "Heptacolunar")
        self.assertTrue(res["cota_conforme"])
        self.assertEqual(res["setores_cobertos"], 7)
        self.assertEqual(res["total_setores"], 7)
        self.assertEqual(res["pares"], 4)
        self.assertEqual(res["impares"], 3)
        self.assertTrue(res["paridade_modal"])
        self.assertEqual(res["soma"], 31)
        self.assertIsNotNone(res["distancia_media_sorteio"])
        self.assertIsNotNone(res["acertos_exatos"])
        self.assertGreater(res["indice_dispersao"], 70.0)

    def test_geracao_multiplos_jogos(self):
        """Valida geração de jogos com 7 dígitos respeitando regras do volante."""
        jogos = self.modelo.gerar_jogos(quantidade=5)
        self.assertEqual(len(jogos), 5)
        for j in jogos:
            self.assertEqual(len(j), 7)
            for d in j:
                self.assertTrue(0 <= d <= 9)

    def test_robustez_entradas_invalidas(self):
        """Testa resposta defensiva a dados com quantidade ou valores incorretos."""
        res_vazio = self.modelo.calcular_dispersao_heptacolunar([])
        self.assertFalse(res_vazio["valido"])

        # Menos de 7 colunas
        res_incompleto = self.modelo.calcular_dispersao_heptacolunar([1, 2, 3])
        self.assertFalse(res_incompleto["valido"])

        # Dígitos fora do intervalo [0..9]
        res_fora = self.modelo.calcular_dispersao_heptacolunar([1, 2, 3, 4, 5, 6, 15])
        self.assertFalse(res_fora["valido"])


if __name__ == '__main__':
    unittest.main()

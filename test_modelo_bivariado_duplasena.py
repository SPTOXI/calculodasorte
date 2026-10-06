"""
Testes unitários e de integração para o Modelo Canônico 4.0 Bivariado da Dupla Sena (MCODSen 4.0).
Validações de topologia em Z_50, cota <= 4, dispersão conjunta S1/S2 e variantes canônicas.
"""

import unittest
from modelo_dupla_sena import ModeloBivariadoDuplaSena, SetorHexagonalDuplaSena


class TestModeloBivariadoDuplaSena(unittest.TestCase):
    def setUp(self):
        self.modelo = ModeloBivariadoDuplaSena

    def test_topologia_setores_z50(self):
        """Valida que os 6 setores cobrem exatamente o espaço de 1 a 50 sem lacunas."""
        self.assertEqual(len(self.modelo.SETORES), 6)
        todos_numeros = []
        for s in self.modelo.SETORES:
            self.assertIn(s.centro, s.dezenas)
            todos_numeros.extend(s.dezenas)
        self.assertEqual(sorted(todos_numeros), list(range(1, 51)))
        self.assertEqual(self.modelo.CENTROS_BASE, [4, 13, 21, 30, 38, 46])

    def test_cota_analitica_maxima_deterministica(self):
        """Garante que todo número de 1 a 50 dista no máximo 4 unidades da Base Pura."""
        for num in range(1, 51):
            dist = self.modelo.menor_distancia_base(num)
            self.assertLessEqual(
                dist, 4,
                f"Número {num} violou a cota máxima com distância {dist} > 4"
            )

    def test_variantes_canonicas_bivariadas(self):
        """Valida a estrutura e integridade das 5 variantes canônicas."""
        variantes = self.modelo.gerar_variantes_canonicas()
        self.assertEqual(len(variantes), 5)
        
        # Base Pura
        base = variantes[0]
        self.assertEqual(base.dezenas, [4, 13, 21, 30, 38, 46])
        self.assertEqual(base.pares, 3)
        self.assertEqual(base.impares, 3)
        self.assertEqual(base.cobertura_setores, 6)

        # Alpha (Moda e Soma 153)
        alpha = variantes[1]
        self.assertEqual(len(alpha.dezenas), 6)
        self.assertEqual(alpha.soma, 153)
        self.assertEqual(alpha.pares, 3)
        self.assertEqual(alpha.impares, 3)
        self.assertEqual(alpha.cobertura_setores, 6)

        # Todas as variantes devem ter 6 dezenas distintas no intervalo [1, 50]
        for v in variantes:
            self.assertEqual(len(v.dezenas), 6)
            self.assertEqual(len(set(v.dezenas)), 6)
            for d in v.dezenas:
                self.assertTrue(1 <= d <= 50)

    def test_calculo_dispersao_bivariada_completa(self):
        """Valida a dispersão simultânea contra o 1º sorteio, 2º sorteio e métricas conjuntas."""
        jogo = [4, 13, 21, 30, 38, 46]
        sorteio1 = [5, 6, 22, 23, 37, 38]
        sorteio2 = [5, 8, 20, 31, 42, 48]

        res = self.modelo.calcular_dispersao_bivariada(jogo, sorteio1, sorteio2)
        self.assertTrue(res["valido"])
        self.assertEqual(res["modelo"], "MCODSen 4.0")
        self.assertTrue(res["cota_conforme"])
        self.assertEqual(res["cobertura_setores"], 6)
        self.assertEqual(res["taxa_cobertura"], 100.0)
        self.assertEqual(res["pares"], 4)
        self.assertEqual(res["impares"], 2)

        # Testar variante Alpha com paridade modal 3P/3I
        res_alpha = self.modelo.calcular_dispersao_bivariada([5, 12, 21, 30, 39, 46], sorteio1, sorteio2)
        self.assertTrue(res_alpha["paridade_modal"])
        self.assertEqual(res_alpha["soma"], 153)
        
        # Métricas do Sorteio 1
        self.assertIsNotNone(res["distancia_sorteio_1"])
        self.assertLessEqual(res["distancia_maxima_sorteio_1"], 4)
        
        # Métricas do Sorteio 2
        self.assertIsNotNone(res["distancia_sorteio_2"])
        self.assertLessEqual(res["distancia_maxima_sorteio_2"], 4)

        # Métricas conjuntas bivariadas
        self.assertIsNotNone(res["distancia_bivariada_conjunta"])
        self.assertIsNotNone(res["indice_bivariado_harmonico"])
        self.assertGreater(res["ide_bivariado"], 70.0)

    def test_geracao_multiplos_jogos(self):
        """Valida geração de 5 jogos com conformidade espacial e regras de aposta."""
        jogos = self.modelo.gerar_jogos(quantidade=5, dezenas_por_jogo=6)
        self.assertEqual(len(jogos), 5)
        for j in jogos:
            self.assertEqual(len(j), 6)
            self.assertEqual(len(set(j)), 6)
            self.assertEqual(j, sorted(j))
            for n in j:
                self.assertTrue(1 <= n <= 50)

    def test_robustez_entradas_invalidas(self):
        """Testa resposta defensiva a dados vazios ou corrompidos."""
        res_vazio = self.modelo.calcular_dispersao_bivariada([])
        self.assertFalse(res_vazio["valido"])

        res_fora = self.modelo.calcular_dispersao_bivariada([99, 105, -3])
        self.assertFalse(res_fora["valido"])


if __name__ == '__main__':
    unittest.main()

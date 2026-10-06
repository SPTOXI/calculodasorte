"""
Testes Unitários do Modelo Canônico 4.0 Biparamétrico Hexa-Trevo (MCOMIL 4.0) - +Milionária
"""

import unittest
from modelo_mais_milionaria import ModeloHexaTrevoMaisMilionaria
from core import ModeloCanonico40, LoteriaType, gerar_jogo_sugerido, gerar_multiplos_jogos
from avaliacao import avaliar_jogo, parecer_jogos


class TestModeloHexaTrevoMaisMilionaria(unittest.TestCase):

    def setUp(self):
        # Concursos sintéticos representativos de sorteios da +Milionária (6 dezenas de 1 a 50)
        self.sorteios_teste = [
            [8, 18, 21, 27, 28, 44],
            [3, 14, 25, 33, 39, 48],
            [5, 12, 22, 31, 38, 47],
            [4, 15, 23, 30, 41, 50],
        ]
        self.trevos_teste = [
            [3, 5],
            [1, 4],
            [2, 6],
            [2, 5],
        ]
        self.modelo = ModeloCanonico40(self.sorteios_teste, LoteriaType.MAIS_MILIONARIA)

    def test_distancia_circular_z50(self):
        """Testa o cálculo da menor distância no anel circular modular Z_50."""
        self.assertEqual(ModeloHexaTrevoMaisMilionaria.distancia_circular(4, 13), 9)
        self.assertEqual(ModeloHexaTrevoMaisMilionaria.distancia_circular(1, 50), 1)
        self.assertEqual(ModeloHexaTrevoMaisMilionaria.distancia_circular(46, 4), 8)
        self.assertEqual(ModeloHexaTrevoMaisMilionaria.distancia_circular(25, 25), 0)
        self.assertEqual(ModeloHexaTrevoMaisMilionaria.distancia_circular(10, 35), 25)

    def test_base_pura_cota_maxima_z50(self):
        """Testa se a base pura (centros dos 6 setores) cobre todo o universo Z_50 com cota <= 4."""
        base_pura = ModeloHexaTrevoMaisMilionaria.gerar_base_pura()
        self.assertEqual(len(base_pura), 6)
        self.assertEqual(base_pura, [4, 13, 21, 30, 38, 46])

        # Todo número de 1 a 50 deve distar no máximo 4 unidades de algum centro da base pura
        for num in range(1, 51):
            d_min = min(ModeloHexaTrevoMaisMilionaria.distancia_circular(num, c) for c in base_pura)
            self.assertLessEqual(d_min, 4, f"Número {num} ultrapassou cota de 4 unidades em Z_50.")

    def test_variantes_canonicas(self):
        """Testa integridade das variantes harmônicas biparamétricas (dezenas e trevos)."""
        variantes = ModeloHexaTrevoMaisMilionaria.gerar_variantes_canonicas()
        self.assertEqual(len(variantes), 5)

        for v in variantes:
            dezenas = v["dezenas"]
            trevos = v["trevos"]
            self.assertEqual(len(dezenas), 6)
            self.assertEqual(len(set(dezenas)), 6)
            self.assertTrue(all(1 <= n <= 50 for n in dezenas))
            self.assertEqual(len(trevos), 2)
            self.assertTrue(all(1 <= t <= 6 for t in trevos))
            self.assertLessEqual(v["dist_max"], 5)
            self.assertEqual(v["pares"] + v["impares"], 6)

        # Variante Alpha deve ter paridade modal 3P / 3I e trevos com soma 7
        alpha = variantes[1]
        self.assertEqual(alpha["pares"], 3)
        self.assertEqual(alpha["impares"], 3)
        self.assertEqual(alpha["trevos_soma"], 7)

    def test_dispersao_biparametrica_core(self):
        """Testa cálculo do IDE biparamétrico através do core da aplicação."""
        jogo_dezenas = [5, 13, 22, 30, 38, 47]
        trevos = [3, 4]
        disp = self.modelo.calcular_dispersao_biparametrica_maismilionaria(jogo_dezenas, trevos)

        self.assertTrue(disp["disponivel"])
        self.assertEqual(disp["geometria"], "Hexa-Trevo")
        self.assertEqual(disp["total_setores"], 6)
        self.assertEqual(disp["setores_cobertos"], 6)
        self.assertEqual(disp["paridade"], "3P/3I")
        self.assertEqual(disp["trevos_info"]["trevos"], [3, 4])
        self.assertEqual(disp["trevos_info"]["soma"], 7)
        self.assertLessEqual(disp["cota_maxima_anel"], 4)
        self.assertTrue(disp["classificacao"].startswith("Excelente"))
        self.assertGreaterEqual(disp["indice_dispersao"], 90.0)

    def test_geracao_jogos_maismilionaria(self):
        """Testa geração de jogos sugeridos e múltiplos jogos da +Milionária."""
        jogo_unico = gerar_jogo_sugerido(self.modelo, 6)
        self.assertEqual(len(jogo_unico), 6)
        self.assertEqual(len(set(jogo_unico)), 6)
        self.assertTrue(all(1 <= n <= 50 for n in jogo_unico))

        jogos_multiplos = gerar_multiplos_jogos(self.modelo, quantidade_jogos=3, quantidade_numeros=6)
        self.assertEqual(len(jogos_multiplos), 3)
        for j in jogos_multiplos:
            self.assertEqual(len(j), 6)
            self.assertEqual(len(set(j)), 6)

    def test_avaliacao_e_parecer_maismilionaria(self):
        """Testa integração com motor de avaliação e parecer técnico da +Milionária."""
        jogo = [5, 13, 22, 30, 38, 47]
        av = avaliar_jogo(jogo, self.modelo)
        self.assertIn("dispersao_espacial", av)
        self.assertIn("dispersao_biparametrica", av)
        self.assertEqual(av["dispersao_biparametrica"]["geometria"], "Hexa-Trevo")

        parecer = parecer_jogos([jogo], self.modelo)
        self.assertIn("MCOMIL 4.0", parecer["parecer_texto"])
        self.assertIn("Hexa-Trevo", parecer["parecer_texto"])


if __name__ == "__main__":
    unittest.main()

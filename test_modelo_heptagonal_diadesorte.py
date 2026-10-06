"""
Testes Unitários do Modelo Canônico 4.0 Heptagonal de Calendário e Mês da Sorte (MCODS 4.0) - Dia de Sorte
"""

import unittest
from modelo_dia_de_sorte import ModeloHeptagonalDiaDeSorte
from core import ModeloCanonico40, LoteriaType, gerar_jogo_sugerido, gerar_multiplos_jogos
from avaliacao import avaliar_jogo, parecer_jogos


class TestModeloHeptagonalDiaDeSorte(unittest.TestCase):

    def setUp(self):
        # Concursos sintéticos representativos do Dia de Sorte (7 dezenas entre 1 e 31)
        self.sorteios_teste = [
            [2, 9, 13, 15, 17, 19, 26],
            [3, 7, 12, 16, 21, 25, 30],
            [1, 8, 14, 20, 24, 28, 31],
            [4, 11, 18, 22, 27, 29, 31],
        ]
        self.meses_teste = [
            "Outubro",
            "Maio",
            "Dezembro",
            "Agosto",
        ]
        self.modelo = ModeloCanonico40(self.sorteios_teste, LoteriaType.DIA_DE_SORTE)

    def test_distancia_circular_z31(self):
        """Testa o cálculo da menor distância no anel circular modular Z_31 (calendário)."""
        self.assertEqual(ModeloHeptagonalDiaDeSorte.distancia_circular(3, 7), 4)
        self.assertEqual(ModeloHeptagonalDiaDeSorte.distancia_circular(1, 31), 1)
        self.assertEqual(ModeloHeptagonalDiaDeSorte.distancia_circular(30, 3), 4)
        self.assertEqual(ModeloHeptagonalDiaDeSorte.distancia_circular(15, 15), 0)
        self.assertEqual(ModeloHeptagonalDiaDeSorte.distancia_circular(1, 16), 15)

    def test_base_pura_cota_maxima_z31(self):
        """Testa se a base pura heptagonal cobre todos os 31 dias com cota máxima <= 2."""
        base_pura = ModeloHeptagonalDiaDeSorte.gerar_base_pura()
        self.assertEqual(len(base_pura), 7)
        self.assertEqual(base_pura, [3, 7, 12, 16, 21, 25, 30])

        # Todo número de 1 a 31 deve estar a no máximo 2 dias de distância de algum centro
        for dia in range(1, 32):
            d_min = min(ModeloHeptagonalDiaDeSorte.distancia_circular(dia, c) for c in base_pura)
            self.assertLessEqual(d_min, 2, f"Dia {dia} ultrapassou a cota máxima de 2 unidades em Z_31.")

    def test_variantes_canonicas(self):
        """Testa integridade das 5 variantes canônicas do Dia de Sorte."""
        variantes = ModeloHeptagonalDiaDeSorte.gerar_variantes_canonicas()
        self.assertEqual(len(variantes), 5)

        for v in variantes:
            dezenas = v["dezenas"]
            self.assertEqual(len(dezenas), 7)
            self.assertEqual(len(set(dezenas)), 7)
            self.assertTrue(all(1 <= n <= 31 for n in dezenas))
            self.assertIn("mes_sugerido", v)
            self.assertIn(v["mes_sugerido"], ModeloHeptagonalDiaDeSorte.MESES)
            self.assertLessEqual(v["dist_max"], 3)
            self.assertEqual(v["pares"] + v["impares"], 7)

        # Base Pura e Beta devem ter paridade modal 3P / 4I
        base = variantes[0]
        self.assertEqual(base["pares"], 3)
        self.assertEqual(base["impares"], 4)

        # Variante Beta deve ter soma baricêntrica exata de 112
        beta = variantes[2]
        self.assertEqual(beta["soma"], 112)

    def test_dispersao_heptagonal_core(self):
        """Testa cálculo do IDE heptagonal através do core da aplicação."""
        jogo = [3, 7, 12, 16, 21, 25, 30]
        disp = self.modelo.calcular_dispersao_heptagonal_diadesorte(jogo, "Outubro")

        self.assertTrue(disp["disponivel"])
        self.assertEqual(disp["geometria"], "Heptagonal")
        self.assertEqual(disp["total_setores"], 7)
        self.assertEqual(disp["setores_cobertos"], 7)
        self.assertEqual(disp["paridade"], "3P/4I")
        self.assertLessEqual(disp["cota_maxima_anel"], 2)
        self.assertTrue(disp["classificacao"].startswith("Excelente"))
        self.assertGreaterEqual(disp["indice_dispersao"], 90.0)

    def test_geracao_jogos_diadesorte(self):
        """Testa geração de jogos sugeridos e múltiplos jogos do Dia de Sorte."""
        jogo_unico = gerar_jogo_sugerido(self.modelo, 7)
        self.assertEqual(len(jogo_unico), 7)
        self.assertEqual(len(set(jogo_unico)), 7)
        self.assertTrue(all(1 <= n <= 31 for n in jogo_unico))

        jogos_multiplos = gerar_multiplos_jogos(self.modelo, quantidade_jogos=3, quantidade_numeros=7)
        self.assertEqual(len(jogos_multiplos), 3)
        for j in jogos_multiplos:
            self.assertEqual(len(j), 7)
            self.assertEqual(len(set(j)), 7)

    def test_avaliacao_e_parecer_diadesorte(self):
        """Testa integração com motor de avaliação e parecer técnico do Dia de Sorte."""
        jogo = [3, 7, 12, 16, 21, 25, 30]
        av = avaliar_jogo(jogo, self.modelo)
        self.assertIn("dispersao_espacial", av)
        self.assertIn("dispersao_heptagonal", av)
        self.assertEqual(av["dispersao_heptagonal"]["geometria"], "Heptagonal")

        parecer = parecer_jogos([jogo], self.modelo)
        self.assertIn("MCODS 4.0", parecer["parecer_texto"])
        self.assertIn("Heptagonal", parecer["parecer_texto"])


if __name__ == "__main__":
    unittest.main()

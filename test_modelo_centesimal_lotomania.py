"""
Testes Unitários do Modelo Canônico 4.0 Centesimal e Matricial 10x10 (MCOC 4.0) - Lotomania
"""

import unittest
from modelo_lotomania import ModeloCentesimalLotomania
from core import ModeloCanonico40, LoteriaType, gerar_jogo_sugerido, gerar_multiplos_jogos
from avaliacao import avaliar_jogo, parecer_jogos


class TestModeloCentesimalLotomania(unittest.TestCase):

    def setUp(self):
        # Concurso sintético representativo de sorteios da Lotomania (20 dezenas entre 0 e 99)
        self.sorteios_teste = [
            [3, 5, 6, 12, 20, 22, 23, 25, 26, 28, 41, 53, 68, 70, 73, 76, 79, 82, 86, 90],
            [1, 9, 14, 15, 27, 33, 35, 42, 59, 61, 66, 70, 74, 78, 80, 85, 89, 92, 94, 98],
            [4, 16, 21, 34, 38, 43, 47, 51, 54, 57, 62, 65, 71, 72, 75, 81, 84, 88, 93, 99],
        ]
        self.modelo = ModeloCanonico40(self.sorteios_teste, LoteriaType.LOTOMANIA)

    def test_coordenadas_grid_10x10(self):
        """Testa o mapeamento de números 00-99 em coordenadas cartesianas (r, c) de 0 a 9."""
        self.assertEqual(ModeloCentesimalLotomania.coordenadas(0), (0, 0))
        self.assertEqual(ModeloCentesimalLotomania.coordenadas(9), (0, 9))
        self.assertEqual(ModeloCentesimalLotomania.coordenadas(42), (4, 2))
        self.assertEqual(ModeloCentesimalLotomania.coordenadas(99), (9, 9))

    def test_distancia_manhattan(self):
        """Testa o cálculo da métrica L1 (Manhattan) no reticulado 10x10."""
        self.assertEqual(ModeloCentesimalLotomania.distancia_manhattan(0, 0), 0)
        self.assertEqual(ModeloCentesimalLotomania.distancia_manhattan(0, 1), 1)
        self.assertEqual(ModeloCentesimalLotomania.distancia_manhattan(0, 10), 1)
        self.assertEqual(ModeloCentesimalLotomania.distancia_manhattan(0, 99), 18)  # |9-0| + |9-0| = 18
        self.assertEqual(ModeloCentesimalLotomania.distancia_manhattan(44, 55), 2)  # |5-4| + |5-4| = 2

    def test_base_pura_cota_maxima_grid(self):
        """Testa se a base pura centesimal (padrão xadrez) cobre o grid com cota máxima <= 1."""
        base_pura = ModeloCentesimalLotomania.gerar_base_pura()
        self.assertEqual(len(base_pura), 50)
        self.assertEqual(len(set(base_pura)), 50)

        # Todo número de 0 a 99 deve estar a no máximo 1 passo de Manhattan de algum número da base pura
        base_coords = [ModeloCentesimalLotomania.coordenadas(p) for p in base_pura]
        for num in range(100):
            nr, nc = ModeloCentesimalLotomania.coordenadas(num)
            min_dist = min(abs(nr - br) + abs(nc - bc) for br, bc in base_coords)
            self.assertLessEqual(min_dist, 1, f"Número {num} ultrapassou cota máxima de 1 passo.")

        # Exatamente 5 por linha e 5 por coluna
        linhas = [n // 10 for n in base_pura]
        colunas = [n % 10 for n in base_pura]
        for r in range(10):
            self.assertEqual(linhas.count(r), 5, f"Linha {r} não possui exatamente 5 dezenas.")
        for c in range(10):
            self.assertEqual(colunas.count(c), 5, f"Coluna {c} não possui exatamente 5 dezenas.")

        # Paridade 25P / 25I
        pares = sum(1 for n in base_pura if n % 2 == 0)
        self.assertEqual(pares, 25)

        # Moldura 18 / Miolo 32
        moldura_count = len(set(base_pura) & ModeloCentesimalLotomania.MOLDURA)
        miolo_count = len(set(base_pura) & ModeloCentesimalLotomania.MIOLO)
        self.assertEqual(moldura_count, 18)
        self.assertEqual(miolo_count, 32)

    def test_variantes_canonicas(self):
        """Testa integridade estrutural das 5 variantes canônicas centesimais da Lotomania."""
        variantes = ModeloCentesimalLotomania.gerar_variantes_canonicas()
        self.assertEqual(len(variantes), 5)

        for v in variantes:
            dezenas = v["dezenas"]
            self.assertEqual(len(dezenas), 50)
            self.assertEqual(len(set(dezenas)), 50)
            self.assertTrue(all(0 <= n <= 99 for n in dezenas))
            self.assertIn("dist_max_grid", v)
            self.assertLessEqual(v["dist_max_grid"], 2)
            self.assertEqual(v["pares"] + v["impares"], 50)
            self.assertEqual(v["moldura"] + v["miolo"], 50)

    def test_dispersao_centesimal_core(self):
        """Testa cálculo do IDE centesimal através do core da aplicação."""
        jogo_base = ModeloCentesimalLotomania.gerar_base_pura()
        disp = self.modelo.calcular_dispersao_centesimal_lotomania(jogo_base)

        self.assertTrue(disp["disponivel"])
        self.assertEqual(disp["geometria"], "Centesimal")
        self.assertEqual(disp["total_setores"], 10)
        self.assertEqual(disp["setores_cobertos"], 10)  # cobre todas as 10 faixas
        self.assertEqual(disp["moldura"], 18)
        self.assertEqual(disp["miolo"], 32)
        self.assertEqual(disp["cota_maxima_grid"], 1)
        self.assertTrue(disp["classificacao"].startswith("Excelente"))
        self.assertGreaterEqual(disp["indice_dispersao"], 90.0)

    def test_geracao_jogos_lotomania(self):
        """Testa geração de jogos sugeridos e múltiplos jogos da Lotomania."""
        jogo_unico = gerar_jogo_sugerido(self.modelo, 50)
        self.assertEqual(len(jogo_unico), 50)
        self.assertEqual(len(set(jogo_unico)), 50)
        self.assertTrue(all(0 <= n <= 99 for n in jogo_unico))

        jogos_multiplos = gerar_multiplos_jogos(self.modelo, quantidade_jogos=3, quantidade_numeros=50)
        self.assertEqual(len(jogos_multiplos), 3)
        for j in jogos_multiplos:
            self.assertEqual(len(j), 50)
            self.assertEqual(len(set(j)), 50)

    def test_avaliacao_e_parecer_lotomania(self):
        """Testa integração com motor de avaliação e parecer técnico da Lotomania."""
        jogo = ModeloCentesimalLotomania.gerar_base_pura()
        av = avaliar_jogo(jogo, self.modelo)
        self.assertIn("dispersao_espacial", av)
        self.assertIn("dispersao_centesimal", av)
        self.assertEqual(av["dispersao_centesimal"]["geometria"], "Centesimal")

        parecer = parecer_jogos([jogo], self.modelo)
        self.assertIn("MCOC 4.0", parecer["parecer_texto"])
        self.assertIn("Centesimal", parecer["parecer_texto"])


if __name__ == "__main__":
    unittest.main()

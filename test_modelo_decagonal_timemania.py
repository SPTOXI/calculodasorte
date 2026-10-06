"""
Testes Unitários do Modelo Canônico 4.0 Decagonal e Time do Coração (MCOD 4.0) - Timemania
"""

import unittest
import os
import json
from modelo_decagonal_timemania import ModeloDecagonalTimemania
from core import ModeloCanonico40, LoteriaType, gerar_jogo_sugerido, gerar_multiplos_jogos
from avaliacao import avaliar_jogo, parecer_jogos
from unittest.mock import patch

with patch('database.init_db'), patch('updater.iniciar_agendador'):
    from app import opcoes_complemento


class TestModeloDecagonalTimemania(unittest.TestCase):

    def setUp(self):
        # Histórico sintético representativo de sorteios da Timemania (7 números sorteados entre 1 e 80)
        self.historico_teste = [
            [14, 15, 43, 54, 72, 23, 60],
            [19, 31, 46, 49, 60, 12, 75],
            [23, 40, 57, 60, 74, 4, 33],
            [34, 41, 51, 70, 76, 18, 2],
            [4, 16, 61, 69, 72, 28, 55],
            [14, 22, 37, 42, 60, 68, 79],
            [10, 44, 46, 70, 73, 20, 36],
            [1, 8, 51, 57, 63, 11, 40],
            [21, 34, 58, 69, 70, 6, 80],
            [38, 39, 43, 51, 53, 27, 66],
            [22, 23, 35, 54, 62, 5, 17],
            [14, 19, 42, 53, 60, 32, 48],
        ]
        self.modelo = ModeloCanonico40(self.historico_teste, LoteriaType.TIMEMANIA)

    def test_distancia_circular_z80(self):
        """Testa o cálculo da menor distância no anel circular modular Z_80."""
        self.assertEqual(ModeloDecagonalTimemania.distancia_circular(4, 12), 8)
        self.assertEqual(ModeloDecagonalTimemania.distancia_circular(1, 80), 1)
        self.assertEqual(ModeloDecagonalTimemania.distancia_circular(4, 76), 8)
        self.assertEqual(ModeloDecagonalTimemania.distancia_circular(40, 40), 0)
        self.assertEqual(ModeloDecagonalTimemania.distancia_circular(10, 70), 20)

    def test_base_pura_cota_maxima(self):
        """Testa se a base pura decagonal (delta=4) cobre todo o espaço com cota máxima <= 4."""
        base_pura = ModeloDecagonalTimemania.gerar_base_pura(delta=4)
        self.assertEqual(len(base_pura), 10)
        self.assertEqual(base_pura, [4, 12, 20, 28, 36, 44, 52, 60, 68, 76])

        # Cada número de 1 a 80 deve estar a no máximo 4 unidades de distância de algum centro
        for num in range(1, 81):
            d_min = min(ModeloDecagonalTimemania.distancia_circular(num, centro) for centro in base_pura)
            self.assertLessEqual(d_min, 4, f"Número {num} ultrapassou a cota máxima de 4 unidades.")

    def test_variantes_canonicas(self):
        """Testa integridade, paridade e Times do Coração das variantes harmônicas decagonais."""
        variantes = ModeloDecagonalTimemania.gerar_variantes_canonicas()
        self.assertGreaterEqual(len(variantes), 5)

        for v in variantes:
            dezenas = v["dezenas"]
            self.assertEqual(len(dezenas), 10)
            self.assertEqual(len(set(dezenas)), 10)
            self.assertTrue(all(1 <= n <= 80 for n in dezenas))
            self.assertIn("time_sugerido", v)
            self.assertTrue(len(v["time_sugerido"]) > 0)
            self.assertLessEqual(v["dist_max"], 5)

        # Variantes Alpha e Beta devem ter paridade modal exata 5P / 5I
        alpha = variantes[1]
        self.assertEqual(alpha["pares"], 5)
        self.assertEqual(alpha["impares"], 5)

        beta = variantes[2]
        self.assertEqual(beta["pares"], 5)
        self.assertEqual(beta["impares"], 5)
        self.assertEqual(beta["soma"], 405)  # Baricentro ótimo exato

    def test_resumo_metodologico_timemania(self):
        """Verifica se o resumo da Timemania identifica a Camada Espacial Decagonal (MCOD 4.0)."""
        resumo = self.modelo.obter_resumo_analise()
        metodologia = resumo["metodologia"]
        camada_espacial = resumo["camada_espacial"]

        self.assertEqual(metodologia["modelo"], "Canônico 4.0 — MCOD (Timemania)")
        self.assertIn("Decagonal", metodologia["camada_espacial"])
        self.assertEqual(camada_espacial["modelo"], "Decagonal K-Medians (Z_80)")
        self.assertEqual(camada_espacial["total_setores"], 10)
        self.assertEqual(camada_espacial["largura_setor"], 8.0)
        self.assertEqual(camada_espacial["distancia_maxima_teorica"], 4.0)

    def test_calcular_dispersao_decagonal(self):
        """Testa o cálculo do IDE Decagonal e alocação nos 10 setores."""
        jogo_decagonal = [4, 12, 20, 28, 36, 44, 52, 60, 68, 76]
        disp = self.modelo.calcular_dispersao_decagonal(jogo_decagonal)

        self.assertTrue(disp["disponivel"])
        self.assertEqual(disp["geometria"], "Decagonal")
        self.assertEqual(disp["setores_cobertos"], 10)
        self.assertEqual(disp["total_setores"], 10)
        self.assertEqual(disp["distancia_maxima_garantida"], 4)
        self.assertGreaterEqual(disp["indice_dispersao"], 90.0)
        self.assertIn("Excelente", disp["classificacao"])

    def test_despacho_polimorfico_espacial(self):
        """Verifica se calcular_dispersao_espacial despacha corretamente para Decagonal na Timemania."""
        jogo = [5, 12, 21, 28, 37, 44, 53, 60, 69, 76]
        disp = self.modelo.calcular_dispersao_espacial(jogo)

        self.assertTrue(disp["disponivel"])
        self.assertEqual(disp["geometria"], "Decagonal")
        self.assertEqual(disp["setores_cobertos"], 10)

    def test_geradores_jogos_timemania(self):
        """Testa a geração de 1 jogo sugerido e múltiplos jogos da Timemania."""
        jogo_sug = gerar_jogo_sugerido(self.modelo, 10)
        self.assertEqual(len(jogo_sug), 10)
        self.assertEqual(len(set(jogo_sug)), 10)
        self.assertTrue(all(1 <= n <= 80 for n in jogo_sug))

        # Múltiplos jogos (3 jogos distintos)
        jogos = gerar_multiplos_jogos(self.modelo, 3, 10)
        self.assertEqual(len(jogos), 3)
        for j in jogos:
            self.assertEqual(len(j), 10)
            self.assertEqual(len(set(j)), 10)
        # Todos devem ser distintos entre si
        self.assertEqual(len({tuple(j) for j in jogos}), 3)

    def test_avaliacao_e_parecer_timemania(self):
        """Testa avaliar_jogo e parecer_jogos com o MCOD 4.0 Decagonal."""
        jogo = [4, 11, 20, 27, 36, 43, 52, 59, 68, 75]
        av = avaliar_jogo(jogo, self.modelo)

        self.assertTrue(av["valido"])
        self.assertIsNotNone(av["dispersao_decagonal"])
        self.assertEqual(av["dispersao_decagonal"]["geometria"], "Decagonal")

        parecer = parecer_jogos([jogo], self.modelo)
        self.assertIn("MCOD 4.0", parecer["parecer_texto"])
        self.assertIn("Decagonal", parecer["parecer_texto"])

    def test_opcoes_complemento_clubes(self):
        """Testa se opcoes_complemento carrega o catálogo de pelo menos 80 clubes oficiais."""
        times = opcoes_complemento("timemania")
        self.assertGreaterEqual(len(times), 80)
        self.assertIn("FLAMENGO/RJ", times)
        self.assertIn("CORINTHIANS/SP", times)
        self.assertIn("PALMEIRAS/SP", times)
        self.assertIn("GREMIO/RS", times)


if __name__ == "__main__":
    unittest.main()

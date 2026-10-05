"""
Testes unitários e de integração para o Modelo Matricial 5x5 da Lotofácil (MCOM 4.0)
Validação matemática do grid bidimensional, quintetos, balanceamento Moldura/Miolo,
paridade modal (8I/7P e 7I/8P), integração com Modelo Canônico 4.0 e avaliação métrica.
"""

import unittest
from core import (
    LoteriaConfig, 
    LoteriaType, 
    ModeloCanonico40, 
    gerar_jogo_sugerido, 
    gerar_multiplos_jogos
)
import avaliacao
from modelo_lotofacil import ModeloMatricialLotofacil, ModeloMatricial


class TestModeloMatricialLotofacil(unittest.TestCase):
    def setUp(self):
        # Histórico sintético determinístico com 40 concursos para Lotofácil (N=25, k=15)
        self.historico = []
        for i in range(40):
            base = [(i * 2 + j) % 25 + 1 for j in range(15)]
            sorteio = sorted(list(set(base)))
            while len(sorteio) < 15:
                prox = (sorteio[-1] % 25) + 1
                if prox not in sorteio:
                    sorteio.append(prox)
                else:
                    sorteio.append(((prox + 2) % 25) + 1)
                sorteio = sorted(list(set(sorteio)))
            self.historico.append(sorteio[:15])

        self.modelo_lotofacil = ModeloCanonico40(self.historico, LoteriaType.LOTOFACIL)

    def test_coordenadas_grid_5x5(self):
        """Valida mapeamento de coordenadas (linha, coluna) no grid 5x5."""
        self.assertEqual(ModeloMatricialLotofacil.coordenadas(1), (0, 0))
        self.assertEqual(ModeloMatricialLotofacil.coordenadas(5), (0, 4))
        self.assertEqual(ModeloMatricialLotofacil.coordenadas(6), (1, 0))
        self.assertEqual(ModeloMatricialLotofacil.coordenadas(13), (2, 2)) # Centro absoluto
        self.assertEqual(ModeloMatricialLotofacil.coordenadas(25), (4, 4))

    def test_distancia_manhattan_grid(self):
        """Valida o cálculo de distância reticulada de Manhattan no grid 5x5."""
        # Vizinhos ortogonais imediatos (distância = 1)
        self.assertEqual(ModeloMatricialLotofacil.distancia_manhattan(1, 2), 1)
        self.assertEqual(ModeloMatricialLotofacil.distancia_manhattan(1, 6), 1)
        self.assertEqual(ModeloMatricialLotofacil.distancia_manhattan(13, 8), 1) # Centro para linha de cima
        self.assertEqual(ModeloMatricialLotofacil.distancia_manhattan(13, 14), 1)
        # Diagonais imediatas (distância = 2)
        self.assertEqual(ModeloMatricialLotofacil.distancia_manhattan(1, 7), 2)
        # Cantos opostos (distância máxima no grid planar 5x5 é 4+4 = 8)
        self.assertEqual(ModeloMatricialLotofacil.distancia_manhattan(1, 25), 8)

    def test_distancia_circular_z25(self):
        """Valida cálculo de menor distância modular no anel Z_25."""
        self.assertEqual(ModeloMatricialLotofacil.distancia_circular(1, 2), 1)
        self.assertEqual(ModeloMatricialLotofacil.distancia_circular(1, 25), 1)
        self.assertEqual(ModeloMatricialLotofacil.distancia_circular(25, 1), 1)
        self.assertEqual(ModeloMatricialLotofacil.distancia_circular(1, 13), 12)
        self.assertEqual(ModeloMatricialLotofacil.distancia_circular(1, 14), 12)

    def test_base_matricial_pura(self):
        """Valida que a base matricial pura possui 10 Moldura / 5 Miolo, paridade 7I/8P e soma 195."""
        base = ModeloMatricialLotofacil.gerar_base_pura()
        self.assertEqual(len(base), 15)
        self.assertEqual(len(set(base)), 15)
        self.assertEqual(base, [1, 2, 3, 6, 8, 10, 11, 14, 15, 17, 18, 19, 22, 24, 25])

        comp = ModeloMatricialLotofacil.analisar_composicao(base)
        self.assertEqual(comp["moldura"], 10)
        self.assertEqual(comp["miolo"], 5)
        self.assertEqual(comp["impares"], 7)
        self.assertEqual(comp["pares"], 8)
        self.assertEqual(comp["soma"], 195)
        self.assertEqual(comp["linhas"], [3, 3, 3, 3, 3])
        self.assertEqual(comp["colunas"], [3, 3, 3, 3, 3])

        # Todo número de 1 a 25 deve ter um vizinho a distância Manhattan <= 1
        base_coords = [ModeloMatricialLotofacil.coordenadas(x) for x in base]
        for n in range(1, 26):
            nr, nc = ModeloMatricialLotofacil.coordenadas(n)
            min_d = min(abs(nr - br) + abs(nc - bc) for br, bc in base_coords)
            self.assertLessEqual(min_d, 1, f"Número {n} tem distância > 1 no grid")

    def test_variantes_canonicas_lotofacil(self):
        """Valida as 5 variantes canônicas do Modelo Matricial 4.0 da Lotofácil."""
        variantes = ModeloMatricialLotofacil.gerar_variantes_canonicas()
        self.assertGreaterEqual(len(variantes), 5)

        for v in variantes:
            dezenas = v["dezenas"]
            self.assertEqual(len(dezenas), 15)
            self.assertEqual(len(set(dezenas)), 15)
            for n in dezenas:
                self.assertTrue(1 <= n <= 25)

            comp = ModeloMatricialLotofacil.analisar_composicao(dezenas)
            self.assertEqual(comp["moldura"], v["moldura"])
            self.assertEqual(comp["miolo"], v["miolo"])
            self.assertEqual(comp["impares"], v["impares"])
            self.assertEqual(comp["pares"], v["pares"])
            self.assertEqual(comp["soma"], v["soma"])
            self.assertTrue(v["moldura"] in (9, 10))
            self.assertTrue(v["impares"] in (7, 8))
            self.assertTrue(190 <= v["soma"] <= 200)

            # Cota máxima no grid <= 1
            v_coords = [ModeloMatricialLotofacil.coordenadas(x) for x in dezenas]
            for n in range(1, 26):
                nr, nc = ModeloMatricialLotofacil.coordenadas(n)
                min_d = min(abs(nr - br) + abs(nc - bc) for br, bc in v_coords)
                self.assertLessEqual(min_d, 1)

    def test_resumo_analise_lotofacil_mcom(self):
        """Valida que obter_resumo_analise identifica a Lotofácil como MCOM 4.0."""
        resumo = self.modelo_lotofacil.obter_resumo_analise()
        metodologia = resumo["metodologia"]
        self.assertEqual(metodologia["versao"], "4.0")
        self.assertIn("MCOM", metodologia["modelo"])
        self.assertIn("Lotofácil", metodologia["modelo"])
        self.assertIn("camada_espacial", resumo)
        self.assertEqual(resumo["camada_espacial"]["total_setores"], 5)
        self.assertEqual(resumo["camada_espacial"]["largura_setor"], 5.0)
        self.assertEqual(resumo["camada_espacial"]["distancia_maxima_teorica"], 1.0)

    def test_dispersao_matricial_metrica(self):
        """Testa o cálculo da Camada 8 Matricial para a Lotofácil."""
        jogo_equilibrado = [1, 2, 3, 6, 8, 10, 11, 14, 15, 17, 18, 19, 21, 24, 25]
        disp = self.modelo_lotofacil.calcular_dispersao_matricial_lotofacil(jogo_equilibrado)
        self.assertTrue(disp["disponivel"])
        self.assertEqual(disp["geometria"], "Matricial")
        self.assertEqual(disp["setores_cobertos"], 5)
        self.assertEqual(disp["total_setores"], 5)
        self.assertEqual(disp["moldura"], 10)
        self.assertEqual(disp["miolo"], 5)
        self.assertIn("Excelente", disp["classificacao"])
        self.assertGreaterEqual(disp["indice_dispersao"], 85.0)

        # Jogo desbalanceado (todas as 15 dezenas nas primeiras 3 linhas)
        jogo_desbalanceado = list(range(1, 16))
        disp_desb = self.modelo_lotofacil.calcular_dispersao_matricial_lotofacil(jogo_desbalanceado)
        self.assertEqual(disp_desb["setores_cobertos"], 3)
        self.assertIn("Concentrada", disp_desb["classificacao"])
        self.assertLess(disp_desb["indice_dispersao"], 50.0)

    def test_despacho_polimorfico_espacial(self):
        """Testa calcular_dispersao_espacial despachando para Matricial na Lotofácil."""
        jogo = [1, 2, 3, 6, 8, 10, 11, 14, 15, 17, 18, 19, 21, 24, 25]
        disp = self.modelo_lotofacil.calcular_dispersao_espacial(jogo)
        self.assertEqual(disp["geometria"], "Matricial")
        self.assertEqual(disp["total_setores"], 5)
        self.assertEqual(disp["distancia_maxima_garantida"], 1)

    def test_geracao_jogos_lotofacil(self):
        """Testa geração de jogos matriciais na Lotofácil."""
        jogos = self.modelo_lotofacil.gerar_jogos_lotofacil(quantidade_jogos=5, quantidade_numeros=15)
        self.assertEqual(len(jogos), 5)
        jogos_tuplas = [tuple(j) for j in jogos]
        self.assertEqual(len(set(jogos_tuplas)), 5)

        for j in jogos:
            self.assertEqual(len(j), 15)
            for n in j:
                self.assertTrue(1 <= n <= 25)
            comp = ModeloMatricialLotofacil.analisar_composicao(j)
            self.assertTrue(comp["moldura"] in (9, 10, 11))
            self.assertTrue(comp["impares"] in (6, 7, 8, 9))
            self.assertTrue(175 <= comp["soma"] <= 215)
            disp = self.modelo_lotofacil.calcular_dispersao_matricial_lotofacil(j)
            self.assertEqual(disp["setores_cobertos"], 5)

    def test_gerar_jogo_sugerido_lotofacil(self):
        """Testa a geração de jogo sugerido na Lotofácil utilizando o modelo matricial."""
        sugerido = gerar_jogo_sugerido(self.modelo_lotofacil, 15)
        self.assertEqual(len(sugerido), 15)
        for n in sugerido:
            self.assertTrue(1 <= n <= 25)
        disp = self.modelo_lotofacil.calcular_dispersao_matricial_lotofacil(sugerido)
        self.assertEqual(disp["setores_cobertos"], 5)
        self.assertGreaterEqual(disp["indice_dispersao"], 80.0)

    def test_gerar_multiplos_jogos_lotofacil(self):
        """Testa a geração de múltiplos jogos na Lotofácil."""
        jogos = gerar_multiplos_jogos(self.modelo_lotofacil, quantidade_jogos=4, quantidade_numeros=15)
        self.assertEqual(len(jogos), 4)
        for j in jogos:
            self.assertEqual(len(j), 15)

    def test_avaliacao_jogo_lotofacil(self):
        """Valida que avaliacao.py inclui métricas matriciais para a Lotofácil."""
        jogo = [1, 2, 3, 6, 8, 10, 11, 14, 15, 17, 18, 19, 21, 24, 25]
        resultado = avaliacao.avaliar_jogo(jogo, self.modelo_lotofacil)
        self.assertTrue(resultado["valido"])
        self.assertIn("dispersao_espacial", resultado)
        self.assertIn("dispersao_matricial", resultado)
        self.assertEqual(resultado["dispersao_matricial"]["geometria"], "Matricial")

        parecer = avaliacao.parecer_jogos([jogo], self.modelo_lotofacil)
        self.assertIn("Dispersão Espacial Matricial", parecer["parecer_texto"])
        self.assertIn("MCOM 4.0", parecer["parecer_texto"])


if __name__ == "__main__":
    unittest.main()

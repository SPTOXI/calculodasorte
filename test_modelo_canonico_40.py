"""
Testes unitários e de integração para o Modelo Canônico 4.0 (MCOH)
Validação matemática do reticulado hexagonal, compatibilidade retroativa e avaliação espacial.
"""

import math
import statistics
import unittest
from core import (
    LoteriaConfig, 
    LoteriaType, 
    ModeloCanonico40, 
    ModeloCanonico30, 
    gerar_jogo_sugerido, 
    gerar_multiplos_jogos
)
import avaliacao
from modelo_hexagonal import ModeloHexagonal


class TestModeloCanonico40(unittest.TestCase):
    def setUp(self):
        # Histórico sintético determinístico com 30 concursos para Mega-Sena (N=60, k=6)
        self.historico = []
        for i in range(30):
            # Gera concurso distribuído
            base = [(i * 2 + j * 10) % 60 + 1 for j in range(6)]
            self.historico.append(sorted(list(set(base))))
            while len(self.historico[-1]) < 6:
                self.historico[-1].append((self.historico[-1][-1] % 60) + 1)
                self.historico[-1] = sorted(list(set(self.historico[-1])))

        self.modelo40 = ModeloCanonico40(self.historico, LoteriaType.MEGA_SENA)

    def test_retrocompatibilidade_modelo_canonico_30(self):
        """Garante que ModeloCanonico30 é um alias idêntico a ModeloCanonico40"""
        self.assertIs(ModeloCanonico30, ModeloCanonico40)
        modelo30 = ModeloCanonico30(self.historico, LoteriaType.MEGA_SENA)
        self.assertEqual(modelo30.T, 30)
        self.assertEqual(modelo30.N, 60)

    def test_resumo_analise_versao_40(self):
        """Valida se o resumo da metodologia reflete a versão 4.0 e a camada espacial"""
        resumo = self.modelo40.obter_resumo_analise()
        metodologia = resumo["metodologia"]
        self.assertEqual(metodologia["versao"], "4.0")
        self.assertIn("Canônico 4.0", metodologia["modelo"])
        self.assertIn("camada_espacial", resumo)
        self.assertEqual(resumo["camada_espacial"]["total_setores"], 6)

    def test_dispersao_hexagonal_metrica(self):
        """Testa o cálculo da Camada 8 (Dispersão Hexagonal)"""
        # Jogo com 1 dezena em cada setor (05, 15, 25, 35, 45, 55)
        jogo_perfeito = [5, 15, 25, 35, 45, 55]
        disp = self.modelo40.calcular_dispersao_hexagonal(jogo_perfeito)
        self.assertTrue(disp["disponivel"])
        self.assertEqual(disp["setores_cobertos"], 6)
        self.assertEqual(disp["total_setores"], 6)
        self.assertIn("Excelente", disp["classificacao"])
        self.assertLessEqual(disp["distancia_maxima_centros"], 1.0)
        self.assertGreaterEqual(disp["indice_dispersao"], 90.0)

        # Jogo hiper-concentrado (todas no primeiro setor: 1, 2, 3, 4, 5, 6)
        jogo_concentrado = [1, 2, 3, 4, 5, 6]
        disp_conc = self.modelo40.calcular_dispersao_hexagonal(jogo_concentrado)
        self.assertEqual(disp_conc["setores_cobertos"], 1)
        self.assertIn("Concentrada", disp_conc["classificacao"])
        self.assertLess(disp_conc["indice_dispersao"], 40.0)

    def test_geracao_jogos_hexagonais(self):
        """Testa a geração de múltiplos jogos hexagonais com paridade equilibrada"""
        jogos = self.modelo40.gerar_jogos_hexagonais(quantidade_jogos=5, quantidade_numeros=6)
        self.assertEqual(len(jogos), 5)
        # Todos os jogos devem ser únicos
        jogos_tuplas = [tuple(j) for j in jogos]
        self.assertEqual(len(set(jogos_tuplas)), 5)

        for j in jogos:
            self.assertEqual(len(j), 6)
            # Todos os números no universo
            for n in j:
                self.assertTrue(1 <= n <= 60)
            # Paridade entre 2 e 4 pares
            pares = sum(1 for n in j if n % 2 == 0)
            self.assertTrue(2 <= pares <= 4)
            # Pelo menos 4 setores cobertos
            disp = self.modelo40.calcular_dispersao_hexagonal(j)
            self.assertGreaterEqual(disp["setores_cobertos"], 4)

    def test_gerar_jogo_sugerido_com_modelo_40(self):
        """Testa a função central gerar_jogo_sugerido"""
        sugerido = gerar_jogo_sugerido(self.modelo40, 6)
        self.assertEqual(len(sugerido), 6)
        disp = self.modelo40.calcular_dispersao_hexagonal(sugerido)
        self.assertGreaterEqual(disp["setores_cobertos"], 5)

    def test_gerar_multiplos_jogos_com_modelo_40(self):
        """Testa a geração de múltiplos jogos balanceados 4.0"""
        jogos = gerar_multiplos_jogos(self.modelo40, quantidade_jogos=4, quantidade_numeros=6)
        self.assertEqual(len(jogos), 4)
        for j in jogos:
            self.assertEqual(len(j), 6)

    def test_avaliacao_jogo_inclui_dispersao_hexagonal(self):
        """Testa se avaliar_jogo em avaliacao.py retorna os dados da dispersão hexagonal"""
        jogo = [4, 15, 26, 33, 44, 55]
        resultado = avaliacao.avaliar_jogo(jogo, self.modelo40)
        self.assertTrue(resultado["valido"])
        self.assertIn("dispersao_hexagonal", resultado)
        self.assertTrue(resultado["dispersao_hexagonal"]["disponivel"])
        self.assertEqual(resultado["dispersao_hexagonal"]["setores_cobertos"], 6)

    def test_parecer_jogos_provedor_modelo_40(self):
        """Testa se o parecer_jogos reporta Modelo Canônico 4.0"""
        jogos = [[4, 15, 26, 33, 44, 55]]
        parecer = avaliacao.parecer_jogos(jogos, self.modelo40)
        self.assertIn("4.0", parecer["provedor"])
        self.assertIn("Dispersão Espacial Hexagonal", parecer["parecer_texto"])

    def test_modulo_hexagonal_independente(self):
        """Valida que modelo_hexagonal.py gera variantes com limites teóricos estritos"""
        variantes = ModeloHexagonal.gerar_variantes_canonicas()
        self.assertGreaterEqual(len(variantes), 4)
        for v in variantes:
            self.assertEqual(len(v["dezenas"]), 6)
            self.assertLessEqual(v["dist_max"], 6)


if __name__ == "__main__":
    unittest.main()

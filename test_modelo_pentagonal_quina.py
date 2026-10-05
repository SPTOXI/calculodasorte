"""
Testes unitários e de integração para o Modelo Pentagonal da Quina (MCOP 4.0)
Validação matemática do reticulado pentagonal Z_80, equilíbrio harmônico,
integração com Modelo Canônico 4.0 e avaliação de proximidade espacial.
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
from modelo_pentagonal import ModeloPentagonalQuina, ModeloPentagonal


class TestModeloPentagonalQuina(unittest.TestCase):
    def setUp(self):
        # Histórico sintético determinístico com 40 concursos para Quina (N=80, k=5)
        self.historico = []
        for i in range(40):
            base = [(i * 3 + j * 16) % 80 + 1 for j in range(5)]
            sorteio = sorted(list(set(base)))
            while len(sorteio) < 5:
                prox = (sorteio[-1] % 80) + 1
                if prox not in sorteio:
                    sorteio.append(prox)
                else:
                    sorteio.append(((prox + 3) % 80) + 1)
                sorteio = sorted(list(set(sorteio)))
            self.historico.append(sorteio[:5])

        self.modelo_quina = ModeloCanonico40(self.historico, LoteriaType.QUINA)

    def test_distancia_circular_z80(self):
        """Valida cálculo de menor distância modular no anel Z_80."""
        # Vizinhos diretos no anel cíclico
        self.assertEqual(ModeloPentagonalQuina.distancia_circular(1, 2), 1)
        self.assertEqual(ModeloPentagonalQuina.distancia_circular(1, 80), 1)
        self.assertEqual(ModeloPentagonalQuina.distancia_circular(80, 1), 1)
        self.assertEqual(ModeloPentagonalQuina.distancia_circular(10, 20), 10)
        # Antípodas (máxima distância possível no anel de 80 números é 40)
        self.assertEqual(ModeloPentagonalQuina.distancia_circular(1, 41), 40)
        self.assertEqual(ModeloPentagonalQuina.distancia_circular(1, 42), 39)

    def test_base_pentagonal_pura(self):
        """Valida que a base pentagonal pura delta=8 produz [08, 24, 40, 56, 72] com cota max <= 8."""
        base = ModeloPentagonalQuina.gerar_base_pura(delta=8)
        self.assertEqual(base, [8, 24, 40, 56, 72])
        self.assertEqual(len(base), 5)

        # Para qualquer número de 1 a 80, a distância para o vértice mais próximo deve ser <= 8
        for n in range(1, 81):
            d_min = min(ModeloPentagonalQuina.distancia_circular(n, v) for v in base)
            self.assertLessEqual(d_min, 8, f"Número {n} excedeu distância máxima teórica de 8")

    def test_variantes_canonicas_pentagonais(self):
        """Valida variantes canônicas pentagonais equilibradas para a Quina."""
        variantes = ModeloPentagonalQuina.gerar_variantes_canonicas()
        self.assertGreaterEqual(len(variantes), 5)

        for v in variantes:
            dezenas = v["dezenas"]
            self.assertEqual(len(dezenas), 5)
            # Todos os números no universo de 1 a 80
            for n in dezenas:
                self.assertTrue(1 <= n <= 80)
            # Cota de distância estritamente limitada
            self.assertLessEqual(v["dist_max"], 9)
            # Cobertura de 5 setores
            setores = set((n - 1) // 16 for n in dezenas)
            self.assertEqual(len(setores), 5, "Variante deve ter 1 dezena em cada setor")

            # Validação de paridade declarada
            pares = sum(1 for n in dezenas if n % 2 == 0)
            self.assertEqual(pares, v["pares"])
            self.assertEqual(5 - pares, v["impares"])

    def test_resumo_analise_quina_mcop(self):
        """Valida que obter_resumo_analise identifica a Quina como MCOP 4.0."""
        resumo = self.modelo_quina.obter_resumo_analise()
        metodologia = resumo["metodologia"]
        self.assertEqual(metodologia["versao"], "4.0")
        self.assertIn("MCOP", metodologia["modelo"])
        self.assertIn("Quina", metodologia["modelo"])
        self.assertIn("camada_espacial", resumo)
        self.assertEqual(resumo["camada_espacial"]["total_setores"], 5)
        self.assertEqual(resumo["camada_espacial"]["largura_setor"], 16.0)
        self.assertEqual(resumo["camada_espacial"]["distancia_maxima_teorica"], 8.0)

    def test_dispersao_pentagonal_metrica(self):
        """Testa o cálculo da Camada 8 Pentagonal para a Quina."""
        # Jogo equilibrado cobrindo todos os 5 setores
        jogo_amplo = [7, 24, 39, 56, 72]
        disp = self.modelo_quina.calcular_dispersao_pentagonal(jogo_amplo)
        self.assertTrue(disp["disponivel"])
        self.assertEqual(disp["geometria"], "Pentagonal")
        self.assertEqual(disp["setores_cobertos"], 5)
        self.assertEqual(disp["total_setores"], 5)
        self.assertIn("Excelente", disp["classificacao"])
        self.assertLessEqual(disp["distancia_maxima_centros"], 2.0)
        self.assertGreaterEqual(disp["indice_dispersao"], 90.0)

        # Jogo aglomerado no setor 1
        jogo_aglomerado = [1, 2, 4, 8, 12]
        disp_aglomerado = self.modelo_quina.calcular_dispersao_pentagonal(jogo_aglomerado)
        self.assertEqual(disp_aglomerado["setores_cobertos"], 1)
        self.assertIn("Concentrada", disp_aglomerado["classificacao"])
        self.assertLess(disp_aglomerado["indice_dispersao"], 45.0)

    def test_despacho_polimorfico_espacial(self):
        """Testa calcular_dispersao_espacial despachando para Pentagonal na Quina."""
        jogo = [7, 24, 39, 56, 72]
        disp = self.modelo_quina.calcular_dispersao_espacial(jogo)
        self.assertEqual(disp["geometria"], "Pentagonal")
        self.assertEqual(disp["total_setores"], 5)

        # E calcular_dispersao_hexagonal em Quina deve redirecionar graciosamente
        disp_hex = self.modelo_quina.calcular_dispersao_hexagonal(jogo)
        self.assertEqual(disp_hex["geometria"], "Pentagonal")

    def test_geracao_jogos_pentagonais(self):
        """Testa geração de jogos pentagonais na Quina."""
        jogos = self.modelo_quina.gerar_jogos_pentagonais(quantidade_jogos=5, quantidade_numeros=5)
        self.assertEqual(len(jogos), 5)
        # Todos os jogos devem ser únicos
        jogos_tuplas = [tuple(j) for j in jogos]
        self.assertEqual(len(set(jogos_tuplas)), 5)

        for j in jogos:
            self.assertEqual(len(j), 5)
            for n in j:
                self.assertTrue(1 <= n <= 80)
            pares = sum(1 for n in j if n % 2 == 0)
            self.assertTrue(2 <= pares <= 3, f"Paridade de {j} deve ser 2P/3I ou 3P/2I")
            disp = self.modelo_quina.calcular_dispersao_pentagonal(j)
            self.assertGreaterEqual(disp["setores_cobertos"], 4)

    def test_gerar_jogo_sugerido_quina(self):
        """Testa a geração de jogo sugerido na Quina utilizando o modelo pentagonal."""
        sugerido = gerar_jogo_sugerido(self.modelo_quina, 5)
        self.assertEqual(len(sugerido), 5)
        for n in sugerido:
            self.assertTrue(1 <= n <= 80)
        disp = self.modelo_quina.calcular_dispersao_pentagonal(sugerido)
        self.assertGreaterEqual(disp["setores_cobertos"], 4)

    def test_gerar_multiplos_jogos_quina(self):
        """Testa a geração de múltiplos jogos na Quina."""
        jogos = gerar_multiplos_jogos(self.modelo_quina, quantidade_jogos=4, quantidade_numeros=5)
        self.assertEqual(len(jogos), 4)
        for j in jogos:
            self.assertEqual(len(j), 5)

    def test_avaliacao_jogo_quina(self):
        """Valida que avaliacao.py inclui métricas pentagonais para a Quina."""
        jogo = [7, 24, 39, 56, 72]
        resultado = avaliacao.avaliar_jogo(jogo, self.modelo_quina)
        self.assertTrue(resultado["valido"])
        self.assertIn("dispersao_espacial", resultado)
        self.assertIn("dispersao_pentagonal", resultado)
        self.assertEqual(resultado["dispersao_pentagonal"]["geometria"], "Pentagonal")

        parecer = avaliacao.parecer_jogos([jogo], self.modelo_quina)
        self.assertIn("Dispersão Espacial Pentagonal", parecer["parecer_texto"])
        self.assertIn("MCOP 4.0", parecer["parecer_texto"])


if __name__ == "__main__":
    unittest.main()

"""
Testes Unitários para a Dinâmica Canônica de Expansão e Retração por Casa.
Cobre todas as 9 loterias da Caixa Econômica Federal.
"""

import unittest
from dinamica_canonica import AvaliadorDinamicaCanonica, ResultadoDinamica


class TestDinamicaCanonica(unittest.TestCase):
    def setUp(self):
        self.avaliador = AvaliadorDinamicaCanonica

    def test_super_sete_expansao_e_retracao(self):
        """Valida detecção de expansão, retração e ajuste restaurador no Super Sete."""
        # Último sorteio com colunas acima e abaixo dos centros [4, 5, 4, 5, 4, 5, 4]
        historico = [
            [4, 5, 4, 5, 4, 5, 4],  # Concurso penúltimo (centros)
            [8, 2, 9, 1, 4, 7, 0],  # Concurso último
        ]
        res = self.avaliador.avaliar_dinamica("super_sete", historico, ultimo_concurso_id=907)

        self.assertIsInstance(res, ResultadoDinamica)
        self.assertEqual(res.total_casas, 7)
        self.assertEqual(len(res.casas), 7)
        self.assertEqual(len(res.jogo_ajustado), 7)

        # Coluna 1: 8 vs centro 4 -> Expansão -> Ajuste negativo
        c1 = res.casas[0]
        self.assertEqual(c1.estado, "expansao")
        self.assertLess(c1.ajuste_aplicado, 0)
        self.assertLess(c1.valor_ajustado, 8)

        # Coluna 2: 2 vs centro 5 -> Retração -> Ajuste positivo
        c2 = res.casas[1]
        self.assertEqual(c2.estado, "retracao")
        self.assertGreater(c2.ajuste_aplicado, 0)
        self.assertGreater(c2.valor_ajustado, 2)

        # Coluna 5: 4 vs centro 4 -> Equilíbrio -> Ajuste 0
        c5 = res.casas[4]
        self.assertEqual(c5.estado, "equilibrio")
        self.assertEqual(c5.ajuste_aplicado, 0)
        self.assertEqual(c5.valor_ajustado, 4)

        # Todos os dígitos ajustados devem ser válidos (0 a 9)
        for d in res.jogo_ajustado:
            self.assertTrue(0 <= d <= 9)

    def test_mega_sena_setores_hexagonais(self):
        """Valida dinâmica nos 6 setores da Mega-Sena."""
        historico = [
            [5, 15, 25, 35, 45, 55],
            [9, 12, 28, 33, 49, 52],
        ]
        res = self.avaliador.avaliar_dinamica("mega_sena", historico, ultimo_concurso_id=2800)

        self.assertEqual(res.total_casas, 6)
        self.assertEqual(len(res.jogo_ajustado), 6)
        # Jogo ajustado deve ter 6 dezenas únicas ordenadas entre 1 e 60
        self.assertEqual(len(set(res.jogo_ajustado)), 6)
        for d in res.jogo_ajustado:
            self.assertTrue(1 <= d <= 60)

    def test_quina_setores_pentagonais(self):
        """Valida dinâmica nos 5 setores da Quina."""
        historico = [
            [8, 24, 40, 56, 72],
            [15, 18, 42, 50, 78],
        ]
        res = self.avaliador.avaliar_dinamica("quina", historico, ultimo_concurso_id=6500)

        self.assertEqual(res.total_casas, 5)
        self.assertEqual(len(res.jogo_ajustado), 5)
        self.assertEqual(len(set(res.jogo_ajustado)), 5)
        for d in res.jogo_ajustado:
            self.assertTrue(1 <= d <= 80)

    def test_lotofacil_matricial_5x5(self):
        """Valida dinâmica matricial e balanceamento para 15 dezenas na Lotofácil."""
        historico = [
            [1, 2, 3, 6, 7, 8, 11, 12, 13, 16, 17, 18, 21, 22, 23],
            [1, 2, 3, 4, 6, 7, 11, 12, 13, 14, 15, 16, 21, 22, 23],  # Linha 1=4, Linha 2=2, Linha 3=5, Linha 4=1, Linha 5=3
        ]
        res = self.avaliador.avaliar_dinamica("lotofacil", historico, ultimo_concurso_id=3200)

        self.assertEqual(res.total_casas, 5)
        self.assertEqual(len(res.jogo_ajustado), 15)
        self.assertEqual(len(set(res.jogo_ajustado)), 15)
        for d in res.jogo_ajustado:
            self.assertTrue(1 <= d <= 25)

    def test_lotomania_matricial_10x10(self):
        """Valida dinâmica das 10 linhas e geração das 50 dezenas na Lotomania."""
        # 20 dezenas sorteadas
        concurso_1 = list(range(0, 40, 2))
        concurso_2 = list(range(1, 41, 2))
        historico = [concurso_1, concurso_2]
        res = self.avaliador.avaliar_dinamica("lotomania", historico, ultimo_concurso_id=2600)

        self.assertEqual(res.total_casas, 10)
        self.assertEqual(len(res.jogo_ajustado), 50)
        self.assertEqual(len(set(res.jogo_ajustado)), 50)
        for d in res.jogo_ajustado:
            self.assertTrue(0 <= d <= 99)

    def test_dupla_sena_bivariada(self):
        """Valida dinâmica nos setores da Dupla Sena."""
        historico = [
            [4, 13, 21, 30, 38, 46],
            [6, 11, 24, 28, 40, 48],
        ]
        res = self.avaliador.avaliar_dinamica("dupla_sena", historico, ultimo_concurso_id=2700)

        self.assertEqual(res.total_casas, 6)
        self.assertEqual(len(res.jogo_ajustado), 6)
        self.assertEqual(len(set(res.jogo_ajustado)), 6)
        for d in res.jogo_ajustado:
            self.assertTrue(1 <= d <= 50)

    def test_mais_milionaria_biparametrica(self):
        """Valida dinâmica das dezenas e trevos da +Milionária."""
        historico = [
            [4, 13, 21, 30, 38, 46],
            [7, 10, 23, 31, 39, 45],
        ]
        res = self.avaliador.avaliar_dinamica("mais_milionaria", historico, ultimo_concurso_id=180)

        self.assertEqual(res.total_casas, 6)
        self.assertEqual(len(res.jogo_ajustado), 6)
        self.assertEqual(len(set(res.jogo_ajustado)), 6)
        self.assertIsNotNone(res.complemento)
        self.assertIn("trevos_ajustados", res.complemento)

    def test_dia_de_sorte_heptagonal(self):
        """Valida dinâmica dos 7 dias e mês do Dia de Sorte."""
        historico = [
            [3, 7, 12, 16, 21, 25, 30],
            [1, 8, 11, 18, 20, 26, 29],
        ]
        res = self.avaliador.avaliar_dinamica("dia_de_sorte", historico, ultimo_concurso_id=980)

        self.assertEqual(res.total_casas, 7)
        self.assertEqual(len(res.jogo_ajustado), 7)
        self.assertEqual(len(set(res.jogo_ajustado)), 7)
        for d in res.jogo_ajustado:
            self.assertTrue(1 <= d <= 31)
        self.assertIsNotNone(res.complemento)
        self.assertIn("mes_ajustado", res.complemento)

    def test_timemania_decagonal(self):
        """Valida dinâmica dos 10 setores da Timemania."""
        historico = [
            [4, 12, 20, 28, 36, 44, 52],
            [6, 10, 22, 30, 34, 46, 50],
        ]
        res = self.avaliador.avaliar_dinamica("timemania", historico, ultimo_concurso_id=2100)

        self.assertEqual(res.total_casas, 10)
        self.assertEqual(len(res.jogo_ajustado), 10)
        self.assertEqual(len(set(res.jogo_ajustado)), 10)
        for d in res.jogo_ajustado:
            self.assertTrue(1 <= d <= 80)
        self.assertIsNotNone(res.complemento)
        self.assertIn("time_ajustado", res.complemento)

    def test_verificacao_ultimos_jogos_com_ultimo_resultado_9_loterias(self):
        """Valida que a inteligência de verificação compara os últimos jogos com o último resultado em todas as 9 loterias."""
        historicos_teste = {
            "mega_sena": [
                [4, 14, 24, 34, 44, 54],
                [7, 17, 27, 37, 47, 57],
                [5, 15, 25, 35, 45, 55],
                [9, 12, 28, 33, 49, 52],
            ],
            "quina": [
                [6, 22, 38, 54, 70],
                [10, 26, 42, 58, 74],
                [8, 24, 40, 56, 72],
                [14, 19, 44, 51, 77],
            ],
            "lotofacil": [
                [1, 2, 3, 6, 7, 8, 11, 12, 13, 16, 17, 18, 21, 22, 23],
                [2, 3, 4, 7, 8, 9, 12, 13, 14, 17, 18, 19, 22, 23, 24],
                [1, 3, 5, 6, 8, 10, 11, 13, 15, 16, 18, 20, 21, 23, 25],
                [1, 2, 4, 5, 6, 9, 11, 12, 14, 15, 17, 19, 20, 22, 25],
            ],
            "timemania": [
                [3, 11, 19, 27, 35, 43, 51],
                [5, 13, 21, 29, 37, 45, 53],
                [4, 12, 20, 28, 36, 44, 52],
                [7, 14, 22, 31, 39, 48, 56],
            ],
            "lotomania": [
                list(range(0, 40, 2)),
                list(range(1, 41, 2)),
                list(range(2, 62, 3)),
                list(range(3, 63, 3)),
            ],
            "mais_milionaria": [
                [3, 11, 19, 27, 35, 43],
                [5, 13, 21, 29, 37, 45],
                [4, 12, 20, 28, 36, 44],
                [8, 15, 23, 31, 39, 47],
            ],
            "dia_de_sorte": [
                [2, 6, 11, 15, 20, 24, 29],
                [4, 8, 13, 17, 22, 26, 31],
                [3, 7, 12, 16, 21, 25, 30],
                [1, 9, 14, 18, 23, 27, 31],
            ],
            "dupla_sena": [
                [3, 11, 19, 27, 35, 43],
                [5, 13, 21, 29, 37, 45],
                [4, 12, 20, 28, 36, 44],
                [7, 15, 23, 31, 39, 48],
            ],
            "super_sete": [
                [3, 4, 3, 4, 3, 4, 3],
                [5, 6, 5, 6, 5, 6, 5],
                [4, 5, 4, 5, 4, 5, 4],
                [8, 2, 7, 1, 6, 3, 9],
            ],
        }

        for loteria, hist in historicos_teste.items():
            with self.subTest(loteria=loteria):
                res = self.avaliador.avaliar_dinamica(loteria, hist, ultimo_concurso_id=100)
                self.assertIsNotNone(res.verificacao_ultimos_jogos)
                verif = res.verificacao_ultimos_jogos
                self.assertTrue(verif.get("disponivel"))
                self.assertIn("indice_assertividade", verif)
                self.assertIn("fator_restaurador_medio", verif)
                self.assertIn("movimento_numerais", verif)
                self.assertIn("resumo_aprendizado", verif)
                self.assertGreaterEqual(verif["indice_assertividade"], 0.0)
                self.assertLessEqual(verif["indice_assertividade"], 100.0)
                for casa in res.casas:
                    self.assertGreater(casa.fator_restaurador, 0.0)
                    self.assertTrue(len(casa.tendencia_numeral) > 0)

    def test_lotofacil_e_lotomania_respondem_dinamicamente_ao_historico(self):
        """Garante que Lotofácil e Lotomania alteram o jogo ajustado conforme expansão ou retração recente."""
        hist_lf_baixo = [
            [1, 2, 3, 6, 7, 8, 11, 12, 13, 16, 17, 18, 21, 22, 23],
            [1, 2, 6, 7, 11, 12, 16, 17, 18, 19, 20, 21, 22, 23, 24],
        ]
        hist_lf_alto = [
            [3, 4, 5, 8, 9, 10, 13, 14, 15, 18, 19, 20, 23, 24, 25],
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 15, 19, 20, 25],
        ]
        res_lf_1 = self.avaliador.avaliar_dinamica("lotofacil", hist_lf_baixo)
        res_lf_2 = self.avaliador.avaliar_dinamica("lotofacil", hist_lf_alto)
        self.assertNotEqual(res_lf_1.jogo_ajustado, res_lf_2.jogo_ajustado)

        hist_lm_1 = [list(range(0, 20)), list(range(0, 40, 2))]
        hist_lm_2 = [list(range(80, 100)), list(range(9, 100, 5))]
        res_lm_1 = self.avaliador.avaliar_dinamica("lotomania", hist_lm_1)
        res_lm_2 = self.avaliador.avaliar_dinamica("lotomania", hist_lm_2)
        self.assertNotEqual(res_lm_1.jogo_ajustado, res_lm_2.jogo_ajustado)


class TestMetodosAnaliseTradicionaisECanonica(unittest.TestCase):
    """Testa as 6 opções de análise e geração escolhidas pelo usuário."""

    def test_todos_os_metodos_geram_jogos_validos_nas_loterias(self):
        from core import ModeloCanonico40, LoteriaType
        from metodos_analise import METODOS_ANALISE_DISPONIVEIS, sugerir_grupo_para_fechamento

        historicos = {
            LoteriaType.MEGA_SENA: [
                [4, 14, 24, 34, 44, 54],
                [7, 17, 27, 37, 47, 57],
                [5, 15, 25, 35, 45, 55],
                [9, 12, 28, 33, 49, 52],
                [2, 11, 23, 36, 48, 59],
            ],
            LoteriaType.LOTOFACIL: [
                [1, 2, 3, 6, 7, 8, 11, 12, 13, 16, 17, 18, 21, 22, 23],
                [2, 3, 4, 7, 8, 9, 12, 13, 14, 17, 18, 19, 22, 23, 24],
                [1, 3, 5, 6, 8, 10, 11, 13, 15, 16, 18, 20, 21, 23, 25],
                [1, 2, 4, 5, 6, 9, 11, 12, 14, 15, 17, 19, 20, 22, 25],
            ],
            LoteriaType.SUPER_SETE: [
                [3, 4, 3, 4, 3, 4, 3],
                [5, 6, 5, 6, 5, 6, 5],
                [4, 5, 4, 5, 4, 5, 4],
                [8, 2, 7, 1, 6, 3, 9],
            ],
            LoteriaType.LOTOMANIA: [
                list(range(0, 40, 2)),
                list(range(1, 41, 2)),
                list(range(2, 62, 3)),
                list(range(3, 63, 3)),
            ],
        }

        for loteria_enum, hist in historicos.items():
            modelo = ModeloCanonico40(hist, loteria_enum)
            opcoes = modelo.obter_opcoes_analise()
            self.assertIn("catalogo_metodos", opcoes)
            self.assertIn("canonica_dinamica", opcoes)
            self.assertIn("frequencia_quentes", opcoes)
            self.assertIn("atraso_frios", opcoes)
            self.assertIn("equilibrio_classico", opcoes)
            self.assertIn("fechamento", opcoes)
            self.assertIn("hibrida_tradicional", opcoes)

            k_min = modelo.config.minimo_aposta
            for metodo in METODOS_ANALISE_DISPONIVEIS.keys():
                with self.subTest(loteria=loteria_enum.value, metodo=metodo):
                    jogos = modelo.gerar_multiplos_jogos(
                        quantidade_jogos=3,
                        quantidade_numeros=k_min,
                        metodo=metodo,
                    )
                    self.assertEqual(len(jogos), 3)
                    for j in jogos:
                        self.assertEqual(len(j), k_min)
                        if not modelo.config.colunas:
                            self.assertEqual(len(set(j)), k_min)

            if not modelo.config.colunas and loteria_enum != LoteriaType.LOTOMANIA:
                grupo = sugerir_grupo_para_fechamento(modelo, k_min + 4, estrategia="hibrido")
                self.assertEqual(len(grupo), k_min + 4)
                self.assertEqual(len(set(grupo)), k_min + 4)


if __name__ == '__main__':
    unittest.main()



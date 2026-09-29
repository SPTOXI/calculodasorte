"""Regressões matemáticas da camada 7, sem rede, Flask ou banco de dados."""

import itertools
import math
import random
import unittest
from collections import Counter
from unittest.mock import patch

from core import LoteriaConfig, LoteriaType, ModeloCanonico30
from validacao import (
    THETAS_ALTERNATIVA,
    ValidaçãoCamada7,
    _distribuicao_hipergeometrica,
)


def _config(N=20, k=5):
    return LoteriaConfig(
        nome="Sistema de teste", universo=N, sorteados=k,
        minimo_aposta=k, maximo_aposta=k, custo_minimo=0,
        dias_sorteio=[], faixas_premiacao=[],
    )


def _modelo(total=300, N=20, k=5, semente=21):
    rng = random.Random(semente)
    historico = [rng.sample(range(1, N + 1), k) for _ in range(total)]
    return ModeloCanonico30(historico, LoteriaType.MEGA_SENA, config_override=_config(N, k))


class TestDistribuicaoNula(unittest.TestCase):
    def test_probabilidades_e_momentos_conferem_com_enumeracao(self):
        sorteios = list(itertools.combinations(range(5), 3))
        contagens = Counter(len(set(c) & {0, 1}) for c in sorteios)
        pmf = _distribuicao_hipergeometrica(5, 2, 3)
        for x, contagem in contagens.items():
            self.assertAlmostEqual(pmf[x], contagem / len(sorteios))
        self.assertAlmostEqual(sum(pmf.values()), 1)
        media = sum(x * p for x, p in pmf.items())
        variancia = sum((x - media) ** 2 * p for x, p in pmf.items())
        self.assertAlmostEqual(media, 1.2)
        self.assertAlmostEqual(variancia, 0.36)

    def test_correcao_de_populacao_finita_no_backtest(self):
        modelo = _modelo(N=20, k=5)
        resultado = ValidaçãoCamada7(modelo).backtest()
        # Cinco dezenas, dez selecionados de vinte: Var = 5*.5*.5*(15/19).
        esperado = 150 * 5 * 0.5 * 0.5 * 15 / 19
        self.assertAlmostEqual(resultado["variancia_nula"], esperado)
        self.assertAlmostEqual(resultado["acertos_esperados"], 375)
        self.assertAlmostEqual(resultado["z_acumulado"],
                               (resultado["acertos"] - 375) / math.sqrt(esperado))

    def test_dupla_sena_conta_repeticoes_entre_sorteios(self):
        historico = [list(range(1, 7)) * 2 for _ in range(300)]
        modelo = ModeloCanonico30(historico, LoteriaType.DUPLA_SENA)
        validacao = ValidaçãoCamada7(modelo)
        selecao = (list(range(1, 11)), {"disponivel": True})
        with patch.object(validacao, "_selecionar_no_treino", return_value=selecao):
            resultado = validacao.backtest()
        nula = resultado["distribuicao_nula"]
        self.assertEqual(nula["sorteios_independentes_por_concurso"], 2)
        self.assertEqual(resultado["acertos"], 1800)
        self.assertAlmostEqual(nula["variancia_por_concurso"], 2 * 6 * .2 * .8 * 44 / 49)

    def test_super_sete_avalia_colunas_e_permite_repeticao(self):
        historico = [[3] * 7 for _ in range(300)]
        modelo = ModeloCanonico30(historico, LoteriaType.SUPER_SETE)
        validacao = ValidaçãoCamada7(modelo)
        selecao = ([3] * 7, {"disponivel": True})
        with patch.object(validacao, "_selecionar_no_treino", return_value=selecao):
            resultado = validacao.backtest()
        self.assertEqual(resultado["blocos"][0]["selecionados"], [3] * 7)
        self.assertEqual(resultado["acertos"], 1050)
        self.assertAlmostEqual(resultado["acertos_esperados"], 105)
        self.assertAlmostEqual(resultado["variancia_nula"], 94.5)
        self.assertEqual(resultado["distribuicao_nula"]["sorteados_por_sorteio"], 1)


class TestWalkForward(unittest.TestCase):
    def test_blocos_sao_disjuntos_e_treino_avanca_no_passado(self):
        validacao = ValidaçãoCamada7(_modelo(total=347))
        with patch.object(validacao, "_selecionar_no_treino", wraps=validacao._selecionar_no_treino) as selecionar:
            resultado = validacao.backtest()
        self.assertEqual([len(c.args[0]) for c in selecionar.call_args_list], [197, 247, 297])
        self.assertEqual([(b["inicio_teste"], b["fim_teste"]) for b in resultado["blocos"]],
                         [(198, 247), (248, 297), (298, 347)])
        self.assertEqual(resultado["concursos_teste"], 150)

    def test_alterar_futuro_nao_muda_selecoes_anteriores(self):
        original = _modelo()
        alterado = ModeloCanonico30(
            original.historico[:250] + [[1, 2, 3, 4, 5] for _ in range(50)],
            original.loteria_type, config_override=original.config,
        )
        antes = ValidaçãoCamada7(original).backtest()
        depois = ValidaçãoCamada7(alterado).backtest()
        self.assertEqual([b["selecionados"] for b in antes["blocos"]],
                         [b["selecionados"] for b in depois["blocos"]])
        self.assertEqual([b["acertos"] for b in antes["blocos"][:2]],
                         [b["acertos"] for b in depois["blocos"][:2]])

    def test_historico_curto_e_blocos_incompletos_nao_validam(self):
        curto = ValidaçãoCamada7(_modelo(total=199)).validacao_completa(simulacoes=20)
        self.assertEqual(curto["status"], "inconclusivo")
        self.assertFalse(curto["validacao_mcp_md"])
        self.assertIsNone(curto["bayesiana"]["bayes_factor"])
        parcial = ValidaçãoCamada7(_modelo(total=249)).validacao_completa(simulacoes=20)
        self.assertEqual(parcial["status"], "inconclusivo")
        self.assertEqual(len(parcial["backtest"]["blocos"]), 1)
        self.assertFalse(parcial["validacao_mcp_md"])

    def test_gamma_indefinido_no_treino_nao_valida(self):
        # Cada elemento aparece 75 vezes em 150 concursos: sigma_hist=0.
        historico = [[1, 2], [3, 4]] * 150
        modelo = ModeloCanonico30(historico, LoteriaType.MEGA_SENA, config_override=_config(4, 2))
        resultado = ValidaçãoCamada7(modelo).validacao_completa(simulacoes=20)
        self.assertEqual(resultado["status"], "inconclusivo")
        self.assertFalse(resultado["validacao_mcp_md"])
        self.assertFalse(resultado["backtest"]["disponivel"])

    def test_parametros_invalidos_sao_rejeitados(self):
        validacao = ValidaçãoCamada7(_modelo(total=10))
        for valor in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                validacao.backtest(janela_teste=valor)
            with self.assertRaises(ValueError):
                validacao.teste_monte_carlo(simulacoes=valor)


class TestMonteCarloEBayes(unittest.TestCase):
    @staticmethod
    def _backtest_pequeno(acertos=1, concursos=1):
        return {
            "disponivel": True,
            "acertos": acertos,
            "concursos_teste": concursos,
            "distribuicao_nula": {"suporte": [0, 1], "probabilidades": [.5, .5]},
        }

    def test_monte_carlo_reprodutivel_e_sem_mudar_rng_global(self):
        validacao = ValidaçãoCamada7(_modelo())
        estado = random.getstate()
        primeiro = validacao.teste_monte_carlo(simulacoes=250, semente=77)
        segundo = validacao.teste_monte_carlo(simulacoes=250, semente=77)
        self.assertEqual(primeiro, segundo)
        self.assertEqual(estado, random.getstate())
        self.assertGreater(primeiro["percentil"], 0)

    def test_monte_carlo_cauda_inclusiva_e_correcao_nao_nula(self):
        validacao = ValidaçãoCamada7(_modelo(total=10))
        with patch.object(validacao, "backtest", return_value=self._backtest_pequeno()):
            resultado = validacao.teste_monte_carlo(simulacoes=10000, semente=8)
        self.assertAlmostEqual(resultado["percentil"], .5, delta=.02)
        self.assertEqual(resultado["percentil"], (resultado["excedencias"] + 1) / 10001)
        with patch.object(validacao, "backtest", return_value=self._backtest_pequeno(acertos=2)):
            extremo = validacao.teste_monte_carlo(simulacoes=99, semente=8)
        self.assertEqual(extremo["percentil"], .01)
        self.assertFalse(extremo["significativo"])

    def test_bayes_factor_confere_com_likelihood_enumerada(self):
        validacao = ValidaçãoCamada7(_modelo(total=10))
        # Sob H0, P(111)=1/8; sob theta, P(111)=[exp(theta)/(1+exp(theta))]^3.
        likelihood_h1 = sum((math.exp(t) / (1 + math.exp(t))) ** 3 for t in THETAS_ALTERNATIVA) / 4
        esperado = likelihood_h1 / (1 / 8)
        with patch.object(validacao, "backtest", return_value=self._backtest_pequeno(acertos=3, concursos=3)):
            resultado = validacao.analise_bayesiana()
        self.assertAlmostEqual(resultado["bayes_factor"], esperado)
        self.assertAlmostEqual(resultado["log_bayes_factor"], math.log(esperado))
        with patch.object(validacao, "backtest", return_value=self._backtest_pequeno(acertos=0, concursos=3)):
            contrario = validacao.analise_bayesiana()
        self.assertLess(contrario["bayes_factor"], 1)

    def test_bayes_overflow_preserva_log_e_json_finito(self):
        validacao = ValidaçãoCamada7(_modelo(total=10))
        with patch.object(validacao, "backtest", return_value=self._backtest_pequeno(acertos=5000, concursos=5000)):
            resultado = validacao.analise_bayesiana()
        self.assertTrue(resultado["bayes_factor_limitado"])
        self.assertTrue(math.isfinite(resultado["bayes_factor"]))
        self.assertGreater(resultado["log_bayes_factor"], 709)

    def test_criterios_canonicos_sao_todos_obrigatorios(self):
        validacao = ValidaçãoCamada7(_modelo(total=10))
        backtest = {"disponivel": True, "blocos": [{}, {}, {}], "z_acumulado": 3.0,
                    "persistencia_blocos": True, "walk_forward_robusto": True}
        monte_carlo = {"significativo": True}
        bayes = {"evidencia_forte": True}
        with patch.object(validacao, "backtest", return_value=backtest), \
             patch.object(validacao, "teste_monte_carlo", return_value=monte_carlo), \
             patch.object(validacao, "analise_bayesiana", return_value=bayes):
            self.assertTrue(validacao.validacao_completa()["validacao_mcp_md"])
            for objeto, campo, falha in (
                (backtest, "z_acumulado", 2.0),
                (backtest, "persistencia_blocos", False),
                (backtest, "walk_forward_robusto", False),
                (monte_carlo, "significativo", False),
                (bayes, "evidencia_forte", False),
            ):
                valor_original = objeto[campo]
                objeto[campo] = falha
                resultado = validacao.validacao_completa()
                self.assertFalse(resultado["validacao_mcp_md"], campo)
                self.assertNotIn("ruído estatístico", resultado["conclusao"].lower())
                objeto[campo] = valor_original


if __name__ == "__main__":
    unittest.main()

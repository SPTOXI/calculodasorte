"""
Módulo de Dinâmica Canônica: Análise de Expansão e Retração por Casa com Ajuste de Aproximação
==============================================================================================
Calculadora da Sorte — Modelo Canônico 4.0 (MCSCE + MCP-MD 1.0)
Desenvolvido para avaliação dinâmica dos últimos sorteios oficiais da Caixa Econômica Federal,
verificando os últimos jogos com o último resultado para auto-calibrar a força restauradora,
identificando a tendência de Expansão (↗), Retração (↘) ou Equilíbrio (🎯) dos numerais em cada
setor/casa/coluna e melhorando continuamente a assertividade no próximo sorteio.
"""

from __future__ import annotations
import math
import statistics
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict


@dataclass
class CasaDinamica:
    """Representação do estado dinâmico de uma casa/setor/coluna canônica."""
    indice: int
    nome: str
    faixa: str
    centro_canonico: int | float
    ultimo_sorteado: int | float
    penultimo_sorteado: Optional[int | float]
    desvio_centro: int | float
    variacao_recente: int | float
    estado: str          # "expansao" | "retracao" | "equilibrio"
    estado_icone: str    # "↗" | "↘" | "🎯"
    estado_rotulo: str   # "Expansão" | "Retração" | "Equilíbrio"
    ajuste_aplicado: int
    valor_ajustado: int
    diagnostico: str
    media_ultimos_jogos: float = 0.0
    fator_calibrado: float = 0.5
    fator_restaurador: float = 0.5
    tendencia_numeral: str = "estavel"
    acertos_recentes_casa: int = 0
    proximidade_ultimo_resultado: float = 100.0
    dezenas_ajustadas_casa: Optional[List[int]] = None

    def __post_init__(self):
        self.fator_restaurador = self.fator_calibrado


@dataclass
class ResultadoDinamica:
    """Resultado consolidado da avaliação dinâmica de expansão e retração."""
    loteria: str
    total_casas: int
    concursos_analisados: int
    ultimo_concurso: Optional[int]
    casas: List[CasaDinamica]
    jogo_ajustado: List[int]
    jogo_ajustado_formatado: str
    resumo_tendencia: Dict[str, Any]
    complemento: Optional[Any] = None
    verificacao_ultimos_jogos: Optional[Dict[str, Any]] = None


class AvaliadorDinamicaCanonica:
    """
    Avaliador unificado de Dinâmica Canônica para as 9 loterias oficiais da Caixa.
    Avalia a dispersão de cada casa nos últimos sorteios, confronta a trajetória dos
    últimos jogos com o último resultado e auto-calibra a força restauradora para
    máxima aproximação métrica e assertividade.
    """

    CONFIG_CASAS = {
        "mega_sena": {
            "nome": "Mega-Sena",
            "universo": 60,
            "minimo": 1,
            "maximo": 60,
            "tipo": "setorial",
            "casas": [
                {"nome": "Setor 1 (01-10)", "faixa": "01 a 10", "min": 1, "max": 10, "centro": 5},
                {"nome": "Setor 2 (11-20)", "faixa": "11 a 20", "min": 11, "max": 20, "centro": 15},
                {"nome": "Setor 3 (21-30)", "faixa": "21 a 30", "min": 21, "max": 30, "centro": 25},
                {"nome": "Setor 4 (31-40)", "faixa": "31 a 40", "min": 31, "max": 40, "centro": 35},
                {"nome": "Setor 5 (41-50)", "faixa": "41 a 50", "min": 41, "max": 50, "centro": 45},
                {"nome": "Setor 6 (51-60)", "faixa": "51 a 60", "min": 51, "max": 60, "centro": 55},
            ]
        },
        "quina": {
            "nome": "Quina",
            "universo": 80,
            "minimo": 1,
            "maximo": 80,
            "tipo": "setorial",
            "casas": [
                {"nome": "Setor 1 (01-16)", "faixa": "01 a 16", "min": 1, "max": 16, "centro": 8},
                {"nome": "Setor 2 (17-32)", "faixa": "17 a 32", "min": 17, "max": 32, "centro": 24},
                {"nome": "Setor 3 (33-48)", "faixa": "33 a 48", "min": 33, "max": 48, "centro": 40},
                {"nome": "Setor 4 (49-64)", "faixa": "49 a 64", "min": 49, "max": 64, "centro": 56},
                {"nome": "Setor 5 (65-80)", "faixa": "65 a 80", "min": 65, "max": 80, "centro": 72},
            ]
        },
        "dupla_sena": {
            "nome": "Dupla Sena",
            "universo": 50,
            "minimo": 1,
            "maximo": 50,
            "tipo": "setorial",
            "casas": [
                {"nome": "Setor 1 (01-08)", "faixa": "01 a 08", "min": 1, "max": 8, "centro": 4},
                {"nome": "Setor 2 (09-17)", "faixa": "09 a 17", "min": 9, "max": 17, "centro": 13},
                {"nome": "Setor 3 (18-25)", "faixa": "18 a 25", "min": 18, "max": 25, "centro": 21},
                {"nome": "Setor 4 (26-34)", "faixa": "26 a 34", "min": 26, "max": 34, "centro": 30},
                {"nome": "Setor 5 (35-42)", "faixa": "35 a 42", "min": 35, "max": 42, "centro": 38},
                {"nome": "Setor 6 (43-50)", "faixa": "43 a 50", "min": 43, "max": 50, "centro": 46},
            ]
        },
        "mais_milionaria": {
            "nome": "+Milionária",
            "universo": 50,
            "minimo": 1,
            "maximo": 50,
            "tipo": "setorial",
            "casas": [
                {"nome": "Setor 1 (01-08)", "faixa": "01 a 08", "min": 1, "max": 8, "centro": 4},
                {"nome": "Setor 2 (09-17)", "faixa": "09 a 17", "min": 9, "max": 17, "centro": 13},
                {"nome": "Setor 3 (18-25)", "faixa": "18 a 25", "min": 18, "max": 25, "centro": 21},
                {"nome": "Setor 4 (26-34)", "faixa": "26 a 34", "min": 26, "max": 34, "centro": 30},
                {"nome": "Setor 5 (35-42)", "faixa": "35 a 42", "min": 35, "max": 42, "centro": 38},
                {"nome": "Setor 6 (43-50)", "faixa": "43 a 50", "min": 43, "max": 50, "centro": 46},
            ]
        },
        "dia_de_sorte": {
            "nome": "Dia de Sorte",
            "universo": 31,
            "minimo": 1,
            "maximo": 31,
            "tipo": "setorial",
            "casas": [
                {"nome": "Setor 1 (01-04)", "faixa": "01 a 04", "min": 1, "max": 4, "centro": 3},
                {"nome": "Setor 2 (05-09)", "faixa": "05 a 09", "min": 5, "max": 9, "centro": 7},
                {"nome": "Setor 3 (10-14)", "faixa": "10 a 14", "min": 10, "max": 14, "centro": 12},
                {"nome": "Setor 4 (15-18)", "faixa": "15 a 18", "min": 15, "max": 18, "centro": 16},
                {"nome": "Setor 5 (19-23)", "faixa": "19 a 23", "min": 19, "max": 23, "centro": 21},
                {"nome": "Setor 6 (24-27)", "faixa": "24 a 27", "min": 24, "max": 27, "centro": 25},
                {"nome": "Setor 7 (28-31)", "faixa": "28 a 31", "min": 28, "max": 31, "centro": 30},
            ]
        },
        "timemania": {
            "nome": "Timemania",
            "universo": 80,
            "minimo": 1,
            "maximo": 80,
            "tipo": "setorial",
            "casas": [
                {"nome": "Setor 1 (01-08)", "faixa": "01 a 08", "min": 1, "max": 8, "centro": 4},
                {"nome": "Setor 2 (09-16)", "faixa": "09 a 16", "min": 9, "max": 16, "centro": 12},
                {"nome": "Setor 3 (17-24)", "faixa": "17 a 24", "min": 17, "max": 24, "centro": 20},
                {"nome": "Setor 4 (25-32)", "faixa": "25 a 32", "min": 25, "max": 32, "centro": 28},
                {"nome": "Setor 5 (33-40)", "faixa": "33 a 40", "min": 33, "max": 40, "centro": 36},
                {"nome": "Setor 6 (41-48)", "faixa": "41 a 48", "min": 41, "max": 48, "centro": 44},
                {"nome": "Setor 7 (49-56)", "faixa": "49 a 56", "min": 49, "max": 56, "centro": 52},
                {"nome": "Setor 8 (57-64)", "faixa": "57 a 64", "min": 57, "max": 64, "centro": 60},
                {"nome": "Setor 9 (65-72)", "faixa": "65 a 72", "min": 65, "max": 72, "centro": 68},
                {"nome": "Setor 10 (73-80)", "faixa": "73 a 80", "min": 73, "max": 80, "centro": 76},
            ]
        },
        "super_sete": {
            "nome": "Super Sete",
            "universo": 10,
            "minimo": 0,
            "maximo": 9,
            "tipo": "colunar",
            "casas": [
                {"nome": "Coluna 1", "faixa": "0 a 9", "min": 0, "max": 9, "centro": 4},
                {"nome": "Coluna 2", "faixa": "0 a 9", "min": 0, "max": 9, "centro": 5},
                {"nome": "Coluna 3", "faixa": "0 a 9", "min": 0, "max": 9, "centro": 4},
                {"nome": "Coluna 4", "faixa": "0 a 9", "min": 0, "max": 9, "centro": 5},
                {"nome": "Coluna 5", "faixa": "0 a 9", "min": 0, "max": 9, "centro": 4},
                {"nome": "Coluna 6", "faixa": "0 a 9", "min": 0, "max": 9, "centro": 5},
                {"nome": "Coluna 7", "faixa": "0 a 9", "min": 0, "max": 9, "centro": 4},
            ]
        },
        "lotofacil": {
            "nome": "Lotofácil",
            "universo": 25,
            "minimo": 1,
            "maximo": 25,
            "tipo": "matricial",
            "casas": [
                {"nome": "Linha 1 (01-05)", "faixa": "01 a 05", "min": 1, "max": 5, "centro": 3, "qtd_esperada": 3},
                {"nome": "Linha 2 (06-10)", "faixa": "06 a 10", "min": 6, "max": 10, "centro": 8, "qtd_esperada": 3},
                {"nome": "Linha 3 (11-15)", "faixa": "11 a 15", "min": 11, "max": 15, "centro": 13, "qtd_esperada": 3},
                {"nome": "Linha 4 (16-20)", "faixa": "16 a 20", "min": 16, "max": 20, "centro": 18, "qtd_esperada": 3},
                {"nome": "Linha 5 (21-25)", "faixa": "21 a 25", "min": 21, "max": 25, "centro": 23, "qtd_esperada": 3},
            ]
        },
        "lotomania": {
            "nome": "Lotomania",
            "universo": 100,
            "minimo": 0,
            "maximo": 99,
            "tipo": "matricial_10x10",
            "casas": [
                {"nome": "Linha 0 (00-09)", "faixa": "00 a 09", "min": 0, "max": 9, "centro": 5, "qtd_esperada": 2},
                {"nome": "Linha 1 (10-19)", "faixa": "10 a 19", "min": 10, "max": 19, "centro": 15, "qtd_esperada": 2},
                {"nome": "Linha 2 (20-29)", "faixa": "20 a 29", "min": 20, "max": 29, "centro": 25, "qtd_esperada": 2},
                {"nome": "Linha 3 (30-39)", "faixa": "30 a 39", "min": 30, "max": 39, "centro": 35, "qtd_esperada": 2},
                {"nome": "Linha 4 (40-49)", "faixa": "40 a 49", "min": 40, "max": 49, "centro": 45, "qtd_esperada": 2},
                {"nome": "Linha 5 (50-59)", "faixa": "50 a 59", "min": 50, "max": 59, "centro": 55, "qtd_esperada": 2},
                {"nome": "Linha 6 (60-69)", "faixa": "60 a 69", "min": 60, "max": 69, "centro": 65, "qtd_esperada": 2},
                {"nome": "Linha 7 (70-79)", "faixa": "70 a 79", "min": 70, "max": 79, "centro": 75, "qtd_esperada": 2},
                {"nome": "Linha 8 (80-89)", "faixa": "80 a 89", "min": 80, "max": 89, "centro": 85, "qtd_esperada": 2},
                {"nome": "Linha 9 (90-99)", "faixa": "90 a 99", "min": 90, "max": 99, "centro": 95, "qtd_esperada": 2},
            ]
        }
    }

    @classmethod
    def avaliar_dinamica(
        cls,
        loteria_type: str,
        historico: List[List[int]],
        ultimo_concurso_id: Optional[int] = None,
        _interno_sem_backtest: bool = False
    ) -> ResultadoDinamica:
        """
        Executa a avaliação dinâmica de expansão e retração para a loteria informada,
        verificando os últimos jogos com o último resultado para calibrar a assertividade.
        """
        slug = loteria_type.lower().replace("-", "_")
        cfg = cls.CONFIG_CASAS.get(slug)
        if not cfg:
            slug = "mega_sena"
            cfg = cls.CONFIG_CASAS["mega_sena"]

        if not historico:
            raise ValueError("Histórico de concursos vazio para avaliação dinâmica.")

        tipo = cfg["tipo"]
        if tipo == "colunar":
            res = cls._avaliar_colunar_super_sete(cfg, historico, ultimo_concurso_id)
        elif tipo == "matricial":
            res = cls._avaliar_matricial_lotofacil(cfg, historico, ultimo_concurso_id)
        elif tipo == "matricial_10x10":
            res = cls._avaliar_matricial_lotomania(cfg, historico, ultimo_concurso_id)
        else:
            res = cls._avaliar_setorial_padrao(cfg, historico, ultimo_concurso_id)

        if not _interno_sem_backtest:
            verificacao = cls._verificar_ultimos_jogos_com_ultimo_resultado(
                slug, cfg, historico, res
            )
            res.verificacao_ultimos_jogos = verificacao
            res.resumo_tendencia["verificacao_ultimos_jogos"] = verificacao
            res.resumo_tendencia["indice_assertividade"] = verificacao.get("indice_assertividade", 0.0)
            res.resumo_tendencia["fator_restaurador_medio"] = verificacao.get("fator_restaurador_medio", 0.5)

        return res

    @classmethod
    def _calibrar_serie_casa(
        cls,
        serie: List[float],
        centro: float,
        c_min: int,
        c_max: int
    ) -> Tuple[float, str, int, float]:
        """
        Compara os valores dos últimos jogos com o último resultado na casa/setor
        para calibrar o fator restaurador (alpha), classificar a tendência do numeral
        e medir a proximidade/acertos recentes.
        Retorna: (fator_calibrado, tendencia_numeral, acertos_recentes, proximidade_ultimo_pct)
        """
        largura = max(1, c_max - c_min)
        tol = 1 if largura <= 10 else 2

        if len(serie) < 2:
            return 0.5, "estavel", 1, 100.0

        val_ult = serie[-1]
        val_pen = serie[-2]
        desvio_ult = val_ult - centro
        desvio_pen = val_pen - centro

        # Classificação da dinâmica entre os últimos jogos e o último resultado
        if abs(desvio_ult) < 1e-6:
            tendencia = "equilibrio_estavel"
        elif desvio_ult * desvio_pen < 0:
            tendencia = "reversao_ciclica"
        elif abs(desvio_ult) < abs(desvio_pen):
            tendencia = "convergencia_centro"
        elif desvio_ult > 0 and val_ult > val_pen:
            tendencia = "expansao_acelerada"
        elif desvio_ult < 0 and val_ult < val_pen:
            tendencia = "retracao_acelerada"
        else:
            tendencia = "oscilacao_moderada"

        # Auto-calibração do fator restaurador alpha testando candidatos na janela recente
        candidatos_alpha = [0.35, 0.50, 0.65, 0.80, 1.00]
        melhor_alpha = 0.50
        menor_erro = float("inf")

        for alpha in candidatos_alpha:
            erro_total = 0.0
            peso_total = 0.0
            for t in range(len(serie) - 1):
                v_atual = serie[t]
                v_real_prox = serie[t + 1]
                d = v_atual - centro
                if d > 0:
                    aj = -max(1, round(abs(d) * alpha))
                elif d < 0:
                    aj = +max(1, round(abs(d) * alpha))
                else:
                    aj = 0
                v_prev = max(c_min, min(c_max, v_atual + aj))
                # O último resultado (t == len(serie) - 2) recebe peso duplo na calibração
                peso = 2.0 if t == len(serie) - 2 else 1.0
                erro_total += abs(v_prev - v_real_prox) * peso
                peso_total += peso

            erro_medio = erro_total / max(peso_total, 1.0)
            if erro_medio < menor_erro - 1e-6:
                menor_erro = erro_medio
                melhor_alpha = alpha

        # Contabiliza acertos recentes (dentro da tolerância) e proximidade no último resultado
        acertos_recentes = 0
        prox_ultimo = 100.0
        for t in range(len(serie) - 1):
            v_atual = serie[t]
            v_real_prox = serie[t + 1]
            d = v_atual - centro
            if d > 0:
                aj = -max(1, round(abs(d) * melhor_alpha))
            elif d < 0:
                aj = +max(1, round(abs(d) * melhor_alpha))
            else:
                aj = 0
            v_prev = max(c_min, min(c_max, v_atual + aj))
            dist = abs(v_prev - v_real_prox)
            if dist <= tol:
                acertos_recentes += 1
            if t == len(serie) - 2:
                prox_ultimo = round(max(0.0, 100.0 * (1.0 - dist / largura)), 1)

        return melhor_alpha, tendencia, acertos_recentes, prox_ultimo

    @classmethod
    def _verificar_ultimos_jogos_com_ultimo_resultado(
        cls,
        slug: str,
        cfg: Dict[str, Any],
        historico: List[List[int]],
        resultado_atual: ResultadoDinamica
    ) -> Dict[str, Any]:
        """
        Verifica o desempenho da fórmula canônica confrontando a previsão gerada
        pelos últimos jogos anteriores (historico[:-1]) com o último resultado real (historico[-1]),
        e detalha a expansão/retração de cada numeral para retroalimentar a assertividade.
        """
        janela = min(len(historico), 10)
        ult = list(historico[-1])
        pen = list(historico[-2]) if len(historico) >= 2 else ult

        if len(historico) >= 2:
            res_anterior = cls.avaliar_dinamica(
                slug,
                historico[:-1],
                ultimo_concurso_id=(resultado_atual.ultimo_concurso - 1 if resultado_atual.ultimo_concurso else None),
                _interno_sem_backtest=True
            )
            jogo_previsto_anterior = res_anterior.jogo_ajustado
        else:
            jogo_previsto_anterior = list(resultado_atual.jogo_ajustado)

        tipo = cfg["tipo"]
        tol_vizinhanca = 1 if cfg["universo"] <= 31 else 2

        if tipo == "colunar":
            acertos_exatos = sum(
                1 for i in range(min(len(jogo_previsto_anterior), len(ult)))
                if jogo_previsto_anterior[i] == int(ult[i])
            )
            acertos_proximos = sum(
                1 for i in range(min(len(jogo_previsto_anterior), len(ult)))
                if abs(jogo_previsto_anterior[i] - int(ult[i])) <= 1
            )
        else:
            set_prev = set(jogo_previsto_anterior)
            set_ult = set(ult)
            acertos_exatos = len(set_prev & set_ult)
            acertos_proximos = sum(
                1 for n_real in ult
                if any(abs(n_real - n_prev) <= tol_vizinhanca for n_prev in jogo_previsto_anterior)
            )

        proximidades_casas = [c.proximidade_ultimo_resultado for c in resultado_atual.casas]
        prox_media_casas = statistics.mean(proximidades_casas) if proximidades_casas else 80.0
        taxa_proximidade_numerais = (acertos_proximos / max(1, len(ult))) * 100.0
        indice_assertividade = round(0.55 * prox_media_casas + 0.45 * taxa_proximidade_numerais, 1)

        fatores = [c.fator_calibrado for c in resultado_atual.casas]
        fator_medio = round(statistics.mean(fatores), 2) if fatores else 0.50

        # Mapeamento numeral a numeral (Expansão vs Retração entre penúltimo/últimos jogos e último resultado)
        ult_ord = sorted(ult) if tipo != "colunar" else [int(x) for x in ult]
        pen_ord = sorted(pen) if tipo != "colunar" else [int(x) for x in pen]
        n_comp = min(len(ult_ord), len(pen_ord))
        movimento_numerais = []
        expansoes_num = 0
        retracoes_num = 0
        estaveis_num = 0

        for i in range(n_comp):
            n_ant = pen_ord[i]
            n_ult = ult_ord[i]
            delta = n_ult - n_ant
            if delta > 0:
                mov = "expansao"
                rotulo_mov = f"Expansão (+{delta})"
                expansoes_num += 1
            elif delta < 0:
                mov = "retracao"
                rotulo_mov = f"Retração ({delta})"
                retracoes_num += 1
            else:
                mov = "estavel"
                rotulo_mov = "Manutenção (0)"
                estaveis_num += 1

            alvo_proj = (
                resultado_atual.jogo_ajustado[i]
                if i < len(resultado_atual.jogo_ajustado)
                else n_ult
            )
            movimento_numerais.append({
                "posicao": i + 1,
                "numeral_anterior": n_ant,
                "numeral_ultimo_resultado": n_ult,
                "variacao": delta,
                "movimento": mov,
                "rotulo": rotulo_mov,
                "numeral_ajustado_proximo": alvo_proj
            })

        # Dezenas que repetiram do penúltimo para o último resultado
        repetidas_ultimo = sorted(list(set(ult) & set(pen))) if tipo != "colunar" else [
            int(ult[i]) for i in range(n_comp) if int(ult[i]) == int(pen[i])
        ]

        resumo_txt = (
            f"Comparando os últimos {janela} concursos com o último resultado: "
            f"{acertos_exatos} acerto(s) exato(s) e {acertos_proximos} de {len(ult)} números muito próximos "
            f"da faixa sorteada, mantendo {indice_assertividade:.1f}% de alinhamento com o movimento recente."
        )
        return {
            "disponivel": True,
            "janela_jogos_analisados": janela,
            "jogo_previsto_antes_ultimo": jogo_previsto_anterior,
            "ultimo_resultado_real": ult_ord,
            "acertos_exatos_ultimo": acertos_exatos,
            "acertos_proximos_ultimo": acertos_proximos,
            "tolerancia_vizinhanca": tol_vizinhanca,
            "proximidade_media_setorial_pct": round(prox_media_casas, 1),
            "indice_assertividade": indice_assertividade,
            "fator_restaurador_medio": fator_medio,
            "repetidas_ultimo_resultado": repetidas_ultimo,
            "qtd_repetidas_ultimo": len(repetidas_ultimo),
            "numerais_em_expansao": expansoes_num,
            "numerais_em_retracao": retracoes_num,
            "numerais_estaveis": estaveis_num,
            "movimento_numerais": movimento_numerais,
            "resumo_calibracao": resumo_txt,
            "resumo_aprendizado": resumo_txt,
        }

    @classmethod
    def _avaliar_colunar_super_sete(
        cls,
        cfg: Dict[str, Any],
        historico: List[List[int]],
        concurso_id: Optional[int]
    ) -> ResultadoDinamica:
        """Avaliação específica para o Super Sete (7 colunas independentes de 0 a 9)."""
        janela_hist = historico[-min(len(historico), 10):]
        ult = historico[-1]
        pen = historico[-2] if len(historico) >= 2 else ult
        casas_analisadas: List[CasaDinamica] = []
        jogo_ajustado: List[int] = []

        expansao_count = 0
        retracao_count = 0
        equilibrio_count = 0

        for idx, c_def in enumerate(cfg["casas"]):
            val_ult = int(ult[idx])
            val_pen = int(pen[idx])
            centro = c_def["centro"]

            serie_col = [int(sorteio[idx]) for sorteio in janela_hist if len(sorteio) > idx]
            media_col = round(statistics.mean(serie_col), 2) if serie_col else float(centro)
            alpha_cal, tendencia_num, acertos_rec, prox_ult = cls._calibrar_serie_casa(
                serie_col, centro, 0, 9
            )

            desvio = val_ult - centro
            variacao = val_ult - val_pen

            # Classificação com força restauradora auto-calibrada pelos últimos jogos
            if desvio > 0:
                estado = "expansao"
                icone = "↗"
                rotulo = "Expansão"
                expansao_count += 1
                ajuste = -max(1, round(desvio * alpha_cal))
                diag = (
                    f"O número {val_ult} subiu acima da faixa central ({centro}). "
                    f"A sugestão recua para equilibrar a coluna no próximo sorteio."
                )
            elif desvio < 0:
                estado = "retracao"
                icone = "↘"
                rotulo = "Retração"
                retracao_count += 1
                ajuste = +max(1, round(abs(desvio) * alpha_cal))
                diag = (
                    f"O número {val_ult} ficou abaixo da faixa central ({centro}). "
                    f"A sugestão avança para equilibrar a coluna no próximo sorteio."
                )
            else:
                estado = "equilibrio"
                icone = "🎯"
                rotulo = "Equilíbrio"
                equilibrio_count += 1
                ajuste = 0
                diag = (
                    f"O número {val_ult} já saiu no ponto de equilíbrio da coluna ({centro}). "
                    f"Faixa mantida para o próximo jogo."
                )

            val_adj = max(0, min(9, val_ult + ajuste))
            jogo_ajustado.append(val_adj)

            casas_analisadas.append(CasaDinamica(
                indice=idx + 1,
                nome=c_def["nome"],
                faixa=c_def["faixa"],
                centro_canonico=centro,
                ultimo_sorteado=val_ult,
                penultimo_sorteado=val_pen,
                desvio_centro=desvio,
                variacao_recente=variacao,
                estado=estado,
                estado_icone=icone,
                estado_rotulo=rotulo,
                ajuste_aplicado=ajuste,
                valor_ajustado=val_adj,
                diagnostico=diag,
                media_ultimos_jogos=media_col,
                fator_calibrado=alpha_cal,
                tendencia_numeral=tendencia_num,
                acertos_recentes_casa=acertos_rec,
                proximidade_ultimo_resultado=prox_ult,
                dezenas_ajustadas_casa=[val_adj]
            ))

        resumo = {
            "expansoes": expansao_count,
            "retracoes": retracao_count,
            "equilibrios": equilibrio_count,
            "predominancia": (
                "Expansão" if expansao_count > retracao_count
                else ("Retração" if retracao_count > expansao_count else "Balanceada")
            ),
            "soma_original": sum(int(x) for x in ult),
            "soma_ajustada": sum(jogo_ajustado),
            "baricentro_teorico": 31.5
        }

        return ResultadoDinamica(
            loteria=cfg["nome"],
            total_casas=len(cfg["casas"]),
            concursos_analisados=min(len(historico), 10),
            ultimo_concurso=concurso_id,
            casas=casas_analisadas,
            jogo_ajustado=jogo_ajustado,
            jogo_ajustado_formatado=" ".join(str(d) for d in jogo_ajustado),
            resumo_tendencia=resumo
        )

    @classmethod
    def _extrair_representante_setor(
        cls,
        sorteio: List[int],
        c_min: int,
        c_max: int,
        centro: float,
        fallback_memoria: Optional[int] = None
    ) -> Tuple[int, bool]:
        """
        Retorna (valor_representativo_no_setor, presente_no_setor).
        Se o setor estiver vazio no sorteio, utiliza a memória setorial recente ou o centro,
        evitando distorcer o setor para as bordas c_min/c_max por números de outros setores.
        """
        no_setor = [n for n in sorteio if c_min <= n <= c_max]
        if no_setor:
            return min(no_setor, key=lambda n: abs(n - centro)), True
        if fallback_memoria is not None and c_min <= fallback_memoria <= c_max:
            return fallback_memoria, False
        return int(round(centro)), False

    @classmethod
    def _avaliar_setorial_padrao(
        cls,
        cfg: Dict[str, Any],
        historico: List[List[int]],
        concurso_id: Optional[int]
    ) -> ResultadoDinamica:
        """
        Avaliação setorial contínua (Mega-Sena, Quina, Timemania, Dupla Sena, +Milionária, Dia de Sorte).
        Verifica a trajetória dos últimos jogos contra o último resultado em cada setor,
        auto-calibra o fator restaurador e corrige a expansão ou retração dos numerais.
        """
        janela_hist = [sorted(s) for s in historico[-min(len(historico), 10):]]
        ult = janela_hist[-1]
        pen = janela_hist[-2] if len(janela_hist) >= 2 else ult
        casas_analisadas: List[CasaDinamica] = []
        jogo_ajustado: List[int] = []

        expansao_count = 0
        retracao_count = 0
        equilibrio_count = 0

        for idx, c_def in enumerate(cfg["casas"]):
            c_min, c_max = c_def["min"], c_def["max"]
            centro = c_def["centro"]

            # Construir série histórica recente do setor preservando memória intra-setorial
            serie_setor: List[float] = []
            ultimo_visto_no_setor: Optional[int] = None
            for s_jogo in janela_hist:
                val_s, presente = cls._extrair_representante_setor(
                    s_jogo, c_min, c_max, centro, fallback_memoria=ultimo_visto_no_setor
                )
                if presente:
                    ultimo_visto_no_setor = val_s
                serie_setor.append(float(val_s))

            # Dezenas do último concurso no setor
            dezenas_setor_ult = [n for n in ult if c_min <= n <= c_max]
            setor_presente_ult = bool(dezenas_setor_ult)
            if dezenas_setor_ult:
                val_ult = min(dezenas_setor_ult, key=lambda n: abs(n - centro))
            elif ultimo_visto_no_setor is not None:
                val_ult = ultimo_visto_no_setor
            else:
                # Nenhum sorteio recente caiu neste setor: usa o número mais próximo do centro mas sem travar na borda
                val_ult = int(centro)

            # Dezenas do penúltimo concurso no setor
            dezenas_setor_pen = [n for n in pen if c_min <= n <= c_max]
            if dezenas_setor_pen:
                val_pen = min(dezenas_setor_pen, key=lambda n: abs(n - centro))
            else:
                val_pen = int(serie_setor[-2]) if len(serie_setor) >= 2 else val_ult

            media_setor = round(statistics.mean(serie_setor), 2) if serie_setor else float(centro)
            alpha_cal, tendencia_num, acertos_rec, prox_ult = cls._calibrar_serie_casa(
                serie_setor, centro, c_min, c_max
            )

            desvio = val_ult - centro
            variacao = val_ult - val_pen

            # Refinamento de inércia/reversão: se o último jogo continuou expandindo na mesma direção
            # da média dos últimos jogos, intensifica levemente a força restauradora hacia o centro
            fator_efetivo = alpha_cal
            if desvio != 0 and (media_setor - centro) * desvio > 0 and abs(media_setor - centro) >= 1.0:
                fator_efetivo = min(0.85, alpha_cal + 0.10)

            nota_ausencia = "" if setor_presente_ult else " (referência recente da faixa)"

            if desvio > 0:
                estado = "expansao"
                icone = "↗"
                rotulo = "Expansão"
                expansao_count += 1
                ajuste = -max(1, round(desvio * fator_efetivo))
                diag = (
                    f"Dezena {val_ult:02d}{nota_ausencia} subiu na faixa (expansão). "
                    f"A sugestão recua para buscar o equilíbrio desta região no próximo sorteio."
                )
            elif desvio < 0:
                estado = "retracao"
                icone = "↘"
                rotulo = "Retração"
                retracao_count += 1
                ajuste = +max(1, round(abs(desvio) * fator_efetivo))
                diag = (
                    f"Dezena {val_ult:02d}{nota_ausencia} desceu na faixa (retração). "
                    f"A sugestão avança para buscar o equilíbrio desta região no próximo sorteio."
                )
            else:
                estado = "equilibrio"
                icone = "🎯"
                rotulo = "Equilíbrio"
                equilibrio_count += 1
                ajuste = 0
                diag = (
                    f"Dezena {val_ult:02d}{nota_ausencia} saiu exatamente na região de equilíbrio da faixa."
                )

            # Valor ajustado provisório confinado no setor
            val_adj = val_ult + ajuste
            val_adj = max(c_min, min(c_max, val_adj))
            jogo_ajustado.append(val_adj)

            casas_analisadas.append(CasaDinamica(
                indice=idx + 1,
                nome=c_def["nome"],
                faixa=c_def["faixa"],
                centro_canonico=centro,
                ultimo_sorteado=val_ult,
                penultimo_sorteado=val_pen,
                desvio_centro=desvio,
                variacao_recente=variacao,
                estado=estado,
                estado_icone=icone,
                estado_rotulo=rotulo,
                ajuste_aplicado=ajuste,
                valor_ajustado=val_adj,
                diagnostico=diag,
                media_ultimos_jogos=media_setor,
                fator_calibrado=round(fator_efetivo, 2),
                tendencia_numeral=tendencia_num,
                acertos_recentes_casa=acertos_rec,
                proximidade_ultimo_resultado=prox_ult,
                dezenas_ajustadas_casa=[val_adj]
            ))

        # Garantir estrita unicidade de dezenas no jogo ajustado
        jogo_final: List[int] = []
        usados: Set[int] = set()
        for idx, val in enumerate(jogo_ajustado):
            c_def = cfg["casas"][idx]
            c_min, c_max = c_def["min"], c_def["max"]
            v = val
            while v in usados and (v + 1 <= c_max or v - 1 >= c_min):
                if v + 1 <= c_max and (v + 1) not in usados:
                    v = v + 1
                elif v - 1 >= c_min and (v - 1) not in usados:
                    v = v - 1
                else:
                    break
            usados.add(v)
            jogo_final.append(v)
            casas_analisadas[idx].valor_ajustado = v
            casas_analisadas[idx].dezenas_ajustadas_casa = [v]

        jogo_final = sorted(jogo_final)

        # Complementos especiais
        complemento_info = None
        if cfg["nome"] == "+Milionária":
            complemento_info = {"trevos_ajustados": [2, 5], "rotulo": "Trevos Canônicos"}
        elif cfg["nome"] == "Dia de Sorte":
            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            complemento_info = {"mes_ajustado": meses[6], "rotulo": "Mês da Sorte"}
        elif cfg["nome"] == "Timemania":
            complemento_info = {"time_ajustado": "Flamengo/RJ", "rotulo": "Time do Coração"}

        resumo = {
            "expansoes": expansao_count,
            "retracoes": retracao_count,
            "equilibrios": equilibrio_count,
            "predominancia": (
                "Expansão" if expansao_count > retracao_count
                else ("Retração" if retracao_count > expansao_count else "Balanceada")
            ),
            "soma_original": sum(ult[:len(cfg["casas"])]),
            "soma_ajustada": sum(jogo_final),
        }

        return ResultadoDinamica(
            loteria=cfg["nome"],
            total_casas=len(cfg["casas"]),
            concursos_analisados=min(len(historico), 10),
            ultimo_concurso=concurso_id,
            casas=casas_analisadas,
            jogo_ajustado=jogo_final,
            jogo_ajustado_formatado=" ".join(f"{d:02d}" for d in jogo_final),
            resumo_tendencia=resumo,
            complemento=complemento_info
        )

    @classmethod
    def _avaliar_matricial_lotofacil(
        cls,
        cfg: Dict[str, Any],
        historico: List[List[int]],
        concurso_id: Optional[int]
    ) -> ResultadoDinamica:
        """
        Avaliação matricial dinâmica para Lotofácil (5 linhas quintetos de 01-25).
        Avalia a densidade de dezenas, o centróide posicional e a transição dos numerais
        nos últimos jogos contra o último resultado em cada uma das 5 linhas,
        selecionando 15 dezenas dinamicamente ajustadas pela expansão e retração.
        """
        janela_hist = [sorted(s) for s in historico[-min(len(historico), 10):]]
        ult = janela_hist[-1]
        pen = janela_hist[-2] if len(janela_hist) >= 2 else ult
        ult_set = set(ult)
        pen_set = set(pen)
        casas_analisadas: List[CasaDinamica] = []

        expansao_count = 0
        retracao_count = 0
        equilibrio_count = 0

        distribuicao_dezenas_linhas: Dict[int, List[int]] = {}

        for idx, c_def in enumerate(cfg["casas"]):
            c_min, c_max = c_def["min"], c_def["max"]
            centro = c_def["centro"]
            qtd_esp = c_def["qtd_esperada"]

            # Série de centróides da linha nos últimos jogos
            serie_centroides: List[float] = []
            for s_jogo in janela_hist:
                dez_s = [n for n in s_jogo if c_min <= n <= c_max]
                serie_centroides.append(statistics.mean(dez_s) if dez_s else float(centro))

            dezenas_ult = [n for n in ult if c_min <= n <= c_max]
            dezenas_pen = [n for n in pen if c_min <= n <= c_max]

            qtd_ult = len(dezenas_ult)
            qtd_pen = len(dezenas_pen)

            media_ult = statistics.mean(dezenas_ult) if dezenas_ult else float(centro)
            media_pen = statistics.mean(dezenas_pen) if dezenas_pen else float(centro)
            media_janela = round(statistics.mean(serie_centroides), 2) if serie_centroides else float(centro)

            alpha_cal, tendencia_num, acertos_rec, prox_ult = cls._calibrar_serie_casa(
                serie_centroides, float(centro), c_min, c_max
            )

            # Desvio posicional do centróide da linha em relação ao centro natural
            desvio_pos = round(media_ult - centro, 1)
            variacao_pos = round(media_ult - media_pen, 1)

            if desvio_pos > 0:
                estado = "expansao"
                icone = "↗"
                rotulo = "Expansão"
                expansao_count += 1
                ajuste = -1
                alvo_centro = max(float(c_min), centro - min(1.25, abs(desvio_pos) * alpha_cal + 0.35))
                diag = (
                    f"Esta linha teve números mais altos no último sorteio ({qtd_ult} dezenas). "
                    f"A sugestão recua suavemente para a esquerda buscando equilíbrio."
                )
            elif desvio_pos < 0:
                estado = "retracao"
                icone = "↘"
                rotulo = "Retração"
                retracao_count += 1
                ajuste = +1
                alvo_centro = min(float(c_max), centro + min(1.25, abs(desvio_pos) * alpha_cal + 0.35))
                diag = (
                    f"Esta linha teve números mais baixos no último sorteio ({qtd_ult} dezenas). "
                    f"A sugestão avança suavemente para a direita buscando equilíbrio."
                )
            else:
                estado = "equilibrio"
                icone = "🎯"
                rotulo = "Equilíbrio"
                equilibrio_count += 1
                ajuste = 0
                # Se a densidade de dezenas variou ou houve variação posicional em relação ao penúltimo, aplica micro-ajuste
                alvo_centro = float(centro) - (0.25 if variacao_pos > 0 else (-0.25 if variacao_pos < 0 else 0.0))
                diag = (
                    f"Esta linha ficou bem equilibrada no centro ({qtd_ult} dezenas). "
                    f"Posição ideal mantida na sugestão."
                )

            # Seleção inteligente e dinâmica das 3 dezenas da linha combinando:
            # 1) Proximidade ao alvo_centro deslocado pela expansão/retração;
            # 2) Comportamento dos numerais nos últimos jogos vs último resultado
            candidatas_linha = list(range(c_min, c_max + 1))
            scores_linha: Dict[int, float] = {}
            for n in candidatas_linha:
                dist_alvo = abs(n - alvo_centro)
                # Frequência recente na janela (ideal na Lotofácil ~ 60% = 0.60)
                presencas_janela = sum(1 for s_j in janela_hist if n in s_j)
                freq_rec = presencas_janela / max(1, len(janela_hist))
                # Sequência consecutiva de aparições nos últimos sorteios
                seq_atual = 0
                for s_j in reversed(janela_hist):
                    if n in s_j:
                        seq_atual += 1
                    else:
                        break

                bonus_dinamico = 0.0
                # Se a linha expandiu demais (muitas dezenas altas), favorece numerais que retraem ao centro/esquerda
                if desvio_pos > 0 and n <= centro:
                    bonus_dinamico += 0.45
                elif desvio_pos < 0 and n >= centro:
                    bonus_dinamico += 0.45

                # Calibração de repetição vs retorno de ausente:
                # Numerais ausentes no último mas presentes no penúltimo (retorno de ciclo curto) ou com 1-2 repetições estáveis
                if n not in ult_set and n in pen_set:
                    bonus_dinamico += 0.30
                elif n in ult_set and 1 <= seq_atual <= 2:
                    bonus_dinamico += 0.20
                elif seq_atual >= 4:
                    # Numeral saturado nos últimos 4+ jogos tende a retrair
                    bonus_dinamico -= 0.35

                # Harmonia com a frequência teórica de 60%
                bonus_dinamico += max(0.0, 0.25 - abs(freq_rec - 0.60) * 0.5)

                scores_linha[n] = -dist_alvo + bonus_dinamico

            candidatas_ordenadas = sorted(
                candidatas_linha,
                key=lambda n: (-scores_linha[n], abs(n - alvo_centro), abs(n - centro))
            )
            escolhidas_linha = sorted(candidatas_ordenadas[:3])
            distribuicao_dezenas_linhas[idx] = escolhidas_linha
            centroide_ajustado = int(round(statistics.mean(escolhidas_linha)))

            casas_analisadas.append(CasaDinamica(
                indice=idx + 1,
                nome=c_def["nome"],
                faixa=c_def["faixa"],
                centro_canonico=centro,
                ultimo_sorteado=round(media_ult, 1),
                penultimo_sorteado=round(media_pen, 1),
                desvio_centro=desvio_pos,
                variacao_recente=variacao_pos,
                estado=estado,
                estado_icone=icone,
                estado_rotulo=rotulo,
                ajuste_aplicado=ajuste,
                valor_ajustado=centroide_ajustado,
                diagnostico=diag,
                media_ultimos_jogos=media_janela,
                fator_calibrado=alpha_cal,
                tendencia_numeral=tendencia_num,
                acertos_recentes_casa=acertos_rec,
                proximidade_ultimo_resultado=prox_ult,
                dezenas_ajustadas_casa=escolhidas_linha
            ))

        jogo_ajustado: List[int] = []
        for idx in range(5):
            jogo_ajustado.extend(distribuicao_dezenas_linhas[idx])
        jogo_ajustado = sorted(jogo_ajustado)

        resumo = {
            "expansoes": expansao_count,
            "retracoes": retracao_count,
            "equilibrios": equilibrio_count,
            "predominancia": (
                "Expansão" if expansao_count > retracao_count
                else ("Retração" if retracao_count > expansao_count else "Balanceada")
            ),
            "soma_original": sum(ult),
            "soma_ajustada": sum(jogo_ajustado),
            "baricentro_teorico": 195.0
        }

        return ResultadoDinamica(
            loteria=cfg["nome"],
            total_casas=5,
            concursos_analisados=min(len(historico), 10),
            ultimo_concurso=concurso_id,
            casas=casas_analisadas,
            jogo_ajustado=jogo_ajustado,
            jogo_ajustado_formatado=" ".join(f"{d:02d}" for d in jogo_ajustado),
            resumo_tendencia=resumo
        )

    @classmethod
    def _avaliar_matricial_lotomania(
        cls,
        cfg: Dict[str, Any],
        historico: List[List[int]],
        concurso_id: Optional[int]
    ) -> ResultadoDinamica:
        """
        Avaliação matricial 10x10 dinâmica para Lotomania (10 linhas de 00 a 99).
        Avalia a densidade e o deslocamento posicional das 20 dezenas sorteadas nos
        últimos jogos contra o último resultado, gerando 50 dezenas ajustadas (5 por linha).
        """
        janela_hist = [sorted(s) for s in historico[-min(len(historico), 10):]]
        ult = janela_hist[-1]
        pen = janela_hist[-2] if len(janela_hist) >= 2 else ult
        ult_set = set(ult)
        pen_set = set(pen)
        casas_analisadas: List[CasaDinamica] = []
        jogo_ajustado: List[int] = []

        expansao_count = 0
        retracao_count = 0
        equilibrio_count = 0

        for idx, c_def in enumerate(cfg["casas"]):
            c_min, c_max = c_def["min"], c_def["max"]
            centro = c_def["centro"]
            qtd_esp = c_def["qtd_esperada"]

            serie_qtd: List[float] = []
            serie_pos: List[float] = []
            for s_jogo in janela_hist:
                dez_s = [n for n in s_jogo if c_min <= n <= c_max]
                serie_qtd.append(float(len(dez_s)))
                serie_pos.append(statistics.mean(dez_s) if dez_s else float(centro))

            dezenas_ult = [n for n in ult if c_min <= n <= c_max]
            dezenas_pen = [n for n in pen if c_min <= n <= c_max]

            qtd_ult = len(dezenas_ult)
            qtd_pen = len(dezenas_pen)
            media_pos_ult = statistics.mean(dezenas_ult) if dezenas_ult else float(centro)
            desvio_pos = media_pos_ult - centro

            media_qtd_janela = round(statistics.mean(serie_qtd), 2) if serie_qtd else float(qtd_esp)
            alpha_cal, tendencia_num, acertos_rec, prox_ult = cls._calibrar_serie_casa(
                serie_qtd, float(qtd_esp), 0, 6
            )

            desvio_qtd = qtd_ult - qtd_esp
            variacao_qtd = qtd_ult - qtd_pen

            if desvio_qtd > 0:
                estado = "expansao"
                icone = "↗"
                rotulo = "Expansão"
                expansao_count += 1
                ajuste_qtd = -1
                diag = (
                    f"Linha com {qtd_ult} dezenas sorteadas (acima da média habitual de {qtd_esp}). "
                    f"Sugestão equilibra a distribuição da linha."
                )
            elif desvio_qtd < 0:
                estado = "retracao"
                icone = "↘"
                rotulo = "Retração"
                retracao_count += 1
                ajuste_qtd = +1
                diag = (
                    f"Linha com {qtd_ult} dezenas sorteadas (abaixo da média habitual de {qtd_esp}). "
                    f"Sugestão reforça a presença desta linha."
                )
            else:
                estado = "equilibrio"
                icone = "🎯"
                rotulo = "Equilíbrio"
                equilibrio_count += 1
                ajuste_qtd = 0
                diag = (
                    f"Linha com {qtd_ult} dezenas sorteadas, exatamente dentro da média habitual."
                )

            # Alvo posicional restaurador dentro da linha [c_min .. c_max]
            if desvio_pos > 0:
                alvo_pos = max(float(c_min + 2), centro - min(2.0, abs(desvio_pos) * 0.5))
            elif desvio_pos < 0:
                alvo_pos = min(float(c_max - 2), centro + min(2.0, abs(desvio_pos) * 0.5))
            else:
                alvo_pos = float(centro)

            # Seleção dinâmica das 5 dezenas da linha para compor as 50 dezenas da Lotomania
            candidatos_linha = list(range(c_min, c_max + 1))
            scores_linha: Dict[int, float] = {}
            for n in candidatos_linha:
                dist_alvo = abs(n - alvo_pos)
                presencas_rec = sum(1 for s_j in janela_hist if n in s_j)
                freq_rec = presencas_rec / max(1, len(janela_hist))

                bonus = 0.0
                # Se a linha expandiu para a direita no último resultado, puxa para a esquerda (e vice-versa)
                if desvio_pos > 0 and n < media_pos_ult:
                    bonus += 0.6
                elif desvio_pos < 0 and n > media_pos_ult:
                    bonus += 0.6

                # Na Lotomania (20/100 = 20% por sorteio), se a linha retraíu em quantidade, prioriza
                # dezenas em retorno de ciclo; se expandiu em quantidade, filtra excesso de repetidas
                if estado == "retracao" and n not in ult_set and presencas_rec >= 1:
                    bonus += 0.5
                elif estado == "expansao" and n in ult_set:
                    bonus -= 0.4
                elif n not in ult_set and n in pen_set:
                    bonus += 0.35

                # Harmonia com a frequência teórica de 20%
                bonus += max(0.0, 0.3 - abs(freq_rec - 0.20))
                scores_linha[n] = -dist_alvo * 0.65 + bonus

            candidatos_ordenados = sorted(
                candidatos_linha,
                key=lambda n: (-scores_linha[n], abs(n - alvo_pos), abs(n - centro))
            )
            dezenas_ajustadas_linha = sorted(candidatos_ordenados[:5])
            jogo_ajustado.extend(dezenas_ajustadas_linha)
            centroide_linha_adj = int(round(statistics.mean(dezenas_ajustadas_linha)))

            casas_analisadas.append(CasaDinamica(
                indice=idx + 1,
                nome=c_def["nome"],
                faixa=c_def["faixa"],
                centro_canonico=centro,
                ultimo_sorteado=qtd_ult,
                penultimo_sorteado=qtd_pen,
                desvio_centro=desvio_qtd,
                variacao_recente=variacao_qtd,
                estado=estado,
                estado_icone=icone,
                estado_rotulo=rotulo,
                ajuste_aplicado=ajuste_qtd,
                valor_ajustado=centroide_linha_adj,
                diagnostico=diag,
                media_ultimos_jogos=media_qtd_janela,
                fator_calibrado=alpha_cal,
                tendencia_numeral=tendencia_num,
                acertos_recentes_casa=acertos_rec,
                proximidade_ultimo_resultado=prox_ult,
                dezenas_ajustadas_casa=dezenas_ajustadas_linha
            ))

        jogo_ajustado = sorted(jogo_ajustado)

        resumo = {
            "expansoes": expansao_count,
            "retracoes": retracao_count,
            "equilibrios": equilibrio_count,
            "predominancia": (
                "Expansão" if expansao_count > retracao_count
                else ("Retração" if retracao_count > expansao_count else "Balanceada")
            ),
            "soma_original": sum(ult),
            "soma_ajustada": sum(jogo_ajustado),
            "baricentro_teorico": 2475.0
        }

        return ResultadoDinamica(
            loteria=cfg["nome"],
            total_casas=10,
            concursos_analisados=min(len(historico), 10),
            ultimo_concurso=concurso_id,
            casas=casas_analisadas,
            jogo_ajustado=jogo_ajustado,
            jogo_ajustado_formatado=" ".join(f"{d:02d}" for d in jogo_ajustado),
            resumo_tendencia=resumo
        )

    @classmethod
    def calcular_pesos_dinamicos_numerais(
        cls,
        loteria_type: str,
        historico: List[List[int]],
        universo_numeros: List[int]
    ) -> Dict[int, float]:
        """
        Calcula o multiplicador dinâmico de peso de cada numeral do universo com base:
        1) Na força restauradora (proximidade ao valor_ajustado da casa/setor);
        2) Na análise de expansão/retração dos últimos jogos com o último resultado;
        3) Na calibração de transição da casa (fator_calibrado).
        """
        if not historico:
            return {n: 1.0 for n in universo_numeros}

        slug = loteria_type.lower().replace("-", "_")
        cfg = cls.CONFIG_CASAS.get(slug, cls.CONFIG_CASAS["mega_sena"])
        res = cls.avaliar_dinamica(slug, historico, _interno_sem_backtest=True)
        ult_set = set(historico[-1])
        pen_set = set(historico[-2]) if len(historico) >= 2 else set()

        pesos_din: Dict[int, float] = {n: 1.0 for n in universo_numeros}
        tipo = cfg["tipo"]

        if tipo == "colunar":
            # Para Super Sete, retorna peso médio por dígito 0..9 considerando os alvos das 7 colunas
            alvos_col = res.jogo_ajustado
            for n in universo_numeros:
                dists = [abs(n - alvo) for alvo in alvos_col]
                min_d = min(dists) if dists else 2
                pesos_din[n] = round(1.0 + max(0.0, (3.0 - min_d) * 0.35), 4)
            return pesos_din

        for idx, c_def in enumerate(cfg["casas"]):
            c_min, c_max = c_def["min"], c_def["max"]
            largura = max(1.0, float(c_max - c_min))
            casa = res.casas[idx]
            alvo_casa = casa.valor_ajustado
            dezenas_casa = set(casa.dezenas_ajustadas_casa or [alvo_casa])

            for n in range(c_min, c_max + 1):
                if n not in pesos_din:
                    continue
                dist_norm = abs(n - alvo_casa) / largura
                # Boost exponencial para numerais próximos ao valor ajustado pela expansão/retração
                boost_atrator = 1.0 + 0.85 * math.exp(-3.0 * dist_norm)
                if n in dezenas_casa:
                    boost_atrator += 0.45

                # Ajuste pela transição entre penúltimo e último resultado
                if casa.estado == "expansao" and n <= casa.centro_canonico:
                    boost_atrator += 0.20
                elif casa.estado == "retracao" and n >= casa.centro_canonico:
                    boost_atrator += 0.20

                # Leve penalização para repetição imediata em loterias de baixa repetição (exceto Lotofácil/Lotomania)
                if slug not in ("lotofacil", "lotomania") and n in ult_set and n in pen_set:
                    boost_atrator *= 0.85

                pesos_din[n] = round(max(0.2, boost_atrator), 4)

        return pesos_din

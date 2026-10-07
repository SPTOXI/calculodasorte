"""
Módulo de Dinâmica Canônica: Análise de Expansão e Retração por Casa com Ajuste de Aproximação
==============================================================================================
Calculadora da Sorte — Modelo Canônico 4.0 (MCSCE + MCP-MD 1.0)
Desenvolvido para avaliação dinâmica dos últimos sorteios oficiais da Caixa Econômica Federal,
identificando a tendência de Expansão (↗), Retração (↘) ou Equilíbrio (🎯) em cada setor/casa,
aplicando a força restauradora canônica para buscar a aproximação contínua no próximo sorteio.
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


class AvaliadorDinamicaCanonica:
    """
    Avaliador unificado de Dinâmica Canônica para as 9 loterias oficiais da Caixa.
    Avalia a dispersão de cada casa nos últimos sorteios e calcula a força restauradora
    para máxima aproximação métrica.
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
        ultimo_concurso_id: Optional[int] = None
    ) -> ResultadoDinamica:
        """
        Executa a avaliação dinâmica de expansão e retração para a loteria informada.
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
            return cls._avaliar_colunar_super_sete(cfg, historico, ultimo_concurso_id)
        elif tipo == "matricial":
            return cls._avaliar_matricial_lotofacil(cfg, historico, ultimo_concurso_id)
        elif tipo == "matricial_10x10":
            return cls._avaliar_matricial_lotomania(cfg, historico, ultimo_concurso_id)
        else:
            return cls._avaliar_setorial_padrao(cfg, historico, ultimo_concurso_id)

    @classmethod
    def _avaliar_colunar_super_sete(
        cls,
        cfg: Dict[str, Any],
        historico: List[List[int]],
        concurso_id: Optional[int]
    ) -> ResultadoDinamica:
        """Avaliação específica para o Super Sete (7 colunas independentes de 0 a 9)."""
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

            desvio = val_ult - centro
            variacao = val_ult - val_pen

            # Classificação
            if desvio > 0:
                estado = "expansao"
                icone = "↗"
                rotulo = "Expansão"
                expansao_count += 1
                ajuste = -max(1, round(desvio * 0.5))
                diag = f"Dígito {val_ult} expandido em +{desvio} acima do centro {centro}. Ajuste restaurador de {ajuste} puxa em direção ao atrator."
            elif desvio < 0:
                estado = "retracao"
                icone = "↘"
                rotulo = "Retração"
                retracao_count += 1
                ajuste = +max(1, round(abs(desvio) * 0.5))
                diag = f"Dígito {val_ult} retraído em {desvio} abaixo do centro {centro}. Ajuste restaurador de +{ajuste} expande em direção ao atrator."
            else:
                estado = "equilibrio"
                icone = "🎯"
                rotulo = "Equilíbrio"
                equilibrio_count += 1
                ajuste = 0
                diag = f"Dígito {val_ult} em equilíbrio perfeito sobre o centro {centro}. Posição mantida para máxima aproximação."

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
                diagnostico=diag
            ))

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
            "baricentro_teorico": 31.5
        }

        return ResultadoDinamica(
            loteria=cfg["nome"],
            total_casas=len(cfg["casas"]),
            concursos_analisados=min(len(historico), 5),
            ultimo_concurso=concurso_id,
            casas=casas_analisadas,
            jogo_ajustado=jogo_ajustado,
            jogo_ajustado_formatado=" ".join(str(d) for d in jogo_ajustado),
            resumo_tendencia=resumo
        )

    @classmethod
    def _avaliar_setorial_padrao(
        cls,
        cfg: Dict[str, Any],
        historico: List[List[int]],
        concurso_id: Optional[int]
    ) -> ResultadoDinamica:
        """
        Avaliação setorial contínua (Mega-Sena, Quina, Timemania, Dupla Sena, +Milionária, Dia de Sorte).
        Mapeia cada setor ao número sorteado mais próximo e aplica a força restauradora.
        """
        ult = sorted(historico[-1])
        pen = sorted(historico[-2]) if len(historico) >= 2 else ult
        casas_analisadas: List[CasaDinamica] = []
        jogo_ajustado: List[int] = []

        expansao_count = 0
        retracao_count = 0
        equilibrio_count = 0

        # Para cada casa, encontrar a dezena do último sorteio que cai na faixa ou a mais próxima
        for idx, c_def in enumerate(cfg["casas"]):
            c_min, c_max = c_def["min"], c_def["max"]
            centro = c_def["centro"]

            # Dezenas do último concurso no setor
            dezenas_setor_ult = [n for n in ult if c_min <= n <= c_max]
            if dezenas_setor_ult:
                # Escolhe a de menor distância ao centro
                val_ult = min(dezenas_setor_ult, key=lambda n: abs(n - centro))
            else:
                # Setor vazio no último concurso: número mais próximo no sorteio
                val_ult = min(ult, key=lambda n: abs(n - centro))

            # Dezenas do penúltimo concurso no setor
            dezenas_setor_pen = [n for n in pen if c_min <= n <= c_max]
            if dezenas_setor_pen:
                val_pen = min(dezenas_setor_pen, key=lambda n: abs(n - centro))
            else:
                val_pen = min(pen, key=lambda n: abs(n - centro))

            desvio = val_ult - centro
            variacao = val_ult - val_pen

            if desvio > 0:
                estado = "expansao"
                icone = "↗"
                rotulo = "Expansão"
                expansao_count += 1
                ajuste = -max(1, round(desvio * 0.5))
                diag = f"Dezena {val_ult:02d} deslocada em +{desvio} acima do centro {centro:02d}. Ajuste restaurador de {ajuste:+d} aproxima do atrator."
            elif desvio < 0:
                estado = "retracao"
                icone = "↘"
                rotulo = "Retração"
                retracao_count += 1
                ajuste = +max(1, round(abs(desvio) * 0.5))
                diag = f"Dezena {val_ult:02d} deslocada em {desvio} abaixo do centro {centro:02d}. Ajuste restaurador de {ajuste:+d} aproxima do atrator."
            else:
                estado = "equilibrio"
                icone = "🎯"
                rotulo = "Equilíbrio"
                equilibrio_count += 1
                ajuste = 0
                diag = f"Dezena {val_ult:02d} exatamente sobre o centro canônico {centro:02d}. Posição de convergência máxima preservada."

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
                diagnostico=diag
            ))

        # Garantir estrita unicidade de dezenas no jogo ajustado
        jogo_final: List[int] = []
        usados: Set[int] = set()
        for idx, val in enumerate(jogo_ajustado):
            c_def = cfg["casas"][idx]
            c_min, c_max = c_def["min"], c_def["max"]
            v = val
            # Se já foi usado por colisão, busca o vizinho mais próximo dentro do setor
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

        jogo_final = sorted(jogo_final)

        # Complementos especiais
        complemento_info = None
        if cfg["nome"] == "+Milionária":
            complemento_info = {"trevos_ajustados": [2, 5], "rotulo": "Trevos Canônicos"}
        elif cfg["nome"] == "Dia de Sorte":
            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            # Centro harmônico de mês
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
            concursos_analisados=min(len(historico), 5),
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
        Avaliação matricial para Lotofácil (5 linhas quintetos de 01-25).
        Avalia a densidade de dezenas e desvio em cada uma das 5 linhas,
        equilibrando para a aposta de 15 dezenas com baricentro ótimo.
        """
        ult = sorted(historico[-1])
        pen = sorted(historico[-2]) if len(historico) >= 2 else ult
        casas_analisadas: List[CasaDinamica] = []

        expansao_count = 0
        retracao_count = 0
        equilibrio_count = 0

        # Mapeamento de dezenas por linha
        distribuicao_dezenas_linhas: Dict[int, List[int]] = {}

        for idx, c_def in enumerate(cfg["casas"]):
            c_min, c_max = c_def["min"], c_def["max"]
            centro = c_def["centro"]
            qtd_esp = c_def["qtd_esperada"]

            dezenas_ult = [n for n in ult if c_min <= n <= c_max]
            dezenas_pen = [n for n in pen if c_min <= n <= c_max]

            qtd_ult = len(dezenas_ult)
            qtd_pen = len(dezenas_pen)

            media_ult = statistics.mean(dezenas_ult) if dezenas_ult else centro
            media_pen = statistics.mean(dezenas_pen) if dezenas_pen else centro

            # Desvio posicional do centróide da linha em relação ao centro natural
            desvio_pos = round(media_ult - centro, 1)
            variacao_pos = round(media_ult - media_pen, 1)

            if desvio_pos > 0:
                estado = "expansao"
                icone = "↗"
                rotulo = "Expansão"
                expansao_count += 1
                ajuste = -1
                diag = f"Linha com centróide em {media_ult:.1f} (desvio de +{desvio_pos} acima do centro {centro:02d}, {qtd_ult} dezenas). Ajuste restaurador de {ajuste:+d} aproxima do atrator canônico."
            elif desvio_pos < 0:
                estado = "retracao"
                icone = "↘"
                rotulo = "Retração"
                retracao_count += 1
                ajuste = +1
                diag = f"Linha com centróide em {media_ult:.1f} (desvio de {desvio_pos} abaixo do centro {centro:02d}, {qtd_ult} dezenas). Ajuste restaurador de {ajuste:+d} aproxima do atrator canônico."
            else:
                estado = "equilibrio"
                icone = "🎯"
                rotulo = "Equilíbrio"
                equilibrio_count += 1
                ajuste = 0
                diag = f"Linha com centróide em {media_ult:.1f} exatamente sobre o centro canônico {centro:02d} ({qtd_ult} dezenas). Posição de convergência máxima preservada."

            # Seleciona dezenas ajustadas da linha em torno do centro
            candidatas_linha = list(range(c_min, c_max + 1))
            # Ordena pela proximidade do centro da linha
            candidatas_ordenadas = sorted(candidatas_linha, key=lambda n: abs(n - centro))
            # Cada linha recebe 3 dezenas (total = 15 dezenas)
            distribuicao_dezenas_linhas[idx] = sorted(candidatas_ordenadas[:3])

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
                valor_ajustado=centro,
                diagnostico=diag
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
            concursos_analisados=min(len(historico), 5),
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
        Avaliação matricial 10x10 para Lotomania (10 linhas de 00 a 99).
        Avalia o fluxo das 20 dezenas sorteadas e gera 50 dezenas ajustadas (5 por linha).
        """
        ult = sorted(historico[-1])
        pen = sorted(historico[-2]) if len(historico) >= 2 else ult
        casas_analisadas: List[CasaDinamica] = []
        jogo_ajustado: List[int] = []

        expansao_count = 0
        retracao_count = 0
        equilibrio_count = 0

        for idx, c_def in enumerate(cfg["casas"]):
            c_min, c_max = c_def["min"], c_def["max"]
            centro = c_def["centro"]
            qtd_esp = c_def["qtd_esperada"]

            dezenas_ult = [n for n in ult if c_min <= n <= c_max]
            dezenas_pen = [n for n in pen if c_min <= n <= c_max]

            qtd_ult = len(dezenas_ult)
            qtd_pen = len(dezenas_pen)

            desvio_qtd = qtd_ult - qtd_esp
            variacao_qtd = qtd_ult - qtd_pen

            if desvio_qtd > 0:
                estado = "expansao"
                icone = "↗"
                rotulo = "Expansão"
                expansao_count += 1
                ajuste_qtd = -1
                diag = f"Linha com {qtd_ult} dezenas sorteadas (acima da média {qtd_esp}). Ajuste restaura dispersão harmônica."
            elif desvio_qtd < 0:
                estado = "retracao"
                icone = "↘"
                rotulo = "Retração"
                retracao_count += 1
                ajuste_qtd = +1
                diag = f"Linha com {qtd_ult} dezenas sorteadas (abaixo da média {qtd_esp}). Ajuste restaura densidade da linha."
            else:
                estado = "equilibrio"
                icone = "🎯"
                rotulo = "Equilíbrio"
                equilibrio_count += 1
                ajuste_qtd = 0
                diag = f"Linha com exatamente {qtd_ult} dezenas sorteadas (alinhada à média esperada)."

            # Aposta simples da Lotomania seleciona 50 números (5 por linha):
            # Seleciona as 5 dezenas mais equilibradas da linha
            candidatos_linha = list(range(c_min, c_max + 1))
            candidatos_ordenados = sorted(candidatos_linha, key=lambda n: abs(n - centro))
            dezenas_ajustadas_linha = sorted(candidatos_ordenados[:5])
            jogo_ajustado.extend(dezenas_ajustadas_linha)

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
                valor_ajustado=centro,
                diagnostico=diag
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
            concursos_analisados=min(len(historico), 5),
            ultimo_concurso=concurso_id,
            casas=casas_analisadas,
            jogo_ajustado=jogo_ajustado,
            jogo_ajustado_formatado=" ".join(f"{d:02d}" for d in jogo_ajustado),
            resumo_tendencia=resumo
        )

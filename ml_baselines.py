"""Baselines reproduzíveis de Machine Learning para a Mega-Sena.

Este módulo é experimental e isolado do Modelo Canônico 4.0 e do gerador.
Implementa somente duas referências iniciais:
1. probabilidade uniforme teórica (6/60 = 0,10 por dezena);
2. frequência histórica empírica, recalculada apenas com concursos anteriores.

O protocolo walk-forward preserva a ordem cronológica recebida. Não embaralha
concursos, não usa o resultado-alvo para calcular atributos e não altera o
gerador canônico.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


UNIVERSO = tuple(range(1, 61))
QUANTIDADE_SORTEADA = 6
PROBABILIDADE_UNIFORME = QUANTIDADE_SORTEADA / len(UNIVERSO)


def normalizar_historico(historico: Sequence[Sequence[int]]) -> List[Tuple[int, ...]]:
    """Valida e normaliza concursos na ordem cronológica fornecida."""
    if not isinstance(historico, (list, tuple)) or not historico:
        raise ValueError("Histórico vazio ou inválido.")

    normalizado: List[Tuple[int, ...]] = []
    for indice, concurso in enumerate(historico, start=1):
        if not isinstance(concurso, (list, tuple)) or len(concurso) != QUANTIDADE_SORTEADA:
            raise ValueError(f"Concurso na posição {indice}: devem existir exatamente 6 dezenas.")

        dezenas: List[int] = []
        for valor in concurso:
            if isinstance(valor, bool) or not isinstance(valor, int):
                raise ValueError(f"Concurso na posição {indice}: dezenas devem ser inteiros.")
            if valor not in UNIVERSO:
                raise ValueError(f"Concurso na posição {indice}: dezena fora do intervalo 1–60.")
            dezenas.append(valor)

        if len(set(dezenas)) != QUANTIDADE_SORTEADA:
            raise ValueError(f"Concurso na posição {indice}: existem dezenas repetidas.")
        normalizado.append(tuple(sorted(dezenas)))

    return normalizado


def carregar_historico_json(caminho: str | Path) -> List[Tuple[int, ...]]:
    """Carrega um JSON no formato de lista de concursos usado pelo repositório."""
    arquivo = Path(caminho)
    with arquivo.open("r", encoding="utf-8") as origem:
        dados = json.load(origem)
    return normalizar_historico(dados)


def prever_uniforme() -> Dict[int, float]:
    """Baseline teórico: 0,10 de probabilidade marginal para cada dezena."""
    return {dezena: PROBABILIDADE_UNIFORME for dezena in UNIVERSO}


def prever_frequencia_historica(
    historico_anterior: Sequence[Sequence[int]],
) -> Dict[int, float]:
    """Frequência marginal observada no passado; não usa suavização ou futuro."""
    passado = normalizar_historico(historico_anterior)
    total_concursos = len(passado)
    contagens = {dezena: 0 for dezena in UNIVERSO}

    for concurso in passado:
        for dezena in concurso:
            contagens[dezena] += 1

    return {dezena: contagens[dezena] / total_concursos for dezena in UNIVERSO}


def _brier_multirrótulo(
    probabilidades: Dict[int, float], resultado: Sequence[int]
) -> float:
    observadas = set(resultado)
    return math.fsum(
        (probabilidades[d] - (1.0 if d in observadas else 0.0)) ** 2
        for d in UNIVERSO
    ) / len(UNIVERSO)


def avaliar_walk_forward(
    historico: Sequence[Sequence[int]], minimo_treino: int = 150
) -> Dict[str, Any]:
    """Compara uniforme e frequência histórica em previsões sequenciais.

    Para cada concurso t, ambos os modelos são avaliados antes de incorporar
    o resultado t. O conjunto de teste é o sufixo após minimo_treino.
    Brier é calculado sobre os 60 indicadores marginais de ocorrência.
    """
    if isinstance(minimo_treino, bool) or not isinstance(minimo_treino, int) or minimo_treino < 1:
        raise ValueError("minimo_treino deve ser um inteiro positivo.")

    concursos = normalizar_historico(historico)
    if len(concursos) <= minimo_treino:
        raise ValueError(
            f"Histórico insuficiente: são necessários mais de {minimo_treino} concursos."
        )

    uniforme = prever_uniforme()
    brier_uniforme: List[float] = []
    brier_frequencia: List[float] = []
    diferencas_por_concurso: List[float] = []

    for indice_teste in range(minimo_treino, len(concursos)):
        # O alvo é previsto usando exclusivamente o prefixo anterior.
        prefixo = concursos[:indice_teste]
        alvo = concursos[indice_teste]
        frequencia = prever_frequencia_historica(prefixo)

        score_uniforme = _brier_multirrótulo(uniforme, alvo)
        score_frequencia = _brier_multirrótulo(frequencia, alvo)
        brier_uniforme.append(score_uniforme)
        brier_frequencia.append(score_frequencia)
        diferencas_por_concurso.append(score_uniforme - score_frequencia)

    media_uniforme = math.fsum(brier_uniforme) / len(brier_uniforme)
    media_frequencia = math.fsum(brier_frequencia) / len(brier_frequencia)
    diferenca_media = media_uniforme - media_frequencia

    return {
        "status": "avaliado",
        "modalidade": "Mega-Sena",
        "concursos_historicos": len(concursos),
        "minimo_treino": minimo_treino,
        "concursos_avaliados": len(brier_uniforme),
        "indice_primeiro_teste_zero_based": minimo_treino,
        "brier_uniforme": media_uniforme,
        "brier_frequencia_historica": media_frequencia,
        "ganho_brier_frequencia_vs_uniforme": diferenca_media,
        "frequencia_superou_uniforme": diferenca_media > 0,
        "interpretacao": (
            "Brier menor é melhor. Diferença positiva favorece frequência histórica; "
            "isso é apenas um resultado retrospectivo e não comprova vantagem futura."
        ),
    }


def relatorio_previsao_atual(
    historico: Sequence[Sequence[int]], minimo_treino: int = 150
) -> Dict[str, Any]:
    """Produz escores para o próximo concurso, sem criar combinação de aposta."""
    concursos = normalizar_historico(historico)
    if len(concursos) < minimo_treino:
        raise ValueError(f"São necessários pelo menos {minimo_treino} concursos.")

    frequencia = prever_frequencia_historica(concursos)
    ranking = sorted(UNIVERSO, key=lambda dezena: (-frequencia[dezena], dezena))
    return {
        "modalidade": "Mega-Sena",
        "concursos_utilizados": len(concursos),
        "probabilidade_uniforme_por_dezena": PROBABILIDADE_UNIFORME,
        "ranking_frequencia_historica": [
            {"dezena": dezena, "frequencia_empirica": frequencia[dezena]}
            for dezena in ranking
        ],
        "aviso": (
            "Ranking descritivo de frequências passadas; não representa probabilidade "
            "comprovada para o próximo concurso nem altera as chances matemáticas."
        ),
    }

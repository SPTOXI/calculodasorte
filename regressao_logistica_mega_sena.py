"""Regressão logística experimental para a Mega-Sena.

Modelo supervisionado multi-rótulo: uma linha por dezena e por concurso-alvo.
As variáveis são frequências em janelas passadas, frequência acumulada,
tempo desde a última ocorrência e identidade da dezena (one-hot).

O módulo não altera o gerador canônico. Requer numpy e scikit-learn.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

from ml_baselines import (
    UNIVERSO,
    _brier_multirrótulo,
    normalizar_historico,
    prever_uniforme,
)

JANELAS_PADRAO = (30, 60, 100, 150)


def construir_features_por_origem(
    historico: Sequence[Sequence[int]],
    min_historico: int = 150,
    janelas: Sequence[int] = JANELAS_PADRAO,
) -> Tuple[List[np.ndarray], List[np.ndarray]]:
    """Gera X e y para cada origem s usando somente concursos anteriores a s.

    X[s] tem 60 linhas (uma por dezena). y[s] indica quais dezenas saíram
    no concurso s. Origens anteriores a min_historico não são usadas.
    """
    concursos = normalizar_historico(historico)
    if min_historico < 1 or min_historico >= len(concursos):
        raise ValueError("min_historico deve ser positivo e menor que o histórico.")
    if not janelas or any(isinstance(w, bool) or not isinstance(w, int) or w < 1 for w in janelas):
        raise ValueError("janelas deve conter inteiros positivos.")

    n = len(concursos)
    indicadores = np.zeros((n, 60), dtype=np.float64)
    for i, concurso in enumerate(concursos):
        for dezena in concurso:
            indicadores[i, dezena - 1] = 1.0

    acumulado = np.vstack([np.zeros((1, 60)), np.cumsum(indicadores, axis=0)])
    ultimo_visto = np.full(60, -1, dtype=np.int64)
    X_por_origem: List[np.ndarray] = []
    y_por_origem: List[np.ndarray] = []

    for origem in range(n):
        # Atualiza o último visto somente depois de construir as features
        # daquela origem; o sorteio da própria origem nunca entra em X.
        if origem >= min_historico:
            blocos = []
            for janela in janelas:
                inicio = max(0, origem - janela)
                tamanho = origem - inicio
                contagens = acumulado[origem] - acumulado[inicio]
                blocos.append((contagens / float(tamanho)).reshape(60, 1))

            frequencia_total = (acumulado[origem] / float(origem)).reshape(60, 1)
            gap = np.where(
                ultimo_visto >= 0,
                origem - 1 - ultimo_visto,
                origem,
            )
            gap = np.minimum(gap, max(janelas)).astype(np.float64) / float(max(janelas))

            identidade = np.eye(60, dtype=np.float64)
            X_origem = np.hstack(blocos + [frequencia_total, gap.reshape(60, 1), identidade])
            X_por_origem.append(X_origem)
            y_por_origem.append(indicadores[origem].copy())

        ocorridas = np.flatnonzero(indicadores[origem])
        ultimo_visto[ocorridas] = origem

    return X_por_origem, y_por_origem


def avaliar_regressao_logistica_walk_forward(
    historico: Sequence[Sequence[int]],
    min_historico: int = 150,
    minimo_origens_treino: int = 150,
    intervalo_retreino: int = 25,
    janelas: Sequence[int] = JANELAS_PADRAO,
    c_regularizacao: float = 1.0,
) -> Dict[str, Any]:
    """Avalia probabilidades por dezena em walk-forward com retreino periódico.

    Para prever o alvo t, o modelo usa rótulos somente das origens s < t.
    O primeiro alvo ocorre após min_historico + minimo_origens_treino
    concursos. Entre retreinamentos, o modelo permanece congelado; isso é
    válido temporalmente e torna o custo computacional controlável.
    """
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError(
            "Dependência ausente: instale scikit-learn e numpy para executar "
            "a regressão logística (pip install numpy scikit-learn)."
        ) from exc

    if intervalo_retreino < 1 or minimo_origens_treino < 2:
        raise ValueError("intervalo_retreino deve ser >=1 e minimo_origens_treino >=2.")
    if c_regularizacao <= 0:
        raise ValueError("c_regularizacao deve ser positivo.")

    concursos = normalizar_historico(historico)
    X_origens, y_origens = construir_features_por_origem(
        concursos, min_historico=min_historico, janelas=janelas
    )
    primeira_origem = min_historico
    primeiro_alvo = primeira_origem + minimo_origens_treino
    if len(concursos) <= primeiro_alvo:
        raise ValueError(
            "Histórico insuficiente: são necessários mais concursos para formar "
            "o treino inicial e ao menos um alvo de teste."
        )

    modelo = None
    scores_logistica: List[float] = []
    scores_uniforme: List[float] = []
    acertos_top6: List[int] = []
    retreinamentos = 0
    indice_primeira_origem = 0

    for alvo_indice in range(primeiro_alvo, len(concursos)):
        quantidade_origens_disponiveis = alvo_indice - primeira_origem
        deve_retreinar = (
            modelo is None
            or (alvo_indice - primeiro_alvo) % intervalo_retreino == 0
        )
        if deve_retreinar:
            X_treino = np.concatenate(
                X_origens[:quantidade_origens_disponiveis], axis=0
            )
            y_treino = np.concatenate(
                y_origens[:quantidade_origens_disponiveis], axis=0
            )
            if np.unique(y_treino).size != 2:
                raise ValueError("O conjunto de treino precisa conter as duas classes.")
            modelo = make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    C=c_regularizacao,
                    solver="lbfgs",
                    max_iter=500,
                    random_state=42,
                ),
            )
            modelo.fit(X_treino, y_treino)
            retreinamentos += 1

        X_alvo = X_origens[quantidade_origens_disponiveis]
        probabilidades = modelo.predict_proba(X_alvo)[:, 1]
        mapa_prob = {dezena: float(probabilidades[dezena - 1]) for dezena in UNIVERSO}
        resultado = concursos[alvo_indice]

        scores_logistica.append(_brier_multirrótulo(mapa_prob, resultado))
        scores_uniforme.append(_brier_multirrótulo(prever_uniforme(), resultado))
        top6 = sorted(UNIVERSO, key=lambda d: (-mapa_prob[d], d))[:6]
        acertos_top6.append(len(set(top6).intersection(resultado)))

    brier_log = math.fsum(scores_logistica) / len(scores_logistica)
    brier_uni = math.fsum(scores_uniforme) / len(scores_uniforme)
    return {
        "status": "avaliado",
        "modalidade": "Mega-Sena",
        "modelo": "Regressão Logística L2",
        "concursos_historicos": len(concursos),
        "min_historico_features": min_historico,
        "minimo_origens_treino": minimo_origens_treino,
        "primeiro_concurso_teste_indice_zero_based": primeiro_alvo,
        "concursos_avaliados": len(scores_logistica),
        "intervalo_retreino": intervalo_retreino,
        "quantidade_retreinamentos": retreinamentos,
        "janelas": list(janelas),
        "c_regularizacao": c_regularizacao,
        "brier_logistica": brier_log,
        "brier_uniforme_mesmo_periodo": brier_uni,
        "ganho_brier_logistica_vs_uniforme": brier_uni - brier_log,
        "media_acertos_top6_logistica": math.fsum(acertos_top6) / len(acertos_top6),
        "interpretacao": (
            "Brier menor é melhor. Ganho positivo favorece a regressão logística. "
            "Resultado retrospectivo, sem garantia de vantagem futura. "
            "O modelo é retreinado em blocos; entre retreinamentos não incorpora "
            "os novos rótulos, embora cada previsão permaneça livre de vazamento."
        ),
    }

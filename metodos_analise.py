"""
Módulo de Métodos de Análise e Geração de Jogos (Canônica Dinâmica, Fechamentos e Tradicionais)
===============================================================================================
Permite ao usuário escolher livremente a forma de análise e de geração de palpites:
1. canonica_dinamica: Fórmula Canônica 4.0 com verificação nos últimos jogos vs último resultado e expansão/retração dos numerais.
2. fechamento: Desdobramentos / Fechamentos matemáticos com garantia condicional e sugestão inteligente de grupo.
3. frequencia_quentes: Análise Tradicional de Frequência Global e Recente (Dezenas Quentes / Sequências).
4. atraso_frios: Análise Tradicional de Atraso Atual, Dezenas Frias e Fechamento do Ciclo das Dezenas.
5. equilibrio_classico: Análise Tradicional de Equilíbrio Combinatório (Soma, Paridade, Repetidas do Último, Primos, Fibonacci, Moldura).
6. hibrida_tradicional: Análise Mista (Quentes + Atrasados/Ciclo + Repetidas do Último + Expansão/Retração Canônica).
"""

from __future__ import annotations
import hashlib
import math
import random
import statistics
from typing import Dict, List, Optional, Any, Set, Tuple

from core import ModeloCanonico40, LoteriaType, LOTERIAS_CONFIG, _peso_canonico
from dinamica_canonica import AvaliadorDinamicaCanonica


PRIMOS_ATE_100 = {
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29,
    31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97
}

FIBONACCI_ATE_100 = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89}

MOLDURA_LOTOFACIL = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

CATALOGO_METODOS_ANALISE = [
    {
        "id": "canonica_dinamica",
        "nome": "Análise Canônica (Expansão e Retração)",
        "nome_curto": "Canônica Dinâmica",
        "icone": "🧭",
        "categoria": "canonica",
        "descricao": (
            "Observa se os números subiram (expansão) ou desceram (retração) nos últimos sorteios "
            "em comparação com o último resultado, buscando o equilíbrio para o próximo jogo."
        ),
        "para_quem": "Ideal para quem quer palpites ajustados pelo movimento mais recente dos sorteios."
    },
    {
        "id": "fechamento",
        "nome": "Fechamentos Inteligentes com Garantia",
        "nome_curto": "Fechamentos",
        "icone": "🔒",
        "categoria": "fechamento",
        "descricao": (
            "Permite escolher mais números favoritos e distribuí-los em vários jogos econômicos, "
            "cercando premiações caso os números sorteados caiam dentro do grupo escolhido."
        ),
        "para_quem": "Ideal para bolões ou para jogar com mais dezenas gastando menos."
    },
    {
        "id": "frequencia_quentes",
        "nome": "Tradicional: Números Quentes (Mais Sorteados)",
        "nome_curto": "Dezenas Quentes",
        "icone": "🔥",
        "categoria": "tradicional",
        "descricao": (
            "Dá preferência aos números que estão saindo com mais frequência nos sorteios recentes "
            "e ao longo da história da loteria."
        ),
        "para_quem": "Ideal para quem gosta de acompanhar a maré e apostar nos números em evidência."
    },
    {
        "id": "atraso_frios",
        "nome": "Tradicional: Atrasados e Ciclo das Dezenas",
        "nome_curto": "Atrasados & Ciclo",
        "icone": "⏳",
        "categoria": "tradicional",
        "descricao": (
            "Foca nos números que estão há mais tempo sem sair e naqueles que faltam ser sorteados "
            "para que todos os números da loteria completem o ciclo atual."
        ),
        "para_quem": "Ideal para quem prefere apostar nos números atrasados que estão prestes a voltar."
    },
    {
        "id": "equilibrio_classico",
        "nome": "Tradicional: Equilíbrio Clássico",
        "nome_curto": "Equilíbrio Clássico",
        "icone": "⚖️",
        "categoria": "tradicional",
        "descricao": (
            "Monta jogos bem distribuídos seguindo o padrão mais comum dos sorteios: equilíbrio entre "
            "pares e ímpares, números bem espalhados pelo volante e dezenas repetidas do último concurso."
        ),
        "para_quem": "Ideal para quem quer jogos equilibrados e dentro do padrão mais comum da Caixa."
    },
    {
        "id": "hibrida_tradicional",
        "nome": "Análise Combinada (Mista)",
        "nome_curto": "Híbrida Completa",
        "icone": "⚡",
        "categoria": "hibrida",
        "descricao": (
            "Reúne um pouco de cada estratégia no mesmo jogo: mistura números quentes do momento, "
            "dezenas atrasadas, números repetidos do último resultado e equilíbrio de faixas."
        ),
        "para_quem": "Ideal para quem quer uma aposta completa e variada sem precisar escolher um único estilo."
    }
]

METODOS_ANALISE_DISPONIVEIS: Dict[str, Dict[str, Any]] = {
    item["id"]: item for item in CATALOGO_METODOS_ANALISE
}


def calcular_ciclo_dezenas(historico: List[List[int]], universo: List[int], eh_colunar: bool = False) -> Dict[str, Any]:
    """
    Calcula o Ciclo das Dezenas da loteria:
    - Quantos ciclos completos ocorreram no histórico;
    - Quais dezenas faltam sair para fechar o ciclo atual;
    - Duração do ciclo atual e média histórica de concursos por ciclo.
    """
    universo_set = set(universo)
    if not historico or not universo_set:
        faltam_ini = sorted(list(universo_set))
        return {
            "ciclo_atual_numero": 1,
            "ciclos_completos": 0,
            "ciclos_completos_historico": 0,
            "concursos_no_ciclo_atual": 0,
            "media_concursos_por_ciclo": 0.0,
            "faltam_sair": faltam_ini,
            "dezenas_faltantes_ciclo": faltam_ini,
            "qtd_faltam_sair": len(universo_set),
            "quantidade_faltantes": len(universo_set),
            "sorteadas_no_ciclo": [],
            "progresso_pct": 0.0
        }

    ciclos_completos = 0
    duracoes_ciclos: List[int] = []
    acumulado: Set[int] = set()
    concursos_ciclo_atual = 0

    for sorteio in historico:
        concursos_ciclo_atual += 1
        acumulado.update(int(x) for x in sorteio if int(x) in universo_set)
        if len(acumulado) >= len(universo_set):
            ciclos_completos += 1
            duracoes_ciclos.append(concursos_ciclo_atual)
            acumulado = set()
            concursos_ciclo_atual = 0

    faltam = sorted(list(universo_set - acumulado))
    sorteadas_ciclo = sorted(list(acumulado))
    progresso = round((len(sorteadas_ciclo) / max(1, len(universo_set))) * 100.0, 1)
    media_ciclo = round(statistics.mean(duracoes_ciclos), 1) if duracoes_ciclos else round(len(historico) / max(1, ciclos_completos + 1), 1)

    return {
        "ciclo_atual_numero": ciclos_completos + 1,
        "ciclos_completos": ciclos_completos,
        "ciclos_completos_historico": ciclos_completos,
        "concursos_no_ciclo_atual": concursos_ciclo_atual,
        "media_concursos_por_ciclo": media_ciclo,
        "faltam_sair": faltam,
        "dezenas_faltantes_ciclo": faltam,
        "qtd_faltam_sair": len(faltam),
        "quantidade_faltantes": len(faltam),
        "sorteadas_no_ciclo": sorteadas_ciclo,
        "progresso_pct": progresso
    }


def calcular_metricas_numerais_tradicionais(modelo: ModeloCanonico40) -> Dict[int, Dict[str, Any]]:
    """
    Calcula para cada numeral do universo:
    - frequencia_total: total de aparições no histórico
    - frequencia_curta_10: aparições nos últimos 10 jogos
    - frequencia_curta_25: aparições nos últimos 25 jogos
    - atraso_atual: quantos concursos seguidos está sem sair
    - atraso_maximo: maior atraso registrado na janela recente
    - sequencia_atual: quantos concursos seguidos vem saindo até o último resultado
    - saiu_ultimo: se esteve presente no último resultado
    - saiu_penultimo: se esteve presente no penúltimo resultado
    """
    historico = modelo.historico
    universo = list(modelo.numeros)
    ult_10 = historico[-min(len(historico), 10):]
    ult_25 = historico[-min(len(historico), 25):]
    ult_set = set(int(x) for x in historico[-1]) if historico else set()
    pen_set = set(int(x) for x in historico[-2]) if len(historico) >= 2 else set()

    metricas: Dict[int, Dict[str, Any]] = {}
    for n in universo:
        freq_total = modelo.contagens_total.get(n, 0)
        freq_10 = sum(1 for s in ult_10 if n in s)
        freq_25 = sum(1 for s in ult_25 if n in s)

        atraso_atual = 0
        for s in reversed(historico):
            if n in s:
                break
            atraso_atual += 1

        sequencia_atual = 0
        for s in reversed(historico):
            if n in s:
                sequencia_atual += 1
            else:
                break

        metricas[n] = {
            "numero": n,
            "frequencia_total": freq_total,
            "frequencia_10": freq_10,
            "frequencia_25": freq_25,
            "atraso_atual": atraso_atual,
            "sequencia_atual": sequencia_atual,
            "saiu_ultimo": n in ult_set,
            "saiu_penultimo": n in pen_set,
            "eh_primo": n in PRIMOS_ATE_100,
            "eh_fibonacci": n in FIBONACCI_ATE_100,
        }
    return metricas


def obter_presets_fechamento(loteria_type: str, config) -> List[Dict[str, Any]]:
    """Retorna matrizes recomendadas de fechamento para a modalidade."""
    slug = loteria_type.lower().replace("-", "_")
    k = config.minimo_aposta
    presets_map = {
        "mega_sena": [
            {"titulo": "Cercar Quadra com 9 Dezenas", "tamanho_grupo": 9, "dezenas_por_jogo": 6, "condicao": 4, "garantia": 4, "descricao": "Garante Quadra se 4 sorteadas estiverem nas 9 escolhidas."},
            {"titulo": "Cercar Quadra com 10 Dezenas", "tamanho_grupo": 10, "dezenas_por_jogo": 6, "condicao": 5, "garantia": 4, "descricao": "Garante Quadra se 5 sorteadas caírem no grupo de 10 dezenas."},
            {"titulo": "Cercar Quina com 9 Dezenas", "tamanho_grupo": 9, "dezenas_por_jogo": 6, "condicao": 5, "garantia": 5, "descricao": "Alta proteção para Quina acertando 5 dezenas no grupo de 9."},
        ],
        "lotofacil": [
            {"titulo": "Cercar 14 Pontos com 17 Dezenas", "tamanho_grupo": 17, "dezenas_por_jogo": 15, "condicao": 15, "garantia": 14, "descricao": "Garante 14 pontos se as 15 sorteadas estiverem entre as 17 escolhidas."},
            {"titulo": "Cercar 13 Pontos com 18 Dezenas", "tamanho_grupo": 18, "dezenas_por_jogo": 15, "condicao": 15, "garantia": 13, "descricao": "Excelente custo-benefício cercando 18 dezenas para 13+ pontos."},
            {"titulo": "Cercar 12 Pontos com 19 Dezenas", "tamanho_grupo": 19, "dezenas_por_jogo": 15, "condicao": 15, "garantia": 12, "descricao": "Ampla cobertura do volante de 25 dezenas com 19 números."},
        ],
        "quina": [
            {"titulo": "Cercar Terno com 8 Dezenas", "tamanho_grupo": 8, "dezenas_por_jogo": 5, "condicao": 4, "garantia": 3, "descricao": "Garante Terno se 4 sorteadas caírem nas 8 dezenas do grupo."},
            {"titulo": "Cercar Quadra com 8 Dezenas", "tamanho_grupo": 8, "dezenas_por_jogo": 5, "condicao": 4, "garantia": 4, "descricao": "Fechamento forte para Quadra com 8 dezenas selecionadas."},
            {"titulo": "Cercar Terno com 10 Dezenas", "tamanho_grupo": 10, "dezenas_por_jogo": 5, "condicao": 5, "garantia": 3, "descricao": "Cobre 10 dezenas garantindo Terno ao acertar as 5 no grupo."},
        ],
        "dupla_sena": [
            {"titulo": "Cercar Quadra com 9 Dezenas", "tamanho_grupo": 9, "dezenas_por_jogo": 6, "condicao": 4, "garantia": 4, "descricao": "Valendo para os 2 sorteios da Dupla Sena com 9 dezenas."},
            {"titulo": "Cercar Quadra com 10 Dezenas", "tamanho_grupo": 10, "dezenas_por_jogo": 6, "condicao": 5, "garantia": 4, "descricao": "Garante Quadra se 5 dezenas saírem entre as 10 escolhidas."},
        ],
        "dia_de_sorte": [
            {"titulo": "Cercar 5 Acertos com 10 Dezenas", "tamanho_grupo": 10, "dezenas_por_jogo": 7, "condicao": 6, "garantia": 5, "descricao": "Garante 5 pontos se 6 dias sorteados estiverem nos 10 escolhidos."},
            {"titulo": "Cercar 6 Acertos com 10 Dezenas", "tamanho_grupo": 10, "dezenas_por_jogo": 7, "condicao": 6, "garantia": 6, "descricao": "Alta precisão cercando 6 acertos a partir de 10 dias."},
        ],
        "timemania": [
            {"titulo": "Cercar 5 Acertos com 13 Dezenas", "tamanho_grupo": 13, "dezenas_por_jogo": 10, "condicao": 6, "garantia": 5, "descricao": "Desdobramento de 13 dezenas em bilhetes de 10 garantindo 5 acertos."},
            {"titulo": "Cercar 4 Acertos com 14 Dezenas", "tamanho_grupo": 14, "dezenas_por_jogo": 10, "condicao": 6, "garantia": 4, "descricao": "Ampla cobertura de 14 dezenas cercando premiação de 4+ pontos."},
        ],
        "mais_milionaria": [
            {"titulo": "Cercar Quadra com 9 Dezenas", "tamanho_grupo": 9, "dezenas_por_jogo": 6, "condicao": 4, "garantia": 4, "descricao": "Garante 4 dezenas acertando 4 entre as 9 escolhidas."},
            {"titulo": "Cercar Quadra com 10 Dezenas", "tamanho_grupo": 10, "dezenas_por_jogo": 6, "condicao": 5, "garantia": 4, "descricao": "Redução inteligente de 10 dezenas em jogos simples de 6."},
        ],
    }
    return presets_map.get(slug, [
        {
            "titulo": f"Fechamento Reduzido ({k + 3} Dezenas)",
            "tamanho_grupo": min(k + 3, config.universo),
            "dezenas_por_jogo": k,
            "condicao": min(config.sorteados, k),
            "garantia": max(1, min(config.faixas_premiacao) if config.faixas_premiacao else k - 2),
            "descricao": "Desdobramento matemático otimizado com redução de custos."
        }
    ])


def sugerir_grupo_para_fechamento(
    modelo: ModeloCanonico40,
    tamanho_grupo: int,
    estrategia: str = "canonica_dinamica"
) -> List[int]:
    """
    Sugere automaticamente as melhores dezenas para compor o grupo base de um Fechamento,
    segundo a estratégia escolhida pelo usuário (canônica dinâmica, quentes, atrasadas ou híbrida).
    """
    lot_slug = modelo.loteria_type.value if hasattr(modelo.loteria_type, "value") else str(modelo.loteria_type)
    universo = list(modelo.numeros)
    tamanho_grupo = max(modelo.config.minimo_aposta + 1, min(len(universo), tamanho_grupo))

    metricas = calcular_metricas_numerais_tradicionais(modelo)
    ciclo = calcular_ciclo_dezenas(modelo.historico, universo, bool(modelo.config.colunas))
    faltam_ciclo = set(ciclo["faltam_sair"])
    din = modelo.avaliar_dinamica_expansao_retracao()
    jogo_din = list(din.get("jogo_ajustado") or [])
    pesos_din = AvaliadorDinamicaCanonica.calcular_pesos_dinamicos_numerais(lot_slug, modelo.historico, universo)

    if estrategia == "frequencia_quentes":
        ordenados = sorted(
            universo,
            key=lambda n: (
                metricas[n]["frequencia_10"] * 2.5 + metricas[n]["frequencia_25"] * 1.2 + metricas[n]["frequencia_total"] * 0.1,
                metricas[n]["sequencia_atual"]
            ),
            reverse=True
        )
        return sorted(ordenados[:tamanho_grupo])

    if estrategia == "atraso_frios":
        ordenados = sorted(
            universo,
            key=lambda n: (
                (100 if n in faltam_ciclo else 0) + metricas[n]["atraso_atual"] * 3.0,
                metricas[n]["frequencia_total"]
            ),
            reverse=True
        )
        return sorted(ordenados[:tamanho_grupo])

    # Default: Canônica Dinâmica + Equilíbrio Setorial
    escolhidos: List[int] = []
    for n in jogo_din:
        if n in universo and n not in escolhidos and len(escolhidos) < tamanho_grupo:
            escolhidos.append(n)

    analises_map = {a.numero: a for a in modelo.analisar_todos_elementos()}
    restantes = [n for n in universo if n not in escolhidos]
    restantes_ord = sorted(
        restantes,
        key=lambda n: _peso_canonico(analises_map[n]) * pesos_din.get(n, 1.0) + (0.25 if n in faltam_ciclo else 0.0),
        reverse=True
    )
    escolhidos.extend(restantes_ord[:max(0, tamanho_grupo - len(escolhidos))])
    return sorted(escolhidos[:tamanho_grupo])


def construir_painel_opcoes_analise(modelo: ModeloCanonico40) -> Dict[str, Any]:
    """
    Constrói o relatório completo de todas as formas de análise para a loteria,
    permitindo ao usuário alternar instantaneamente na interface entre:
    - Fórmula Canônica Dinâmica (Expansão/Retração + Últimos Jogos vs Último Resultado)
    - Fechamentos Matemáticos (Presets + Grupo Sugerido)
    - Tradicional: Frequência e Dezenas Quentes
    - Tradicional: Atrasos e Ciclo das Dezenas
    - Tradicional: Equilíbrio Clássico (Soma, Paridade, Primos, Fibonacci, Moldura, Repetidas)
    - Análise Híbrida
    """
    lot_slug = modelo.loteria_type.value if hasattr(modelo.loteria_type, "value") else str(modelo.loteria_type)
    config = modelo.config
    historico = modelo.historico
    universo = list(modelo.numeros)
    ult = list(historico[-1]) if historico else []
    pen = list(historico[-2]) if len(historico) >= 2 else ult

    metricas = calcular_metricas_numerais_tradicionais(modelo)
    ciclo = calcular_ciclo_dezenas(historico, universo, bool(config.colunas))

    # 1. Ranking Quentes (Frequência Global + Curto Prazo 10/25 jogos)
    ranking_quentes = sorted(
        metricas.values(),
        key=lambda m: (m["frequencia_10"] * 2.0 + m["frequencia_25"] + m["frequencia_total"] * 0.05, m["frequencia_total"]),
        reverse=True
    )
    top_quentes = ranking_quentes[:min(15, len(universo))]
    em_sequencia = [m for m in ranking_quentes if m["sequencia_atual"] >= 2][:10]

    # 2. Ranking Atrasados / Frios e Ciclo
    ranking_atrasados = sorted(
        metricas.values(),
        key=lambda m: (m["atraso_atual"], -m["frequencia_10"], m["frequencia_total"]),
        reverse=True
    )
    top_atrasados = ranking_atrasados[:min(15, len(universo))]

    # 3. Equilíbrio Clássico no Último Resultado e no Histórico
    ult_set = set(int(x) for x in ult)
    pen_set = set(int(x) for x in pen)
    repetidas_ult = sorted(list(ult_set & pen_set))
    pares_ult = sum(1 for x in ult if int(x) % 2 == 0)
    impares_ult = len(ult) - pares_ult
    primos_ult = sorted([int(x) for x in ult if int(x) in PRIMOS_ATE_100])
    fibo_ult = sorted([int(x) for x in ult if int(x) in FIBONACCI_ATE_100])
    soma_ult = sum(int(x) for x in ult)

    somas_hist = [sum(int(x) for x in s) for s in historico[-min(len(historico), 100):]]
    soma_media = round(statistics.mean(somas_hist), 1) if somas_hist else float(soma_ult)
    soma_dp = round(statistics.pstdev(somas_hist), 1) if len(somas_hist) > 1 else 15.0
    faixa_soma_min = int(round(soma_media - 1.28 * soma_dp))
    faixa_soma_max = int(round(soma_media + 1.28 * soma_dp))

    # Média histórica de repetidas entre sorteios consecutivos
    if len(historico) >= 2 and not config.colunas:
        reps_hist = [
            len(set(historico[t]) & set(historico[t - 1]))
            for t in range(max(1, len(historico) - 50), len(historico))
        ]
        media_repetidas = round(statistics.mean(reps_hist), 1) if reps_hist else 1.0
    else:
        media_repetidas = round((config.sorteados ** 2) / max(1, config.universo), 1)

    moldura_ult = None
    if lot_slug == "lotofacil":
        moldura_ult = len([x for x in ult if int(x) in MOLDURA_LOTOFACIL])

    # 4. Fechamentos e Grupos Sugeridos
    presets_fechamento = obter_presets_fechamento(lot_slug, config)
    tam_grupo_padrao = presets_fechamento[0]["tamanho_grupo"] if presets_fechamento else min(config.minimo_aposta + 3, config.universo)
    grupo_hibrido = sugerir_grupo_para_fechamento(modelo, tam_grupo_padrao, "hibrido")
    grupos_sugeridos_fechamento = {
        "canonico_hibrido": grupo_hibrido,
        "canonica_dinamica": sugerir_grupo_para_fechamento(modelo, tam_grupo_padrao, "canonica_dinamica"),
        "frequencia_quentes": sugerir_grupo_para_fechamento(modelo, tam_grupo_padrao, "frequencia_quentes"),
        "atraso_frios": sugerir_grupo_para_fechamento(modelo, tam_grupo_padrao, "atraso_frios"),
    }

    top_quentes_global = sorted(
        metricas.values(),
        key=lambda m: (m["frequencia_total"], m["frequencia_10"]),
        reverse=True
    )[:min(15, len(universo))]

    k_aposta = config.minimo_aposta
    dinamica_res = modelo.avaliar_dinamica_expansao_retracao()
    jogo_canonico = list(dinamica_res.get("jogo_ajustado") or [])
    # Os jogos de exemplo do painel usam uma semente derivada do histórico: o mesmo histórico
    # gera sempre o mesmo resumo. O estado global do random é restaurado em seguida, para não
    # afetar a geração de jogos pedida pelo usuário.
    estado_random = random.getstate()
    random.seed(hashlib.sha256(repr((lot_slug, modelo.historico)).encode()).hexdigest())
    try:
        jogo_quentes = gerar_jogos_por_metodo(modelo, 1, k_aposta, "frequencia_quentes")[0]
        jogo_atraso = gerar_jogos_por_metodo(modelo, 1, k_aposta, "atraso_frios")[0]
        jogo_equil = gerar_jogos_por_metodo(modelo, 1, k_aposta, "equilibrio_classico")[0]
        jogo_hibrido = gerar_jogos_por_metodo(modelo, 1, k_aposta, "hibrida_tradicional")[0]
    finally:
        random.setstate(estado_random)

    faixa_rep_min = max(0, int(math.floor(media_repetidas - 1)))
    faixa_rep_max = min(config.sorteados, int(math.ceil(media_repetidas + 1)))

    return {
        "catalogo_metodos": CATALOGO_METODOS_ANALISE,
        "canonica_dinamica": {
            "dinamica": dinamica_res,
            "jogo_sugerido": jogo_canonico,
            "resumo": (
                dinamica_res.get("verificacao_ultimos_jogos", {}).get("resumo_calibracao")
                or "Fórmula Canônica 4.0 com análise de expansão e retração por casa/setor."
            )
        },
        "frequencia_quentes": {
            "janela_curta": min(len(historico), 10),
            "janela_media": min(len(historico), 25),
            "top_quentes": top_quentes,
            "top_quentes_curto_prazo": top_quentes,
            "top_quentes_global": top_quentes_global,
            "dezenas_em_sequencia": em_sequencia,
            "quentes_no_ultimo_resultado": sorted([m["numero"] for m in top_quentes[:10] if m["saiu_ultimo"]]),
            "jogo_sugerido": jogo_quentes,
            "resumo": (
                f"As dezenas mais quentes nos últimos 10 sorteios lideram com até "
                f"{top_quentes[0]['frequencia_10'] if top_quentes else 0} aparições recentes."
            )
        },
        "atraso_frios": {
            "top_atrasados": top_atrasados,
            "ciclo": ciclo,
            "ciclo_dezenas": ciclo,
            "jogo_sugerido": jogo_atraso,
            "resumo": (
                f"Ciclo #{ciclo['ciclo_atual_numero']} em andamento ({ciclo['concursos_no_ciclo_atual']} sorteios; "
                f"média de {ciclo['media_concursos_por_ciclo']} por ciclo). "
                f"Faltam {ciclo['qtd_faltam_sair']} dezena(s) para fechar o ciclo."
            )
        },
        "equilibrio_classico": {
            "ultimo_resultado": {
                "soma": soma_ult,
                "pares": pares_ult,
                "impares": impares_ult,
                "repetidas_do_anterior": repetidas_ult,
                "qtd_repetidas": len(repetidas_ult),
                "primos": primos_ult,
                "qtd_primos": len(primos_ult),
                "fibonacci": fibo_ult,
                "qtd_fibonacci": len(fibo_ult),
                "moldura": moldura_ult,
                "miolo": (len(ult) - moldura_ult) if moldura_ult is not None else None,
            },
            "repetidas_ultimo_sorteio": {
                "ultimo_total": len(repetidas_ult),
                "dezenas_repetidas_no_ultimo": repetidas_ult,
                "media_historica": media_repetidas,
                "faixa_tipica": [faixa_rep_min, faixa_rep_max],
            },
            "metas_ideais": {
                "soma_media": soma_media,
                "faixa_soma_80pct": [faixa_soma_min, faixa_soma_max],
                "pares_ideais": [max(1, config.minimo_aposta // 2 - 1), min(config.minimo_aposta, (config.minimo_aposta + 1) // 2 + 1)],
                "media_repetidas_esperada": media_repetidas,
                "alvo_repetidas": max(0, int(round(media_repetidas))),
            },
            "jogo_sugerido": jogo_equil,
            "resumo": (
                f"Último resultado teve soma {soma_ult} (faixa ideal {faixa_soma_min}–{faixa_soma_max}), "
                f"{pares_ult}P/{impares_ult}I, {len(repetidas_ult)} repetida(s) (média {media_repetidas}) e {len(primos_ult)} primo(s)."
            )
        },
        "fechamento": {
            "disponivel": lot_slug in {"mega_sena", "quina", "lotofacil", "dupla_sena", "dia_de_sorte", "timemania", "mais_milionaria"},
            "presets": presets_fechamento,
            "grupos_sugeridos": grupos_sugeridos_fechamento,
            "resumo": (
                f"{len(presets_fechamento)} matriz(es) reduzida(s) pronta(s) com sugestão automática de grupo base."
            )
        },
        "hibrida_tradicional": {
            "jogo_sugerido": jogo_hibrido,
            "resumo": (
                "Reúne números quentes do momento, dezenas atrasadas do ciclo, repetidas do último sorteio e equilíbrio de faixas."
            )
        }
    }


def gerar_jogos_por_metodo(
    modelo: ModeloCanonico40,
    quantidade_jogos: int,
    quantidade_numeros: int,
    metodo: str = "canonica_dinamica",
    numeros_base: Optional[List[int]] = None
) -> List[List[int]]:
    """
    Gera N jogos segundo o método de análise escolhido pelo usuário:
    - 'canonica_dinamica': Fórmula Canônica 4.0 + Expansão e Retração calibrada nos últimos jogos vs último resultado
    - 'frequencia_quentes': Análise Tradicional de Dezenas Quentes (Frequência Global + Curto Prazo)
    - 'atraso_frios': Análise Tradicional de Atraso Atual + Fechamento do Ciclo das Dezenas
    - 'equilibrio_classico': Análise Tradicional Clássica (Soma 80%, Paridade, Repetidas do Último, Primos, Fibonacci)
    - 'hibrida_tradicional': Combinação proporcional Quentes + Atrasados/Ciclo + Repetidas + Canônica Dinâmica
    - 'fechamento': Desdobramento matemático reduzido sobre grupo base (informado ou sugerido automaticamente)
    """
    from core import gerar_multiplos_jogos

    metodo_norm = (metodo or "canonica_dinamica").strip().lower()
    if metodo_norm in ("canonica", "canonica_dinamica", "dinamico", "expansao_retracao"):
        return gerar_multiplos_jogos(modelo, quantidade_jogos, quantidade_numeros, numeros_base=numeros_base)

    if modelo.config.colunas:
        return _gerar_colunar_por_metodo(modelo, quantidade_jogos, metodo_norm, numeros_base)

    if metodo_norm == "fechamento":
        return _gerar_fechamento_automatico_ou_base(modelo, quantidade_jogos, quantidade_numeros, numeros_base)

    universo = sorted(list({n for n in (numeros_base or modelo.numeros) if n in modelo.contagens_total}))
    if len(universo) < quantidade_numeros:
        universo = list(modelo.numeros)

    metricas = calcular_metricas_numerais_tradicionais(modelo)
    ciclo = calcular_ciclo_dezenas(modelo.historico, list(modelo.numeros), False)
    faltam_ciclo = set(ciclo["faltam_sair"])
    lot_slug = modelo.loteria_type.value if hasattr(modelo.loteria_type, "value") else str(modelo.loteria_type)
    pesos_din = AvaliadorDinamicaCanonica.calcular_pesos_dinamicos_numerais(lot_slug, modelo.historico, universo)
    analises_map = {a.numero: a for a in modelo.analisar_todos_elementos()}
    ult_set = set(int(x) for x in modelo.historico[-1]) if modelo.historico else set()

    # Calcula pesos específicos do método escolhido pelo usuário
    pesos_metodo: Dict[int, float] = {}
    max_freq = max((m["frequencia_total"] for m in metricas.values()), default=1) or 1
    max_atraso = max((m["atraso_atual"] for m in metricas.values()), default=1) or 1

    for n in universo:
        m = metricas[n]
        w_quente = 0.5 + 1.8 * (m["frequencia_10"] / 10.0) + 1.2 * (m["frequencia_25"] / 25.0) + 1.0 * (m["frequencia_total"] / max_freq)
        if m["sequencia_atual"] >= 2:
            w_quente += 0.45

        w_atraso = 0.4 + 2.2 * (m["atraso_atual"] / max_atraso) + (1.5 if n in faltam_ciclo else 0.0)
        w_canon = _peso_canonico(analises_map[n]) * pesos_din.get(n, 1.0)

        if metodo_norm == "frequencia_quentes":
            pesos_metodo[n] = max(0.05, w_quente ** 1.6)
        elif metodo_norm == "atraso_frios":
            pesos_metodo[n] = max(0.05, w_atraso ** 1.6)
        elif metodo_norm == "equilibrio_classico":
            # Valoriza equilíbrio entre repetidas esperadas, primos, Fibonacci e estabilidade
            bonus_eq = 1.0
            if n in PRIMOS_ATE_100:
                bonus_eq += 0.25
            if n in FIBONACCI_ATE_100:
                bonus_eq += 0.20
            pesos_metodo[n] = max(0.05, (0.5 * w_canon + 0.5 * w_quente) * bonus_eq)
        else:
            # hibrida_tradicional
            pesos_metodo[n] = max(0.05, 0.35 * w_quente + 0.30 * w_atraso + 0.35 * w_canon)

    return _amostrar_jogos_ponderados(
        modelo, universo, pesos_metodo, quantidade_jogos, quantidade_numeros, metodo_norm, ult_set, faltam_ciclo
    )


def _amostrar_jogos_ponderados(
    modelo: ModeloCanonico40,
    universo: List[int],
    pesos: Dict[int, float],
    quantidade_jogos: int,
    quantidade_numeros: int,
    metodo_norm: str,
    ult_set: Set[int],
    faltam_ciclo: Set[int]
) -> List[List[int]]:
    """Amostra jogos únicos respeitando a assinatura da estratégia escolhida pelo usuário."""
    jogos: List[List[int]] = []
    jogos_set: Set[Tuple[int, ...]] = set()

    # Metas de equilíbrio clássico para filtragem
    somas_hist = [sum(int(x) for x in s) for s in modelo.historico[-min(len(modelo.historico), 100):]]
    fator_escala = quantidade_numeros / max(1, modelo.config.sorteados)
    soma_media = (statistics.mean(somas_hist) if somas_hist else (modelo.N * quantidade_numeros / 2.0)) * fator_escala
    soma_dp = (statistics.pstdev(somas_hist) if len(somas_hist) > 1 else (modelo.N * 0.4)) * fator_escala
    soma_min = soma_media - 1.65 * max(soma_dp, 10.0)
    soma_max = soma_media + 1.65 * max(soma_dp, 10.0)

    alvo_rep = int(round((quantidade_numeros * modelo.config.sorteados) / max(1, modelo.config.universo)))
    ult_disponiveis = [n for n in universo if n in ult_set]
    ciclo_disponiveis = [n for n in universo if n in faltam_ciclo]

    # Jogo #1 determinístico (Elite da estratégia escolhida)
    ordenados_elite = sorted(universo, key=lambda n: pesos.get(n, 1.0), reverse=True)
    if metodo_norm in ("frequencia_quentes", "atraso_frios") and len(ordenados_elite) >= quantidade_numeros:
        jogo_topo = tuple(sorted(ordenados_elite[:quantidade_numeros]))
        jogos_set.add(jogo_topo)
        jogos.append(list(jogo_topo))

    tentativas = 0
    max_tentativas = quantidade_jogos * 220

    while len(jogos) < quantidade_jogos and tentativas < max_tentativas:
        tentativas += 1
        escolhidos: Set[int] = set()

        # Regras de ancoragem por método
        if metodo_norm == "atraso_frios" and ciclo_disponiveis:
            cota_ciclo = min(len(ciclo_disponiveis), max(1, int(round(quantidade_numeros * 0.45))))
            pesos_c = [pesos.get(n, 1.0) for n in ciclo_disponiveis]
            while len(escolhidos) < cota_ciclo:
                escolhidos.add(random.choices(ciclo_disponiveis, weights=pesos_c, k=1)[0])

        elif metodo_norm in ("equilibrio_classico", "hibrida_tradicional") and ult_disponiveis and alvo_rep > 0:
            cota_rep = min(len(ult_disponiveis), max(1, min(quantidade_numeros // 2, alvo_rep + random.choice([-1, 0, 0, 1]))))
            pesos_r = [pesos.get(n, 1.0) for n in ult_disponiveis]
            while len(escolhidos) < cota_rep:
                escolhidos.add(random.choices(ult_disponiveis, weights=pesos_r, k=1)[0])

        # Completa o jogo por amostragem ponderada sem reposição
        while len(escolhidos) < quantidade_numeros:
            restantes = [n for n in universo if n not in escolhidos]
            if not restantes:
                break
            pesos_rest = [pesos.get(n, 1.0) for n in restantes]
            escolhidos.add(random.choices(restantes, weights=pesos_rest, k=1)[0])

        if len(escolhidos) != quantidade_numeros:
            continue

        candidato = sorted(list(escolhidos))
        pares = sum(1 for n in candidato if n % 2 == 0)
        soma = sum(candidato)

        # Filtro de equilíbrio de paridade e soma (mais rigoroso no equilibrio_classico)
        pares_min = max(1, quantidade_numeros // 2 - 2)
        pares_max = min(quantidade_numeros - 1, (quantidade_numeros + 1) // 2 + 2)
        if metodo_norm == "equilibrio_classico" and tentativas < max_tentativas * 0.75:
            pares_min = max(1, quantidade_numeros // 2 - 1)
            pares_max = min(quantidade_numeros - 1, (quantidade_numeros + 1) // 2 + 1)
            if not (pares_min <= pares <= pares_max and soma_min <= soma <= soma_max):
                continue

        tup = tuple(candidato)
        if tup not in jogos_set:
            jogos_set.add(tup)
            jogos.append(candidato)

    return jogos[:quantidade_jogos]


def _gerar_fechamento_automatico_ou_base(
    modelo: ModeloCanonico40,
    quantidade_jogos: int,
    quantidade_numeros: int,
    numeros_base: Optional[List[int]] = None
) -> List[List[int]]:
    """Gera jogos via matriz de fechamento matemático usando o grupo do usuário ou grupo sugerido."""
    import fechamento
    lot_slug = modelo.loteria_type.value if hasattr(modelo.loteria_type, "value") else str(modelo.loteria_type)
    presets = obter_presets_fechamento(lot_slug, modelo.config)
    preset = presets[0] if presets else None

    if numeros_base and len(numeros_base) > quantidade_numeros:
        grupo = sorted(list(set(numeros_base)))[:min(len(numeros_base), quantidade_numeros + 4)]
    else:
        tam_grupo = preset["tamanho_grupo"] if preset and preset["tamanho_grupo"] > quantidade_numeros else min(modelo.config.universo, quantidade_numeros + 3)
        grupo = sugerir_grupo_para_fechamento(modelo, tam_grupo, "canonica_dinamica")

    menor_faixa = min((f for f in modelo.config.faixas_premiacao if f > 0), default=max(1, quantidade_numeros - 2))
    garantia = preset["garantia"] if preset and preset["garantia"] <= quantidade_numeros else max(menor_faixa, quantidade_numeros - 2)
    condicao = preset["condicao"] if preset and preset["condicao"] >= garantia else min(modelo.config.sorteados, quantidade_numeros)

    try:
        fechados = fechamento.gerar_fechamento(grupo, quantidade_numeros, condicao, garantia, tempo_maximo=2.5)
        if len(fechados) >= quantidade_jogos:
            return fechados[:quantidade_jogos]
        # Se o fechamento enxuto tiver menos jogos que o pedido, complementa com variações do grupo
        vistos = {tuple(j) for j in fechados}
        extras = _amostrar_jogos_ponderados(
            modelo, grupo, {n: 1.0 for n in grupo}, quantidade_jogos - len(fechados), quantidade_numeros, "hibrida_tradicional", set(), set()
        )
        for ex in extras:
            if tuple(ex) not in vistos and len(fechados) < quantidade_jogos:
                vistos.add(tuple(ex))
                fechados.append(ex)
        return fechados[:quantidade_jogos]
    except Exception:
        from core import gerar_multiplos_jogos
        return gerar_multiplos_jogos(modelo, quantidade_jogos, quantidade_numeros, numeros_base=grupo)


def _gerar_colunar_por_metodo(
    modelo: ModeloCanonico40,
    quantidade_jogos: int,
    metodo_norm: str,
    numeros_base: Optional[List[int]] = None
) -> List[List[int]]:
    """Geração colunar (Super Sete) adaptada ao método tradicional ou híbrido escolhido."""
    from core import modelos_por_coluna
    modelos_col = modelos_por_coluna(modelo)
    permitidos = {n for n in (numeros_base or []) if n in modelo.contagens_total} or None
    din = modelo.avaliar_dinamica_expansao_retracao()
    jogo_din = list(din.get("jogo_ajustado") or [])

    jogos: List[List[int]] = []
    vistos: Set[Tuple[int, ...]] = set()

    if metodo_norm in ("canonica_dinamica", "hibrida_tradicional") and len(jogo_din) == len(modelos_col) and not permitidos:
        vistos.add(tuple(jogo_din))
        jogos.append(jogo_din)

    tentativas = 0
    while len(jogos) < quantidade_jogos and tentativas < quantidade_jogos * 150:
        tentativas += 1
        jogo_col: List[int] = []
        for idx, m_col in enumerate(modelos_col):
            metricas_c = calcular_metricas_numerais_tradicionais(m_col)
            candidatos = [d for d in m_col.numeros if not permitidos or d in permitidos]
            if not candidatos:
                candidatos = list(m_col.numeros)
            if metodo_norm == "frequencia_quentes":
                pesos_c = [max(0.1, metricas_c[d]["frequencia_10"] * 2.0 + metricas_c[d]["frequencia_total"] * 0.2) for d in candidatos]
            elif metodo_norm == "atraso_frios":
                pesos_c = [max(0.1, metricas_c[d]["atraso_atual"] * 2.0 + 0.5) for d in candidatos]
            else:
                alvo_c = jogo_din[idx] if idx < len(jogo_din) else 4
                pesos_c = [max(0.1, 2.5 - abs(d - alvo_c) * 0.4 + metricas_c[d]["frequencia_10"] * 0.3) for d in candidatos]
            jogo_col.append(random.choices(candidatos, weights=pesos_c, k=1)[0])

        tup = tuple(jogo_col)
        if tup not in vistos:
            vistos.add(tup)
            jogos.append(jogo_col)

    return jogos[:quantidade_jogos]

"""
Avaliação dos jogos do usuário e parecer dos jogos gerados, calculados localmente
a partir do Modelo Canônico 3.0 (sem chamadas de IA).
"""

from collections import Counter
from math import comb
from typing import Dict, List, Optional

from core import ModeloCanonico30, LoteriaType, _peso_canonico, modelos_por_coluna

AVISO_PROBABILIDADE = (
    "Todas as combinações têm exatamente a mesma chance de serem sorteadas. "
    "A análise canônica descreve o histórico de sorteios; ela não prevê o próximo resultado."
)

MOTIVO_PADRAO_POPULAR = "Muitos apostadores escolhem esse padrão: se ele for sorteado, o prêmio tende a ser dividido entre mais ganhadores."


def _um_em(p: float) -> Optional[int]:
    return round(1 / p) if p > 0 else None


def probabilidades(modelo: ModeloCanonico30, quantidade: int) -> Dict:
    """Chance exata de cada faixa de acertos para um jogo com `quantidade` números."""
    config = modelo.config
    faixas = config.faixas_premiacao
    observacao = None

    if config.colunas:
        p = 1 / config.universo
        k = config.colunas

        def prob(j):
            return comb(k, j) * p ** j * (1 - p) ** (k - j)
    else:
        N, k = config.universo, config.sorteados
        total = comb(N, k)

        def prob(j):
            return comb(quantidade, j) * comb(N - quantidade, k - j) / total

    if modelo.loteria_type == LoteriaType.MAIS_MILIONARIA:
        faixas = [2, 3, 4, 5, 6]
        observacao = "Chances calculadas só para os 6 números; os 2 trevos também definem as faixas de prêmio."
    if config.sorteios_por_concurso > 1:
        observacao = f"A {config.nome} tem {config.sorteios_por_concurso} sorteios por concurso; o mesmo jogo concorre nos dois."

    linhas = []
    for j in sorted(faixas, reverse=True):
        pj = prob(j)
        item = {'acertos': j, 'probabilidade': pj, 'um_em': _um_em(pj)}
        if config.sorteios_por_concurso > 1:
            item['um_em_algum_sorteio'] = _um_em(1 - (1 - pj) ** config.sorteios_por_concurso)
        linhas.append(item)

    return {
        'faixas': linhas,
        'custo_aposta': round(comb(quantidade, config.minimo_aposta) * config.custo_minimo, 2),
        'observacao': observacao,
    }


def _ultimos_sorteios(modelo: ModeloCanonico30) -> List[List[int]]:
    if not modelo.historico:
        return []
    ultimo = modelo.historico[-1]
    k = modelo.config.colunas or modelo.config.sorteados
    return [ultimo[i:i + k] for i in range(0, len(ultimo), k)]


def _maior_sequencia(numeros: List[int]) -> int:
    maior = atual = 1
    for a, b in zip(numeros, numeros[1:]):
        atual = atual + 1 if b == a + 1 else 1
        maior = max(maior, atual)
    return maior


def _alertas(jogo: List[int], modelo: ModeloCanonico30, ultimos: List[List[int]]) -> List[Dict]:
    config = modelo.config
    alertas = []

    if config.colunas:
        digito, qtd = Counter(jogo).most_common(1)[0]
        if qtd >= 5:
            alertas.append({'tipo': 'mesmo_digito', 'mensagem': f'{qtd} colunas com o dígito {digito}.'})
        if max(_maior_sequencia(jogo), _maior_sequencia([-d for d in jogo])) >= 5:
            alertas.append({'tipo': 'sequencia', 'mensagem': '5 ou mais colunas com dígitos em sequência (ex.: 1-2-3-4-5).'})
        if any(jogo == u for u in ultimos):
            alertas.append({'tipo': 'repete_ultimo', 'mensagem': 'Jogo idêntico ao último resultado.'})
        for a in alertas:
            a['motivo'] = MOTIVO_PADRAO_POPULAR
        return alertas

    n, N = len(jogo), config.universo
    ordenado = sorted(jogo)
    esparso = n / N <= 0.3

    if N > 31 and all(x <= 31 for x in ordenado):
        alertas.append({'tipo': 'datas', 'mensagem': 'Todos os números vão até 31, como em apostas feitas com datas de aniversário.'})
    if esparso and n >= 3:
        difs = {b - a for a, b in zip(ordenado, ordenado[1:])}
        if _maior_sequencia(ordenado) >= 3:
            alertas.append({'tipo': 'sequencia', 'mensagem': 'Tem 3 ou mais números seguidos (ex.: 21-22-23).'})
        elif n >= 4 and len(difs) == 1:
            alertas.append({'tipo': 'progressao', 'mensagem': 'Números igualmente espaçados (ex.: 5-10-15-20).'})
        final, qtd = Counter(x % 10 for x in ordenado).most_common(1)[0]
        if qtd >= max(4, -(-n * 6 // 10)):
            alertas.append({'tipo': 'mesmo_final', 'mensagem': f'{qtd} números terminam em {final} (mesma coluna do volante).'})
    if any(len(u) and set(u) <= set(ordenado) for u in ultimos):
        alertas.append({'tipo': 'repete_ultimo', 'mensagem': 'Repete todas as dezenas do último resultado.'})

    for a in alertas:
        a['motivo'] = MOTIVO_PADRAO_POPULAR
    return alertas


def _sugerir_trocas(jogo: List[int], modelo: ModeloCanonico30, ultimos: List[List[int]], max_trocas: int = 3) -> Dict:
    """Trocas que eliminam padrões populares, preferindo números com maior peso canônico."""
    config = modelo.config
    atual = list(jogo)
    trocas = []

    if config.colunas:
        pesos_col = [{a.numero: _peso_canonico(a) for a in m.analisar_todos_elementos()} for m in modelos_por_coluna(modelo)]
    else:
        pesos = {a.numero: _peso_canonico(a) for a in modelo.analisar_todos_elementos()}

    def gravidade(j):
        # Nº de alertas e, no Super Sete, quantas colunas repetem o mesmo dígito
        return (len(_alertas(j, modelo, ultimos)), Counter(j).most_common(1)[0][1] if config.colunas else 0)

    for _ in range(max_trocas):
        base = gravidade(atual)
        if base[0] == 0:
            break
        melhor = None
        if config.colunas:
            for i, digito_atual in enumerate(atual):
                for d in config.numeros:
                    if d == digito_atual:
                        continue
                    novo = atual[:i] + [d] + atual[i + 1:]
                    chave = (*gravidade(novo), -pesos_col[i][d])
                    if melhor is None or chave < melhor[0]:
                        melhor = (chave, {'coluna': i + 1, 'sai': digito_atual, 'entra': d}, novo)
        else:
            presentes = set(atual)
            for r in atual:
                for a in config.numeros:
                    if a in presentes:
                        continue
                    novo = sorted((presentes - {r}) | {a})
                    chave = (*gravidade(novo), -pesos[a], pesos[r])
                    if melhor is None or chave < melhor[0]:
                        melhor = (chave, {'sai': r, 'entra': a}, novo)
        if melhor is None or melhor[0][:2] >= base:
            break
        trocas.append(melhor[1])
        atual = melhor[2]

    return {'trocas': trocas, 'jogo_sugerido': atual if trocas else None}


def _atrasos(historico: List[List[int]], numeros: List[int]) -> Dict[int, Optional[int]]:
    atrasos = {n: None for n in numeros}
    for distancia, concurso in enumerate(reversed(historico)):
        for n in concurso:
            if n in atrasos and atrasos[n] is None:
                atrasos[n] = distancia
    return atrasos


def _situacao(fr: float) -> str:
    if fr > 1.15:
        return 'acima da média'
    if fr < 0.85:
        return 'abaixo da média'
    return 'na média'


def _perfil(analise, atraso: Optional[int]) -> Dict:
    return {
        'numero': analise.numero,
        'vezes_sorteado': analise.contagem_total,
        'fr': round(analise.fr, 3),
        'situacao': _situacao(analise.fr),
        'classe': analise.classe,
        'maturidade': analise.maturidade,
        'concursos_sem_sair': atraso,
        'score_mcp': round(analise.score_mcp, 4),
    }


def validar_jogo(jogo, modelo: ModeloCanonico30) -> Optional[str]:
    config = modelo.config
    if not isinstance(jogo, list) or not all(isinstance(n, int) and not isinstance(n, bool) for n in jogo):
        return 'O jogo deve ser uma lista de números inteiros.'
    fora = [n for n in jogo if not config.numero_inicial <= n <= config.numero_final]
    if fora:
        return f'Número(s) fora do volante ({config.numero_inicial} a {config.numero_final}): {fora}.'
    if config.colunas:
        if len(jogo) != config.colunas:
            return f'O jogo da {config.nome} tem exatamente {config.colunas} colunas.'
        return None
    if len(set(jogo)) != len(jogo):
        return 'O jogo tem números repetidos.'
    if not config.minimo_aposta <= len(jogo) <= config.maximo_aposta:
        return f'A {config.nome} aceita de {config.minimo_aposta} a {config.maximo_aposta} números por jogo.'
    return None


def avaliar_jogo(jogo: List[int], modelo: ModeloCanonico30) -> Dict:
    config = modelo.config
    erro = validar_jogo(jogo, modelo)
    if erro:
        return {'jogo': jogo, 'valido': False, 'erro': erro}

    ultimos = _ultimos_sorteios(modelo)

    if config.colunas:
        perfil = []
        for i, (digito, m) in enumerate(zip(jogo, modelos_por_coluna(modelo))):
            analise = next(a for a in m.analisar_todos_elementos() if a.numero == digito)
            item = _perfil(analise, _atrasos(m.historico, [digito])[digito])
            item['coluna'] = i + 1
            perfil.append(item)
        equilibrio = None
    else:
        jogo = sorted(jogo)
        analises = {a.numero: a for a in modelo.analisar_todos_elementos()}
        atrasos = _atrasos(modelo.historico, jogo)
        perfil = [_perfil(analises[n], atrasos[n]) for n in jogo]
        pares = sum(1 for n in jogo if n % 2 == 0)
        pares_no_volante = sum(1 for n in config.numeros if n % 2 == 0)
        equilibrio = {
            'pares': pares,
            'impares': len(jogo) - pares,
            'pares_esperado': round(len(jogo) * pares_no_volante / config.universo, 1),
        }

    return {
        'jogo': jogo,
        'valido': True,
        'probabilidades': probabilidades(modelo, len(jogo)),
        'perfil_numeros': perfil,
        'equilibrio': equilibrio,
        'alertas': _alertas(jogo, modelo, ultimos),
        'sugestao': _sugerir_trocas(jogo, modelo, ultimos),
        'aviso': AVISO_PROBABILIDADE,
    }


def parecer_jogos(jogos: List[List[int]], modelo: ModeloCanonico30) -> Dict:
    """Parecer dos jogos gerados, montado a partir das métricas canônicas já calculadas."""
    config = modelo.config
    if not jogos:
        return {'parecer_texto': 'Nenhum jogo gerado.', 'recomendacoes': [], 'provedor': 'Modelo Canônico 3.0'}

    ultimos = _ultimos_sorteios(modelo)
    com_alerta = sum(1 for j in jogos if _alertas(j, modelo, ultimos))
    prob = probabilidades(modelo, len(jogos[0]))
    faixa_max, faixa_min = prob['faixas'][0], prob['faixas'][-1]

    linhas = [f"{len(jogos)} jogo(s) de {len(jogos[0])} números para a {config.nome}, a partir de {modelo.T} concursos analisados."]
    if not config.colunas:
        analises = {a.numero: a for a in modelo.analisar_todos_elementos()}
        escolhidos = [n for j in jogos for n in j]
        distintos = set(escolhidos)
        fr_medio = sum(analises[n].fr for n in escolhidos) / len(escolhidos)
        classes = Counter(analises[n].classe for n in distintos)
        linhas.append(f"Os jogos cobrem {len(distintos)} dos {config.universo} números do volante.")
        linhas.append(f"Fator de recorrência médio dos números escolhidos: {fr_medio:.2f} (1,00 = exatamente a média histórica).".replace('.', ',', 1))
        linhas.append("Classes canônicas dos números usados: " + ", ".join(f"{c}: {classes.get(c, 0)}" for c in "ABCD") + ".")
    linhas.append(
        f"Chance de {faixa_max['acertos']} acertos com cada jogo: 1 em {faixa_max['um_em']:,}".replace(',', '.')
        + f"; de {faixa_min['acertos']} acertos: 1 em {faixa_min['um_em']:,}.".replace(',', '.')
    )
    if com_alerta:
        linhas.append(f"{com_alerta} jogo(s) têm padrões populares entre apostadores; use \"Avaliar meus jogos\" para ver sugestões de troca.")
    else:
        linhas.append("Nenhum jogo tem padrões populares (datas, sequências, repetição do último resultado).")

    return {
        'parecer_texto': "\n".join(linhas),
        'recomendacoes': [
            AVISO_PROBABILIDADE,
            "Evitar padrões populares não aumenta a chance de acertar, mas reduz a chance de dividir o prêmio.",
            f"Custo de cada jogo: R$ {prob['custo_aposta']:.2f}".replace('.', ',') + ". Defina um orçamento fixo por concurso.",
        ],
        'provedor': 'Modelo Canônico 3.0 (cálculo local)',
    }

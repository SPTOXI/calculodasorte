"""
Fechamentos (desdobramentos) com garantia: a partir de um grupo de números escolhido
pelo apostador, gera o menor conjunto de jogos que conseguimos encontrar tal que,
se `condicao` números sorteados estiverem no grupo, algum jogo terá pelo menos
`garantia` acertos.
"""

import random
import time
from itertools import combinations
from math import comb
from typing import List, Optional

from core import LoteriaConfig

LOTERIAS_FECHAMENTO = {'mega_sena', 'quina', 'lotofacil', 'dupla_sena', 'dia_de_sorte', 'timemania'}
LIMITE_CONDICOES = 20000
LIMITE_JOGOS = 500
TEMPO_MAXIMO = 6.0
MAX_GRUPO = 30


class FechamentoInviavel(ValueError):
    pass


def _cobre(alvo: int, jogo: int, garantia: int) -> bool:
    return (alvo & jogo).bit_count() >= garantia


def _remover_redundantes(jogos: List[int], alvos: List[int], garantia: int) -> List[int]:
    cobertura = {a: sum(1 for j in jogos if _cobre(a, j, garantia)) for a in alvos}
    resultado = list(jogos)
    for jogo in reversed(jogos):
        cobertos = [a for a in alvos if _cobre(a, jogo, garantia)]
        if all(cobertura[a] >= 2 for a in cobertos):
            resultado.remove(jogo)
            for a in cobertos:
                cobertura[a] -= 1
    return resultado


def _melhorar(mascara: int, amostra: List[int], indices: List[int], garantia: int) -> int:
    """Busca local: troca um número de dentro por um de fora enquanto isso cobrir mais pendências."""
    def pontos(m):
        return sum(1 for p in amostra if _cobre(p, m, garantia))
    atual = pontos(mascara)
    melhorou = True
    while melhorou:
        melhorou = False
        dentro = [i for i in indices if mascara >> i & 1]
        fora = [i for i in indices if not mascara >> i & 1]
        for i in dentro:
            for o in fora:
                candidata = mascara ^ (1 << i) ^ (1 << o)
                p = pontos(candidata)
                if p > atual:
                    mascara, atual, melhorou = candidata, p, True
                    break
            if melhorou:
                break
    return mascara


def _cobertura_gulosa(v: int, tamanho_jogo: int, condicao: int, garantia: int, alvos: List[int],
                      rnd: random.Random, prazo: float) -> Optional[List[int]]:
    indices = list(range(v))
    pendentes = list(alvos)
    jogos: List[int] = []
    while pendentes:
        if len(jogos) >= LIMITE_JOGOS or time.monotonic() > prazo:
            return None
        alvo = pendentes[rnd.randrange(len(pendentes))]
        bits_alvo = [i for i in indices if alvo >> i & 1]
        amostra = pendentes if len(pendentes) <= 800 else rnd.sample(pendentes, 800)

        melhor = None
        for _ in range(12):
            escolhidos = set(rnd.sample(bits_alvo, rnd.randint(garantia, min(condicao, tamanho_jogo))))
            escolhidos.update(rnd.sample([i for i in indices if i not in escolhidos], tamanho_jogo - len(escolhidos)))
            mascara = sum(1 << i for i in escolhidos)
            pontos = sum(1 for p in amostra if _cobre(p, mascara, garantia))
            if melhor is None or pontos > melhor[0]:
                melhor = (pontos, mascara)

        jogo = _melhorar(melhor[1], amostra, indices, garantia)
        jogos.append(jogo)
        pendentes = [p for p in pendentes if not _cobre(p, jogo, garantia)]

    if len(jogos) * len(alvos) <= 3_000_000:
        jogos = _remover_redundantes(jogos, alvos, garantia)
    return jogos


def gerar_fechamento(grupo: List[int], tamanho_jogo: int, condicao: int, garantia: int,
                     semente: Optional[int] = None, tempo_maximo: float = TEMPO_MAXIMO) -> List[List[int]]:
    """Cobertura gulosa com máscaras de bits e busca local, repetida enquanto houver tempo;
    fica com a solução de menos jogos. Toda solução devolvida cumpre a garantia."""
    grupo = sorted(set(grupo))
    v = len(grupo)
    if tamanho_jogo >= v:
        return [grupo]
    if comb(v, condicao) > LIMITE_CONDICOES:
        raise FechamentoInviavel('Grupo grande demais para essa garantia. Diminua o grupo ou escolha uma garantia menor.')

    rnd = random.Random(semente)
    alvos = [sum(1 << i for i in c) for c in combinations(range(v), condicao)]
    inicio = time.monotonic()
    prazo_final = inicio + tempo_maximo
    melhor: Optional[List[int]] = None
    sem_melhora = 0

    while True:
        solucao = _cobertura_gulosa(v, tamanho_jogo, condicao, garantia, alvos, rnd, prazo_final)
        if solucao is not None and (melhor is None or len(solucao) < len(melhor)):
            melhor, sem_melhora = solucao, 0
        else:
            sem_melhora += 1
        decorrido = time.monotonic() - inicio
        # Novas tentativas até ~2,5 s, parando antes se 20 seguidas não melhorarem
        if solucao is None or decorrido > min(2.5, tempo_maximo / 2) or sem_melhora >= 20 or len(melhor) <= 1:
            break

    if melhor is None:
        raise FechamentoInviavel('Esse fechamento exigiria jogos demais. Diminua o grupo ou escolha uma garantia menor.')
    return [[grupo[i] for i in range(v) if mascara >> i & 1] for mascara in melhor]


def garantia_valida(jogos: List[List[int]], grupo: List[int], condicao: int, garantia: int) -> bool:
    """Confere a garantia por força bruta sobre todas as condições possíveis."""
    conjuntos = [set(j) for j in jogos]
    return all(any(len(c & j) >= garantia for j in conjuntos) for c in map(set, combinations(sorted(set(grupo)), condicao)))


def chance_condicao(config: LoteriaConfig, tamanho_grupo: int, condicao: int) -> float:
    """Probabilidade de pelo menos `condicao` números sorteados caírem no grupo."""
    N, k = config.universo, config.sorteados
    return sum(comb(tamanho_grupo, j) * comb(N - tamanho_grupo, k - j) for j in range(condicao, k + 1)) / comb(N, k)


def validar_pedido(loteria_type: str, config: LoteriaConfig, grupo, tamanho_jogo: int, condicao: int, garantia: int) -> Optional[str]:
    if loteria_type not in LOTERIAS_FECHAMENTO:
        return f'Fechamento ainda não disponível para a {config.nome}.'
    if not isinstance(grupo, list) or not all(isinstance(n, int) and not isinstance(n, bool) for n in grupo):
        return 'O grupo deve ser uma lista de números.'
    if len(set(grupo)) != len(grupo):
        return 'O grupo tem números repetidos.'
    if any(not config.numero_inicial <= n <= config.numero_final for n in grupo):
        return f'Os números devem estar entre {config.numero_inicial} e {config.numero_final}.'
    if not config.minimo_aposta <= tamanho_jogo <= config.maximo_aposta:
        return f'Cada jogo da {config.nome} tem de {config.minimo_aposta} a {config.maximo_aposta} números.'
    if not tamanho_jogo < len(grupo) <= min(MAX_GRUPO, config.universo - 1):
        return f'Escolha de {tamanho_jogo + 1} a {min(MAX_GRUPO, config.universo - 1)} números no grupo.'
    menor_faixa = min(f for f in config.faixas_premiacao if f > 0)
    if not menor_faixa <= garantia <= min(condicao, tamanho_jogo):
        return f'A garantia deve ficar entre {menor_faixa} e {min(condicao, tamanho_jogo)} acertos.'
    if not garantia <= condicao <= min(config.sorteados, len(grupo)):
        return f'A condição deve ficar entre {garantia} e {min(config.sorteados, len(grupo))} números sorteados no grupo.'
    return None

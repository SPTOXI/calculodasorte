"""
Conferência de apostas salvas contra o sorteio oficial do concurso correspondente.
"""

from typing import Dict, List, Optional, Tuple

import updater


def rotulo_premio(loteria_type: str, qtd_acertos: int, sorteio_premiado: Optional[int] = None) -> Optional[str]:
    rotulo = None
    if loteria_type == 'mega_sena':
        rotulo = {6: 'Sena (6 acertos) 🏆', 5: 'Quina (5 acertos) ⭐', 4: 'Quadra (4 acertos) 🎯'}.get(qtd_acertos)
    elif loteria_type == 'quina':
        rotulo = {5: 'Quina (5 acertos) 🏆', 4: 'Quadra (4 acertos) ⭐', 3: 'Terno (3 acertos) 🎯', 2: 'Duque (2 acertos)'}.get(qtd_acertos)
    elif loteria_type == 'lotofacil':
        rotulo = {15: '15 Acertos 🏆', 14: '14 Acertos ⭐', 13: '13 Acertos 🎯', 12: '12 Acertos', 11: '11 Acertos'}.get(qtd_acertos)
    elif loteria_type == 'dupla_sena':
        rotulo = {6: 'Sena (6 acertos) 🏆', 5: 'Quina (5 acertos) ⭐', 4: 'Quadra (4 acertos) 🎯', 3: 'Terno (3 acertos)'}.get(qtd_acertos)
        if rotulo and sorteio_premiado:
            rotulo += f' - {sorteio_premiado}º sorteio'
    elif loteria_type == 'lotomania':
        if qtd_acertos == 20:
            rotulo = '20 Acertos 🏆'
        elif 15 <= qtd_acertos <= 19:
            rotulo = f'{qtd_acertos} Acertos ⭐'
        elif qtd_acertos == 0:
            rotulo = '0 Acertos 🎯'
    elif loteria_type in ('super_sete', 'timemania'):
        if qtd_acertos == 7:
            rotulo = '7 Acertos 🏆'
        elif qtd_acertos >= 3:
            rotulo = f'{qtd_acertos} Acertos ⭐'
    elif loteria_type == 'dia_de_sorte':
        rotulo = {7: '7 Acertos 🏆', 6: '6 Acertos ⭐', 5: '5 Acertos 🎯', 4: '4 Acertos'}.get(qtd_acertos)
    elif qtd_acertos >= 4:
        rotulo = f'{qtd_acertos} acertos 🎯'
    return rotulo


def proximo_concurso(loteria_type: str) -> Optional[int]:
    """Concurso em que uma aposta salva agora vai concorrer."""
    ultimo = updater.carregar_meta(loteria_type).get('ultimo_concurso')
    return ultimo + 1 if ultimo else None


def sorteio_do_concurso(loteria_type: str, concurso: Optional[int]) -> Dict:
    """Dezenas sorteadas no concurso pedido (ou no último, se não informado)."""
    historico = updater.carregar_historico_local(loteria_type)
    meta = updater.carregar_meta(loteria_type)
    ultimo = meta.get('ultimo_concurso') or len(historico)
    if not historico:
        return {'status': 'indisponivel', 'concurso': concurso}

    concurso = concurso or ultimo
    if concurso > ultimo:
        return {'status': 'aguardando', 'concurso': concurso}

    indice = len(historico) - 1 - (ultimo - concurso)
    if indice < 0:
        return {'status': 'indisponivel', 'concurso': concurso}

    segundo = []
    if loteria_type == 'dupla_sena':
        segundos = updater.carregar_segundo_sorteio_local(loteria_type)
        if len(segundos) == len(historico):
            segundo = segundos[indice]

    return {
        'status': 'conferido',
        'concurso': concurso,
        'data_apuracao': meta.get('data_apuracao') if concurso == ultimo else None,
        'dezenas': historico[indice],
        'segundo_sorteio': segundo,
    }


def conferir_jogos(loteria_type: str, jogos: List[List[int]], sorteio: List[int],
                   segundo_sorteio: Optional[List[int]] = None) -> Tuple[List[Dict], Dict[str, int]]:
    resultado = []
    premiacoes: Dict[str, int] = {}
    set_sorteio = set(sorteio)

    for idx, jogo in enumerate(jogos, 1):
        acertos_posicoes = None
        sorteio_premiado = None
        if loteria_type == 'super_sete':
            # Super Sete: acerto é o dígito certo na coluna certa
            acertos_posicoes = [i for i, (n, s) in enumerate(zip(jogo, sorteio)) if n == s]
            acertos = [jogo[i] for i in acertos_posicoes]
        else:
            acertos = sorted(set(jogo) & set_sorteio)
            if segundo_sorteio:
                acertos_2 = sorted(set(jogo) & set(segundo_sorteio))
                sorteio_premiado = 1
                if len(acertos_2) > len(acertos):
                    acertos, sorteio_premiado = acertos_2, 2

        rotulo = rotulo_premio(loteria_type, len(acertos), sorteio_premiado)
        if rotulo:
            premiacoes[rotulo] = premiacoes.get(rotulo, 0) + 1

        resultado.append({
            'numero': idx,
            'jogo': jogo,
            'acertos': acertos,
            'qtd_acertos': len(acertos),
            'acertos_posicoes': acertos_posicoes,
            'rotulo_premio': rotulo,
        })
    return resultado, premiacoes


def resumo_aposta(aposta: Dict, sorteios_cache: Optional[Dict] = None) -> Dict:
    """Situação de uma aposta salva no concurso em que ela concorre."""
    loteria_type = aposta['loteria_type']
    concurso = aposta.get('concurso_alvo')
    chave = (loteria_type, concurso)
    if sorteios_cache is not None and chave in sorteios_cache:
        sorteio = sorteios_cache[chave]
    else:
        sorteio = sorteio_do_concurso(loteria_type, concurso)
        if sorteios_cache is not None:
            sorteios_cache[chave] = sorteio

    if sorteio['status'] != 'conferido':
        return {'status': sorteio['status'], 'concurso': sorteio['concurso']}

    jogos, premiacoes = conferir_jogos(loteria_type, aposta.get('jogos', []), sorteio['dezenas'], sorteio['segundo_sorteio'])
    return {
        'status': 'conferido',
        'concurso': sorteio['concurso'],
        'jogos_premiados': sum(1 for j in jogos if j['rotulo_premio']),
        'melhor_acerto': max((j['qtd_acertos'] for j in jogos), default=0),
        'premiacoes': premiacoes,
    }

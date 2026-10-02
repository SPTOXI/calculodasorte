"""
Conferência de apostas salvas contra o sorteio oficial do concurso correspondente.
"""

from typing import Dict, List, Optional, Tuple

import updater


def rotulo_premio(loteria_type: str, qtd_acertos: int, sorteio_premiado: Optional[int] = None,
                  trevos_acertados: Optional[int] = None) -> Optional[str]:
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
    elif loteria_type == 'mais_milionaria':
        rotulo = rotulo_mais_milionaria(qtd_acertos, trevos_acertados)
    elif qtd_acertos >= 4:
        rotulo = f'{qtd_acertos} acertos 🎯'
    return rotulo


def rotulo_mais_milionaria(acertos: int, trevos: Optional[int]) -> Optional[str]:
    """Faixas oficiais da +Milionária (dezenas + trevos):
    6+2, 6+1/0, 5+2, 5+1/0, 4+2, 4+1/0, 3+2, 3+1/0, 2+2 e 2+1.
    Sem os trevos do jogo, só dá para afirmar prêmio a partir de 3 dezenas."""
    if trevos is None:
        return f'{acertos} Acertos (confira os trevos)' + (' 🏆' if acertos == 6 else '') if acertos >= 3 else None
    if acertos >= 3 or (acertos == 2 and trevos >= 1):
        faixa = f'{acertos} + {trevos} trevo(s)'
        return faixa + (' 🏆' if (acertos, trevos) == (6, 2) else ' ⭐' if acertos >= 5 else ' 🎯')
    return None


def proximo_concurso(loteria_type: str) -> Optional[int]:
    """Concurso em que uma aposta salva agora vai concorrer."""
    ultimo = updater.carregar_meta(loteria_type).get('ultimo_concurso')
    return ultimo + 1 if ultimo else None


MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
         'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
ROTULO_COMPLEMENTO = {'timemania': '⚽ Time do Coração', 'dia_de_sorte': '📅 Mês da Sorte'}


def normalizar_complemento(valor) -> str:
    """Compara 'VOLTA REDONDA    /RJ' com 'Volta Redonda/RJ' e 'março' com 'Março'."""
    import re
    return re.sub(r'\s*/\s*', '/', ' '.join(str(valor or '').split())).casefold()


_CONCURSOS_CACHE: Dict[Tuple[str, int], Dict] = {}


def _dados_do_concurso(loteria_type: str, concurso: int) -> Optional[Dict]:
    """Resultado oficial de um concurso específico (o resultado de um concurso nunca muda)."""
    chave = (loteria_type, concurso)
    if chave in _CONCURSOS_CACHE:
        return _CONCURSOS_CACHE[chave]
    dados = updater.carregar_ultimo_resultado_local(loteria_type)
    if not dados or dados.get('numero') != concurso:
        slug = updater.LOTERIAS_SLUGS.get(loteria_type)
        dados = updater.consultar_caixa(slug, concurso=concurso, max_retries=1) if slug else None
    if dados and dados.get('numero') == concurso:
        _CONCURSOS_CACHE[chave] = dados
        return dados
    return None


def sorteio_do_concurso(loteria_type: str, concurso: Optional[int]) -> Dict:
    """Dezenas sorteadas no concurso pedido (ou no último, se não informado)."""
    meta = updater.carregar_meta(loteria_type)
    ultimo = meta.get('ultimo_concurso')
    if not ultimo:
        return {'status': 'indisponivel', 'concurso': concurso}

    concurso = concurso or ultimo
    if concurso > ultimo:
        return {'status': 'aguardando', 'concurso': concurso}

    dados = _dados_do_concurso(loteria_type, concurso)
    if not dados:
        # Sem o resultado oficial do concurso não dá para conferir: a posição no histórico
        # local não é confiável, pois concursos que falharam no download ficam de fora.
        return {'status': 'indisponivel', 'concurso': concurso}

    slug = updater.LOTERIAS_SLUGS.get(loteria_type)
    return {
        'status': 'conferido',
        'concurso': concurso,
        'data_apuracao': dados.get('dataApuracao'),
        'dezenas': updater.extrair_dezenas(dados, slug),
        'segundo_sorteio': updater.extrair_segundo_sorteio(dados) if loteria_type == 'dupla_sena' else [],
        'trevos': updater.extrair_trevos(dados) if loteria_type == 'mais_milionaria' else [],
        'complemento': dados.get('nomeTimeCoracaoMesSorte') if loteria_type in ROTULO_COMPLEMENTO else None,
    }


def conferir_jogos(loteria_type: str, jogos: List[List[int]], sorteio: List[int],
                   segundo_sorteio: Optional[List[int]] = None,
                   trevos_sorteio: Optional[List[int]] = None,
                   trevos_jogos: Optional[List[List[int]]] = None,
                   complemento_sorteio: Optional[str] = None,
                   complementos_jogos: Optional[List[Optional[str]]] = None) -> Tuple[List[Dict], Dict[str, int]]:
    resultado = []
    premiacoes: Dict[str, int] = {}
    set_sorteio = set(sorteio)

    for idx, jogo in enumerate(jogos, 1):
        acertos_posicoes = None
        rotulos: List[str] = []
        trevos_acertados = None
        if loteria_type == 'super_sete':
            # Super Sete: acerto é o dígito certo na coluna certa
            acertos_posicoes = [i for i, (n, s) in enumerate(zip(jogo, sorteio)) if n == s]
            acertos = [jogo[i] for i in acertos_posicoes]
            rotulos = [rotulo_premio(loteria_type, len(acertos))]
        elif loteria_type == 'dupla_sena' and segundo_sorteio:
            # Dupla Sena: o mesmo jogo concorre nos 2 sorteios e pode ser premiado em ambos
            acertos_1 = sorted(set(jogo) & set_sorteio)
            acertos_2 = sorted(set(jogo) & set(segundo_sorteio))
            rotulos = [rotulo_premio(loteria_type, len(acertos_1), 1), rotulo_premio(loteria_type, len(acertos_2), 2)]
            acertos = acertos_2 if len(acertos_2) > len(acertos_1) else acertos_1
        else:
            acertos = sorted(set(jogo) & set_sorteio)
            if loteria_type == 'mais_milionaria' and trevos_sorteio and trevos_jogos and idx <= len(trevos_jogos):
                trevos_acertados = len(set(trevos_jogos[idx - 1] or []) & set(trevos_sorteio))
            rotulos = [rotulo_premio(loteria_type, len(acertos), trevos_acertados=trevos_acertados)]

        # Timemania e Dia de Sorte: acertar o Time do Coração / Mês da Sorte também é prêmio
        acertou_complemento = None
        if loteria_type in ROTULO_COMPLEMENTO and complemento_sorteio and complementos_jogos and idx <= len(complementos_jogos):
            escolhido = complementos_jogos[idx - 1]
            if escolhido:
                acertou_complemento = normalizar_complemento(escolhido) == normalizar_complemento(complemento_sorteio)
                if acertou_complemento:
                    rotulos.append(ROTULO_COMPLEMENTO[loteria_type])

        rotulos = [r for r in rotulos if r]
        for r in rotulos:
            premiacoes[r] = premiacoes.get(r, 0) + 1

        resultado.append({
            'numero': idx,
            'jogo': jogo,
            'acertos': acertos,
            'qtd_acertos': len(acertos),
            'acertos_posicoes': acertos_posicoes,
            'trevos': trevos_jogos[idx - 1] if (trevos_jogos and idx <= len(trevos_jogos)) else [],
            'trevos_acertados': trevos_acertados,
            'complemento': complementos_jogos[idx - 1] if (complementos_jogos and idx <= len(complementos_jogos)) else None,
            'acertou_complemento': acertou_complemento,
            'rotulo_premio': ' + '.join(rotulos) or None,
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

    jogos, premiacoes = conferir_jogos(loteria_type, aposta.get('jogos', []), sorteio['dezenas'], sorteio['segundo_sorteio'],
                                       sorteio.get('trevos'), aposta.get('trevos'),
                                       sorteio.get('complemento'), aposta.get('complementos'))
    return {
        'status': 'conferido',
        'concurso': sorteio['concurso'],
        'jogos_premiados': sum(1 for j in jogos if j['rotulo_premio']),
        'melhor_acerto': max((j['qtd_acertos'] for j in jogos), default=0),
        'premiacoes': premiacoes,
    }

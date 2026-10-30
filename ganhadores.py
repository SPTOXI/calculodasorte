"""
Ganhadores do prêmio principal por cidade/UF.

Guarda, por loteria, a cidade e a UF dos ganhadores da faixa principal de cada concurso
(`data/<loteria>_ganhadores.json`) e agrega os dados para as páginas /ganhadores.
Aceita os dois formatos de API usados no updater: Caixa (`listaMunicipioUFGanhadores`)
e loteriascaixa-api (`localGanhadores`).
"""

import json
import os
import re
import unicodedata
from collections import defaultdict
from typing import Any, Dict, List, Optional

import updater

UFS = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 'CE': 'Ceará',
    'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 'MA': 'Maranhão',
    'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 'PA': 'Pará',
    'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí', 'RJ': 'Rio de Janeiro',
    'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima',
    'SC': 'Santa Catarina', 'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins',
}

_CACHE: Dict[str, Dict[str, Any]] = {}


def slugify(texto: str) -> str:
    texto = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', texto.lower()).strip('-')


def _nome_cidade(municipio: str) -> str:
    """'SAO JOSE DOS CAMPOS' -> 'Sao Jose Dos Campos' com preposições em minúsculas."""
    palavras = (municipio or '').strip().title().split()
    return ' '.join(p.lower() if i and p.lower() in ('de', 'da', 'do', 'das', 'dos', 'e') else p
                    for i, p in enumerate(palavras))


def extrair_ganhadores(dados: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Ganhadores do prêmio principal de um concurso: [{municipio, uf, ganhadores}].
    Lista vazia = ninguém ganhou (ou só canal eletrônico sem cidade). None = dado ausente."""
    if not dados:
        return None
    if 'listaMunicipioUFGanhadores' in dados:
        brutos = dados.get('listaMunicipioUFGanhadores') or []
        itens = [{'municipio': b.get('municipio'), 'uf': b.get('uf'),
                  'ganhadores': b.get('ganhadores') or 1} for b in brutos]
    elif 'localGanhadores' in dados:
        itens = [{'municipio': b.get('municipio'), 'uf': b.get('uf'),
                  'ganhadores': b.get('ganhadores') or 1} for b in dados.get('localGanhadores') or []]
    else:
        return None
    saida = []
    for it in itens:
        uf = (it['uf'] or '').strip().upper()
        municipio = (it['municipio'] or '').strip()
        if uf not in UFS or not municipio:
            uf, municipio = '--', 'CANAL ELETRONICO'
        saida.append({'municipio': municipio.upper(), 'uf': uf, 'ganhadores': int(it['ganhadores'])})
    return saida


def _caminho(loteria: str, pasta: str) -> str:
    return os.path.join(pasta, f'{loteria}_ganhadores.json')


def carregar(loteria: str) -> Dict[str, Dict[str, Any]]:
    """{concurso(str): {'data': 'dd/mm/aaaa', 'locais': [...]}}"""
    for pasta in (updater.DATA_DIR, updater.ORIGINAL_DATA_DIR):
        path = _caminho(loteria, pasta)
        if os.path.exists(path):
            try:
                with open(path, encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, ValueError):
                pass
    return {}


def salvar(loteria: str, registros: Dict[str, Dict[str, Any]]):
    os.makedirs(updater.DATA_DIR, exist_ok=True)
    ordenado = dict(sorted(registros.items(), key=lambda kv: int(kv[0])))
    with open(_caminho(loteria, updater.DATA_DIR), 'w', encoding='utf-8') as f:
        json.dump(ordenado, f, ensure_ascii=False, separators=(',', ':'))
    _CACHE.pop(loteria, None)


def registrar(loteria: str, dados: Dict[str, Any]) -> bool:
    """Grava os ganhadores de um resultado da API, se ainda não estiverem salvos."""
    numero = (dados or {}).get('numero') or (dados or {}).get('concurso')
    locais = extrair_ganhadores(dados)
    if not numero or locais is None:
        return False
    registros = carregar(loteria)
    if str(numero) in registros:
        return False
    registros[str(numero)] = {'data': dados.get('dataApuracao') or dados.get('data'), 'locais': locais}
    salvar(loteria, registros)
    return True


def agregados(loteria: str) -> Dict[str, Any]:
    """Ganhadores agrupados por UF e cidade, com os concursos de cada cidade."""
    if loteria in _CACHE:
        return _CACHE[loteria]
    ufs: Dict[str, Dict[str, Any]] = {}
    canal = 0
    total = 0
    for concurso, reg in carregar(loteria).items():
        for loc in reg.get('locais') or []:
            total += loc['ganhadores']
            if loc['uf'] == '--':
                canal += loc['ganhadores']
                continue
            uf = ufs.setdefault(loc['uf'], {'uf': loc['uf'], 'nome': UFS[loc['uf']], 'slug': loc['uf'].lower(),
                                            'ganhadores': 0, 'cidades': {}})
            uf['ganhadores'] += loc['ganhadores']
            slug = slugify(loc['municipio'])
            cidade = uf['cidades'].setdefault(slug, {'slug': slug, 'nome': _nome_cidade(loc['municipio']),
                                                     'ganhadores': 0, 'concursos': []})
            cidade['ganhadores'] += loc['ganhadores']
            cidade['concursos'].append({'concurso': int(concurso), 'data': reg.get('data'),
                                        'ganhadores': loc['ganhadores']})
    for uf in ufs.values():
        for c in uf['cidades'].values():
            c['concursos'].sort(key=lambda x: -x['concurso'])
    resultado = {'ufs': ufs, 'canal_eletronico': canal, 'total': total,
                 'concursos_registrados': len(carregar(loteria))}
    _CACHE[loteria] = resultado
    return resultado


def backfill(loteria: str) -> Dict[str, int]:
    """Preenche o histórico de ganhadores com a lista completa da loteriascaixa-api."""
    slug = updater.LOTERIAS_SLUGS[loteria]
    lista = updater._baixar_lista_completa(slug)
    if not lista:
        return {'adicionados': 0, 'erro': 1}
    registros = carregar(loteria)
    adicionados = 0
    for dados in lista:
        numero = dados.get('concurso') or dados.get('numero')
        locais = extrair_ganhadores(dados)
        if not numero or locais is None or str(numero) in registros:
            continue
        registros[str(numero)] = {'data': dados.get('data') or dados.get('dataApuracao'), 'locais': locais}
        adicionados += 1
    if adicionados:
        salvar(loteria, registros)
    return {'adicionados': adicionados, 'total': len(registros)}


if __name__ == '__main__':
    # python ganhadores.py  -> backfill de todas as loterias em data/
    for lot in updater.LOTERIAS_SLUGS:
        print(lot, backfill(lot))

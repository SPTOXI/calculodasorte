"""
Bolões: precificação e regras de configuração (etapa 1).

Valor da cota = (custo oficial dos jogos na Caixa + taxa de serviço) / total de cotas

A taxa de serviço é definida exclusivamente pelo administrador (system_settings
'bolao_config'); o organizador só escolhe jogos e número de cotas.
Todos os valores usam Decimal e a cota é arredondada PARA CIMA em centavos,
para que a soma das cotas nunca fique abaixo do custo total.
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP
from math import comb
from typing import Dict, List, Optional

from core import LoteriaConfig

CENTAVO = Decimal('0.01')

STATUS_BOLAO = ('aberto', 'fechado', 'registrado', 'premiado', 'nao_premiado', 'cancelado')
STATUS_COTA = ('disponivel', 'reservada', 'paga', 'estornada')
TIPOS_TAXA = ('percentual', 'fixa')

CONFIG_PADRAO = {
    'ativo': False,               # módulo desligado até o admin liberar
    'taxa_tipo': 'percentual',
    'taxa_valor': '20.00',        # 20% sobre o custo dos jogos, ou R$ se 'fixa'
    'min_cotas': 2,
    'max_cotas': 100,
    'horas_comprovante': 3,       # comprovante até X horas antes do sorteio
    'minutos_reserva': 15,        # tempo de reserva da cota no checkout
}


def _dec(valor) -> Decimal:
    return Decimal(str(valor))


def custo_jogo(config: LoteriaConfig, dezenas: int) -> Decimal:
    """Custo oficial (tabela Caixa) de um jogo com `dezenas` números."""
    return comb(dezenas, config.minimo_aposta) * _dec(config.custo_minimo)


def custo_jogos(config: LoteriaConfig, jogos: List[List[int]]) -> Decimal:
    return sum((custo_jogo(config, len(j)) for j in jogos), Decimal('0')).quantize(CENTAVO)


def normalizar_config(dados: Optional[dict]) -> dict:
    """Mescla com os padrões e valida; levanta ValueError com mensagem amigável."""
    cfg = dict(CONFIG_PADRAO)
    cfg.update({k: v for k, v in (dados or {}).items() if k in CONFIG_PADRAO})

    cfg['ativo'] = bool(cfg['ativo'])
    if cfg['taxa_tipo'] not in TIPOS_TAXA:
        raise ValueError('Tipo de taxa inválido.')
    try:
        taxa = _dec(cfg['taxa_valor'])
        min_cotas, max_cotas = int(cfg['min_cotas']), int(cfg['max_cotas'])
        horas, minutos = int(cfg['horas_comprovante']), int(cfg['minutos_reserva'])
    except Exception:
        raise ValueError('Valores numéricos inválidos.')
    if taxa < 0 or (cfg['taxa_tipo'] == 'percentual' and taxa > 100):
        raise ValueError('Taxa deve estar entre 0 e 100%.' if cfg['taxa_tipo'] == 'percentual' else 'Taxa não pode ser negativa.')
    if not 1 <= min_cotas <= max_cotas:
        raise ValueError('Faixa de cotas inválida.')
    if horas < 0 or minutos < 1:
        raise ValueError('Prazos inválidos.')

    cfg.update(taxa_valor=str(taxa.quantize(CENTAVO)), min_cotas=min_cotas, max_cotas=max_cotas,
               horas_comprovante=horas, minutos_reserva=minutos)
    return cfg


def carregar_config(raw: Optional[str]) -> dict:
    try:
        return normalizar_config(json.loads(raw) if raw else None)
    except (ValueError, TypeError):
        return dict(CONFIG_PADRAO)


def calcular_taxa(custo: Decimal, taxa_tipo: str, taxa_valor) -> Decimal:
    taxa_valor = _dec(taxa_valor)
    if taxa_tipo == 'percentual':
        return (custo * taxa_valor / 100).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return taxa_valor.quantize(CENTAVO)


def calcular_precos(config: LoteriaConfig, jogos: List[List[int]], total_cotas: int, cfg: dict) -> Dict:
    """Calcula custo, taxa e valor da cota de um bolão a partir da configuração do admin."""
    if not jogos:
        raise ValueError('O bolão precisa de pelo menos um jogo.')
    for j in jogos:
        if not config.minimo_aposta <= len(j) <= config.maximo_aposta:
            raise ValueError(f'Jogo com {len(j)} números fora do permitido para {config.nome}.')
    if not cfg['min_cotas'] <= total_cotas <= cfg['max_cotas']:
        raise ValueError(f"O número de cotas deve ficar entre {cfg['min_cotas']} e {cfg['max_cotas']}.")

    custo = custo_jogos(config, jogos)
    taxa = calcular_taxa(custo, cfg['taxa_tipo'], cfg['taxa_valor'])
    total = custo + taxa
    valor_cota = (total / total_cotas).quantize(CENTAVO, rounding=ROUND_CEILING)
    return {
        'custo_caixa': custo,
        'taxa_tipo': cfg['taxa_tipo'],
        'taxa_valor': _dec(cfg['taxa_valor']),
        'taxa_servico': taxa,
        'custo_total': total,
        'total_cotas': total_cotas,
        'valor_cota': valor_cota,
        'arrecadacao_maxima': valor_cota * total_cotas,
        'sobra_arredondamento': valor_cota * total_cotas - total,
    }


def precos_para_json(precos: Dict) -> Dict:
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in precos.items()}


# Super Sete (colunas) e +Milionária (trevos alteram o preço) ficam para uma etapa futura
LOTERIAS_SUPORTADAS = ('mega_sena', 'lotofacil', 'quina', 'lotomania', 'dupla_sena', 'timemania', 'dia_de_sorte')
PAPEIS_ORGANIZADOR = ('admin', 'organizador')


def pode_organizar(user: Optional[dict], cfg: dict) -> bool:
    """Admin sempre pode (inclusive para testar com o módulo desligado); organizador só com o módulo ativo."""
    if not user or user.get('is_blocked'):
        return False
    if user.get('role') == 'admin':
        return True
    return user.get('role') == 'organizador' and cfg['ativo']


def validar_jogos(config: LoteriaConfig, jogos) -> List[List[int]]:
    """Confere formato, tamanho e faixa de cada jogo; devolve os jogos ordenados."""
    if not isinstance(jogos, list) or not jogos:
        raise ValueError('O bolão precisa de pelo menos um jogo.')
    validos = []
    for jogo in jogos:
        if not isinstance(jogo, list) or not all(isinstance(n, int) and not isinstance(n, bool) for n in jogo):
            raise ValueError('Jogo em formato inválido.')
        if len(set(jogo)) != len(jogo):
            raise ValueError('Jogo com números repetidos.')
        if any(n < config.numero_inicial or n > config.numero_final for n in jogo):
            raise ValueError(f'Número fora do volante da {config.nome}.')
        validos.append(sorted(jogo))
    return validos



# ---------- Etapa 4: comprovante, prazos e rateio ----------

# Os sorteios da Caixa acontecem às 20h de Brasília (23h UTC); prazos são gravados em UTC
HORA_SORTEIO_UTC = 23
TAMANHO_MAX_COMPROVANTE = 4 * 1024 * 1024  # o corpo de requisição da Vercel é limitado a ~4,5 MB
TIPOS_COMPROVANTE = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'%PDF-': 'application/pdf',
}


def data_do_sorteio(dados_ultimo_resultado: Optional[dict], concurso: int) -> Optional[datetime]:
    """Data/hora (UTC) do sorteio do concurso, quando a Caixa já a divulgou (só para o próximo concurso)."""
    if not dados_ultimo_resultado or dados_ultimo_resultado.get('numero') != concurso - 1:
        return None
    try:
        dia = datetime.strptime(dados_ultimo_resultado.get('dataProximoConcurso') or '', '%d/%m/%Y')
    except ValueError:
        return None
    return dia.replace(hour=HORA_SORTEIO_UTC)


def calcular_prazo_comprovante(sorteio_utc: Optional[datetime], horas_antes: int) -> Optional[datetime]:
    return sorteio_utc - timedelta(hours=horas_antes) if sorteio_utc else None


def tipo_do_comprovante(conteudo: bytes) -> Optional[str]:
    """Identifica o arquivo pelos primeiros bytes (a extensão e o Content-Type do navegador não são confiáveis)."""
    for assinatura, mime in TIPOS_COMPROVANTE.items():
        if conteudo.startswith(assinatura):
            return mime
    return None


def rateio_por_cota(valor_premio, total_cotas: int) -> Decimal:
    """Divide o prêmio líquido recebido igualmente entre as cotas, arredondando para baixo (sobra fica registrada)."""
    if total_cotas <= 0:
        raise ValueError('Total de cotas inválido.')
    valor = _dec(valor_premio)
    if valor < 0:
        raise ValueError('Valor do prêmio não pode ser negativo.')
    return (valor / total_cotas).quantize(CENTAVO, rounding=ROUND_DOWN)

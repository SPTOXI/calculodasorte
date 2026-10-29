"""
Aplicação Web Flask para Análise Estatística de Loterias
Baseada no Modelo Canônico 4.0 + MCP-MD 1.0 (Otimização Hexagonal e Cobertura Espacial)
Com Painel Administrativo, Gestão de Usuários e Atualizador Diário Caixa
"""

from functools import wraps
import hashlib
import json
import os
import uuid
import re
from math import comb
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, send_from_directory
from werkzeug.security import check_password_hash

import requests
import database
import updater
import ai_agent
import avaliacao
import bolao
import boloes_rotina
import conferencia
import fechamento
import importador
from core import (
    proximo_sorteio,
    ModeloCanonico40,
    ModeloCanonico30,
    ValidaçãoCamada7,
    gerar_jogo_sugerido,
    gerar_jogo_dinamico_ajustado,
    gerar_multiplos_jogos,
    analise_por_coluna,
    LoteriaType,
    LoteriaConfig,
    LOTERIAS_CONFIG
)

def _carregar_env():
    """Carrega variáveis do arquivo .env local se existir"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and v:
                            os.environ[k] = v
        except Exception:
            pass

_carregar_env()

import secrets
import time
from collections import defaultdict

app = Flask(__name__)

# Configuração Criptográfica de Sessão (Proteção contra falsificação de cookies)
PRECO_ANALISE = 1.00
PRECO_AVULSO = 5.00
PRECO_MENSAL = 49.90
secret_from_env = os.getenv('SECRET_KEY')
if not secret_from_env:
    # Chave aleatória por processo: sessões não sobrevivem a reinícios, mas nunca ficam forjáveis.
    print("[SEGURANÇA] SECRET_KEY não definida no ambiente! Usando chave temporária aleatória; defina SECRET_KEY em produção.")
    secret_from_env = secrets.token_hex(32)
app.config['SECRET_KEY'] = secret_from_env
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

_NOMES_LOTERIAS = {t.value: c.nome for t, c in LOTERIAS_CONFIG.items()}


@app.template_filter('data_brt')
def formatar_data_brt(valor) -> str:
    """Prazos são gravados em UTC; exibe em horário de Brasília (UTC-3, sem horário de verão)."""
    return (valor - timedelta(hours=3)).strftime('%d/%m/%Y %H:%M') if valor else ''


@app.template_filter('brl')
def formatar_brl(valor) -> str:
    """1234.5 -> 'R$ 1.234,50'"""
    return 'R$ ' + f'{float(valor or 0):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

# Inicializar Banco de Dados e Agendador de Loterias
database.init_db()
updater.iniciar_agendador()

# Diretório para armazenar dados
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)


# ==========================================
# ==========================================
# SEO & GEO GLOBALS (Redirects, Robots, LLMs)
# ==========================================

@app.before_request
def enforce_canonical_domain():
    # Only redirect in production if the host is calculodasorte.com.br or calculadoradasorte.com.br
    # Avoid breaking localhost, 127.0.0.1 or Vercel preview domains
    host = request.headers.get('Host', '').split(':')[0].lower()
    if host in ('calculodasorte.com.br', 'calculadoradasorte.com.br', 'www.calculadoradasorte.com.br'):
        return redirect(f"https://www.calculodasorte.com.br{request.full_path.rstrip('?')}", code=301)
    # Redirect http to https for www.calculodasorte.com.br if behind proxy (X-Forwarded-Proto)
    proto = request.headers.get('X-Forwarded-Proto', 'http')
    if host == 'www.calculodasorte.com.br' and proto == 'http':
        return redirect(f"https://www.calculodasorte.com.br{request.full_path.rstrip('?')}", code=301)

@app.route('/robots.txt')
def robots_txt():
    content = """User-agent: GPTBot
User-agent: OAI-SearchBot
User-agent: ChatGPT-User
User-agent: ClaudeBot
User-agent: Claude-SearchBot
User-agent: Claude-User
User-agent: PerplexityBot
User-agent: Perplexity-User
User-agent: Google-Extended
User-agent: Applebot-Extended
User-agent: Bingbot
Allow: /
Disallow: /login
Disallow: /cadastro
Disallow: /painel
Disallow: /api

User-agent: *
Allow: /
Disallow: /login
Disallow: /cadastro
Disallow: /painel
Disallow: /api
Disallow: /*?plano=*

Sitemap: https://www.calculodasorte.com.br/sitemap.xml
"""
    return Response(content, mimetype='text/plain')

from flask import make_response

@app.route('/sitemap.xml')
def sitemap_index():
    host = "https://www.calculodasorte.com.br"
    hoje = datetime.now().strftime('%Y-%m-%d')
    loterias = [k.value for k in LOTERIAS_CONFIG.keys()]
    
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    sitemaps = [
        'sitemap-paginas.xml',
        'sitemap-ferramentas.xml',
        'sitemap-estatisticas.xml',
        'sitemap-blog.xml'
    ]
    for loteria in loterias:
        sitemaps.append(f'sitemap-concursos-{loteria.replace("_", "-")}.xml')
        
    for sm in sitemaps:
        parts.append('  <sitemap>')
        parts.append(f'    <loc>{host}/{sm}</loc>')
        parts.append(f'    <lastmod>{hoje}</lastmod>')
        parts.append('  </sitemap>')
        
    parts.append('</sitemapindex>')
    xml = "\n".join(parts)
    
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/sitemap-paginas.xml')
def sitemap_paginas():
    host = "https://www.calculodasorte.com.br"
    hoje = datetime.now().strftime('%Y-%m-%d')
    urls = [
        '/', '/resultados', '/sobre', '/metodologia', '/autor/silvio-morais', '/planos', '/privacidade', '/termos'
    ]
    
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for url in urls:
        parts.append('  <url>')
        parts.append(f'    <loc>{host}{url}</loc>')
        parts.append(f'    <lastmod>{hoje}</lastmod>')
        parts.append('  </url>')
    
    for loteria_enum in LOTERIAS_CONFIG.keys():
        slug = loteria_enum.value.replace('_', '-')
        parts.append('  <url>')
        parts.append(f'    <loc>{host}/{slug}</loc>')
        parts.append(f'    <lastmod>{hoje}</lastmod>')
        parts.append('  </url>')
        parts.append('  <url>')
        parts.append(f'    <loc>{host}/resultados/{slug}</loc>')
        parts.append(f'    <lastmod>{hoje}</lastmod>')
        parts.append('  </url>')
        
    parts.append('</urlset>')
    xml = "\n".join(parts)
    
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

def ferramentas_da_loteria(loteria_key):
    """Lista de slugs de ferramentas válidas para uma loteria (chave enum, ex: 'mega_sena').
    Usada pelo sitemap para anunciar exatamente as URLs que o blueprint seo_routes atende."""
    ferramentas = ['simulador', 'probabilidade']
    if loteria_key in ['mega_sena', 'quina', 'lotofacil', 'dupla_sena', 'dia_de_sorte', 'timemania']:
        ferramentas.append('fechamento')
        if loteria_key == 'lotofacil':
            ferramentas.extend(['fechamento-18-dezenas', 'fechamento-20-dezenas', 'fechamento-24-dezenas', 'desdobramento'])
        if loteria_key == 'mega_sena':
            ferramentas.append('desdobramento')
    return ferramentas


ESTATISTICAS_SLUGS = ['numeros-mais-sorteados', 'numeros-atrasados']


@app.route('/sitemap-ferramentas.xml')
def sitemap_ferramentas():
    host = "https://www.calculodasorte.com.br"
    hoje = datetime.now().strftime('%Y-%m-%d')

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    for loteria_enum in LOTERIAS_CONFIG.keys():
        loteria = loteria_enum.value
        slug = loteria.replace('_', '-')
        for fer in ferramentas_da_loteria(loteria):
            parts.append('  <url>')
            parts.append(f'    <loc>{host}/{slug}/{fer}</loc>')
            parts.append(f'    <lastmod>{hoje}</lastmod>')
            parts.append('  </url>')

    parts.append('</urlset>')
    xml = "\n".join(parts)

    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/sitemap-estatisticas.xml')
def sitemap_estatisticas():
    host = "https://www.calculodasorte.com.br"
    hoje = datetime.now().strftime('%Y-%m-%d')

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    for loteria_enum in LOTERIAS_CONFIG.keys():
        slug = loteria_enum.value.replace('_', '-')
        for stat in ESTATISTICAS_SLUGS:
            parts.append('  <url>')
            parts.append(f'    <loc>{host}/{slug}/{stat}</loc>')
            parts.append(f'    <lastmod>{hoje}</lastmod>')
            parts.append('  </url>')

    parts.append('</urlset>')
    xml = "\n".join(parts)

    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/sitemap-blog.xml')
def sitemap_blog():
    host = "https://www.calculodasorte.com.br"
    hoje = datetime.now().strftime('%Y-%m-%d')

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    parts.append('  <url>')
    parts.append(f'    <loc>{host}/blog</loc>')
    parts.append(f'    <lastmod>{hoje}</lastmod>')
    parts.append('  </url>')
    for slug, post in BLOG_POSTS.items():
        if post.get('redirect_only') or post.get('canonical_slug'):
            continue
        parts.append('  <url>')
        parts.append(f'    <loc>{host}/blog/{slug}</loc>')
        parts.append(f'    <lastmod>{post.get("date", hoje)}</lastmod>')
        parts.append('  </url>')
    for loteria_enum in LOTERIAS_CONFIG.keys():
        slug_canonico = loteria_enum.value.replace('_', '-')
        post = _gerar_post_acumulado(slug_canonico)
        if post:
            parts.append('  <url>')
            parts.append(f'    <loc>{host}/blog/concurso-acumulado-{slug_canonico}</loc>')
            parts.append(f'    <lastmod>{hoje}</lastmod>')
            parts.append('  </url>')

    parts.append('</urlset>')
    xml = "\n".join(parts)

    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/sitemap-concursos-<loteria_slug>.xml')
def sitemap_concursos(loteria_slug):
    loteria_key = loteria_slug.replace('-', '_')
    valid = False
    for k in LOTERIAS_CONFIG.keys():
        if k.value == loteria_key:
            valid = True
            break
    if not valid:
        return "Not found", 404
        
    host = "https://www.calculodasorte.com.br"
    historico = updater.carregar_historico_local(loteria_key)
    meta = updater.carregar_meta(loteria_key)
    ultimo_concurso = meta.get('ultimo_concurso') or len(historico)
    
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    lastmod = datetime.now().strftime('%Y-%m-%d')
    if historico and ultimo_concurso:
        primeiro = max(1, ultimo_concurso - len(historico) + 1)
        for numero in range(primeiro, ultimo_concurso + 1):
            parts.append('  <url>')
            parts.append(f'    <loc>{host}/{loteria_slug}/concurso/{numero}</loc>')
            parts.append(f'    <lastmod>{lastmod}</lastmod>')
            parts.append('  </url>')
    else:
        for i in range(len(historico)):
            numero = i + 1
            parts.append('  <url>')
            parts.append(f'    <loc>{host}/{loteria_slug}/concurso/{numero}</loc>')
            parts.append(f'    <lastmod>{lastmod}</lastmod>')
            parts.append('  </url>')
        
    parts.append('</urlset>')
    xml = "\n".join(parts)
    
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route('/llms-full.txt')
def llms_full_txt():
    content = """# Cálculo da Sorte - Full Document
Ferramentas estatísticas e fechamentos.

## Metodologia
Todas as tabelas usam a fórmula C(n,k) = n! / (k!(n-k)!). As combinações não garantem vitórias incondicionais, mas cobrem faixas específicas caso os números sorteados estejam no grupo escolhido.

## Hubs e Ferramentas
- Mega-Sena: 1 em 50 milhões (6 dezenas). Ferramentas de desdobramento disponíveis.
- Lotofácil: 1 em 3.2 milhões (15 dezenas). Fechamentos otimizados (18, 20, 24 dezenas) reduzem drasticamente o custo do desdobramento completo.

## Dúvidas Comuns
O fechamento elimina combinações redundantes de um desdobramento completo, economizando dinheiro ao abrir mão da garantia do prêmio máximo (que fica sujeita à sorte), garantindo prêmios menores se as condições matemáticas (acertar as dezenas) forem atingidas.
"""
    return Response(content, mimetype='text/plain')

@app.route('/llms.txt')
def llms_txt():
    content = """# Cálculo da Sorte
Ferramentas estatísticas, desdobramentos, fechamentos e análise histórica para as loterias da Caixa Econômica Federal.
Este serviço organiza dados matemáticos e oficiais. NÃO fazemos apostas, NÃO garantimos ganhos, apenas fornecemos ferramentas analíticas.

## Ferramentas grátis
- [Mega-Sena](/mega-sena): Simulador, resultados e estatísticas da Mega-Sena.
- [Lotofácil](/lotofacil): Fechamentos e análises da Lotofácil.
- [Quina](/quina): Ferramentas gratuitas para Quina.
- [Lotomania](/lotomania): Ferramentas gratuitas para Lotomania.
- [Super Sete](/super-sete): Ferramentas gratuitas para Super Sete.
- [Dupla Sena](/dupla-sena): Ferramentas gratuitas para Dupla Sena.
- [Timemania](/timemania): Ferramentas gratuitas para Timemania.
- [Dia de Sorte](/dia-de-sorte): Ferramentas gratuitas para Dia de Sorte.
- [+Milionária](/mais-milionaria): Ferramentas gratuitas para +Milionária.

## Resultados Oficiais
- [Central de Resultados](/resultados): Resultados mais recentes das 9 loterias da Caixa.

## Estatísticas
- [/lotofacil/numeros-mais-sorteados](/lotofacil/numeros-mais-sorteados): Números que mais saem na Lotofácil.

## Metodologia
- [/metodologia](/metodologia): Como calculamos nossas probabilidades (fórmulas exatas, C(n,k)).
"""
    return Response(content, mimetype='text/plain')

# ==========================================
# CABEÇALHOS DE SEGURANÇA E RATE LIMITING
# ==========================================

@app.after_request
def aplicar_cabecalhos_seguranca(response):
    """Aplica cabeçalhos HTTP defensivos para mitigar ataques comuns (XSS, Clickjacking, MIME-sniffing)"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


# Rate Limiter em memória para proteção contra ataques de força bruta, flood e DoS
_rate_limits = defaultdict(list)

def rate_limit(max_requests: int = 15, window_seconds: int = 60, by_ip: bool = True):
    """
    Decorator de Rate Limiting leve em memória para prevenir abusos, scraping agressivo e força bruta.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if by_ip:
                client_id = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
            else:
                client_id = str(session.get('user_id') or request.remote_addr or 'anon')

            key = f"{f.__name__}:{client_id}"
            now = time.time()

            _rate_limits[key] = [t for t in _rate_limits[key] if now - t < window_seconds]

            if len(_rate_limits[key]) >= max_requests:
                if request.path.startswith('/api/'):
                    return jsonify({
                        'erro': 'Muitas requisições. Por favor, aguarde alguns instantes antes de tentar novamente.',
                        'rate_limited': True
                    }), 429
                return render_template('login.html', erro='Muitas tentativas. Aguarde 1 minuto.'), 429

            _rate_limits[key].append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ==========================================
# DECORATORS DE AUTENTICAÇÃO E PERMISSÃO
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({
                    'sucesso': False,
                    'erro': 'Autenticação necessária. Por favor, faça login para continuar.',
                    'requer_login': True
                }), 401
            return redirect(url_for('login', next=request.url))
        user = database.get_user_by_id(session['user_id'])
        if not user or user['is_blocked']:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({
                    'sucesso': False,
                    'erro': 'Sessão expirada ou usuário bloqueado.',
                    'requer_login': True
                }), 401
            return redirect(url_for('login', erro='Sessão expirada ou usuário bloqueado.'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({
                    'sucesso': False,
                    'erro': 'Autenticação necessária',
                    'requer_login': True
                }), 401
            return redirect(url_for('login', next=request.url))
        user = database.get_user_by_id(session['user_id'])
        if not user or user['is_blocked']:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Usuário bloqueado'}), 403
            return redirect(url_for('login', erro='Usuário bloqueado.'))
        if user['role'] != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'sucesso': False, 'erro': 'Acesso exclusivo para administradores'}), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# MANIPULADORES GLOBAIS DE ERRO (PREVENÇÃO DE HTML EM APIS)
# ==========================================

@app.errorhandler(401)
def erro_401_unauthorized(e):
    if request.path.startswith('/api/'):
        return jsonify({
            'sucesso': False,
            'erro': 'Autenticação necessária. Por favor, faça login para continuar.',
            'requer_login': True
        }), 401
    return redirect(url_for('login', next=request.url))


@app.errorhandler(404)
def erro_404_not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Recurso ou rota não encontrada.'}), 404
    return ("Página não encontrada (404)", 404)


@app.errorhandler(500)
def erro_500_internal(e):
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'erro': 'Erro interno do servidor. Tente novamente mais tarde.'}), 500
    return ("Erro interno do servidor (500)", 500)


@app.errorhandler(Exception)
def erro_global_exception(e):
    if request.path.startswith('/api/'):
        print(f"[API ERROR] Exceção em {request.path}: {e}")
        return jsonify({'sucesso': False, 'erro': f'Erro no processamento: {str(e)}'}), 500
    raise e


# ==========================================
# FUNÇÕES DE PERSISTÊNCIA DE HISTÓRICO
# ==========================================

def carregar_historico(loteria_type: str) -> list:
    """Carregar histórico de concursos do arquivo JSON"""
    return updater.carregar_historico_local(loteria_type)


def opcoes_complemento(loteria_type: str) -> list:
    """Times do Coração (Timemania) oficiais/cadastrados ou vistos nos resultados, ou os 12 meses (Dia de Sorte)."""
    if loteria_type == 'dia_de_sorte':
        return list(conferencia.MESES)
    if loteria_type == 'timemania':
        vistos = {}
        # 1. Carregar catálogo oficial de clubes da Timemania (80/82 clubes)
        caminho_clubes = os.path.join(DATA_DIR, 'timemania_clubes.json')
        if os.path.exists(caminho_clubes):
            try:
                with open(caminho_clubes, 'r', encoding='utf-8') as f:
                    clubes_oficiais = json.load(f)
                    for c in clubes_oficiais:
                        if c:
                            nome = ' '.join(c.split()).replace(' /', '/')
                            vistos[conferencia.normalizar_complemento(nome)] = nome
            except Exception:
                pass
        # 2. Mesclar com histórico de times sorteados localmente
        for t in updater.carregar_times_local('timemania'):
            if t:
                nome = ' '.join(t.split()).replace(' /', '/')
                vistos[conferencia.normalizar_complemento(nome)] = nome
        return sorted(vistos.values())
    return []


def carregar_historico_analise(loteria_type: str) -> list:
    """Histórico para cálculos estatísticos: na Dupla Sena inclui os 2 sorteios de cada concurso."""
    if loteria_type == 'dupla_sena':
        return updater.historico_com_segundo_sorteio(loteria_type)
    return carregar_historico(loteria_type)


_MODELOS_CACHE = {}


def modelo_canonico(loteria_type: str):
    """Modelo Canônico 4.0 calculado sobre o histórico oficial, reaproveitado até entrar um novo concurso.
    Retorna None se houver menos de 10 concursos."""
    historico = carregar_historico_analise(loteria_type)
    if len(historico) < 10:
        return None
    # Uma correção em qualquer concurso também invalida as métricas memoizadas.
    chave = hashlib.sha256(json.dumps(
        historico, sort_keys=True, separators=(',', ':')
    ).encode('utf-8')).hexdigest()
    em_cache = _MODELOS_CACHE.get(loteria_type)
    if em_cache and em_cache[0] == chave:
        return em_cache[1]
    modelo = ModeloCanonico40(historico, LoteriaType(loteria_type))
    _MODELOS_CACHE[loteria_type] = (chave, modelo)
    return modelo


def salvar_historico(loteria_type: str, historico: list):
    """Salvar histórico de concursos no arquivo JSON"""
    updater.salvar_historico_local(loteria_type, historico)


# ==========================================
# ROTAS PÚBLICAS E PÁGINAS PRINCIPAIS
# ==========================================

@app.route('/')
def index():
    """Página inicial: Landing Page para visitantes, ou redireciona para dashboard se autenticado"""
    if 'user_id' in session:
        user = database.get_user_by_id(session['user_id'])
        if user and not user['is_blocked']:
            return redirect(url_for('dashboard'))
    agora = updater.agora_brasilia()
    proximos = {}
    for lt in LoteriaType:
        prox = proximo_sorteio(LOTERIAS_CONFIG[lt], agora)
        proximos[lt.value] = prox[1] if prox else ''
    return render_template('landing.html', proximos=proximos)


# Configuração sintética do universo dos "trevos" da +Milionária (1 a 6, 2 sorteados),
# usada para rodar o mesmo Modelo Canônico 4.0 sobre o segundo sorteio da loteria.
TREVO_CONFIG = LoteriaConfig(
    nome="Trevo da Sorte",
    universo=6,
    sorteados=2,
    minimo_aposta=2,
    maximo_aposta=2,
    custo_minimo=0.0,
    dias_sorteio=[],
    faixas_premiacao=[]
)


LOTERIAS_THEME = {
    'mega_sena': {
        'cor': '#209869',
        'cor_dark': '#135c3f',
        'cor_gradiente': 'linear-gradient(135deg, #209869 0%, #0d462f 100%)',
        'cor_glow': 'rgba(32, 152, 105, 0.45)',
        'icone': '🍀',
        'tag': 'Maior Prêmio da Caixa',
        'tag_bg': 'rgba(32, 152, 105, 0.12)',
        'tag_cor': '#135c3f',
        'dias_resumo': 'Ter, Qui, Dom',
        'seo_title': 'Gerador de Números e Fechamento Mega-Sena | Inteligência Artificial',
        'seo_desc': 'Use nosso simulador de fechamento para a Mega-Sena. Gere palpites matemáticos, veja os números que mais saem e utilize nossa IA para otimizar suas apostas.',
    },
    'lotofacil': {
        'cor': '#930089',
        'cor_dark': '#5c0055',
        'cor_gradiente': 'linear-gradient(135deg, #930089 0%, #4c0047 100%)',
        'cor_glow': 'rgba(147, 0, 137, 0.45)',
        'icone': '✨',
        'tag': 'A Mais Fácil de Ganhar',
        'tag_bg': 'rgba(147, 0, 137, 0.12)',
        'tag_cor': '#5c0055',
        'dias_resumo': 'Dom a Sex',
        'seo_title': 'Desdobramento e Simulador Lotofácil 15 a 20 números | Grátis',
        'seo_desc': 'Simulador de desdobramento Lotofácil com inteligência artificial. Gere combinações precisas baseadas nos padrões históricos para 14 e 15 pontos.',
    },
    'quina': {
        'cor': '#260085',
        'cor_dark': '#170052',
        'cor_gradiente': 'linear-gradient(135deg, #260085 0%, #11003d 100%)',
        'cor_glow': 'rgba(38, 0, 133, 0.45)',
        'icone': '⭐',
        'tag': 'Sorteio de Domingo a Sexta',
        'tag_bg': 'rgba(38, 0, 133, 0.12)',
        'tag_cor': '#170052',
        'dias_resumo': 'Dom a Sex',
    },
    'lotomania': {
        'cor': '#f78100',
        'cor_dark': '#9b5100',
        'cor_gradiente': 'linear-gradient(135deg, #f78100 0%, #874600 100%)',
        'cor_glow': 'rgba(247, 129, 0, 0.45)',
        'icone': '🎯',
        'tag': '50 Dezenas no Bilhete',
        'tag_bg': 'rgba(247, 129, 0, 0.14)',
        'tag_cor': '#9b5100',
        'dias_resumo': 'Seg, Qua, Sex',
    },
    'mais_milionaria': {
        'cor': '#c48208',
        'cor_dark': '#734c03',
        'cor_gradiente': 'linear-gradient(135deg, #c48208 0%, #614002 100%)',
        'cor_glow': 'rgba(196, 130, 8, 0.45)',
        'icone': '👑',
        'tag': 'Mínimo R$ 10 Milhões',
        'tag_bg': 'rgba(196, 130, 8, 0.14)',
        'tag_cor': '#734c03',
        'dias_resumo': 'Qua, Dom',
    },
    'dupla_sena': {
        'cor': '#a61322',
        'cor_dark': '#610a13',
        'cor_gradiente': 'linear-gradient(135deg, #a61322 0%, #4e070e 100%)',
        'cor_glow': 'rgba(166, 19, 34, 0.45)',
        'icone': '🎲',
        'tag': '2 Sorteios no Mesmo Jogo',
        'tag_bg': 'rgba(166, 19, 34, 0.12)',
        'tag_cor': '#610a13',
        'dias_resumo': 'Seg, Qua, Sex',
    },
    'timemania': {
        'cor': '#049645',
        'cor_dark': '#025225',
        'cor_gradiente': 'linear-gradient(135deg, #049645 0%, #013819 100%)',
        'cor_glow': 'rgba(4, 150, 69, 0.45)',
        'icone': '⚽',
        'tag': 'Seu Time do Coração',
        'tag_bg': 'rgba(4, 150, 69, 0.12)',
        'tag_cor': '#025225',
        'dias_resumo': 'Ter, Qui, Dom',
    },
    'dia_de_sorte': {
        'cor': '#cb852a',
        'cor_dark': '#754a14',
        'cor_gradiente': 'linear-gradient(135deg, #cb852a 0%, #5e3b0e 100%)',
        'cor_glow': 'rgba(203, 133, 42, 0.45)',
        'icone': '📅',
        'tag': 'Dias e Meses da Sorte',
        'tag_bg': 'rgba(203, 133, 42, 0.14)',
        'tag_cor': '#754a14',
        'dias_resumo': 'Dom a Sex',
    },
    'super_sete': {
        'cor': '#8bc53f',
        'cor_dark': '#4e7320',
        'cor_gradiente': 'linear-gradient(135deg, #8bc53f 0%, #3a5717 100%)',
        'cor_glow': 'rgba(139, 197, 63, 0.45)',
        'icone': '⚡',
        'tag': 'Colunas Premiadas',
        'tag_bg': 'rgba(139, 197, 63, 0.16)',
        'tag_cor': '#4e7320',
        'dias_resumo': 'Seg, Qua, Sex',
    },
}


@app.route('/dashboard')
@login_required
def dashboard():
    """Painel do apostador autenticado com seleção das 9 loterias e status da conta"""
    loterias = []
    for loteria, config in LOTERIAS_CONFIG.items():
        theme = LOTERIAS_THEME.get(loteria.value, {
            'cor': '#0046AD',
            'cor_dark': '#003380',
            'cor_gradiente': 'linear-gradient(135deg, #0046AD 0%, #003380 100%)',
            'cor_glow': 'rgba(0, 70, 173, 0.45)',
            'icone': '🎲',
            'tag': 'Oficial Caixa',
            'tag_bg': 'rgba(0, 70, 173, 0.12)',
            'tag_cor': '#003380',
            'dias_resumo': ', '.join(config.dias_sorteio)
        })
        loterias.append({
            'id': loteria.value,
            'nome': config.nome,
            'config': config,
            'theme': theme
        })
    current_user = database.get_user_by_id(session['user_id'])
    access = database.check_user_access(session['user_id'])
    return render_template('index.html', loterias=loterias, current_user=current_user, access=access)


@app.route('/analise/<loteria_type>')
@login_required
def analise_page(loteria_type: str):
    """Página de análise para uma loteria específica (Protegida por cadastro/login)"""
    try:
        loteria = LoteriaType(loteria_type)
        config = LOTERIAS_CONFIG[loteria]
    except ValueError:
        return redirect(url_for('dashboard'))
    
    current_user = database.get_user_by_id(session['user_id'])
    access = database.check_user_access(session['user_id'])
    
    return render_template(
        'analise.html', 
        loteria=loteria, 
        config=config, 
        current_user=current_user, 
        access=access
    )


@app.route('/planos')
def planos_page():
    """Página de seleção de planos e recargas PIX (Acessível publicamente para indexação nos buscadores)"""
    user_id = session.get('user_id')
    user = database.get_user_by_id(user_id) if user_id else None
    access = database.check_user_access(user_id) if user_id else None
    sucesso = request.args.get('sucesso')
    erro = request.args.get('erro')
    return render_template('planos.html', user=user, access=access, sucesso=sucesso, erro=erro)


# ==========================================
# ROTAS DE AUTENTICAÇÃO (CADASTRO / LOGIN / LOGOUT)
# ==========================================

@app.route('/cadastro', methods=['GET', 'POST'])
@rate_limit(max_requests=10, window_seconds=60)
def cadastro():
    """Auto-cadastro de novos apostadores (oferta de 1 análise por R$ 1,00)"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    plano_desejado = request.args.get('plano', 'free')
    erro = None
    nome = ''
    email = ''

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        plano_desejado = request.form.get('plano_desejado', 'free')
        termos_lgpd = request.form.get('termos_lgpd')

        if not nome:
            erro = 'Por favor, informe seu nome completo.'
        elif not email or '@' not in email:
            erro = 'Por favor, informe um endereço de e-mail válido.'
        elif len(password) < 4:
            erro = 'A senha deve conter pelo menos 4 caracteres.'
        elif password != confirm_password:
            erro = 'As senhas digitadas não coincidem.'
        elif not termos_lgpd:
            erro = 'Você deve concordar com os Termos de Uso e Política de Privacidade (LGPD) para se cadastrar.'
        elif database.get_user_by_email(email):
            erro = 'Este e-mail já está cadastrado. Faça login para continuar.'

        if not erro:
            try:
                user = database.create_user(
                    email=email,
                    password=password,
                    name=nome,
                    role='user',
                    plan='free',
                    credits=0, # Sem análise gratuita; oferta promocional de 1 real no cadastro
                    accepted_terms=True
                )
                session.permanent = True
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['user_role'] = user['role']
                session['user_name'] = user.get('name', nome)
                database.record_login(user['id'])

                if plano_desejado == 'vip':
                    return redirect(url_for('planos_page', sucesso='Conta criada com sucesso! Assine seu Plano VIP abaixo:'))
                elif plano_desejado == 'avulso':
                    return redirect(url_for('planos_page', sucesso='Conta criada com sucesso! Adquira seu Acesso de 24 Horas abaixo:'))
                elif plano_desejado in ['analise', 'promocional']:
                    return redirect(url_for('planos_page', sucesso='Conta criada com sucesso! Aproveite o bônus: pague 1 real por análise completa abaixo:'))
                
                return redirect(url_for('dashboard'))
            except Exception as e:
                erro = f'Erro ao criar conta: {str(e)}'

    return render_template('cadastro.html', erro=erro, nome=nome, email=email, plano_desejado=plano_desejado)


@app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=10, window_seconds=60)
def login():
    """Tela de login de usuários e administradores"""
    if 'user_id' in session:
        user = database.get_user_by_id(session['user_id'])
        if user and not user['is_blocked']:
            return redirect(url_for('admin_dashboard') if user['role'] == 'admin' else url_for('dashboard'))

    erro = request.args.get('erro')
    sucesso = request.args.get('sucesso')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = database.get_user_by_email(email)
        if not user or not check_password_hash(user['password_hash'], password):
            return render_template('login.html', erro='E-mail ou senha incorretos.', email=email)

        if user['is_blocked']:
            return render_template('login.html', erro='Esta conta está bloqueada pelo administrador.', email=email)

        # Autenticar sessão
        session.permanent = True
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_role'] = user['role']
        session['user_name'] = user.get('name', 'Apostador')
        database.record_login(user['id'])

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    return render_template('login.html', erro=erro, sucesso=sucesso)


@app.route('/logout')
def logout():
    """Encerrar sessão"""
    session.clear()
    return redirect(url_for('login', sucesso='Você saiu da sua conta.'))


# ==========================================
# ROTAS LGPD E PRIVACIDADE (LEI Nº 13.709/2018)
# ==========================================

@app.route('/privacidade')
def privacidade():
    """Página institucional de Política de Privacidade e Direitos do Titular (LGPD)"""
    return render_template('privacidade.html')


@app.route('/termos')
def termos():
    """Página institucional de Termos de Uso e Jogo Responsável (+18 anos)"""
    return render_template('termos.html')


BLOG_POSTS = {
    'a-matematica-oculta-das-loterias': {
        'title': 'A Matemática Oculta das Loterias: Por que Palpites Aleatórios Desperdiçam seu Dinheiro',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Entenda o erro matemático de usar datas de aniversário e o limite das funções aleatórias. Descubra como a análise probabilística e a distribuição equitativa blindam o apostador.',
        'template': 'blog/artigo_1.html'
    },
    'o-poder-dos-fechamentos-combinatorios': {
        'title': 'O Poder dos Fechamentos Combinatórios: Estratégia Avançada para Múltiplas Premiações',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Aprenda o princípio das matrizes matemáticas ortogonais e sistemas de redução. Veja como cercar dezenas otimiza a cobertura de faixas secundárias e reduz o custo das apostas.',
        'template': 'blog/artigo_2.html'
    },
    'inteligencia-artificial-e-analise-estocastica': {
        'title': 'Como a Inteligência Artificial Transforma a Análise Estocástica de Sorteios',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Descubra como Agentes IAs extraem padrões temporais e tendências históricas que o cérebro humano ignora, traduzindo complexidade matemática em estratégias de jogo claras.',
        'template': 'blog/artigo_3.html'
    },
    'o-paradoxo-do-jogador-e-lei-das-medias': {
        'title': 'O Paradoxo do Jogador: A Falácia da "Lei das Médias" nas Apostas',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Entenda por que uma dezena que está atrasada há 15 concursos não tem mais chance de sair hoje do que qualquer outra. Desvende a falácia do apostador.',
        'template': 'blog/artigo_4.html'
    },
    'filtros-matematicos-como-eliminar-dezenas': {
        'title': 'Filtros Matemáticos: Como Eliminar Combinações que Destroem seu Investimento',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Aprenda o poder da filtragem baseada em soma de dezenas e geometria de volante. Veja por que apostar sem filtros é doação para a banca.',
        'template': 'blog/artigo_5.html'
    },
    'a-curva-de-gauss-nas-loterias': {
        'title': 'A Curva de Gauss: Por Que Extremos Nunca Ganham em Loterias',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Mergulhe na distribuição normal e veja por que a soma das dezenas sorteadas sempre se concentra na área mediana do gráfico estatístico.',
        'template': 'blog/artigo_6.html'
    },
    'desdobramentos-vs-fechamentos': {
        'title': 'Desdobramentos vs. Fechamentos: O Segredo Financeiro da Matemática',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'A diferença colossal entre apostar em força bruta (combinatória completa) e usar matrizes ortogonais para reduzir custos mantendo prêmios.',
        'template': 'blog/artigo_7.html'
    },
    'estatistica-bayesiana-em-loterias': {
        'title': 'Estatística Bayesiana e Loterias: É Possível Prever o Futuro?',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Uma aula sobre o Teorema de Bayes e como a atualização de probabilidade (Priors e Posteriors) refina os algoritmos heurísticos das nossas análises.',
        'template': 'blog/artigo_8.html'
    },
    'teoria-do-caos-e-a-maquina-de-sorteio': {
        'title': 'Teoria do Caos: A Física Intransponível dos Globos de Sorteio',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Entenda por que calcular o peso e a velocidade das bolinhas físicas é impossível devido ao "Efeito Borboleta" e à entropia projetada.',
        'template': 'blog/artigo_9.html'
    },
    'gestao-de-banca-em-loterias': {
        'title': 'Otimização de Banca: A Engenharia de Não Quebrar Apostando',
        'date': '2026-09-12',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Loterias possuem Valor Esperado (EV) negativo. Descubra as táticas de Bankroll Management para mitigar perdas enquanto mira no jackpot.',
        'template': 'blog/artigo_10.html'
    },
    'quais-os-numeros-que-mais-saem-na-lotofacil': {
        'title': 'Quais os números que mais saem na Lotofácil? (Atualizado 2026)',
        'date': '2026-09-13',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Analisamos todos os sorteios da história para descobrir quais as dezenas mais sorteadas na Lotofácil e como usar isso a seu favor com um gerador inteligente.',
        'template': 'blog/artigo_11.html',
        'redirect_only': True
    },
    'frequencia-estatistica-de-dezenas': {
        'title': 'Frequência Estatística de Dezenas: Estudo Histórico de Sorteios',
        'date': '2026-09-13',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Estudo estatístico e análise de dados sobre a distribuição de frequência histórica das dezenas em sorteios oficiais.',
        'template': 'blog/artigo_11.html'
    },
    'como-ganhar-na-lotofacil-garantido': {
        'title': 'Existe método 100% garantido na Lotofácil? O fim do mito e a estatística real',
        'date': '2026-09-13',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Existe método 100% garantido? Desmistificamos falsas promessas e ensinamos como simuladores de fechamento da Lotofácil aumentam sua eficiência.',
        'template': 'blog/artigo_12.html',
        'canonical_slug': 'probabilidade-matematica-e-estatistica'
    },
    'probabilidade-matematica-e-estatistica': {
        'title': 'Probabilidade Matemática e Estatística: O Fim do Mito e a Ciência dos Sorteios',
        'date': '2026-09-13',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Análise probabilística e combinatória desmistificando mitos e demonstrando como matrizes matemáticas organizam dados.',
        'template': 'blog/artigo_12.html'
    },
    'diferenca-entre-desdobramento-e-fechamento': {
        'title': 'Diferença entre Desdobramento e Fechamento Matemático',
        'date': '2026-09-13',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Aprenda de uma vez por todas a diferença técnica entre desdobramento e fechamento para economizar nas suas apostas da Mega-Sena e Quina.',
        'template': 'blog/artigo_13.html'
    },
    'estatistica-lotomania-aposta-espelho': {
        'title': 'Estatística da Lotomania: Como Funciona a Aposta Espelho e a Redução Combinatória',
        'date': '2026-09-22',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Entenda a teoria probabilística por trás dos 100 números da Lotomania, o funcionamento da aposta espelho e o impacto da curva de Gauss na soma das dezenas.',
        'template': 'blog/artigo_14.html'
    },
    'fechamento-quina-estrategia-combinatoria': {
        'title': 'Fechamento da Quina: Estratégias Matemáticas para Otimizar Cobertura e Reduzir Custos',
        'date': '2026-09-22',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Descubra como matrizes ortogonais da Quina permitem cercar 8, 9 ou 10 dezenas com redução de até 85% no custo e proteção condicional para Quadra.',
        'template': 'blog/artigo_15.html'
    }
}

RESULTS_CACHE = {}
RESULTS_CACHE_TIME = {}

@app.route('/resultados')
def resultados_index():
    """Página central com o resultado do concurso atual de todas as 9 loterias da Caixa"""
    loterias = []
    for loteria, config in LOTERIAS_CONFIG.items():
        theme = LOTERIAS_THEME.get(loteria.value, {
            'cor': '#0046AD',
            'cor_dark': '#003380',
            'cor_gradiente': 'linear-gradient(135deg, #0046AD 0%, #003380 100%)',
            'icone': '🎲',
            'dias_resumo': ', '.join(config.dias_sorteio)
        })
        loterias.append({
            'id': loteria.value,
            'nome': config.nome,
            'theme': theme
        })
    return render_template('resultados_index.html', loterias=loterias)


@app.route('/resultados/<loteria_type>')
def ver_resultado(loteria_type):
    loteria_type = loteria_type.replace('-', '_')
    try:
        loteria_enum = LoteriaType(loteria_type)
    except ValueError:
        return "Loteria não encontrada", 404

    if loteria_enum not in LOTERIAS_CONFIG:
        return "Loteria não encontrada", 404

    slug = updater.LOTERIAS_SLUGS.get(loteria_type)
    if not slug:
        return "Loteria não suportada para resultados", 404

    # Busca o resultado mais recente com múltiplos fallbacks (sempre atualizado)
    dados_caixa = updater.obter_ultimo_resultado_completo(loteria_type)

    if not dados_caixa:
        return "Não foi possível carregar os resultados da Caixa no momento. Tente novamente.", 503

    numeros = updater.extrair_dezenas(dados_caixa, slug)
    trevos = updater.extrair_trevos(dados_caixa) if loteria_type == 'mais_milionaria' else []
    time_coracao = updater.extrair_time_coracao(dados_caixa) if loteria_type == 'timemania' else None
    mes_sorte = dados_caixa.get('nomeTimeCoracaoMesSorte') if loteria_type == 'dia_de_sorte' else None
    segundo_sorteio = updater.extrair_segundo_sorteio(dados_caixa) if loteria_type == 'dupla_sena' else []

    # Tema visual oficial da modalidade para garantir contraste perfeito das bolinhas
    tema = LOTERIAS_THEME.get(loteria_type, {})
    cor_loteria = tema.get('cor', '#0046AD')
    cor_gradiente = tema.get('cor_gradiente', f'linear-gradient(135deg, {cor_loteria} 0%, #0A1A3F 100%)')

    return render_template('resultado.html',
                           loteria=LOTERIAS_CONFIG[loteria_enum],
                           loteria_type=loteria_type,
                           tema=tema,
                           cor_loteria=cor_loteria,
                           cor_gradiente=cor_gradiente,
                           dados=dados_caixa,
                           numeros=numeros,
                           trevos=trevos,
                           time_coracao=time_coracao,
                           mes_sorte=mes_sorte,
                           segundo_sorteio=segundo_sorteio)


def _slug_to_loteria(loteria_slug):
    """Converte um slug de URL pública (com hífen ou underscore) para o LoteriaType correspondente."""
    chave = loteria_slug.replace('-', '_')
    try:
        enum = LoteriaType(chave)
    except ValueError:
        return None
    if enum not in LOTERIAS_CONFIG:
        return None
    return enum


def _gerar_post_acumulado(loteria_slug):
    """Post de blog dinâmico: título e conteúdo montados a partir do valor acumulado
    real e atual da loteria (não é um texto estático salvo em arquivo)."""
    loteria_enum = _slug_to_loteria(loteria_slug)
    if loteria_enum is None:
        return None
    loteria_key = loteria_enum.value
    config = LOTERIAS_CONFIG[loteria_enum]

    dados_caixa = updater.obter_ultimo_resultado_completo(loteria_key)
    if not dados_caixa or not dados_caixa.get('acumulado'):
        return None
    valor = dados_caixa.get('valorEstimadoProximoConcurso')
    if not valor:
        return None

    valor_fmt = f"R$ {valor:,.0f}".replace(',', '.')
    slug_canonico = loteria_key.replace('_', '-')

    return {
        'title': f'Análise Estatística para o Concurso Acumulado da {config.nome} de {valor_fmt}',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'author': 'Equipe Cálculo da Sorte',
        'description': f'A {config.nome} acumulou e o próximo concurso paga {valor_fmt}. Veja a análise estatística do histórico de sorteios antes de montar seu jogo.',
        'template': 'blog/concurso_acumulado.html',
        'dinamico': True,
        'loteria_nome': config.nome,
        'loteria_slug': slug_canonico,
        'valor_fmt': valor_fmt,
        'numero_concurso': dados_caixa.get('numero'),
        'data_proximo': dados_caixa.get('dataProximoConcurso'),
    }


@app.route('/blog')
def blog_index():
    posts = {
        s: p for s, p in BLOG_POSTS.items()
        if not p.get('redirect_only') and not p.get('canonical_slug')
    }
    for loteria_enum in LOTERIAS_CONFIG.keys():
        slug_canonico = loteria_enum.value.replace('_', '-')
        post = _gerar_post_acumulado(slug_canonico)
        if post:
            posts[f'concurso-acumulado-{slug_canonico}'] = post
    return render_template('blog_index.html', posts=posts)


@app.route('/blog/<slug>')
def blog_post(slug):
    post = BLOG_POSTS.get(slug)
    if not post and slug.startswith('concurso-acumulado-'):
        post = _gerar_post_acumulado(slug[len('concurso-acumulado-'):])
    if not post:
        return "Artigo não encontrado", 404
    return render_template('blog_post.html', post=post, slug=slug)


@app.route('/minha-conta')
@app.route('/perfil')
@login_required
def minha_conta():
    """Página de gestão de perfil, dados cadastrais, plano e segurança do usuário"""
    user_id = session['user_id']
    current_user = database.get_user_by_id(user_id)
    if not current_user:
        session.clear()
        return redirect(url_for('login', erro='Sessão inválida. Faça login novamente.'))
    
    access = database.check_user_access(user_id)
    apostas = database.listar_apostas(user_id=user_id, limit=20)
    
    erro = request.args.get('erro')
    sucesso = request.args.get('sucesso')
    
    return render_template(
        'minha_conta.html',
        current_user=current_user,
        access=access,
        apostas=apostas,
        erro=erro,
        sucesso=sucesso
    )


@app.route('/minha-conta/alterar-senha', methods=['POST'])
@login_required
def minha_conta_alterar_senha():
    """Alteração de senha do usuário logado com validação da senha atual"""
    user_id = session['user_id']
    senha_atual = request.form.get('senha_atual', '')
    nova_senha = request.form.get('nova_senha', '')
    confirmar_senha = request.form.get('confirmar_senha', '')
    
    user = database.get_user_by_id(user_id)
    if not user:
        return redirect(url_for('login'))
        
    if not check_password_hash(user['password_hash'], senha_atual):
        return redirect(url_for('minha_conta', erro='A senha atual informada está incorreta.'))
        
    if len(nova_senha) < 4:
        return redirect(url_for('minha_conta', erro='A nova senha deve ter pelo menos 4 caracteres.'))
        
    if nova_senha != confirmar_senha:
        return redirect(url_for('minha_conta', erro='A confirmação de senha não coincide com a nova senha.'))
        
    try:
        database.update_password(user_id, nova_senha)
        return redirect(url_for('minha_conta', sucesso='Senha alterada com sucesso!'))
    except Exception as e:
        return redirect(url_for('minha_conta', erro=f'Erro ao atualizar senha: {str(e)}'))


@app.route('/minha-conta/avisos', methods=['POST'])
@login_required
def minha_conta_avisos():
    """Liga ou desliga o aviso por e-mail de apostas premiadas"""
    ativo = request.form.get('avisos_email') == '1'
    database.set_avisos_email(session['user_id'], ativo)
    msg = 'Avisos de prêmio por e-mail ativados.' if ativo else 'Avisos de prêmio por e-mail desativados.'
    return redirect(url_for('minha_conta', sucesso=msg))


@app.route('/api/usuario/exportar-dados', methods=['GET'])
@login_required
def api_usuario_exportar_dados():
    """Portabilidade de dados cadastrais e apostas em formato JSON (Art. 18, V da LGPD) como arquivo de download"""
    import json
    user_id = session['user_id']
    dados_portabilidade = database.export_user_data(user_id)
    json_bytes = json.dumps(dados_portabilidade, indent=2, ensure_ascii=False, default=str).encode('utf-8')
    resp = Response(json_bytes, mimetype='application/json')
    resp.headers["Content-Disposition"] = "attachment; filename=meus_dados_calculo_da_sorte.json"
    return resp


@app.route('/api/usuario/excluir-conta', methods=['POST'])
@login_required
def api_usuario_excluir_conta():
    """Eliminação dos dados pessoais / Direito ao Esquecimento (Art. 18, VI da LGPD)"""
    user_id = session['user_id']
    database.delete_user_and_data(user_id)
    session.clear()
    return jsonify({
        'sucesso': True,
        'mensagem': 'Conta e dados pessoais excluídos com sucesso em estrita conformidade com a LGPD.'
    })


# ==========================================
# PAINEL ADMINISTRATIVO E GESTÃO DE USUÁRIOS
# ==========================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Dashboard do painel administrativo com renderização imediata de dados"""
    user = database.get_user_by_id(session['user_id'])
    usuarios = database.get_all_users()
    pagamentos = database.get_all_payments()
    
    chat_logs = database.get_all_chat_logs()
    system_errors = database.get_system_errors()
    logs = database.get_latest_sync_logs(15)
    status_loterias = updater.obter_status_loterias(consultar_online=False)
    
    total_usuarios = len(usuarios)
    usuarios_ativos = sum(1 for u in usuarios if not u.get('is_blocked'))
    total_pagamentos = len(pagamentos)
    pagamentos_aprovados = sum(1 for p in pagamentos if p.get('status') == 'aprovado')
    receita_total = sum(float(p.get('valor', 0)) for p in pagamentos if p.get('status') == 'aprovado')
    
    metricas = {
        'total_usuarios': total_usuarios,
        'usuarios_ativos': usuarios_ativos,
        'total_pagamentos': total_pagamentos,
        'pagamentos_aprovados': pagamentos_aprovados,
        'receita_total': receita_total
    }
    
    aba_ativa = request.args.get('aba', 'tab-loterias')
    storage_status = {}
    
    import ai_agent
    import json
    
    api_status = {
        'gemini': bool(ai_agent._get_gemini_key()),
        'claude': bool(ai_agent._get_claude_key()),
        'kimi': bool(ai_agent._get_moonshot_key()),
        'caixa': True
    }
    import os
    
    ai_keys_json = database.get_setting('ai_api_keys', '{}')
    try:
        db_api_keys_config = json.loads(ai_keys_json)
    except Exception:
        db_api_keys_config = {}
        
    has_env = {
        'gemini': bool(os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')),
        'claude': bool(os.environ.get('ANTHROPIC_API_KEY')),
        'kimi': bool(os.environ.get('MOONSHOT_API_KEY') or os.environ.get('KIMI_API_KEY'))
    }
    
    ui_api_keys_config = {}
    for prov in ['gemini', 'claude', 'kimi']:
        db_conf = db_api_keys_config.get(prov, {})
        active = db_conf.get('active', True if prov == 'gemini' else False)
        
        display_key = ''
        if db_conf.get('key'):
            display_key = '***MASCARADO (Via Painel/DB)***'
        elif has_env[prov]:
            display_key = '***MASCARADO (Via arquivo .env)***'
            
        ui_api_keys_config[prov] = {
            'active': active,
            'display_key': display_key
        }

    return render_template(
        'admin.html', 
        user=user, 
        usuarios=usuarios, 
        pagamentos=pagamentos,
        logs=logs,
        status_loterias=status_loterias,
        metricas=metricas,
        storage_status=storage_status,
        aba_ativa=aba_ativa,
        pix_config=database.get_pix_config(),
        chat_logs=chat_logs,
        system_errors=system_errors,
        api_status=api_status,
        api_keys_config=ui_api_keys_config,
        boloes=database.get_all_boloes(),
        bolao_config=database.get_bolao_config(),
        reembolsos=database.listar_reembolsos_pendentes(),
        loterias_bolao=_NOMES_LOTERIAS,
    )


@app.route('/admin/config-ia', methods=['POST'])
@admin_required
def salvar_config_ia():
    import json
    dados = request.get_json() or {}
    
    config_atual_json = database.get_setting('ai_api_keys', '{}')
    try:
        config_atual = json.loads(config_atual_json)
    except Exception:
        config_atual = {}
        
    for provider in ['gemini', 'claude', 'kimi']:
        if provider in dados:
            provider_data = dados[provider]
            if provider not in config_atual:
                config_atual[provider] = {}
            if 'active' in provider_data:
                config_atual[provider]['active'] = bool(provider_data['active'])
            if 'key' in provider_data:
                # Only update if the user actually sent a new key and not the masked one
                new_key = provider_data['key'].strip()
                if new_key and '***MASCARADO' not in new_key:
                    config_atual[provider]['key'] = new_key
                elif not new_key:
                    # User sent empty string, meaning they want to remove it
                    config_atual[provider]['key'] = ''
                    
    database.set_setting('ai_api_keys', json.dumps(config_atual))
    return jsonify({'sucesso': True})


@app.route('/admin/alterar-senha', methods=['POST'])
@login_required
def alterar_senha_propria():
    """Permite ao usuário logado alterar sua própria senha"""
    dados = request.get_json() or {}
    nova_senha = dados.get('nova_senha', '').strip()

    if len(nova_senha) < 4:
        return jsonify({'erro': 'A nova senha deve conter pelo menos 4 caracteres'}), 400

    user_id = session['user_id']
    database.update_password(user_id, nova_senha)
    return jsonify({'sucesso': True, 'mensagem': 'Senha alterada com sucesso!'})


@app.route('/api/admin/usuarios', methods=['GET'])
@admin_required
def api_admin_listar_usuarios():
    """Listar todos os usuários cadastrados"""
    usuarios = database.get_all_users()
    return jsonify(usuarios)


@app.route('/api/admin/usuarios', methods=['POST'])
@admin_required
def api_admin_criar_usuario():
    """Criar novo usuário"""
    dados = request.get_json() or {}
    email = dados.get('email', '').strip()
    password = dados.get('password', '')
    role = dados.get('role', 'user')

    if not email or '@' not in email:
        return jsonify({'erro': 'E-mail válido é obrigatório'}), 400
    if len(password) < 4:
        return jsonify({'erro': 'A senha deve conter ao menos 4 caracteres'}), 400

    if database.get_user_by_email(email):
        return jsonify({'erro': 'Já existe um usuário com este e-mail'}), 409

    try:
        user = database.create_user(
            email=email,
            password=password,
            name=dados.get('name') or email.split('@')[0],
            role=role
        )
        return jsonify(user), 201
    except Exception as e:
        return jsonify({'erro': str(e)}), 400


@app.route('/api/admin/usuarios/<int:user_id>', methods=['PUT'])
@admin_required
def api_admin_editar_usuario(user_id: int):
    """Editar usuário existente"""
    dados = request.get_json() or {}
    email = dados.get('email')
    password = dados.get('password')
    role = dados.get('role')

    try:
        user = database.update_user(user_id, email=email, password=password, role=role)
        return jsonify(user)
    except Exception as e:
        return jsonify({'erro': str(e)}), 400


@app.route('/api/admin/usuarios/<int:user_id>/bloquear', methods=['POST'])
@admin_required
def api_admin_bloquear_usuario(user_id: int):
    """Alternar status de bloqueio do usuário"""
    if user_id == session.get('user_id'):
        return jsonify({'erro': 'Você não pode bloquear a sua própria conta'}), 400

    try:
        esta_bloqueado = database.toggle_block_user(user_id)
        return jsonify({'sucesso': True, 'bloqueado': esta_bloqueado})
    except Exception as e:
        return jsonify({'erro': str(e)}), 400


@app.route('/api/admin/usuarios/<int:user_id>', methods=['DELETE'])
@admin_required
def api_admin_deletar_usuario(user_id: int):
    """Excluir usuário do sistema"""
    if user_id == session.get('user_id'):
        return jsonify({'erro': 'Você não pode excluir a sua própria conta'}), 400

    sucesso = database.delete_user(user_id)
    if sucesso:
        return jsonify({'sucesso': True})
    return jsonify({'erro': 'Usuário não encontrado'}), 404


# ==========================================
# APIS DE ATUALIZAÇÃO E SINCRONIZAÇÃO CAIXA
# ==========================================

@app.route('/api/admin/loterias/status', methods=['GET'])
@admin_required
def api_admin_loterias_status():
    """Retorna status e logs recentes das 9 loterias"""
    status = updater.obter_status_loterias()
    logs = database.get_latest_sync_logs(15)
    return jsonify({'status': status, 'logs': logs})


@app.route('/api/admin/loterias/sincronizar/<loteria_type>', methods=['POST'])
@admin_required
def api_admin_sincronizar_loteria(loteria_type: str):
    """Sincroniza uma loteria específica"""
    res = updater.sincronizar_loteria(loteria_type, n_historico=50)
    return jsonify(res)


@app.route('/api/admin/loterias/sincronizar-todas', methods=['POST'])
@admin_required
def api_admin_sincronizar_todas():
    """Sincroniza todas as 9 loterias da Caixa"""
    res = updater.sincronizar_todas(n_historico=50)
    return jsonify(res)


def _ultimos_concursos(valor, padrao: int = 300) -> int:
    """Quantos dos concursos mais recentes importar (0 = todos)."""
    try:
        return max(0, int(valor))
    except (TypeError, ValueError):
        return padrao


@app.route('/api/admin/importar-resultados', methods=['POST'])
@admin_required
def api_admin_importar_resultados():
    """Importa resultados anteriores de uma loteria a partir de CSV, Excel ou Google Sheets.
    Com confirmar=0 só valida e mostra a prévia; com confirmar=1 grava e mescla ao histórico."""
    loteria_type = (request.form.get('loteria') or '').strip()
    if loteria_type not in updater.LOTERIAS_SLUGS:
        return jsonify({'sucesso': False, 'erro': 'Selecione uma loteria válida.'}), 400
    arquivo = request.files.get('arquivo')
    conteudo = arquivo.read() if arquivo and arquivo.filename else None
    if conteudo and len(conteudo) > 4 * 1024 * 1024:
        return jsonify({'sucesso': False, 'erro': 'Arquivo muito grande (limite de 4 MB). Divida a planilha.'}), 400
    try:
        res = importador.processar(
            loteria_type,
            nome_arquivo=arquivo.filename if conteudo else '',
            conteudo=conteudo,
            url=(request.form.get('url') or '').strip(),
        )
    except importador.ErroImportacao as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 400

    concursos = res['concursos']
    ultimos = _ultimos_concursos(request.form.get('ultimos'))
    if ultimos:
        concursos = concursos[-ultimos:]
    resposta = {
        'sucesso': True,
        'loteria': loteria_type,
        'validos': len(concursos),
        'ignoradas': res['ignoradas'],
        'erros': res['erros'][:importador.MAX_ERROS_EXIBIDOS],
        'total_erros': len(res['erros']),
        'primeiro': concursos[0]['concurso'] if concursos else None,
        'ultimo': concursos[-1]['concurso'] if concursos else None,
        'amostra': concursos[:3] + (concursos[-2:] if len(concursos) > 5 else []),
        'comparacao': updater.comparar_com_local(loteria_type, concursos) if concursos else None,
    }
    if request.form.get('confirmar') != '1':
        resposta['previa'] = True
        return jsonify(resposta)
    if not concursos:
        return jsonify({'sucesso': False, 'erro': 'Nenhum concurso válido para importar.', **resposta}), 400

    # Só grava os concursos que ainda não temos; os existentes são ignorados
    existentes = updater.concursos_existentes(loteria_type)
    novos = [c for c in concursos if c['concurso'] not in existentes]
    if novos:
        database.salvar_concursos_importados(loteria_type, novos)
        updater.mesclar_importados(loteria_type, novos)
    database.log_sync(loteria_type, concursos[-1]['concurso'], concursos[-1].get('data'), 'SUCESSO',
                      f'Importação por planilha: {len(novos)} concursos novos, '
                      f'{len(concursos) - len(novos)} já existentes ignorados.')
    resposta.update({'previa': False, 'adicionados': len(novos), 'ignorados': len(concursos) - len(novos),
                     'total_local': len(updater.concursos_existentes(loteria_type))})
    return jsonify(resposta)


@app.route('/api/admin/historico-completo/<loteria_type>', methods=['POST'])
@admin_required
def api_admin_historico_completo(loteria_type: str):
    """Baixa da API todos os concursos que faltam da loteria (os existentes são ignorados).
    Pode ser chamado repetidamente até 'faltam' chegar a zero."""
    if loteria_type not in updater.LOTERIAS_SLUGS:
        return jsonify({'sucesso': False, 'erro': 'Loteria inválida.'}), 400
    usar_lista = request.args.get('lista', '1') != '0'
    return jsonify(updater.baixar_historico_completo(
        loteria_type, usar_lista_completa=usar_lista, ultimos=_ultimos_concursos(request.args.get('ultimos')),
        abaixo_de=request.args.get('abaixo_de', type=int)))


@app.route('/api/admin/importar-resultados/resumo', methods=['GET'])
@admin_required
def api_admin_importar_resumo():
    resumo = database.resumo_concursos_importados()
    itens = []
    for loteria_type, nome in updater.LOTERIAS_NOMES.items():
        meta = updater.carregar_meta(loteria_type)
        itens.append({
            'loteria': loteria_type,
            'nome': nome,
            'total_local': meta.get('total_concursos') or len(updater.carregar_historico_local(loteria_type)),
            'ultimo_concurso': meta.get('ultimo_concurso'),
            'importados': resumo.get(loteria_type),
        })
    return jsonify({'loterias': itens})


@app.route('/api/admin/importar-resultados/modelo/<loteria_type>', methods=['GET'])
@admin_required
def api_admin_importar_modelo(loteria_type: str):
    try:
        conteudo = importador.modelo_csv(loteria_type)
    except importador.ErroImportacao as e:
        return jsonify({'erro': str(e)}), 404
    return Response('\ufeff' + conteudo, mimetype='text/csv', headers={
        'Content-Disposition': f'attachment; filename=modelo_{loteria_type}.csv'})


@app.route('/api/admin/importar-resultados/<loteria_type>', methods=['DELETE'])
@admin_required
def api_admin_importar_excluir(loteria_type: str):
    if loteria_type not in updater.LOTERIAS_SLUGS:
        return jsonify({'sucesso': False, 'erro': 'Loteria inválida.'}), 400
    removidos = updater.remover_importados(loteria_type)
    database.log_sync(loteria_type, None, None, 'SUCESSO',
                      f'Importação por planilha desfeita: {removidos} concursos removidos do histórico.')
    return jsonify({'sucesso': True, 'removidos': removidos})


# ==========================================
# APIS ESTATÍSTICAS DO MODELO CANÔNICO 4.0
# ==========================================

@app.route('/api/analise/<loteria_type>', methods=['POST'])
def api_analise(loteria_type: str):
    """API para realizar análise estatística completa (Canônica Dinâmica, Fechamentos e Tradicionais)"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    try:
        modelo = modelo_canonico(loteria_type)
    except ValueError as exc:
        return jsonify({'erro': f'Histórico inválido para análise: {exc}'}), 400
    if modelo is None:
        return jsonify({
            'erro': 'Histórico insuficiente. Mínimo de 10 concursos necessários para a análise descritiva.'
        }), 400

    dados_req = request.get_json(silent=True) or {}
    metodo_escolhido = (dados_req.get('metodo_analise') or 'canonica_dinamica').strip().lower()

    resumo = dict(modelo.obter_resumo_analise())

    # Validações da Camada 7 (Monte Carlo etc.): também calculadas uma vez por concurso
    if 'validacao' not in modelo._memo:
        modelo._memo['validacao'] = ValidaçãoCamada7(modelo).validacao_completa()
    resumo['validacao_camada7'] = modelo._memo['validacao']
    
    # Gerar sugestões de jogos e dinâmica de expansão/retração
    config = LOTERIAS_CONFIG[loteria]
    dinamica = resumo.get('dinamica_canonica') or modelo.avaliar_dinamica_expansao_retracao()
    resumo['dinamica_canonica'] = dinamica
    opcoes_analise = resumo.get('opcoes_analise') or modelo.obter_opcoes_analise()
    resumo['opcoes_analise'] = opcoes_analise
    resumo['metodo_analise_ativo'] = metodo_escolhido

    resumo['sugestoes'] = {
        'jogo_simples': gerar_jogo_sugerido(modelo, config.minimo_aposta, metodo=metodo_escolhido),
        'jogo_medio': gerar_jogo_sugerido(modelo, min(config.minimo_aposta + 2, config.maximo_aposta), metodo=metodo_escolhido),
        'jogo_dinamico_ajustado': dinamica.get('jogo_ajustado') if isinstance(dinamica, dict) else None,
        'por_metodo': {
            'canonica_dinamica': gerar_jogo_sugerido(modelo, config.minimo_aposta, metodo='canonica_dinamica'),
            'frequencia_quentes': gerar_jogo_sugerido(modelo, config.minimo_aposta, metodo='frequencia_quentes'),
            'atraso_frios': gerar_jogo_sugerido(modelo, config.minimo_aposta, metodo='atraso_frios'),
            'equilibrio_classico': gerar_jogo_sugerido(modelo, config.minimo_aposta, metodo='equilibrio_classico'),
            'hibrida_tradicional': gerar_jogo_sugerido(modelo, config.minimo_aposta, metodo='hibrida_tradicional'),
        }
    }
    if config.colunas:
        resumo['analise_por_coluna'] = analise_por_coluna(modelo)
    resumo['indicadores_classicos'] = avaliacao.resumo_indicadores(modelo)
    
    return jsonify(resumo)


@app.route('/api/sugerir-grupo-fechamento/<loteria_type>', methods=['POST'])
def api_sugerir_grupo_fechamento(loteria_type: str):
    """Sugere automaticamente um grupo de dezenas para Fechamento com base na análise escolhida pelo usuário"""
    try:
        loteria = LoteriaType(loteria_type)
        config = LOTERIAS_CONFIG[loteria]
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400

    modelo = modelo_canonico(loteria_type)
    if modelo is None:
        return jsonify({'erro': 'Histórico insuficiente para sugerir grupo.'}), 400

    dados = request.get_json(silent=True) or {}
    estrategia = (dados.get('estrategia') or 'canonica_dinamica').strip().lower()
    try:
        tamanho = int(dados.get('tamanho_grupo', config.minimo_aposta + 3))
    except (TypeError, ValueError):
        tamanho = config.minimo_aposta + 3

    from metodos_analise import sugerir_grupo_para_fechamento
    grupo = sugerir_grupo_para_fechamento(modelo, tamanho, estrategia=estrategia)
    return jsonify({
        'sucesso': True,
        'loteria': config.nome,
        'estrategia': estrategia,
        'tamanho_grupo': len(grupo),
        'grupo': grupo
    })


@app.route('/api/dinamica-canonica/<loteria_type>', methods=['GET', 'POST'])
def api_dinamica_canonica(loteria_type: str):
    """API para consultar a dinâmica de expansão e retração dos últimos sorteios por casa com ajuste de aproximação"""
    try:
        modelo = modelo_canonico(loteria_type)
    except Exception as exc:
        return jsonify({'erro': f'Erro ao carregar modelo: {exc}'}), 400
    if modelo is None:
        return jsonify({'erro': 'Histórico insuficiente para análise dinâmica.'}), 400
    return jsonify(modelo.avaliar_dinamica_expansao_retracao())


def _obter_identificadores_usuario():
    """Retorna (user_id, session_id) garantindo sessão única"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session.get('user_id'), session.get('session_id')


@app.route('/api/apostas/salvar', methods=['POST'])
def api_salvar_apostas():
    """Salva um lote de jogos no histórico do usuário no SQLite"""
    dados = request.get_json() or {}
    loteria_type = dados.get('loteria_type')
    modalidade = dados.get('modalidade', 'manual')
    jogos = dados.get('jogos', [])
    titulo = dados.get('titulo')
    
    try:
        loteria = LoteriaType(loteria_type)
    except (ValueError, TypeError):
        return jsonify({'erro': 'Loteria inválida'}), 400

    if not isinstance(jogos, list) or len(jogos) == 0:
        return jsonify({'erro': 'Nenhum jogo fornecido'}), 400

    dezenas_por_jogo = len(jogos[0]) if jogos and isinstance(jogos[0], list) else 6
    user_id, session_id = _obter_identificadores_usuario()

    # +Milionária: os 2 trevos de cada jogo também definem as faixas de prêmio
    trevos = dados.get('trevos') if loteria == LoteriaType.MAIS_MILIONARIA else None
    if loteria == LoteriaType.MAIS_MILIONARIA and not trevos:
        trevos = [sorted(secrets.SystemRandom().sample(range(1, 7), 2)) for _ in range(len(jogos))]
    elif trevos is not None:
        valido = (isinstance(trevos, list) and len(trevos) == len(jogos) and all(
            isinstance(t, list) and 2 <= len(t) <= 6 and len(set(t)) == len(t)
            and all(isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= 6 for n in t)
            for t in trevos))
        if not valido:
            return jsonify({'erro': 'Trevos inválidos: informe de 2 a 6 trevos diferentes (1 a 6) para cada jogo.'}), 400

    # Timemania / Dia de Sorte: Time do Coração ou Mês da Sorte de cada jogo
    complementos = dados.get('complementos') if loteria_type in conferencia.ROTULO_COMPLEMENTO else None
    if loteria_type in conferencia.ROTULO_COMPLEMENTO and not complementos:
        opts = opcoes_complemento(loteria_type)
        if opts:
            sorteador = secrets.SystemRandom()
            complementos = [sorteador.choice(opts) for _ in range(len(jogos))]
    elif complementos is not None:
        if not (isinstance(complementos, list) and len(complementos) == len(jogos)
                and all(c is None or (isinstance(c, str) and 0 < len(c) <= 60) for c in complementos)):
            return jsonify({'erro': 'Informe um Time do Coração / Mês da Sorte válido para cada jogo.'}), 400
        if loteria_type == 'dia_de_sorte' and any(
                c and conferencia.normalizar_complemento(c) not in {conferencia.normalizar_complemento(m) for m in conferencia.MESES}
                for c in complementos):
            return jsonify({'erro': 'Mês da Sorte inválido.'}), 400

    aposta_id = database.salvar_aposta(
        loteria_type=loteria_type,
        modalidade=modalidade,
        jogos=jogos,
        dezenas_por_jogo=dezenas_por_jogo,
        user_id=user_id,
        session_id=session_id,
        titulo=titulo,
        concurso_alvo=conferencia.proximo_concurso(loteria_type),
        trevos=trevos,
        complementos=complementos
    )

    return jsonify({
        'sucesso': True,
        'aposta_id': aposta_id,
        'quantidade_jogos': len(jogos),
        'mensagem': f'{len(jogos)} aposta(s) salvas no seu histórico!'
    })


@app.route('/api/apostas/listar/<loteria_type>', methods=['GET'])
def api_listar_apostas(loteria_type: str):
    """Lista o histórico de apostas salvas do usuário para a loteria"""
    user_id, session_id = _obter_identificadores_usuario()
    apostas = database.listar_apostas(
        loteria_type=loteria_type,
        user_id=user_id,
        session_id=session_id
    )
    sorteios_cache = {}
    for aposta in apostas:
        aposta['conferencia'] = conferencia.resumo_aposta(aposta, sorteios_cache)
    return jsonify({
        'sucesso': True,
        'apostas': apostas,
        'total': len(apostas)
    })


@app.route('/api/apostas/<int:aposta_id>', methods=['DELETE'])
def api_excluir_aposta(aposta_id: int):
    """Exclui uma aposta salva do usuário"""
    user_id, session_id = _obter_identificadores_usuario()
    sucesso = database.excluir_aposta(aposta_id, user_id=user_id, session_id=session_id)
    if sucesso:
        return jsonify({'sucesso': True, 'mensagem': 'Aposta removida com sucesso'})
    return jsonify({'erro': 'Aposta não encontrada ou não autorizada'}), 404


@app.route('/api/apostas/<int:aposta_id>/complementos', methods=['POST'])
@login_required
def api_atualizar_complementos(aposta_id: int):
    """Troca o Time do Coração / Mês da Sorte dos jogos de uma aposta ainda não sorteada."""
    aposta = database.obter_aposta(aposta_id)
    if not aposta or aposta.get('user_id') != session['user_id']:
        return jsonify({'erro': 'Aposta não encontrada'}), 404
    loteria_type = aposta['loteria_type']
    if loteria_type not in conferencia.ROTULO_COMPLEMENTO:
        return jsonify({'erro': 'Esta loteria não tem Time do Coração / Mês da Sorte'}), 400
    if conferencia.sorteio_do_concurso(loteria_type, aposta.get('concurso_alvo'))['status'] != 'aguardando':
        return jsonify({'erro': 'O concurso desta aposta já foi sorteado'}), 400

    complementos = (request.get_json(silent=True) or {}).get('complementos')
    jogos = aposta.get('jogos') or []
    if not (isinstance(complementos, list) and len(complementos) == len(jogos)
            and all(c is None or (isinstance(c, str) and 0 < len(c) <= 60) for c in complementos)):
        return jsonify({'erro': 'Informe um Time do Coração / Mês da Sorte válido para cada jogo.'}), 400
    if loteria_type == 'dia_de_sorte' and any(
            c and conferencia.normalizar_complemento(c) not in {conferencia.normalizar_complemento(m) for m in conferencia.MESES}
            for c in complementos):
        return jsonify({'erro': 'Mês da Sorte inválido.'}), 400

    database.atualizar_complementos_aposta(aposta_id, complementos)
    return jsonify({'sucesso': True})


@app.route('/api/apostas/conferir/<int:aposta_id>', methods=['GET'])
def api_conferir_aposta(aposta_id: int):
    """Confere as cartelas de uma aposta salva contra o último sorteio oficial da Caixa com validação de posse"""
    aposta = database.obter_aposta(aposta_id)
    if not aposta:
        return jsonify({'erro': 'Aposta não encontrada'}), 404

    # Proteção IDOR: Apenas o titular da aposta ou administrador pode visualizar/conferir
    user_id, session_id = _obter_identificadores_usuario()
    dono_user = aposta.get('user_id')
    dono_session = aposta.get('session_id')
    is_admin = session.get('user_role') == 'admin'

    if not is_admin:
        if user_id and dono_user != user_id and dono_session != session_id:
            return jsonify({'erro': 'Acesso não autorizado a esta aposta'}), 403
        elif not user_id and dono_session != session_id:
            return jsonify({'erro': 'Acesso não autorizado a esta aposta'}), 403

    loteria_type = aposta['loteria_type']
    sorteio = conferencia.sorteio_do_concurso(loteria_type, aposta.get('concurso_alvo'))
    if sorteio['status'] == 'aguardando':
        return jsonify({
            'sucesso': True,
            'status': 'aguardando',
            'concurso_numero': sorteio['concurso'],
            'mensagem': f"Esta aposta concorre no concurso {sorteio['concurso']}, que ainda não foi sorteado. A conferência é automática assim que o resultado sair."
        })
    if sorteio['status'] != 'conferido':
        return jsonify({'erro': 'Resultado desse concurso não está disponível para conferência'}), 400

    jogos_conferidos, premiacoes_resumo = conferencia.conferir_jogos(
        loteria_type, aposta.get('jogos', []), sorteio['dezenas'], sorteio['segundo_sorteio'],
        sorteio.get('trevos'), aposta.get('trevos'),
        sorteio.get('complemento'), aposta.get('complementos'))

    return jsonify({
        'sucesso': True,
        'status': 'conferido',
        'aposta_titulo': aposta.get('titulo'),
        'concurso_numero': sorteio['concurso'],
        'data_apuracao': sorteio.get('data_apuracao') or '',
        'dezenas_sorteadas': sorteio['dezenas'],
        'dezenas_segundo_sorteio': sorteio['segundo_sorteio'],
        'trevos_sorteados': sorteio.get('trevos') or [],
        'complemento_sorteado': sorteio.get('complemento'),
        'jogos_conferidos': jogos_conferidos,
        'premiacoes_resumo': premiacoes_resumo
    })


@app.route('/api/salvar-historico/<loteria_type>', methods=['POST'])
def api_salvar_historico(loteria_type: str):
    """API para salvar apostas manuais do usuário no banco SQLite (sem alterar dados da Caixa)"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    dados = request.get_json()
    historico = dados.get('historico', [])
    
    if not historico:
        return jsonify({'erro': 'Histórico vazio'}), 400
    
    for concurso in historico:
        if not isinstance(concurso, list) or len(concurso) == 0:
            return jsonify({'erro': 'Formato de concurso inválido'}), 400
    
    user_id, session_id = _obter_identificadores_usuario()
    dezenas_por_jogo = len(historico[0]) if historico else 6

    trevos = dados.get('trevos')
    complementos = dados.get('complementos')
    if loteria == LoteriaType.MAIS_MILIONARIA and not trevos:
        trevos = [[1, 2] for _ in range(len(historico))]
    if loteria_type in ('dia_de_sorte', 'timemania') and not complementos:
        opts = opcoes_complemento(loteria_type)
        if opts:
            sorteador = secrets.SystemRandom()
            complementos = [sorteador.choice(opts) for _ in range(len(historico))]

    aposta_id = database.salvar_aposta(
        loteria_type=loteria_type,
        modalidade='manual',
        jogos=historico,
        dezenas_por_jogo=dezenas_por_jogo,
        user_id=user_id,
        session_id=session_id,
        titulo=f"Jogos Digitados ({len(historico)} aposta(s))",
        concurso_alvo=conferencia.proximo_concurso(loteria_type),
        trevos=trevos,
        complementos=complementos
    )
    
    return jsonify({
        'sucesso': True,
        'aposta_id': aposta_id,
        'concursos_salvos': len(historico)
    })


@app.route('/api/carregar-historico/<loteria_type>', methods=['GET'])
def api_carregar_historico(loteria_type: str):
    """API para carregar histórico salvo com metadados e atualização inteligente sob demanda"""
    # Se solicitado via parâmetro ou se a rotina detectar que os dados precisam de atualização
    if request.args.get('auto_sync') == '1' or updater.verificar_se_necessita_atualizacao(loteria_type):
        try:
            updater.sincronizar_loteria(loteria_type, n_historico=25)
        except Exception as e:
            print(f"[API] Aviso na auto-sincronização de {loteria_type}: {e}")

    historico = carregar_historico(loteria_type)
    meta = updater.carregar_meta(loteria_type)
    resposta = {
        'historico': historico,
        'concursos_count': len(historico),
        'meta': meta
    }
    if loteria_type in ('timemania', 'dia_de_sorte'):
        times_ou_meses = updater.carregar_times_local(loteria_type)
        resposta['times_coracao'] = times_ou_meses
        resposta['complementos'] = times_ou_meses
    if loteria_type == 'mais_milionaria':
        resposta['trevos'] = updater.carregar_trevos_local(loteria_type)
    concursos = updater.carregar_concursos_local(loteria_type)
    resposta['concursos'] = concursos if len(concursos) == len(historico) else []
    if loteria_type == 'dupla_sena':
        segundos = updater.carregar_segundo_sorteio_local(loteria_type)
        resposta['segundo_sorteio'] = segundos if len(segundos) == len(historico) else []
    return jsonify(resposta)


@app.route('/api/sincronizar/<loteria_type>', methods=['POST'])
def api_sincronizar_publica(loteria_type: str):
    """Sincroniza os últimos resultados oficiais da Caixa para a modalidade (Exclusivo Administrador)"""
    if session.get('user_role') != 'admin':
        return jsonify({
            'sucesso': False,
            'erro': 'A sincronização manual com a Caixa é permitida apenas para administradores.'
        }), 403
    res = updater.sincronizar_loteria(loteria_type, n_historico=25)
    return jsonify(res)


@app.route('/gerar-jogo/<loteria_type>', methods=['POST'])
def gerar_jogo(loteria_type: str):
    """Gerar sugestão de jogo baseado na análise escolhida pelo usuário"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    dados = request.get_json(silent=True) or {}
    config = LOTERIAS_CONFIG[loteria]
    try:
        quantidade = int(dados.get('quantidade', config.minimo_aposta))
    except (TypeError, ValueError):
        quantidade = config.minimo_aposta
    quantidade = max(config.minimo_aposta, min(config.maximo_aposta, quantidade))

    modelo = modelo_canonico(loteria_type)
    if modelo is None:
        return jsonify({'erro': 'Histórico insuficiente para análise'}), 400

    modo = (dados.get('modo') or dados.get('metodo_analise') or 'canonica_dinamica').strip().lower()
    if modo in ('dinamico', 'dinamico_ajustado', 'expansao_retracao'):
        jogo = gerar_jogo_dinamico_ajustado(modelo)
    else:
        jogo = gerar_jogo_sugerido(modelo, quantidade, metodo=modo)
    
    return jsonify({
        'jogo': jogo,
        'quantidade': len(jogo),
        'metodo_analise': modo,
        'analise_resumo': {
            'ict_medio': modelo.obter_resumo_analise()['estatisticas_gerais']['ict_medio'],
            'entropia': modelo.obter_resumo_analise()['camada_informacional']['entropia']
        }
    })


MSG_ACESSO_EXPIRADO = 'Seu tempo de acesso ou créditos expiraram. Libere 1 análise por R$ 1,00, Acesso 24 Horas por R$ 5,00 ou assine o Plano VIP Ilimitado (R$ 49,90/mês) para continuar gerando jogos.'


def _acesso_bloqueado(user_id):
    """Resposta 403 se o usuário não tiver plano ou créditos; None se puder gerar."""
    if not database.check_user_access(user_id).get('has_access'):
        return jsonify({'sucesso': False, 'erro': MSG_ACESSO_EXPIRADO, 'precisa_plano': True}), 403
    return None


ROTULOS_METODO_ANALISE = {
    'canonica_dinamica': 'Fórmula Canônica 4.0 (Expansão e Retração)',
    'fechamento': 'Fechamento Matemático com Garantia',
    'frequencia_quentes': 'Tradicional: Frequência e Dezenas Quentes',
    'atraso_frios': 'Tradicional: Atrasados e Ciclo das Dezenas',
    'equilibrio_classico': 'Tradicional: Equilíbrio Clássico (Soma/Primos/Repetidas)',
    'hibrida_tradicional': 'Análise Híbrida (Quentes + Atrasados + Canônica)',
}


@app.route('/api/gerar-multiplos-jogos/<loteria_type>', methods=['POST'])
@login_required
def api_gerar_multiplos_jogos(loteria_type: str):
    """Gera múltiplos palpites estatísticos segundo a forma de análise escolhida pelo usuário"""
    try:
        loteria = LoteriaType(loteria_type)
        config = LOTERIAS_CONFIG[loteria]
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400

    user_id = session['user_id']
    bloqueio = _acesso_bloqueado(user_id)
    if bloqueio:
        return bloqueio

    dados = request.get_json(silent=True) or {}
    quantidade_jogos = int(dados.get('quantidade_jogos', 5))
    quantidade_jogos = max(1, min(100, quantidade_jogos))

    dezenas = int(dados.get('dezenas_por_jogo', config.minimo_aposta))
    dezenas = max(config.minimo_aposta, min(config.maximo_aposta, dezenas))

    metodo_analise = (dados.get('metodo_analise') or dados.get('metodo') or 'canonica_dinamica').strip().lower()
    if metodo_analise not in ROTULOS_METODO_ANALISE:
        metodo_analise = 'canonica_dinamica'
    rotulo_metodo = ROTULOS_METODO_ANALISE[metodo_analise]

    numeros_base = dados.get('numeros_base', [])
    if numeros_base and len(numeros_base) < dezenas:
        return jsonify({
            'erro': f'Para gerar apostas de {dezenas} dezenas no modo personalizado, selecione ao menos {dezenas} números favoritos.'
        }), 400

    modelo = modelo_canonico(loteria_type)
    if modelo is None:
        return jsonify({'erro': 'Histórico insuficiente para cálculo estatístico'}), 400

    filtro_inteligente = dados.get('filtro_inteligente', True) is not False
    if filtro_inteligente and metodo_analise not in ('frequencia_quentes', 'atraso_frios', 'fechamento'):
        # Gera candidatos extras e prioriza os que passam no filtro; completa com os demais se faltar
        candidatos = gerar_multiplos_jogos(
            modelo, min(quantidade_jogos * 6, 300), dezenas,
            numeros_base=numeros_base or None, metodo=metodo_analise
        )
        aprovados = [j for j in candidatos if avaliacao.jogo_aprovado(j, modelo)]
        restantes = [j for j in candidatos if j not in aprovados]
        jogos = (aprovados + restantes)[:quantidade_jogos]
    else:
        jogos = gerar_multiplos_jogos(
            modelo, quantidade_jogos, dezenas,
            numeros_base=numeros_base or None, metodo=metodo_analise
        )
    jogos_aprovados = [avaliacao.jogo_aprovado(j, modelo) for j in jogos]

    # +Milionária: sorteia também os 2 "trevos" (universo 1-6) com o mesmo Modelo Canônico 4.0
    trevos = None
    if loteria == LoteriaType.MAIS_MILIONARIA:
        qtd_trevos = max(2, min(6, int(dados.get('trevos_por_jogo', 2) or 2)))
        trevos_historico = [t for t in updater.carregar_trevos_local('mais_milionaria') if t and len(t) == 2]
        if len(trevos_historico) >= 10 and qtd_trevos < 6:
            modelo_trevo = ModeloCanonico40(trevos_historico, loteria, config_override=TREVO_CONFIG)
            trevos = [sorted(gerar_jogo_sugerido(modelo_trevo, qtd_trevos)) for _ in range(len(jogos))]
        else:
            trevos = [sorted(secrets.SystemRandom().sample(range(1, 7), qtd_trevos)) for _ in range(len(jogos))]

    # Timemania e Dia de Sorte: o volante exige escolher um Time do Coração / Mês da Sorte.
    complementos = opcoes_complemento(loteria_type)
    if complementos:
        sorteador = secrets.SystemRandom()
        complementos = [sorteador.choice(complementos) for _ in range(len(jogos))]
    else:
        complementos = None

    database.consume_user_credit(user_id)
    access = database.check_user_access(user_id)

    # Todo jogo gerado vai direto para "Meus Jogos Salvos" e entra na conferência automática
    aposta_id = database.salvar_aposta(
        loteria_type=loteria_type,
        modalidade='fechamento' if (numeros_base or metodo_analise == 'fechamento') else 'automatico',
        jogos=jogos,
        dezenas_por_jogo=dezenas,
        user_id=user_id,
        titulo=(f'Jogos ({rotulo_metodo}) a partir de {len(numeros_base)} números - {len(jogos)} jogo(s)' if numeros_base
                else f'{rotulo_metodo} - {len(jogos)} jogo(s)'),
        concurso_alvo=conferencia.proximo_concurso(loteria_type),
        trevos=trevos,
        complementos=complementos,
    )

    return jsonify({
        'sucesso': True,
        'aposta_id': aposta_id,
        'concurso_alvo': conferencia.proximo_concurso(loteria_type),
        'loteria': config.nome,
        'quantidade_jogos': len(jogos),
        'dezenas_por_jogo': dezenas,
        'jogos': jogos,
        'trevos': trevos,
        'complementos': complementos,
        'complemento_tipo': {'timemania': 'time', 'dia_de_sorte': 'mes'}.get(loteria_type),
        'opcoes_complemento': opcoes_complemento(loteria_type),
        'parecer': avaliacao.parecer_jogos(jogos, modelo),
        'filtro_inteligente': filtro_inteligente,
        'jogos_aprovados': jogos_aprovados,
        'modo': 'manual_pool' if numeros_base else 'caixa_automatico',
        'metodo_analise': metodo_analise,
        'metodo_rotulo': rotulo_metodo,
        'metricas_gerais': {
            'ict_medio': round(modelo.obter_resumo_analise()['estatisticas_gerais']['ict_medio'], 4),
            'entropia': round(modelo.obter_resumo_analise()['camada_informacional']['entropia'], 4)
        },
        'user_access': access
    })


@app.route('/api/fechamento/<loteria_type>', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)
def api_fechamento(loteria_type: str):
    """Gera um fechamento (desdobramento) com garantia a partir do grupo de números do usuário"""
    try:
        config = LOTERIAS_CONFIG[LoteriaType(loteria_type)]
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400

    user_id = session['user_id']
    bloqueio = _acesso_bloqueado(user_id)
    if bloqueio:
        return bloqueio

    dados = request.get_json(silent=True) or {}
    grupo = dados.get('grupo')
    try:
        tamanho_jogo = int(dados.get('dezenas_por_jogo', config.minimo_aposta))
        condicao = int(dados.get('condicao', config.sorteados))
        garantia = int(dados.get('garantia', 0))
    except (TypeError, ValueError):
        return jsonify({'erro': 'Parâmetros inválidos.'}), 400

    erro = fechamento.validar_pedido(loteria_type, config, grupo, tamanho_jogo, condicao, garantia)
    if erro:
        return jsonify({'erro': erro}), 400

    try:
        jogos = fechamento.gerar_fechamento(grupo, tamanho_jogo, condicao, garantia)
    except fechamento.FechamentoInviavel as e:
        return jsonify({'erro': str(e)}), 422

    # +Milionária: trevos por jogo (se fornecido pelo usuário ou gerado pelo modelo/sorteador)
    trevos = None
    if LoteriaType(loteria_type) == LoteriaType.MAIS_MILIONARIA:
        trevos_input = dados.get('trevos')
        if isinstance(trevos_input, list) and len(trevos_input) == len(jogos):
            trevos = trevos_input
        elif isinstance(trevos_input, list) and 2 <= len(trevos_input) <= 6:
            trevos = [sorted(trevos_input) for _ in range(len(jogos))]
        else:
            qtd_trevos = max(2, min(6, int(dados.get('trevos_por_jogo', 2) or 2)))
            trevos_historico = [t for t in updater.carregar_trevos_local('mais_milionaria') if t and len(t) == 2]
            if len(trevos_historico) >= 10 and qtd_trevos < 6:
                modelo_trevo = ModeloCanonico40(trevos_historico, LoteriaType(loteria_type), config_override=TREVO_CONFIG)
                trevos = [sorted(gerar_jogo_sugerido(modelo_trevo, qtd_trevos)) for _ in range(len(jogos))]
            else:
                trevos = [sorted(secrets.SystemRandom().sample(range(1, 7), qtd_trevos)) for _ in range(len(jogos))]

    # Timemania e Dia de Sorte: Time do Coração / Mês da Sorte
    complementos = None
    if loteria_type in conferencia.ROTULO_COMPLEMENTO:
        comp_input = dados.get('complementos') or dados.get('complemento')
        if isinstance(comp_input, list) and len(comp_input) == len(jogos):
            complementos = comp_input
        elif isinstance(comp_input, str) and comp_input:
            complementos = [comp_input for _ in range(len(jogos))]
        else:
            opcoes = opcoes_complemento(loteria_type)
            if opcoes:
                sorteador = secrets.SystemRandom()
                complementos = [sorteador.choice(opcoes) for _ in range(len(jogos))]

    database.consume_user_credit(user_id)
    aposta_id = database.salvar_aposta(
        loteria_type=loteria_type,
        modalidade='fechamento',
        jogos=jogos,
        dezenas_por_jogo=tamanho_jogo,
        user_id=user_id,
        titulo=f'Fechamento com garantia ({len(grupo)} dezenas, {garantia} acertos) - {len(jogos)} jogo(s)',
        concurso_alvo=conferencia.proximo_concurso(loteria_type),
        trevos=trevos,
        complementos=complementos,
    )
    chance = fechamento.chance_condicao(config, len(grupo), condicao)
    custo_jogo = comb(tamanho_jogo, config.minimo_aposta) * config.custo_minimo
    premio = re.sub(r'\s*[🏆⭐🎯]', '', conferencia.rotulo_premio(loteria_type, garantia) or f'{garantia} acertos')

    return jsonify({
        'sucesso': True,
        'aposta_id': aposta_id,
        'concurso_alvo': conferencia.proximo_concurso(loteria_type),
        'loteria': config.nome,
        'jogos': jogos,
        'trevos': trevos,
        'complementos': complementos,
        'complemento_tipo': {'timemania': 'time', 'dia_de_sorte': 'mes'}.get(loteria_type),
        'opcoes_complemento': opcoes_complemento(loteria_type),
        'quantidade_jogos': len(jogos),
        'dezenas_por_jogo': tamanho_jogo,
        'garantia_texto': (
            (f'Se os {condicao} números sorteados' if condicao == config.sorteados else f'Se {condicao} dos {config.sorteados} números sorteados')
            + f' estiverem entre os seus {len(grupo)}, '
            f'pelo menos um jogo fará {premio}.'
            + (' A garantia vale para cada um dos 2 sorteios.' if config.sorteios_por_concurso > 1 else '')
        ),
        'chance_condicao_um_em': round(1 / chance) if chance > 0 else None,
        'custo_total': round(len(jogos) * custo_jogo, 2),
        'user_access': database.check_user_access(user_id),
    })


@app.route('/api/avaliar-jogos/<loteria_type>', methods=['POST'])
@login_required
@rate_limit(max_requests=30, window_seconds=60)
def api_avaliar_jogos(loteria_type: str):
    """Avalia os jogos do usuário com base no Modelo Canônico 4.0 (sem IA)"""
    try:
        LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400

    jogos = (request.get_json(silent=True) or {}).get('jogos')
    if not isinstance(jogos, list) or not jogos:
        return jsonify({'erro': 'Envie ao menos um jogo.'}), 400
    if len(jogos) > 20:
        return jsonify({'erro': 'Avalie no máximo 20 jogos por vez.'}), 400

    modelo = modelo_canonico(loteria_type)
    if modelo is None:
        return jsonify({'erro': 'Histórico insuficiente para avaliação'}), 400

    return jsonify({
        'sucesso': True,
        'concursos_analisados': modelo.T,
        'avaliacoes': [avaliacao.avaliar_jogo(jogo, modelo) for jogo in jogos],
    })


# ==========================================
# ROTAS DE CHECKOUT PIX E MONETIZAÇÃO
# ==========================================

@app.route('/api/checkout/pix', methods=['POST'])
@login_required
def api_checkout_pix():
    """Gera cobrança PIX para assinatura VIP, recarga avulsa (24h) ou 1 análise promocional (R$ 1,00)"""
    try:
        dados = request.get_json(silent=True) or {}
        tipo = dados.get('tipo', 'vip_mensal')
        if tipo == 'vip_mensal':
            valor = PRECO_MENSAL
        elif tipo in ['analise', 'analise_1', 'credito']:
            valor = PRECO_ANALISE  # Bônus promocional: R$ 1,00 por análise completa
        else:
            valor = PRECO_AVULSO  # Preço único padronizado de R$ 5,00 para qualquer loteria
        loteria_type = dados.get('loteria_type')

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'sucesso': False, 'erro': 'Autenticação necessária', 'requer_login': True}), 401

        pagamento = database.create_payment(user_id=user_id, tipo=tipo, valor=valor, loteria_type=loteria_type)

        return jsonify({
            'sucesso': True,
            'payment_id': pagamento['id'],
            'valor': float(pagamento['valor']),
            'tipo': pagamento['tipo'],
            'pix_copia_cola': pagamento.get('pix_copia_cola'),
            'pix_qr_code_base64': pagamento.get('pix_qr_code_base64'),
            'pagamento': pagamento
        })
    except Exception as e:
        print(f"[CHECKOUT PIX] Erro ao gerar PIX: {e}")
        return jsonify({'sucesso': False, 'erro': f'Falha ao gerar cobrança PIX: {str(e)}'}), 500


@app.route('/api/checkout/confirmar/<int:payment_id>', methods=['POST'])
@login_required
def api_confirmar_pix(payment_id: int):
    """O PIX copia-e-cola não tem confirmação automática: o aviso do usuário só registra
    o pedido, e o acesso é liberado quando o administrador confere o extrato e aprova."""
    pagamento = database.get_payment_by_id(payment_id)
    if not pagamento or pagamento['user_id'] != session['user_id']:
        return jsonify({'sucesso': False, 'erro': 'Pagamento não encontrado'}), 404
    if pagamento.get('status') == 'aprovado':
        return jsonify({
            'sucesso': True,
            'mensagem': 'Pagamento aprovado! Acesso liberado.',
            'novo_status': 'aprovado',
            'access': database.check_user_access(session['user_id'])
        })
    return jsonify({
        'sucesso': False,
        'novo_status': pagamento.get('status'),
        'erro': 'Recebemos seu aviso. O acesso é liberado assim que o PIX for confirmado no extrato.'
    })


# ==========================================
# INTEGRAÇÃO INFINITEPAY (TAXA ZERO & D+0)
# ==========================================

INFINITEPAY_HANDLE = os.environ.get('INFINITEPAY_HANDLE', 'silvio_morais_')


def infinitepay_pagamento_confirmado(pagamento: dict, transaction_nsu, slug) -> bool:
    """Confirma na própria InfinitePay que o pedido foi pago no valor cobrado.
    Dados vindos do navegador ou do webhook não bastam: qualquer um pode forjá-los."""
    if not pagamento or not transaction_nsu or not slug:
        return False
    try:
        resp = requests.post("https://api.checkout.infinitepay.io/payment_check", json={
            "handle": INFINITEPAY_HANDLE,
            "order_nsu": str(pagamento['id']),
            "transaction_nsu": str(transaction_nsu),
            "slug": str(slug),
        }, timeout=12)
        dados = resp.json() if resp.status_code == 200 else {}
    except Exception as e:
        print(f"[INFINITEPAY] Falha ao consultar pagamento #{pagamento['id']}: {e}")
        return False
    valor_centavos = int(round(float(pagamento['valor']) * 100))
    pago = dados.get('paid_amount') or dados.get('amount') or 0
    return bool(dados.get('success') and dados.get('paid') and int(pago) >= valor_centavos)


def _criar_link_infinitepay(payment_id: int, valor, descricao: str, user, redirect_path: str):
    """Pede à InfinitePay um link de checkout para o pagamento; devolve a resposta HTTP."""
    base_url = request.host_url.rstrip('/')
    sep = '&' if '?' in redirect_path else '?'
    payload = {
        "handle": INFINITEPAY_HANDLE,
        "order_nsu": str(payment_id),
        "webhook_url": f"{base_url}/api/webhook/infinitepay",
        "redirect_url": f"{base_url}{redirect_path}{sep}checkout=sucesso&payment_id={payment_id}",
        "items": [
            {
                "quantity": 1,
                "price": int(round(float(valor) * 100)),
                "description": descricao
            }
        ]
    }
    if user:
        payload["customer"] = {
            "name": user.get('name') or 'Apostador',
            "email": user.get('email') or ''
        }
    return requests.post("https://api.checkout.infinitepay.io/links", json=payload, timeout=12)


@app.route('/api/checkout/infinitepay', methods=['POST'])
@login_required
def api_checkout_infinitepay():
    """Gera link de checkout oficial da InfinitePay (Taxa Zero no PIX e Liberação Imediata)"""
    try:
        dados = request.get_json(silent=True) or {}
        tipo = dados.get('tipo', 'vip_mensal')
        if tipo == 'vip_mensal':
            valor = PRECO_MENSAL
            descricao = "Plano VIP Mensal (30 dias) - Cálculo da Sorte"
        elif tipo in ['analise', 'analise_1', 'credito']:
            valor = PRECO_ANALISE
            descricao = "1 Análise Completa (R$ 1,00) - Cálculo da Sorte"
        else:
            valor = PRECO_AVULSO  # Preço único padronizado de R$ 5,00 para qualquer loteria
            descricao = "Acesso 24 Horas (R$ 5,00) - Cálculo da Sorte"
        loteria_type = dados.get('loteria_type')

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'sucesso': False, 'erro': 'Autenticação necessária', 'requer_login': True}), 401

        user = database.get_user_by_id(user_id)
        pagamento = database.create_payment(user_id=user_id, tipo=tipo, valor=valor, loteria_type=loteria_type)
        payment_id = pagamento['id']

        redirect_path = dados.get('redirect_path', '/planos')
        if not isinstance(redirect_path, str) or not redirect_path.startswith('/') or redirect_path.startswith('//'):
            redirect_path = '/planos'

        resp = _criar_link_infinitepay(payment_id, valor, descricao, user, redirect_path)
        if resp.status_code == 200:
            data_inf = resp.json()
            checkout_url = data_inf.get('url')
            return jsonify({
                'sucesso': True,
                'checkout_url': checkout_url,
                'payment_id': payment_id,
                'valor': valor,
                'tipo': tipo,
                'handle': INFINITEPAY_HANDLE
            })
        else:
            print(f"[INFINITEPAY] Erro na API ({resp.status_code}): {resp.text}")
            return jsonify({
                'sucesso': False,
                'erro': f'Falha ao gerar link na InfinitePay ({resp.status_code})',
                'detalhes': resp.text
            }), 400
    except Exception as e:
        print(f"[INFINITEPAY] Exceção na conexão: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/webhook/infinitepay', methods=['POST'])
def api_webhook_infinitepay():
    """Webhook para confirmação automática em tempo real de pagamentos da InfinitePay"""
    dados = request.get_json(silent=True) or request.form.to_dict() or {}
    print(f"[INFINITEPAY WEBHOOK] Dados recebidos: {dados}")

    order_nsu = dados.get('order_nsu')
    if not order_nsu:
        return jsonify({'erro': 'order_nsu não informado'}), 400

    try:
        payment_id = int(str(order_nsu).replace('P', '').strip())
    except ValueError:
        return jsonify({'erro': 'order_nsu inválido'}), 400

    pagamento = database.get_payment_by_id(payment_id)
    if not infinitepay_pagamento_confirmado(pagamento, dados.get('transaction_nsu'), dados.get('invoice_slug') or dados.get('slug')):
        print(f"[INFINITEPAY WEBHOOK] Pagamento #{payment_id} não confirmado pela InfinitePay; ignorado.")
        return jsonify({'sucesso': False, 'erro': 'Pagamento não confirmado'}), 400

    sucesso = database.approve_payment(payment_id)
    if sucesso:
        print(f"[INFINITEPAY WEBHOOK] Pagamento #{payment_id} aprovado com sucesso! Acesso liberado.")
        return jsonify({'sucesso': True, 'payment_id': payment_id, 'status': 'aprovado'}), 200
    else:
        return jsonify({'sucesso': True, 'mensagem': 'Pagamento já processado ou inexistente'}), 200


@app.route('/api/checkout/status/<int:payment_id>', methods=['GET'])
@login_required
def api_checkout_status(payment_id: int):
    """Consulta o status atual de um pagamento e auto-aprova se retorno do checkout com sucesso"""
    try:
        pagamento = database.get_payment_by_id(payment_id)
        if not pagamento:
            return jsonify({'sucesso': False, 'erro': 'Pagamento não encontrado'}), 404

        if pagamento['user_id'] != session.get('user_id'):
            return jsonify({'sucesso': False, 'erro': 'Pagamento não encontrado'}), 404

        # Retorno do checkout: só aprova se a InfinitePay confirmar o pagamento
        if pagamento.get('status') != 'aprovado' and infinitepay_pagamento_confirmado(
                pagamento, request.args.get('transaction_nsu'), request.args.get('slug')):
            database.approve_payment(payment_id)
            pagamento = database.get_payment_by_id(payment_id)

        access = database.check_user_access(session['user_id'])
        return jsonify({
            'sucesso': True,
            'status': pagamento.get('status'),
            'is_approved': pagamento.get('status') == 'aprovado',
            'access': access
        })
    except Exception as e:
        print(f"[CHECKOUT STATUS] Erro: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/admin/pagamentos', methods=['GET'])
@admin_required
def api_admin_pagamentos():
    """Lista todos os pagamentos para o painel admin"""
    pagamentos = database.get_all_payments()
    return jsonify({'sucesso': True, 'pagamentos': pagamentos, 'total': len(pagamentos)})


@app.route('/api/admin/pagamentos/<int:payment_id>/aprovar', methods=['POST'])
@admin_required
def api_admin_aprovar_pagamento(payment_id: int):
    """Aprova manualmente um pagamento no painel admin"""
    sucesso = database.approve_payment(payment_id)
    if sucesso:
        return jsonify({'sucesso': True, 'mensagem': f'Pagamento #{payment_id} aprovado com sucesso!'})
    return jsonify({'erro': 'Pagamento não encontrado ou já aprovado'}), 400


@app.route('/api/admin/pagamentos/<int:payment_id>', methods=['DELETE'])
@admin_required
def api_admin_excluir_pagamento(payment_id: int):
    """Exclui um pagamento no painel admin"""
    try:
        sucesso = database.delete_payment(payment_id)
        if sucesso:
            return jsonify({'sucesso': True, 'mensagem': f'Pagamento #{payment_id} removido com sucesso!'})
        return jsonify({'erro': 'Pagamento não encontrado'}), 400
    except Exception as e:
        print(f"[ADMIN PAGAMENTOS] Erro ao excluir pagamento {payment_id}: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/admin/config-pix', methods=['GET', 'POST'])
@admin_required
def api_admin_config_pix():
    """Consulta ou atualiza as configurações da chave PIX oficial"""
    if request.method == 'POST':
        dados = request.get_json() or {}
        chave = dados.get('chave', '').strip()
        beneficiario = dados.get('beneficiario', '').strip()
        cidade = dados.get('cidade', '').strip()
        
        if not chave:
            return jsonify({'erro': 'A chave PIX não pode ser vazia'}), 400
            
        config = database.save_pix_config(chave=chave, beneficiario=beneficiario, cidade=cidade)
        
        # Gerar amostra de payload e QR code para validação imediata
        amostra_copia_cola = database.gerar_pix_copia_e_cola(
            chave=config['chave'],
            nome=config['beneficiario'],
            cidade=config['cidade'],
            valor=5.00,
            txid='***'
        )
        amostra_qr = database.gerar_qrcode_pix_base64(amostra_copia_cola)
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Configurações do PIX salvas com sucesso!',
            'config': config,
            'amostra_copia_cola': amostra_copia_cola,
            'amostra_qr': amostra_qr
        })
        
    config = database.get_pix_config()
    amostra_copia_cola = database.gerar_pix_copia_e_cola(
        chave=config['chave'],
        nome=config['beneficiario'],
        cidade=config['cidade'],
        valor=5.00,
        txid='***'
    )
    amostra_qr = database.gerar_qrcode_pix_base64(amostra_copia_cola)
    return jsonify({
        'sucesso': True,
        'config': config,
        'amostra_copia_cola': amostra_copia_cola,
        'amostra_qr': amostra_qr
    })



# ==========================================
# BOLÕES (ADMIN)
# ==========================================

@app.route('/api/admin/boloes/config', methods=['GET', 'POST'])
@admin_required
def api_admin_bolao_config():
    """Consulta ou define a taxa de serviço e as regras dos bolões (exclusivo do admin)"""
    if request.method == 'POST':
        try:
            cfg = database.save_bolao_config(request.get_json(silent=True) or {})
        except ValueError as e:
            return jsonify({'erro': str(e)}), 400
        return jsonify({'sucesso': True, 'config': cfg})
    return jsonify({'sucesso': True, 'config': database.get_bolao_config()})


@app.route('/api/admin/boloes/simular', methods=['POST'])
@admin_required
def api_admin_bolao_simular():
    """Simula o preço da cota com a taxa configurada (ou a enviada, para testar antes de salvar)"""
    dados = request.get_json(silent=True) or {}
    try:
        config = LOTERIAS_CONFIG[LoteriaType(dados.get('loteria_type'))]
        dezenas = int(dados.get('dezenas_por_jogo', config.minimo_aposta))
        qtd = int(dados.get('quantidade_jogos', 1))
        cotas = int(dados.get('total_cotas', 1))
        cfg = bolao.normalizar_config({**database.get_bolao_config(), **(dados.get('config') or {})})
        if not 1 <= qtd <= 1000:
            raise ValueError('Quantidade de jogos deve ficar entre 1 e 1000.')
        precos = bolao.calcular_precos(config, [list(range(dezenas))] * qtd, cotas, cfg)
    except (ValueError, TypeError) as e:
        return jsonify({'erro': str(e) or 'Parâmetros inválidos.'}), 400
    return jsonify({'sucesso': True, 'loteria': config.nome, **bolao.precos_para_json(precos)})


@app.route('/api/admin/boloes', methods=['GET'])
@admin_required
def api_admin_boloes():
    return jsonify({'sucesso': True, 'boloes': database.get_all_boloes()})


@app.route('/api/admin/boloes/<int:bolao_id>/status', methods=['POST'])
@admin_required
def api_admin_bolao_status(bolao_id: int):
    status = (request.get_json(silent=True) or {}).get('status')
    if status == 'cancelado':
        # Cancelar estorna as cotas pagas e manda os pagamentos para a fila de reembolso
        afetados = database.cancelar_bolao(bolao_id, 'Cancelado pelo administrador.')
        return jsonify({'sucesso': True, 'reembolsos': len(afetados)})
    try:
        ok = database.update_bolao_status(bolao_id, status)
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    if not ok:
        return jsonify({'erro': 'Bolão não encontrado'}), 404
    return jsonify({'sucesso': True})


# ==========================================
# BOLÕES (ORGANIZADOR E VITRINE)
# ==========================================

def _usuario_logado():
    return database.get_user_by_id(session['user_id']) if session.get('user_id') else None


def _vitrine_visivel(cfg) -> bool:
    user = _usuario_logado()
    return cfg['ativo'] or bool(user and user.get('role') == 'admin')


def _montar_bolao(user_id: int, dados: dict):
    """Valida o fechamento salvo escolhido pelo organizador e calcula os preços com a taxa do admin."""
    try:
        aposta_id = int(dados.get('aposta_id'))
        total_cotas = int(dados.get('total_cotas'))
    except (TypeError, ValueError):
        raise ValueError('Escolha um jogo salvo e informe o número de cotas.')
    aposta = database.obter_aposta(aposta_id)
    if not aposta or aposta.get('user_id') != user_id:
        raise LookupError('Jogo salvo não encontrado.')
    loteria_type = aposta['loteria_type']
    if loteria_type not in bolao.LOTERIAS_SUPORTADAS:
        raise ValueError('Esta loteria ainda não está disponível para bolões.')
    config = LOTERIAS_CONFIG[LoteriaType(loteria_type)]
    jogos = bolao.validar_jogos(config, aposta['jogos'])

    proximo = conferencia.proximo_concurso(loteria_type)
    concurso = aposta.get('concurso_alvo') or proximo
    if not concurso:
        raise ValueError('Não foi possível identificar o próximo concurso desta loteria.')
    if proximo and concurso < proximo:
        raise ValueError(f'O concurso {concurso} já foi sorteado. Gere um novo fechamento para o concurso {proximo}.')

    precos = bolao.calcular_precos(config, jogos, total_cotas, database.get_bolao_config())
    return aposta, config, jogos, concurso, precos


def _organizador_ou_erro():
    user = _usuario_logado()
    if not bolao.pode_organizar(user, database.get_bolao_config()):
        return None, (jsonify({'erro': 'Seu perfil não pode organizar bolões. Fale com o administrador.'}), 403)
    return user, None


@app.route('/boloes')
def pagina_boloes():
    """Vitrine pública de bolões abertos"""
    cfg = database.get_bolao_config()
    if not _vitrine_visivel(cfg):
        return redirect(url_for('index'))
    return render_template('boloes.html', boloes=database.listar_boloes_abertos(),
                           loterias=_NOMES_LOTERIAS, modulo_ativo=cfg['ativo'], current_user=_usuario_logado())


@app.route('/boloes/<int:bolao_id>')
def pagina_bolao(bolao_id: int):
    cfg = database.get_bolao_config()
    if not _vitrine_visivel(cfg):
        return redirect(url_for('index'))
    b = database.get_bolao(bolao_id, com_jogos=True)
    if not b:
        return redirect(url_for('pagina_boloes'))
    user = _usuario_logado()
    minhas = database.listar_cotas_usuario(user['id'], bolao_id) if user else []
    resultado = json.loads(b['resultado_json']) if b.get('resultado_json') else None
    return render_template('bolao_detalhe.html', b=b, loterias=_NOMES_LOTERIAS, cfg=cfg, current_user=user,
                           minhas_cotas=minhas, resultado=resultado)


@app.route('/organizador')
@login_required
def pagina_organizador():
    user = _usuario_logado()
    cfg = database.get_bolao_config()
    if not bolao.pode_organizar(user, cfg):
        return redirect(url_for('dashboard'))
    fechamentos = [a for a in database.listar_apostas(user_id=user['id'], session_id=session.get('session_id'), limit=100)
                   if a.get('user_id') == user['id'] and a['loteria_type'] in bolao.LOTERIAS_SUPORTADAS]
    return render_template('organizador.html', user=user, current_user=user, cfg=cfg, fechamentos=fechamentos,
                           boloes=database.listar_boloes_organizador(user['id']), loterias=_NOMES_LOTERIAS)


@app.route('/api/boloes', methods=['GET'])
def api_listar_boloes():
    cfg = database.get_bolao_config()
    if not _vitrine_visivel(cfg):
        return jsonify({'erro': 'Bolões indisponíveis no momento.'}), 404
    return jsonify({'sucesso': True, 'boloes': database.listar_boloes_abertos()})


@app.route('/api/boloes/preview', methods=['POST'])
@login_required
def api_preview_bolao():
    """Mostra ao organizador o custo e o valor da cota antes de criar o bolão"""
    user, erro = _organizador_ou_erro()
    if erro:
        return erro
    try:
        aposta, config, jogos, concurso, precos = _montar_bolao(user['id'], request.get_json(silent=True) or {})
    except LookupError as e:
        return jsonify({'erro': str(e)}), 404
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    return jsonify({'sucesso': True, 'loteria': config.nome, 'concurso': concurso,
                    'quantidade_jogos': len(jogos), **bolao.precos_para_json(precos)})


@app.route('/api/boloes', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)
def api_criar_bolao():
    """Cria um bolão a partir de um fechamento salvo; preços sempre recalculados no servidor"""
    user, erro = _organizador_ou_erro()
    if erro:
        return erro
    dados = request.get_json(silent=True) or {}
    try:
        aposta, config, jogos, concurso, precos = _montar_bolao(user['id'], dados)
    except LookupError as e:
        return jsonify({'erro': str(e)}), 404
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400

    titulo = str(dados.get('titulo') or '').strip()[:120] or f'Bolão {config.nome} - Concurso {concurso}'
    complementos = aposta.get('complementos') if isinstance(aposta.get('complementos'), list) else None
    bolao_id = database.create_bolao(
        organizador_id=user['id'], loteria_type=aposta['loteria_type'], concurso=concurso, titulo=titulo,
        jogos=jogos, custos=[bolao.custo_jogo(config, len(j)) for j in jogos], precos=precos,
        complementos=complementos if complementos and len(complementos) == len(jogos) else None,
        aposta_origem_id=aposta['id'],
    )
    sorteio = bolao.data_do_sorteio(updater.carregar_ultimo_resultado_local(aposta['loteria_type']), concurso)
    prazo = bolao.calcular_prazo_comprovante(sorteio, database.get_bolao_config()['horas_comprovante'])
    if prazo:
        database.definir_prazo_bolao(bolao_id, sorteio, prazo)
    return jsonify({'sucesso': True, 'bolao_id': bolao_id, 'url': url_for('pagina_bolao', bolao_id=bolao_id),
                    **bolao.precos_para_json(precos)}), 201


@app.route('/api/boloes/<int:bolao_id>/fechar', methods=['POST'])
@login_required
def api_fechar_bolao(bolao_id: int):
    user, erro = _organizador_ou_erro()
    if erro:
        return erro
    if not database.fechar_vendas_bolao(bolao_id, user['id']):
        return jsonify({'erro': 'Bolão não encontrado, não é seu ou já está fechado.'}), 404
    return jsonify({'sucesso': True})


@app.route('/api/boloes/<int:bolao_id>/comprar', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)
def api_comprar_cota(bolao_id: int):
    """Reserva uma cota e gera o checkout Pix; a cota só vira 'paga' quando a InfinitePay confirma"""
    cfg = database.get_bolao_config()
    if not _vitrine_visivel(cfg):
        return jsonify({'erro': 'Bolões indisponíveis no momento.'}), 404
    if not (request.get_json(silent=True) or {}).get('aceite_termos'):
        return jsonify({'erro': 'Confirme que leu e aceita os termos do bolão para continuar.'}), 400
    b = database.get_bolao(bolao_id)
    if not b or b['status'] != 'aberto':
        return jsonify({'erro': 'Este bolão não está aberto para vendas.'}), 400

    user = _usuario_logado()
    cota = database.reservar_cota(bolao_id, user['id'], cfg['minutos_reserva'])
    if not cota:
        return jsonify({'erro': 'As cotas deste bolão esgotaram.'}), 409

    pagamento = database.get_payment_by_id(cota['payment_id']) if cota.get('payment_id') else None
    if not pagamento or pagamento.get('status') != 'pendente':
        pagamento = database.create_payment(user_id=user['id'], tipo='cota_bolao', valor=float(b['valor_cota']),
                                            loteria_type=b['loteria_type'])
        database.vincular_pagamento_cota(cota['id'], pagamento['id'], bolao_id)

    descricao = f"Cota {cota['numero']} - {b['titulo']}"[:100]
    try:
        resp = _criar_link_infinitepay(pagamento['id'], b['valor_cota'], descricao, user, f'/boloes/{bolao_id}')
        checkout_url = resp.json().get('url') if resp.status_code == 200 else None
    except Exception as e:
        print(f"[BOLOES] Falha ao gerar checkout da cota #{cota['id']}: {e}")
        checkout_url = None
    if not checkout_url:
        return jsonify({'erro': 'Não foi possível gerar o pagamento agora. Sua cota segue reservada; tente de novo.'}), 502
    return jsonify({'sucesso': True, 'checkout_url': checkout_url, 'payment_id': pagamento['id'],
                    'cota_numero': cota['numero'], 'reservada_ate': cota['reservada_ate'].isoformat(),
                    'valor': float(b['valor_cota'])})


@app.route('/bilhete/<hash_bilhete>')
def pagina_bilhete(hash_bilhete: str):
    """Bilhete digital público, verificável pelo hash"""
    bilhete = database.get_bilhete(hash_bilhete) if re.fullmatch(r'[0-9a-f]{64}', hash_bilhete) else None
    if not bilhete:
        return render_template('bilhete.html', bilhete=None, loterias=_NOMES_LOTERIAS), 404
    return render_template('bilhete.html', bilhete=bilhete, loterias=_NOMES_LOTERIAS, current_user=_usuario_logado())


@app.route('/minhas-cotas')
@login_required
def pagina_minhas_cotas():
    user = _usuario_logado()
    return render_template('minhas_cotas.html', cotas=database.listar_cotas_usuario(user['id']),
                           loterias=_NOMES_LOTERIAS, current_user=user)


@app.route('/api/boloes/<int:bolao_id>/comprovante', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)
def api_enviar_comprovante(bolao_id: int):
    """O organizador anexa a foto/PDF do comprovante da lotérica; o bolão passa a 'registrado'"""
    user = _usuario_logado()
    b = database.get_bolao(bolao_id)
    if not b or not user or (b['organizador_id'] != user['id'] and user.get('role') != 'admin'):
        return jsonify({'erro': 'Bolão não encontrado.'}), 404
    if b['status'] not in ('aberto', 'fechado', 'registrado'):
        return jsonify({'erro': 'Este bolão não aceita mais comprovante.'}), 400
    arquivo = request.files.get('arquivo')
    if not arquivo:
        return jsonify({'erro': 'Envie a foto ou o PDF do comprovante.'}), 400
    conteudo = arquivo.read(bolao.TAMANHO_MAX_COMPROVANTE + 1)
    if len(conteudo) > bolao.TAMANHO_MAX_COMPROVANTE:
        return jsonify({'erro': 'Arquivo maior que 4 MB. Reduza a foto ou o PDF.'}), 400
    mime = bolao.tipo_do_comprovante(conteudo)
    if not mime:
        return jsonify({'erro': 'Formato não aceito. Use JPG, PNG ou PDF.'}), 400
    sha = database.salvar_comprovante(bolao_id, conteudo, mime, arquivo.filename or 'comprovante', user['id'])
    if not sha:
        return jsonify({'erro': 'Não foi possível registrar o comprovante.'}), 400
    return jsonify({'sucesso': True, 'comprovante_hash': sha, 'url': url_for('ver_comprovante', bolao_id=bolao_id)})


@app.route('/boloes/<int:bolao_id>/comprovante')
def ver_comprovante(bolao_id: int):
    comp = database.get_comprovante(bolao_id)
    if not comp:
        return redirect(url_for('pagina_bolao', bolao_id=bolao_id))
    ext = {'image/jpeg': 'jpg', 'image/png': 'png', 'application/pdf': 'pdf'}[comp['mime']]
    resp = Response(comp['conteudo'], mimetype=comp['mime'])
    resp.headers['Content-Disposition'] = f'inline; filename="comprovante-bolao-{bolao_id}.{ext}"'
    resp.headers['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"
    resp.headers['Cache-Control'] = 'private, max-age=300'
    return resp


@app.route('/api/admin/boloes/rotina', methods=['POST'])
@admin_required
def api_admin_bolao_rotina():
    """Roda agora a rotina diária (prazos, alertas, cancelamentos e conferência)"""
    return jsonify({'sucesso': True, **boloes_rotina.executar()})


@app.route('/api/admin/boloes/<int:bolao_id>/premio', methods=['POST'])
@admin_required
def api_admin_bolao_premio(bolao_id: int):
    """Registra o prêmio líquido recebido e calcula o rateio por cota"""
    b = database.get_bolao(bolao_id)
    if not b:
        return jsonify({'erro': 'Bolão não encontrado'}), 404
    try:
        valor = str((request.get_json(silent=True) or {}).get('valor_premio', '')).replace(',', '.')
        por_cota = bolao.rateio_por_cota(valor, b['total_cotas'])
    except Exception:
        return jsonify({'erro': 'Informe um valor de prêmio válido.'}), 400
    if not database.registrar_premio_bolao(bolao_id, valor, por_cota):
        return jsonify({'erro': 'Só é possível registrar prêmio em bolão com status premiado.'}), 400
    return jsonify({'sucesso': True, 'premio_por_cota': float(por_cota)})


@app.route('/api/admin/reembolsos/<int:payment_id>/concluir', methods=['POST'])
@admin_required
def api_admin_concluir_reembolso(payment_id: int):
    if not database.marcar_reembolsado(payment_id):
        return jsonify({'erro': 'Reembolso não encontrado ou já concluído'}), 404
    return jsonify({'sucesso': True})


# ==========================================
# ROTAS DO AGENTE IA CONSULTOR
# ==========================================

@app.route('/api/ia/chat', methods=['POST'])
@login_required
@rate_limit(max_requests=15, window_seconds=60)
def api_ia_chat():
    """Bate-papo consultivo com o Agente IA sobre probabilidades e estratégias"""
    dados = request.get_json() or {}
    pergunta = (dados.get('pergunta') or dados.get('mensagem') or '').strip()
    loteria_type = dados.get('loteria_type', 'mega_sena')

    if not pergunta:
        return jsonify({'erro': 'Pergunta vazia'}), 400

    try:
        loteria = LoteriaType(loteria_type)
        config = LOTERIAS_CONFIG[loteria]
        loteria_nome = config.nome
    except ValueError:
        loteria_nome = 'Loteria da Caixa'

    
    # Identificar usuário logado ou anonimo
    user_ident = "Anônimo"
    if 'user_id' in session:
        usr = database.get_user_by_id(session['user_id'])
        if usr:
            user_ident = usr.get('email', f"ID: {session['user_id']}")
            
    resposta = ai_agent.responder_chat_consultor(pergunta, loteria_nome, user_ident=user_ident)
    return jsonify({'sucesso': True, 'resposta': resposta})


@app.route('/download/historico/<loteria_type>/<formato>', methods=['GET'])
def download_historico(loteria_type: str, formato: str):
    """Download do histórico oficial em formato .md ou .txt"""
    try:
        loteria = LoteriaType(loteria_type)
        config = LOTERIAS_CONFIG[loteria]
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400

    historico = carregar_historico(loteria_type)
    meta = updater.carregar_meta(loteria_type)
    ultimo = meta.get('ultimo_concurso', len(historico))
    data_apuracao = meta.get('data_apuracao', 'Recente')
    atualizado_em = meta.get('atualizado_em', datetime.now().strftime('%d/%m/%Y %H:%M:%S'))

    if formato == 'md':
        linhas = [
            f"# Histórico Oficial de Sorteios — {config.nome}",
            f"**Última Atualização:** {atualizado_em}  ",
            f"**Último Concurso Caixa:** #{ultimo} ({data_apuracao})  ",
            f"**Total de Concursos Catalogados:** {len(historico)}  ",
            "",
            "| Concurso Histórico | Dezenas Sorteadas |",
            "| :---: | :--- |"
        ]
        for idx, sorteio in enumerate(reversed(historico), 1):
            dezenas_str = ", ".join(f"{n:02d}" for n in sorteio)
            linhas.append(f"| #{len(historico) - idx + 1} | {dezenas_str} |")
        
        conteudo = "\n".join(linhas)
        mimetype = 'text/markdown; charset=utf-8'
        extensao = 'md'
    elif formato == 'txt':
        linhas = [
            "=" * 60,
            f"HISTÓRICO OFICIAL DE SORTEIOS — {config.nome.upper()}",
            f"Última Atualização: {atualizado_em}",
            f"Último Concurso Caixa: #{ultimo} ({data_apuracao})",
            f"Total de Concursos Catalogados: {len(historico)}",
            "=" * 60,
            ""
        ]
        for idx, sorteio in enumerate(reversed(historico), 1):
            dezenas_str = " ".join(f"{n:02d}" for n in sorteio)
            linhas.append(f"Concurso #{len(historico) - idx + 1:04d}: [ {dezenas_str} ]")
        
        conteudo = "\n".join(linhas)
        mimetype = 'text/plain; charset=utf-8'
        extensao = 'txt'
    else:
        return jsonify({'erro': 'Formato não suportado (use md ou txt)'}), 400

    nome_arquivo = f"historico_{loteria_type}_{ultimo}.{extensao}"
    return Response(
        conteudo,
        mimetype=mimetype,
        headers={'Content-Disposition': f'attachment; filename="{nome_arquivo}"'}
    )


@app.route('/download/jogos/<loteria_type>/<formato>', methods=['POST'])
def download_jogos(loteria_type: str, formato: str):
    """Exportar apostas calculadas em formato .md ou .txt"""
    try:
        loteria = LoteriaType(loteria_type)
        config = LOTERIAS_CONFIG[loteria]
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400

    dados = request.get_json() or {}
    jogos = dados.get('jogos', [])
    trevos = dados.get('trevos') or []
    complementos = dados.get('complementos') or []

    if not jogos:
        return jsonify({'erro': 'Nenhum jogo fornecido para download'}), 400

    tem_trevos = bool(trevos and len(trevos) >= len(jogos) and any(t for t in trevos))
    tem_comp = bool(complementos and len(complementos) >= len(jogos) and any(c for c in complementos))
    rotulo_comp = "Time do Coração ⚽" if loteria_type == 'timemania' else "Mês da Sorte 📅"

    data_hora = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')

    if formato == 'md':
        headers_tab = ["Jogo", "Dezenas Recomendadas"]
        alinhamentos = [":---:", ":---"]
        if tem_trevos:
            headers_tab.append("Trevos da Sorte 🍀")
            alinhamentos.append(":---:")
        if tem_comp:
            headers_tab.append(rotulo_comp)
            alinhamentos.append(":---:")
        headers_tab.append("Total Dezenas")
        alinhamentos.append(":---:")

        linhas = [
            f"# Palpites Gerados — {config.nome}",
            "**Metodologia:** Modelo Canônico 4.0 (Otimização Hexagonal + MCP-MD 1.0)  ",
            f"**Data de Geração:** {data_hora}  ",
            f"**Total de Jogos:** {len(jogos)}  ",
            "",
            "| " + " | ".join(headers_tab) + " |",
            "| " + " | ".join(alinhamentos) + " |"
        ]
        for i, j in enumerate(jogos, 1):
            dezenas_str = ", ".join(f"{n:02d}" for n in j)
            colunas = [f"**Jogo {i:02d}**", dezenas_str]
            if tem_trevos:
                t_str = ", ".join(str(t) for t in (trevos[i - 1] or []))
                colunas.append(f"🍀 {t_str}")
            if tem_comp:
                colunas.append(str(complementos[i - 1] or '-'))
            colunas.append(str(len(j)))
            linhas.append("| " + " | ".join(colunas) + " |")

        conteudo = "\n".join(linhas)
        mimetype = 'text/markdown; charset=utf-8'
        extensao = 'md'
    elif formato == 'txt':
        linhas = [
            "=" * 60,
            f"PALPITES GERADOS — {config.nome.upper()}",
            f"Modelo Canônico 4.0 + MCP-MD 1.0 (AGENTE LLN ICT FR MCOH)",
            f"Data: {data_hora}",
            f"Total de Combinações: {len(jogos)}",
            "=" * 60,
            ""
        ]
        for i, j in enumerate(jogos, 1):
            dezenas_str = " ".join(f"{n:02d}" for n in j)
            linha = f"Jogo {i:02d}: [ {dezenas_str} ] ({len(j)} dezenas)"
            if tem_trevos and i - 1 < len(trevos) and trevos[i - 1]:
                t_str = " ".join(str(t) for t in trevos[i - 1])
                linha += f" + Trevos: [ {t_str} ]"
            if tem_comp and i - 1 < len(complementos) and complementos[i - 1]:
                r = "Time" if loteria_type == 'timemania' else "Mês"
                linha += f" + {r}: {complementos[i - 1]}"
            linhas.append(linha)
        
        linhas.extend([
            "",
            "=" * 60,
            "Boa sorte nas suas apostas!",
            "=" * 60
        ])
        conteudo = "\n".join(linhas)
        mimetype = 'text/plain; charset=utf-8'
        extensao = 'txt'
    else:
        return jsonify({'erro': 'Formato inválido'}), 400

    nome_arquivo = f"palpites_{loteria_type}_{len(jogos)}jogos.{extensao}"
    return Response(
        conteudo,
        mimetype=mimetype,
        headers={'Content-Disposition': f'attachment; filename="{nome_arquivo}"'}
    )


@app.route('/api/cron/atualizar', methods=['GET', 'POST'])
def cron_atualizar():
    """Endpoint chamado pelo Vercel Cron Job pontualmente às 23:00h do Horário de Brasília (02:00 UTC)
    e pelo GitHub Action. Com CRON_SECRET definido, exige o cabeçalho Authorization: Bearer <CRON_SECRET>
    (o Vercel Cron envia esse cabeçalho sozinho quando a variável existe no projeto)."""
    segredo = os.environ.get('CRON_SECRET')
    if segredo:
        recebido = request.headers.get('Authorization', '')
        if not secrets.compare_digest(recebido.encode(), f'Bearer {segredo}'.encode()):
            return jsonify({'sucesso': False, 'erro': 'Não autorizado'}), 401
    else:
        print("[CRON] CRON_SECRET não definida: endpoint de sincronização sem proteção.")
    agora_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    print(f"[CRON] Executando sincronização diária oficial da Caixa às 23:00h BRT ({agora_str})...")
    res = updater.sincronizar_todas(n_historico=50)
    res['boloes'] = boloes_rotina.executar()
    return jsonify(res)


@app.route('/comparar-concursos/<loteria_type>', methods=['POST'])
def comparar_concursos(loteria_type: str):
    """Comparar concurso atual com padrões históricos"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    dados = request.get_json() or {}
    concurso_atual = dados.get('concurso', [])

    modelo = modelo_canonico(loteria_type)
    if modelo is None:
        return jsonify({'erro': 'Histórico insuficiente'}), 400
    analises = modelo.analisar_todos_elementos()
    
    scores_concurso = []
    numeros_analisados = []
    
    for numero in concurso_atual:
        if numero in modelo.contagens_total:
            analise = next((a for a in analises if a.numero == numero), None)
            if analise:
                scores_concurso.append(analise.score_mcp)
                numeros_analisados.append({
                    'numero': numero,
                    'score_mcp': round(analise.score_mcp, 4),
                    'classe': analise.classe,
                    'maturidade': analise.maturidade
                })
    
    score_medio_concurso = sum(scores_concurso) / len(scores_concurso) if scores_concurso else 0
    score_medio_geral = sum(a.score_mcp for a in analises) / len(analises)
    
    return jsonify({
        'concurso': concurso_atual,
        'numeros_analisados': numeros_analisados,
        'score_medio_concurso': round(score_medio_concurso, 4),
        'score_medio_geral': round(score_medio_geral, 4),
        'performance_relativa': round(score_medio_concurso / score_medio_geral, 4) if score_medio_geral > 0 else 0,
        'interpretacao': 'Acima da média' if score_medio_concurso > score_medio_geral else 'Abaixo da média'
    })


# ==========================================
# ROTAS DE SEO, GEO E LLM DISCOVERABILITY
# ==========================================

@app.route('/favicon.ico')
def favicon():
    """Serve o ícone .ico oficial do dado da sorte na raiz do site"""
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


import seo_routes
seo_routes.register_seo_routes(app)


@app.route('/sobre')
def sobre():
    return render_template('seo_sobre.html')

@app.route('/metodologia')
def metodologia():
    return render_template('seo_metodologia.html')



@app.route('/<path:path>.md')
def serve_markdown(path):
    # Fallback genérico para LLMs (na prática, chamaria a rota real e extrairia o texto, ou buscaria de um cache MD)
    # Por segurança e simplicidade, redirecionamos para o llms-full ou enviamos um texto limpo
    return Response(f"# Cálculo da Sorte\nVeja mais em https://www.calculodasorte.com.br/{path}", mimetype='text/markdown')


@app.route('/8473a2b1c9f4d5e68473a2b1c9f4d5e6.txt')
def indexnow_key():
    return Response("8473a2b1c9f4d5e68473a2b1c9f4d5e6", mimetype='text/plain')


@app.route('/autor/silvio-morais')
def autor():
    return render_template('seo_autor.html')


@app.route('/blog/quais-os-numeros-que-mais-saem-na-lotofacil')
def old_blog_post_redirect():
    return redirect('/lotofacil/numeros-mais-sorteados', code=301)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

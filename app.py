"""
Aplicação Web Flask para Análise Estatística de Loterias
Baseada no Modelo Canônico 3.0 + MCP-MD 1.0
Com Painel Administrativo, Gestão de Usuários e Atualizador Diário Caixa
"""

from functools import wraps
import json
import os
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, send_from_directory
from werkzeug.security import check_password_hash

import requests
import database
import updater
import ai_agent
from core import (
    ModeloCanonico30, 
    ValidaçãoCamada7, 
    gerar_jogo_sugerido,
    gerar_multiplos_jogos,
    LoteriaType, 
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
PRECO_AVULSO = 5.00
PRECO_MENSAL = 49.90
secret_from_env = os.getenv('SECRET_KEY')
if not secret_from_env:
    secret_from_env = '6f04de83e1c5a30f789647fcece0a8052dc5ae7ecc5f08f4b75cb9f9dd8734ef'
app.config['SECRET_KEY'] = secret_from_env
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Inicializar Banco de Dados e Agendador de Loterias
database.init_db()
updater.iniciar_agendador()

# Diretório para armazenar dados
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)


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
    return render_template('landing.html')


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
        'dias_resumo': 'Ter, Qui, Sáb',
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
        'dias_resumo': 'Seg a Sáb',
        'seo_title': 'Desdobramento e Simulador Lotofácil 15 a 20 números | Grátis',
        'seo_desc': 'Simulador de desdobramento Lotofácil com inteligência artificial. Gere combinações precisas baseadas nos padrões históricos para 14 e 15 pontos.',
    },
    'quina': {
        'cor': '#260085',
        'cor_dark': '#170052',
        'cor_gradiente': 'linear-gradient(135deg, #260085 0%, #11003d 100%)',
        'cor_glow': 'rgba(38, 0, 133, 0.45)',
        'icone': '⭐',
        'tag': 'Sorteio de Seg a Sáb',
        'tag_bg': 'rgba(38, 0, 133, 0.12)',
        'tag_cor': '#170052',
        'dias_resumo': 'Seg a Sáb',
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
        'dias_resumo': 'Qua, Sáb',
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
        'dias_resumo': 'Ter, Qui, Sáb',
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
        'dias_resumo': 'Ter, Qui, Sáb',
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
        'dias_resumo': 'Ter, Qui, Sáb',
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
    """Auto-cadastro de novos apostadores com 1 crédito grátis de cortesia"""
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
                    credits=1, # 1 crédito de degustação gratuito!
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
        'description': 'Aprenda o princípio das matrizes matemáticas ortogonais e sistemas de redução. Veja como cercar dezenas garante prêmios secundários e reduz o custo das apostas.',
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
        'template': 'blog/artigo_11.html'
    },
    'como-ganhar-na-lotofacil-garantido': {
        'title': 'Como ganhar na Lotofácil garantido: O fim do mito e a estatística real',
        'date': '2026-09-13',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Existe método 100% garantido? Desmistificamos falsas promessas e ensinamos como simuladores de desdobramento da Lotofácil aumentam suas chances.',
        'template': 'blog/artigo_12.html'
    },
    'diferenca-entre-desdobramento-e-fechamento': {
        'title': 'Diferença entre Desdobramento e Fechamento Matemático',
        'date': '2026-09-13',
        'author': 'Equipe Cálculo da Sorte',
        'description': 'Aprenda de uma vez por todas a diferença técnica entre desdobramento e fechamento para economizar nas suas apostas da Mega-Sena e Quina.',
        'template': 'blog/artigo_13.html'
    }
}

RESULTS_CACHE = {}
RESULTS_CACHE_TIME = {}

@app.route('/resultados/<loteria_type>')
def ver_resultado(loteria_type):
    if loteria_type not in LOTERIAS_CONFIG:
        return "Loteria não encontrada", 404
    
    slug = updater.LOTERIAS_SLUGS.get(loteria_type)
    if not slug:
        return "Loteria não suportada para resultados", 404
        
    import time
    now = time.time()
    
    # Cache em memória (10 minutos) para aguentar o pico de acessos do Google (Tráfego de Vaidade)
    if loteria_type in RESULTS_CACHE and (now - RESULTS_CACHE_TIME.get(loteria_type, 0)) < 600:
        dados_caixa = RESULTS_CACHE[loteria_type]
    else:
        dados_caixa = updater.consultar_caixa(slug)
        if dados_caixa:
            RESULTS_CACHE[loteria_type] = dados_caixa
            RESULTS_CACHE_TIME[loteria_type] = now
        else:
            dados_caixa = RESULTS_CACHE.get(loteria_type)
            
    if not dados_caixa:
        return "Não foi possível carregar os resultados da Caixa no momento. Tente novamente.", 503
        
    numeros = updater.extrair_dezenas(dados_caixa, slug)
    
    return render_template('resultado.html', 
                           loteria=LOTERIAS_CONFIG[loteria_type],
                           dados=dados_caixa, 
                           numeros=numeros)


@app.route('/blog')
def blog_index():
    return render_template('blog_index.html', posts=BLOG_POSTS)


@app.route('/blog/<slug>')
def blog_post(slug):
    post = BLOG_POSTS.get(slug)
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


@app.route('/api/usuario/exportar-dados', methods=['GET'])
@login_required
def api_usuario_exportar_dados():
    """Portabilidade de dados cadastrais e apostas em formato JSON (Art. 18, V da LGPD) como arquivo de download"""
    import json
    user_id = session['user_id']
    dados_portabilidade = database.export_user_data(user_id)
    json_bytes = json.dumps(dados_portabilidade, indent=2, ensure_ascii=False).encode('utf-8')
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
        api_keys_config=ui_api_keys_config
    )


@app.route('/admin/config-ia', methods=['POST'])
@login_required
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


# ==========================================
# APIS ESTATÍSTICAS DO MODELO CANÔNICO 3.0
# ==========================================

@app.route('/api/analise/<loteria_type>', methods=['POST'])
def api_analise(loteria_type: str):
    """API para realizar análise estatística completa"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    dados = request.get_json() or {}
    historico_input = dados.get('historico', [])
    
    # Se não houver histórico no input, carregar do arquivo
    if not historico_input:
        historico_input = carregar_historico(loteria_type)
    
    if len(historico_input) < 10:
        return jsonify({
            'erro': 'Histórico insuficiente. Mínimo de 10 concursos necessários para cálculo estatístico completo.',
            'concursos_atuais': len(historico_input)
        }), 400
    
    # Criar modelo e realizar análise
    modelo = ModeloCanonico30(historico_input, loteria)
    resumo = modelo.obter_resumo_analise()
    
    # Realizar validações da Camada 7
    validacao = ValidaçãoCamada7(modelo)
    resumo['validacao_camada7'] = validacao.validacao_completa()
    
    # Gerar sugestões de jogos
    config = LOTERIAS_CONFIG[loteria]
    resumo['sugestoes'] = {
        'jogo_simples': gerar_jogo_sugerido(modelo, config.minimo_aposta),
        'jogo_medio': gerar_jogo_sugerido(modelo, min(config.minimo_aposta + 2, config.maximo_aposta)),
    }
    
    return jsonify(resumo)


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

    aposta_id = database.salvar_aposta(
        loteria_type=loteria_type,
        modalidade=modalidade,
        jogos=jogos,
        dezenas_por_jogo=dezenas_por_jogo,
        user_id=user_id,
        session_id=session_id,
        titulo=titulo
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
    historico = carregar_historico(loteria_type)
    meta = updater.carregar_meta(loteria_type)

    if not historico:
        return jsonify({'erro': 'Nenhum sorteio oficial disponível para conferência'}), 400

    ultimo_sorteio = historico[-1]
    set_sorteio = set(ultimo_sorteio)

    conferencia_jogos = []
    premiacoes_resumo = {}

    for idx, jogo in enumerate(aposta.get('jogos', []), 1):
        set_jogo = set(jogo)
        acertos = sorted(list(set_jogo.intersection(set_sorteio)))
        qtd_acertos = len(acertos)
        
        rotulo_premio = None
        if loteria_type == 'mega_sena':
            if qtd_acertos == 6: rotulo_premio = 'Sena (6 acertos) 🏆'
            elif qtd_acertos == 5: rotulo_premio = 'Quina (5 acertos) ⭐'
            elif qtd_acertos == 4: rotulo_premio = 'Quadra (4 acertos) 🎯'
        elif loteria_type == 'quina':
            if qtd_acertos == 5: rotulo_premio = 'Quina (5 acertos) 🏆'
            elif qtd_acertos == 4: rotulo_premio = 'Quadra (4 acertos) ⭐'
            elif qtd_acertos == 3: rotulo_premio = 'Terno (3 acertos) 🎯'
            elif qtd_acertos == 2: rotulo_premio = 'Duque (2 acertos)'
        elif loteria_type == 'lotofacil':
            if qtd_acertos == 15: rotulo_premio = '15 Acertos 🏆'
            elif qtd_acertos == 14: rotulo_premio = '14 Acertos ⭐'
            elif qtd_acertos == 13: rotulo_premio = '13 Acertos 🎯'
            elif qtd_acertos == 12: rotulo_premio = '12 Acertos'
            elif qtd_acertos == 11: rotulo_premio = '11 Acertos'
        elif loteria_type == 'dupla_sena':
            if qtd_acertos == 6: rotulo_premio = 'Sena (6 acertos) 🏆'
            elif qtd_acertos == 5: rotulo_premio = 'Quina (5 acertos) ⭐'
            elif qtd_acertos == 4: rotulo_premio = 'Quadra (4 acertos) 🎯'
            elif qtd_acertos == 3: rotulo_premio = 'Terno (3 acertos)'
        elif loteria_type == 'dia_de_sorte':
            if qtd_acertos == 7: rotulo_premio = '7 Acertos 🏆'
            elif qtd_acertos == 6: rotulo_premio = '6 Acertos ⭐'
            elif qtd_acertos == 5: rotulo_premio = '5 Acertos 🎯'
            elif qtd_acertos == 4: rotulo_premio = '4 Acertos'
        else:
            if qtd_acertos >= 4:
                rotulo_premio = f'{qtd_acertos} acertos 🎯'

        if rotulo_premio:
            premiacoes_resumo[rotulo_premio] = premiacoes_resumo.get(rotulo_premio, 0) + 1

        conferencia_jogos.append({
            'numero': idx,
            'jogo': jogo,
            'acertos': acertos,
            'qtd_acertos': qtd_acertos,
            'rotulo_premio': rotulo_premio
        })

    return jsonify({
        'sucesso': True,
        'aposta_titulo': aposta.get('titulo'),
        'concurso_numero': meta.get('ultimo_concurso', len(historico)),
        'data_apuracao': meta.get('data_apuracao', 'Recente'),
        'dezenas_sorteadas': ultimo_sorteio,
        'jogos_conferidos': conferencia_jogos,
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
    aposta_id = database.salvar_aposta(
        loteria_type=loteria_type,
        modalidade='manual',
        jogos=historico,
        dezenas_por_jogo=dezenas_por_jogo,
        user_id=user_id,
        session_id=session_id,
        titulo=f"Jogos Digitados ({len(historico)} aposta(s))"
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
    return jsonify({
        'historico': historico,
        'concursos_count': len(historico),
        'meta': meta
    })


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
    """Gerar sugestão de jogo baseado na análise"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    dados = request.get_json() or {}
    historico_input = dados.get('historico', [])
    quantidade = dados.get('quantidade', LOTERIAS_CONFIG[loteria].minimo_aposta)
    
    if not historico_input:
        historico_input = carregar_historico(loteria_type)
    
    if len(historico_input) < 10:
        return jsonify({'erro': 'Histórico insuficiente para análise'}), 400
    
    modelo = ModeloCanonico30(historico_input, loteria)
    jogo = gerar_jogo_sugerido(modelo, quantidade)
    
    return jsonify({
        'jogo': jogo,
        'quantidade': len(jogo),
        'analise_resumo': {
            'ict_medio': modelo.obter_resumo_analise()['estatisticas_gerais']['ict_medio'],
            'entropia': modelo.obter_resumo_analise()['camada_informacional']['entropia']
        }
    })


@app.route('/api/gerar-multiplos-jogos/<loteria_type>', methods=['POST'])
def api_gerar_multiplos_jogos(loteria_type: str):
    """Gera múltiplos palpites estatísticos baseados no Modelo Canônico 3.0 com verificação de plano/créditos"""
    try:
        loteria = LoteriaType(loteria_type)
        config = LOTERIAS_CONFIG[loteria]
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400

    # Verificação de Acesso / Créditos do Usuário
    user_id = session.get('user_id')
    access = {'is_vip': True, 'credits': 999}
    if user_id:
        access = database.check_user_access(user_id)
        if not access.get('has_access'):
            return jsonify({
                'sucesso': False,
                'erro': 'Seu tempo de acesso expirou. Assine o Plano VIP Ilimitado (R$ 49,90/mês) ou adquira um Acesso de 24 Horas para continuar gerando jogos.',
                'precisa_plano': True
            }), 403

    dados = request.get_json() or {}
    quantidade_jogos = int(dados.get('quantidade_jogos', 5))
    quantidade_jogos = max(1, min(100, quantidade_jogos))

    dezenas = int(dados.get('dezenas_por_jogo', config.minimo_aposta))
    dezenas = max(config.minimo_aposta, min(config.maximo_aposta, dezenas))

    numeros_base = dados.get('numeros_base', [])
    if numeros_base and len(numeros_base) < dezenas:
        return jsonify({
            'erro': f'Para gerar apostas de {dezenas} dezenas no modo personalizado, selecione ao menos {dezenas} números favoritos.'
        }), 400

    historico_input = dados.get('historico', [])
    if not historico_input:
        historico_input = carregar_historico(loteria_type)

    if len(historico_input) < 10:
        return jsonify({'erro': 'Histórico insuficiente para cálculo estatístico'}), 400

    modelo = ModeloCanonico30(historico_input, loteria)
    jogos = gerar_multiplos_jogos(modelo, quantidade_jogos, dezenas, numeros_base=numeros_base if numeros_base else None)

    # Consumir crédito de usuário se for avulso/free
    if user_id:
        database.consume_user_credit(user_id)
        access = database.check_user_access(user_id)

    return jsonify({
        'sucesso': True,
        'loteria': config.nome,
        'quantidade_jogos': len(jogos),
        'dezenas_por_jogo': dezenas,
        'jogos': jogos,
        'modo': 'manual_pool' if numeros_base else 'caixa_automatico',
        'metricas_gerais': {
            'ict_medio': round(modelo.obter_resumo_analise()['estatisticas_gerais']['ict_medio'], 4),
            'entropia': round(modelo.obter_resumo_analise()['camada_informacional']['entropia'], 4)
        },
        'user_access': access
    })


# ==========================================
# ROTAS DE CHECKOUT PIX E MONETIZAÇÃO
# ==========================================

@app.route('/api/checkout/pix', methods=['POST'])
@login_required
def api_checkout_pix():
    """Gera cobrança PIX para assinatura VIP ou recarga avulsa (Preço Único R$ 5,00)"""
    try:
        dados = request.get_json(silent=True) or {}
        tipo = dados.get('tipo', 'vip_mensal')
        if tipo == 'vip_mensal':
            valor = PRECO_MENSAL
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
            'valor': pagamento['valor'],
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
    """Aprova pagamento PIX e libera acesso VIP ou créditos de análise"""
    try:
        sucesso = database.approve_payment(payment_id)
        if sucesso:
            access = database.check_user_access(session['user_id'])
            return jsonify({
                'sucesso': True,
                'mensagem': 'Pagamento aprovado com sucesso! Acesso liberado.',
                'novo_status': 'aprovado',
                'access': access
            })
        return jsonify({'sucesso': False, 'erro': 'Pagamento não encontrado ou já processado'}), 400
    except Exception as e:
        print(f"[CHECKOUT CONFIRMAR] Erro: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# ==========================================
# INTEGRAÇÃO INFINITEPAY (TAXA ZERO & D+0)
# ==========================================

INFINITEPAY_HANDLE = os.environ.get('INFINITEPAY_HANDLE', 'silvio_morais_')


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

        base_url = request.host_url.rstrip('/')
        redirect_path = dados.get('redirect_path', '/planos')
        if not isinstance(redirect_path, str) or not redirect_path.startswith('/') or redirect_path.startswith('//'):
            redirect_path = '/planos'
        
        sep = '&' if '?' in redirect_path else '?'
        target_redirect = f"{base_url}{redirect_path}{sep}checkout=sucesso&payment_id={payment_id}"

        payload = {
            "handle": INFINITEPAY_HANDLE,
            "order_nsu": str(payment_id),
            "webhook_url": f"{base_url}/api/webhook/infinitepay",
            "redirect_url": target_redirect,
            "items": [
                {
                    "quantity": 1,
                    "price": int(round(valor * 100)),
                    "description": descricao
                }
            ]
        }
        if user:
            payload["customer"] = {
                "name": user.get('name') or 'Apostador',
                "email": user.get('email') or ''
            }

        resp = requests.post("https://api.checkout.infinitepay.io/links", json=payload, timeout=12)
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

        # Se pertence ao usuário logado e ainda pendente, aprovar se checkout confirmado
        auto_approve = request.args.get('auto_approve') == 'true' or request.args.get('checkout') == 'sucesso'
        if auto_approve and pagamento['user_id'] == session.get('user_id') and pagamento.get('status') != 'aprovado':
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
# ROTAS DO AGENTE IA CONSULTOR
# ==========================================

@app.route('/api/ia/parecer/<loteria_type>', methods=['POST'])
@login_required
@rate_limit(max_requests=10, window_seconds=60)
def api_ia_parecer(loteria_type: str):
    """Gera parecer estatístico didático do Agente IA para a rodada e palpites"""
    try:
        loteria = LoteriaType(loteria_type)
        config = LOTERIAS_CONFIG[loteria]
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400

    dados = request.get_json() or {}
    jogos = dados.get('jogos', [])

    historico = carregar_historico(loteria_type)
    if not historico or len(historico) < 10:
        return jsonify({'erro': 'Histórico insuficiente para a IA analisar'}), 400

    modelo = ModeloCanonico30(historico, loteria)
    resumo_analise = modelo.obter_resumo_analise()

    parecer = ai_agent.gerar_parecer_ia(config.nome, resumo_analise, jogos)
    return jsonify({
        'sucesso': True,
        'parecer': parecer
    })


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

    if not jogos:
        return jsonify({'erro': 'Nenhum jogo fornecido para download'}), 400

    data_hora = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')

    if formato == 'md':
        linhas = [
            f"# Palpites Gerados — {config.nome}",
            "**Metodologia:** Modelo Canônico 3.0 (MCP-MD 1.0)  ",
            f"**Data de Geração:** {data_hora}  ",
            f"**Total de Jogos:** {len(jogos)}  ",
            "",
            "| Jogo | Dezenas Recomendadas | Total Dezenas |",
            "| :---: | :--- | :---: |"
        ]
        for i, j in enumerate(jogos, 1):
            dezenas_str = ", ".join(f"{n:02d}" for n in j)
            linhas.append(f"| **Jogo {i:02d}** | {dezenas_str} | {len(j)} |")

        conteudo = "\n".join(linhas)
        mimetype = 'text/markdown; charset=utf-8'
        extensao = 'md'
    elif formato == 'txt':
        linhas = [
            "=" * 60,
            f"PALPITES GERADOS — {config.nome.upper()}",
            f"Modelo Canônico 3.0 + MCP-MD 1.0 (AGENTE LLN ICT FR)",
            f"Data: {data_hora}",
            f"Total de Combinações: {len(jogos)}",
            "=" * 60,
            ""
        ]
        for i, j in enumerate(jogos, 1):
            dezenas_str = " ".join(f"{n:02d}" for n in j)
            linhas.append(f"Jogo {i:02d}: [ {dezenas_str} ] ({len(j)} dezenas)")
        
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
    """Endpoint chamado pelo Vercel Cron Job pontualmente às 23:00h do Horário de Brasília (02:00 UTC)"""
    agora_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    print(f"[CRON] Executando sincronização diária oficial da Caixa às 23:00h BRT ({agora_str})...")
    res = updater.sincronizar_todas(n_historico=50)
    return jsonify(res)


@app.route('/comparar-concursos/<loteria_type>', methods=['POST'])
def comparar_concursos(loteria_type: str):
    """Comparar concurso atual com padrões históricos"""
    try:
        loteria = LoteriaType(loteria_type)
    except ValueError:
        return jsonify({'erro': 'Loteria inválida'}), 400
    
    dados = request.get_json()
    concurso_atual = dados.get('concurso', [])
    historico_input = dados.get('historico', [])
    
    if not historico_input:
        historico_input = carregar_historico(loteria_type)
    
    if len(historico_input) < 10:
        return jsonify({'erro': 'Histórico insuficiente'}), 400
    
    modelo = ModeloCanonico30(historico_input, loteria)
    analises = modelo.analisar_todos_elementos()
    
    scores_concurso = []
    numeros_analisados = []
    
    for numero in concurso_atual:
        if 1 <= numero <= modelo.N:
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


@app.route('/robots.txt', methods=['GET'])
def robots_txt():
    """Diretrizes para rastreadores de busca tradicionais e bots de IA generativa"""
    conteudo = """# Robots.txt — calculodasorte.com.br
User-agent: *
Allow: /
Allow: /planos
Allow: /login
Allow: /cadastro
Allow: /termos
Allow: /privacidade
Disallow: /admin
Disallow: /api/
Disallow: /download/
Disallow: /logout
Disallow: /dashboard

# Agentes e Motores de Busca Generativa (LLMs)
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot
Allow: /

User-agent: Bytespider
Allow: /

# Sitemap oficial
Sitemap: https://calculodasorte.com.br/sitemap.xml
"""
    return Response(conteudo.strip(), mimetype='text/plain')


@app.route('/sitemap.xml', methods=['GET'])
def sitemap_xml():
    """Mapa do site XML para indexação no Google, Bing e outros motores de busca"""
    base_url = "https://calculodasorte.com.br"
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    paginas = [
        {"loc": f"{base_url}/", "changefreq": "daily", "priority": "1.0"},
        {"loc": f"{base_url}/planos", "changefreq": "weekly", "priority": "0.9"},
        {"loc": f"{base_url}/blog", "changefreq": "daily", "priority": "0.9"},
        {"loc": f"{base_url}/cadastro", "changefreq": "monthly", "priority": "0.8"},
        {"loc": f"{base_url}/login", "changefreq": "monthly", "priority": "0.7"},
        {"loc": f"{base_url}/termos", "changefreq": "monthly", "priority": "0.5"},
        {"loc": f"{base_url}/privacidade", "changefreq": "monthly", "priority": "0.5"},
    ]
    
    # Adicionar as 9 loterias oficiais (Páginas de SEO / Resultados)
    loterias_slugs = [
        "mega_sena", "lotofacil", "quina", "lotomania", 
        "timemania", "dupla_sena", "dia_da_sorte", "super_sete", "milionaria"
    ]
    for slug in loterias_slugs:
        paginas.append({"loc": f"{base_url}/resultados/{slug}", "changefreq": "hourly", "priority": "0.95"})
    
    # Adicionar páginas do blog (Carregadas da pasta data/blog)
    try:
        if os.path.exists('data/blog'):
            for filename in os.listdir('data/blog'):
                if filename.endswith('.md'):
                    slug = filename.replace('.md', '')
                    paginas.append({"loc": f"{base_url}/blog/{slug}", "changefreq": "weekly", "priority": "0.85"})
    except Exception as e:
        print(f"Erro ao gerar sitemap do blog: {e}")
    
    xml_linhas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for p in paginas:
        xml_linhas.append('  <url>')
        xml_linhas.append(f'    <loc>{p["loc"]}</loc>')
        xml_linhas.append(f'    <lastmod>{hoje}</lastmod>')
        xml_linhas.append(f'    <changefreq>{p["changefreq"]}</changefreq>')
        xml_linhas.append(f'    <priority>{p["priority"]}</priority>')
        xml_linhas.append('  </url>')
    xml_linhas.append('</urlset>')
    
    return Response('\n'.join(xml_linhas), mimetype='application/xml')


@app.route('/llms.txt', methods=['GET'])
def llms_txt():
    """Especificação llms.txt para consumo por agentes de IA e busca generativa"""
    conteudo = """# Cálculo da Sorte

> Plataforma analítica e consultiva de inteligência combinatória para apostadores das 9 loterias oficiais da Caixa Econômica Federal no Brasil.

O [Cálculo da Sorte](https://calculodasorte.com.br) oferece ferramentas de geração inteligente de palpites estruturados, fechamentos e desdobramentos matemáticos no volante, conferência automática com dados oficiais da Caixa e consultoria estratégica via Agente de Inteligência Artificial.

## URLs e Mapas
- [Página Inicial](https://calculodasorte.com.br/)
- [Planos e Preços](https://calculodasorte.com.br/planos)
- [Página de Login](https://calculodasorte.com.br/login)
- [Criar Conta](https://calculodasorte.com.br/cadastro)
- [Blog de Dicas](https://calculodasorte.com.br/blog)

## Resultados Oficiais das Loterias
- [Mega-Sena](https://calculodasorte.com.br/resultados/mega_sena)
- [Lotofácil](https://calculodasorte.com.br/resultados/lotofacil)
- [Quina](https://calculodasorte.com.br/resultados/quina)
- [Lotomania](https://calculodasorte.com.br/resultados/lotomania)
- [Timemania](https://calculodasorte.com.br/resultados/timemania)
- [Dupla Sena](https://calculodasorte.com.br/resultados/dupla_sena)
- [Dia de Sorte](https://calculodasorte.com.br/resultados/dia_da_sorte)
- [Super Sete](https://calculodasorte.com.br/resultados/super_sete)
- [+Milionária](https://calculodasorte.com.br/resultados/milionaria)

## Documentação Legal
- [Termos de Uso](https://calculodasorte.com.br/termos)
- [Política de Privacidade](https://calculodasorte.com.br/privacidade)

## Sobre as Ferramentas
- **Gerador Inteligente de Palpites**: Gera cartelas combinatórias balanceadas.
- **Fechamentos no Volante**: O apostador seleciona suas dezenas prediletas e o sistema gera matrizes combinatórias.
- **Agente IA Consultor**: Assistente conversacional para responder dúvidas de probabilidades.
- **Jogo Responsável (+18)**: Ferramenta estritamente voltada a estudo probabilístico.
"""
    return Response(conteudo, mimetype='text/markdown')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

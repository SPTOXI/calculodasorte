"""
Aplicação Web Flask para Análise Estatística de Loterias
Baseada no Modelo Canônico 3.0 + MCP-MD 1.0
Com Painel Administrativo, Gestão de Usuários e Atualizador Diário Caixa
"""

from functools import wraps
import json
import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
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

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'loteria-canonical-secret-2026-key')

# Inicializar Banco de Dados e Agendador de Loterias
database.init_db()
updater.iniciar_agendador()

# Diretório para armazenar dados
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)


# ==========================================
# DECORATORS DE AUTENTICAÇÃO E PERMISSÃO
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        user = database.get_user_by_id(session['user_id'])
        if not user or user['is_blocked']:
            session.clear()
            return redirect(url_for('login', erro='Sessão expirada ou usuário bloqueado.'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'erro': 'Autenticação necessária'}), 401
            return redirect(url_for('login', next=request.url))
        user = database.get_user_by_id(session['user_id'])
        if not user or user['is_blocked']:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'erro': 'Usuário bloqueado'}), 403
            return redirect(url_for('login', erro='Usuário bloqueado.'))
        if user['role'] != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'erro': 'Acesso exclusivo para administradores'}), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


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


@app.route('/dashboard')
@login_required
def dashboard():
    """Painel do apostador autenticado com seleção das 9 loterias e status da conta"""
    loterias = [
        {
            'id': loteria.value,
            'nome': loteria.value.replace('_', ' ').title(),
            'config': config
        }
        for loteria, config in LOTERIAS_CONFIG.items()
    ]
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
@login_required
def planos_page():
    """Página de seleção de planos e recargas PIX"""
    user = database.get_user_by_id(session['user_id'])
    access = database.check_user_access(session['user_id'])
    return render_template('planos.html', user=user, access=access)


# ==========================================
# ROTAS DE AUTENTICAÇÃO (CADASTRO / LOGIN / LOGOUT)
# ==========================================

@app.route('/cadastro', methods=['GET', 'POST'])
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
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['user_role'] = user['role']
                session['user_name'] = user.get('name', nome)
                database.record_login(user['id'])

                if plano_desejado == 'vip':
                    return redirect(url_for('planos_page', sucesso='Conta criada com sucesso! Assine seu Plano VIP abaixo:'))
                elif plano_desejado == 'avulso':
                    return redirect(url_for('planos_page', sucesso='Conta criada com sucesso! Adquira sua recarga avulsa abaixo:'))
                
                return redirect(url_for('dashboard'))
            except Exception as e:
                erro = f'Erro ao criar conta: {str(e)}'

    return render_template('cadastro.html', erro=erro, nome=nome, email=email, plano_desejado=plano_desejado)


@app.route('/login', methods=['GET', 'POST'])
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


@app.route('/api/usuario/exportar-dados', methods=['GET'])
@login_required
def api_usuario_exportar_dados():
    """Portabilidade de dados cadastrais e apostas em formato JSON (Art. 18, V da LGPD)"""
    user_id = session['user_id']
    dados_portabilidade = database.export_user_data(user_id)
    return jsonify(dados_portabilidade)


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
    """Dashboard do painel administrativo"""
    user = database.get_user_by_id(session['user_id'])
    return render_template('admin.html', user=user)


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
        user = database.create_user(email, password, role)
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
            'erro': 'Histórico insuficiente. Mínimo de 10 concursos necessários. Use a opção de sincronização ou gere dados de exemplo.',
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
    """Confere as cartelas de uma aposta salva contra o último sorteio oficial da Caixa"""
    aposta = database.obter_aposta(aposta_id)
    if not aposta:
        return jsonify({'erro': 'Aposta não encontrada'}), 404

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
    """API para carregar histórico salvo com metadados"""
    historico = carregar_historico(loteria_type)
    meta = updater.carregar_meta(loteria_type)
    return jsonify({
        'historico': historico,
        'concursos_count': len(historico),
        'meta': meta
    })


@app.route('/api/sincronizar/<loteria_type>', methods=['POST'])
def api_sincronizar_publica(loteria_type: str):
    """Sincroniza os últimos resultados oficiais da Caixa para a modalidade"""
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
                'erro': 'Você utilizou todos os seus créditos de análise. Assine o Plano VIP (R$ 29,90/mês) ou adquira uma recarga avulsa para continuar gerando jogos.',
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
    dados = request.get_json() or {}
    tipo = dados.get('tipo', 'avulso')
    if tipo == 'vip_mensal':
        valor = 29.90
    else:
        valor = 5.00  # Preço único padronizado de R$ 5,00 para qualquer loteria
    loteria_type = dados.get('loteria_type')

    user_id = session['user_id']
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


@app.route('/api/checkout/confirmar/<int:payment_id>', methods=['POST'])
@login_required
def api_confirmar_pix(payment_id: int):
    """Aprova pagamento PIX e libera acesso VIP ou créditos de análise"""
    sucesso = database.approve_payment(payment_id)
    if sucesso:
        access = database.check_user_access(session['user_id'])
        return jsonify({
            'sucesso': True,
            'mensagem': 'Pagamento aprovado com sucesso! Acesso liberado.',
            'novo_status': 'aprovado',
            'access': access
        })
    return jsonify({'erro': 'Pagamento não encontrado ou já processado'}), 400


# ==========================================
# INTEGRAÇÃO INFINITEPAY (TAXA ZERO & D+0)
# ==========================================

INFINITEPAY_HANDLE = os.environ.get('INFINITEPAY_HANDLE', 'silvio_morais_')


@app.route('/api/checkout/infinitepay', methods=['POST'])
@login_required
def api_checkout_infinitepay():
    """Gera link de checkout oficial da InfinitePay (Taxa Zero no PIX e Liberação Imediata)"""
    dados = request.get_json() or {}
    tipo = dados.get('tipo', 'vip_mensal')
    if tipo == 'vip_mensal':
        valor = 29.90
        descricao = "Plano VIP Mensal (30 dias) - Cálculo da Sorte"
    else:
        valor = 5.00  # Preço único padronizado de R$ 5,00 para qualquer loteria
        descricao = "Recarga de Análise Avulsa (R$ 5,00) - Cálculo da Sorte"
    loteria_type = dados.get('loteria_type')

    user_id = session['user_id']
    user = database.get_user_by_id(user_id)
    pagamento = database.create_payment(user_id=user_id, tipo=tipo, valor=valor, loteria_type=loteria_type)
    payment_id = pagamento['id']

    base_url = request.host_url.rstrip('/')

    payload = {
        "handle": INFINITEPAY_HANDLE,
        "order_nsu": str(payment_id),
        "webhook_url": f"{base_url}/api/webhook/infinitepay",
        "redirect_url": f"{base_url}/planos?checkout=sucesso&payment_id={payment_id}",
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

    try:
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
    """Consulta o status atual de um pagamento"""
    pagamento = database.get_payment_by_id(payment_id)
    if not pagamento:
        return jsonify({'erro': 'Pagamento não encontrado'}), 404

    access = database.check_user_access(session['user_id'])
    return jsonify({
        'sucesso': True,
        'status': pagamento.get('status'),
        'is_approved': pagamento.get('status') == 'aprovado',
        'access': access
    })


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



# ==========================================
# ROTAS DO AGENTE IA CONSULTOR
# ==========================================

@app.route('/api/ia/parecer/<loteria_type>', methods=['POST'])
@login_required
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

    resposta = ai_agent.responder_chat_consultor(pergunta, loteria_nome)
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
    """Endpoint chamado pelo Vercel Cron Job às 23:59h"""
    print("[CRON] Executando sincronização diária oficial da Caixa às 23:59h...")
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

"""
Módulo de Banco de Dados SQLite para Gestão de Usuários e Autenticação
Projeto Calculadora da Sorte
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash

ORIGINAL_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
if os.environ.get('VERCEL'):
    DATA_DIR = os.path.join('/tmp', 'data')
else:
    DATA_DIR = ORIGINAL_DATA_DIR

DB_PATH = os.path.join(DATA_DIR, 'database.db')

from contextlib import contextmanager


@contextmanager
def get_db_connection():
    """Retorna conexão com o banco SQLite com row_factory configurado e fechamento garantido"""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Inicializa as tabelas do banco de dados e cria o administrador padrão"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Tabela de Usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL DEFAULT 'Apostador',
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                plan TEXT NOT NULL DEFAULT 'free',
                credits INTEGER NOT NULL DEFAULT 1,
                vip_expires_at TIMESTAMP,
                is_blocked INTEGER NOT NULL DEFAULT 0,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # Migração segura de colunas na tabela users se já existir
        colunas_existentes = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if 'name' not in colunas_existentes:
            conn.execute("ALTER TABLE users ADD COLUMN name TEXT NOT NULL DEFAULT 'Apostador'")
        if 'plan' not in colunas_existentes:
            conn.execute("ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'")
        if 'credits' not in colunas_existentes:
            conn.execute("ALTER TABLE users ADD COLUMN credits INTEGER NOT NULL DEFAULT 1")
        if 'vip_expires_at' not in colunas_existentes:
            conn.execute("ALTER TABLE users ADD COLUMN vip_expires_at TIMESTAMP")
        if 'accepted_terms_at' not in colunas_existentes:
            conn.execute("ALTER TABLE users ADD COLUMN accepted_terms_at TIMESTAMP")
        
        # Tabela de Histórico de Sincronizações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loteria_type TEXT NOT NULL,
                concurso INTEGER,
                data_sorteio TEXT,
                status TEXT NOT NULL,
                mensagem TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de Histórico de Apostas dos Usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT,
                loteria_type TEXT NOT NULL,
                titulo TEXT,
                modalidade TEXT NOT NULL,
                quantidade_jogos INTEGER NOT NULL,
                dezenas_por_jogo INTEGER NOT NULL,
                jogos_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Tabela de Pagamentos (PIX / Assinaturas / Avulso)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                loteria_type TEXT,
                valor REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                pix_copia_cola TEXT,
                pix_txid TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()

    # Garantir criação do admin padrão
    seed_admin()


def seed_admin(email: str = 'silvio.luis.morais@gmail.com', password: str = '123456'):
    """Garante a existência do usuário administrador padrão"""
    user = get_user_by_email(email)
    if not user:
        create_user(
            email=email,
            password=password,
            name='Administrador Silvio',
            role='admin',
            plan='vip_mensal',
            credits=9999,
            must_change_password=1
        )
        print(f"[DB] Administrador padrão criado: {email}")
    else:
        with get_db_connection() as conn:
            conn.execute('''
                UPDATE users 
                SET role = 'admin', plan = 'vip_mensal', credits = 9999, name = 'Administrador Silvio' 
                WHERE email = ?
            ''', (email,))
            conn.commit()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Buscar usuário por ID"""
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Buscar usuário por e-mail (case-insensitive)"""
    with get_db_connection() as conn:
        row = conn.execute(
            'SELECT * FROM users WHERE LOWER(email) = LOWER(?)', 
            (email.strip(),)
        ).fetchone()
        return dict(row) if row else None


def get_all_users() -> List[Dict[str, Any]]:
    """Listar todos os usuários com dados de plano e créditos"""
    with get_db_connection() as conn:
        rows = conn.execute(
            'SELECT id, email, name, role, plan, credits, vip_expires_at, is_blocked, must_change_password, created_at, last_login '
            'FROM users ORDER BY id ASC'
        ).fetchall()
        return [dict(r) for r in rows]


def create_user(
    email: str, 
    password: str, 
    name: str = 'Apostador',
    role: str = 'user', 
    plan: str = 'free',
    credits: int = 1,
    must_change_password: int = 0,
    accepted_terms: bool = True
) -> Dict[str, Any]:
    """Criar novo usuário no sistema com crédito de degustação gratuito e registro de consentimento LGPD"""
    email_clean = email.strip().lower()
    if not email_clean or '@' not in email_clean:
        raise ValueError("E-mail inválido")
    
    if len(password) < 4:
        raise ValueError("A senha deve conter pelo menos 4 caracteres")

    name_clean = (name or 'Apostador').strip()
    pwd_hash = generate_password_hash(password)
    terms_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if accepted_terms else None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (email, name, password_hash, role, plan, credits, is_blocked, must_change_password, accepted_terms_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        ''', (email_clean, name_clean, pwd_hash, role, plan, credits, must_change_password, terms_date))
        conn.commit()
        user_id = cursor.lastrowid
        
    return get_user_by_id(user_id)


def update_user(
    user_id: int, 
    email: Optional[str] = None, 
    password: Optional[str] = None, 
    role: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Atualizar dados do usuário"""
    fields = []
    values = []

    if email is not None:
        email_clean = email.strip().lower()
        if not email_clean or '@' not in email_clean:
            raise ValueError("E-mail inválido")
        fields.append("email = ?")
        values.append(email_clean)

    if password is not None and password.strip():
        if len(password.strip()) < 4:
            raise ValueError("A senha deve conter pelo menos 4 caracteres")
        fields.append("password_hash = ?")
        values.append(generate_password_hash(password.strip()))

    if role is not None:
        if role not in ('admin', 'user'):
            raise ValueError("Perfil inválido (deve ser admin ou user)")
        fields.append("role = ?")
        values.append(role)

    if not fields:
        return get_user_by_id(user_id)

    values.append(user_id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"

    with get_db_connection() as conn:
        conn.execute(query, values)
        conn.commit()

    return get_user_by_id(user_id)


def toggle_block_user(user_id: int) -> bool:
    """Alternar status de bloqueio do usuário (retorna novo estado: True se bloqueado)"""
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Usuário não encontrado")

    new_status = 0 if user['is_blocked'] else 1
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET is_blocked = ? WHERE id = ?', (new_status, user_id))
        conn.commit()

    return bool(new_status)


def delete_user(user_id: int) -> bool:
    """Excluir usuário"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return cursor.rowcount > 0


def update_password(user_id: int, new_password: str) -> bool:
    """Alterar senha do usuário e resetar flag must_change_password"""
    if len(new_password) < 4:
        raise ValueError("A nova senha deve ter pelo menos 4 caracteres")

    pwd_hash = generate_password_hash(new_password)
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE users 
            SET password_hash = ?, must_change_password = 0 
            WHERE id = ?
        ''', (pwd_hash, user_id))
    return True


def set_must_change_password(user_id: int, flag: int = 1):
    """Define flag se usuário deve trocar de senha"""
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET must_change_password = ? WHERE id = ?', (flag, user_id))



def record_login(user_id: int):
    """Registrar data/hora do login"""
    with get_db_connection() as conn:
        conn.execute(
            'UPDATE users SET last_login = ? WHERE id = ?', 
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)
        )
        conn.commit()


def log_sync(
    loteria_type: str, 
    concurso: Optional[int], 
    data_sorteio: Optional[str], 
    status: str, 
    mensagem: str
):
    """Registrar log de sincronização de loteria"""
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO sync_logs (loteria_type, concurso, data_sorteio, status, mensagem)
            VALUES (?, ?, ?, ?, ?)
        ''', (loteria_type, concurso, data_sorteio, status, mensagem))
        conn.commit()


def get_latest_sync_logs(limit: int = 20) -> List[Dict[str, Any]]:
    """Buscar últimos logs de sincronização"""
    with get_db_connection() as conn:
        rows = conn.execute(
            'SELECT * FROM sync_logs ORDER BY id DESC LIMIT ?', 
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ==========================================
# GESTÃO DE HISTÓRICO DE APOSTAS DO USUÁRIO
# ==========================================

def salvar_aposta(
    loteria_type: str,
    modalidade: str,
    jogos: List[List[int]],
    dezenas_por_jogo: int,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    titulo: Optional[str] = None
) -> int:
    """Salva um lote de jogos no banco de dados SQLite"""
    import json
    if not titulo:
        mod_label = {
            'automatico': 'Geração Automática (Caixa)',
            'fechamento': 'Fechamento / Desdobramento',
            'manual': 'Apostas Manuais'
        }.get(modalidade, 'Apostas')
        data_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        titulo = f"{mod_label} - {len(jogos)} jogo(s) ({data_str})"

    jogos_json = json.dumps(jogos)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_bets 
            (user_id, session_id, loteria_type, titulo, modalidade, quantidade_jogos, dezenas_por_jogo, jogos_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, session_id, loteria_type, titulo, modalidade, len(jogos), dezenas_por_jogo, jogos_json))
        conn.commit()
        return cursor.lastrowid


def listar_apostas(
    loteria_type: Optional[str] = None,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lista apostas do usuário logado ou da sessão atual"""
    import json
    with get_db_connection() as conn:
        query = "SELECT * FROM user_bets WHERE "
        params = []

        if user_id:
            query += "(user_id = ? OR session_id = ?) "
            params.extend([user_id, session_id or ''])
        elif session_id:
            query += "session_id = ? "
            params.append(session_id)
        else:
            query += "1=1 "

        if loteria_type:
            query += "AND loteria_type = ? "
            params.append(loteria_type)

        query += "ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, tuple(params)).fetchall()
        resultado = []
        for r in rows:
            d = dict(r)
            try:
                d['jogos'] = json.loads(d['jogos_json'])
            except Exception:
                d['jogos'] = []
            resultado.append(d)
        return resultado


def obter_aposta(aposta_id: int) -> Optional[Dict[str, Any]]:
    """Obtém detalhes completos de uma aposta por ID"""
    import json
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM user_bets WHERE id = ?", (aposta_id,)).fetchone()
        if row:
            d = dict(row)
            try:
                d['jogos'] = json.loads(d['jogos_json'])
            except Exception:
                d['jogos'] = []
            return d
        return None


def excluir_aposta(aposta_id: int, user_id: Optional[int] = None, session_id: Optional[str] = None) -> bool:
    """Exclui aposta garantindo autenticação por usuário ou sessão"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM user_bets WHERE id = ? AND (user_id = ? OR session_id = ?)", (aposta_id, user_id, session_id or ''))
        elif session_id:
            cursor.execute("DELETE FROM user_bets WHERE id = ? AND session_id = ?", (aposta_id, session_id))
        else:
            cursor.execute("DELETE FROM user_bets WHERE id = ?", (aposta_id,))
        conn.commit()
        return cursor.rowcount > 0


# ==========================================
# CONTROLE DE ACESSO, CRÉDITOS E MONETIZAÇÃO
# ==========================================

def check_user_access(user_id: int) -> Dict[str, Any]:
    """
    Verifica o status de acesso do usuário:
    - Se é admin: acesso ilimitado liberado
    - Se plano == 'vip_mensal' e não expirou: acesso ilimitado liberado
    - Se possui créditos > 0: acesso liberado por crédito
    - Caso contrário: bloqueado (necessário assinar ou recarregar)
    """
    user = get_user_by_id(user_id)
    if not user:
        return {'has_access': False, 'reason': 'not_found', 'credits': 0, 'is_vip': False, 'name': 'Visitante'}

    if user.get('role') == 'admin':
        return {
            'has_access': True, 
            'reason': 'admin', 
            'credits': 9999, 
            'is_vip': True, 
            'plan': 'vip_mensal',
            'name': user.get('name', 'Administrador')
        }

    # Verificar VIP
    if user.get('plan') == 'vip_mensal':
        vip_expires_at = user.get('vip_expires_at')
        if not vip_expires_at:
            return {
                'has_access': True, 
                'reason': 'vip', 
                'credits': user.get('credits', 0), 
                'is_vip': True, 
                'plan': 'vip_mensal',
                'name': user.get('name', 'Apostador VIP')
            }
        try:
            exp_date = datetime.strptime(vip_expires_at, '%Y-%m-%d %H:%M:%S')
            if datetime.now() <= exp_date:
                return {
                    'has_access': True, 
                    'reason': 'vip', 
                    'credits': user.get('credits', 0), 
                    'is_vip': True, 
                    'plan': 'vip_mensal', 
                    'expires_at': vip_expires_at,
                    'name': user.get('name', 'Apostador VIP')
                }
        except Exception:
            pass

    # Verificar créditos avulsos
    credits = user.get('credits', 0)
    if credits > 0:
        return {
            'has_access': True, 
            'reason': 'credits', 
            'credits': credits, 
            'is_vip': False, 
            'plan': user.get('plan', 'free'),
            'name': user.get('name', 'Apostador')
        }

    return {
        'has_access': False, 
        'reason': 'no_credits', 
        'credits': 0, 
        'is_vip': False, 
        'plan': user.get('plan', 'free'),
        'name': user.get('name', 'Apostador')
    }


def consume_user_credit(user_id: int) -> bool:
    """Consome 1 crédito do usuário caso não seja VIP ativo ou admin"""
    user = get_user_by_id(user_id)
    if not user:
        return False
    if user.get('role') == 'admin':
        return True
    
    access = check_user_access(user_id)
    if access.get('is_vip'):
        return True

    if access.get('credits', 0) > 0:
        with get_db_connection() as conn:
            conn.execute('UPDATE users SET credits = credits - 1 WHERE id = ? AND credits > 0', (user_id,))
            conn.commit()
        return True

    return False


def activate_vip_plan(user_id: int, days: int = 30):
    """Ativa ou renova plano VIP por X dias"""
    now = datetime.now()
    user = get_user_by_id(user_id)
    current_exp = user.get('vip_expires_at') if user else None
    
    base_date = now
    if current_exp:
        try:
            parsed = datetime.strptime(current_exp, '%Y-%m-%d %H:%M:%S')
            if parsed > now:
                base_date = parsed
        except Exception:
            base_date = now
            
    new_exp = (base_date + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE users 
            SET plan = 'vip_mensal', vip_expires_at = ? 
            WHERE id = ?
        ''', (new_exp, user_id))
        conn.commit()


def add_user_credits(user_id: int, amount: int = 1):
    """Adiciona créditos de análise ao usuário"""
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET credits = credits + ? WHERE id = ?', (amount, user_id))
        conn.commit()


def create_payment(user_id: int, tipo: str, valor: float, loteria_type: Optional[str] = None) -> Dict[str, Any]:
    """Registra uma intenção de pagamento PIX e gera payload Copia e Cola"""
    import random
    import string
    txid = 'PIX' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    pix_copia_cola = f"00020126580014br.gov.bcb.pix0136silvio.luis.morais@gmail.com520400005303986540{valor:.2f}5802BR5920Calculadora da Sorte6009Sao Paulo62070503***6304{txid[-4:]}"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO payments (user_id, tipo, loteria_type, valor, status, pix_copia_cola, pix_txid)
            VALUES (?, ?, ?, ?, 'pendente', ?, ?)
        ''', (user_id, tipo, loteria_type, valor, pix_copia_cola, txid))
        conn.commit()
        payment_id = cursor.lastrowid
        
    return get_payment_by_id(payment_id)


def get_payment_by_id(payment_id: int) -> Optional[Dict[str, Any]]:
    """Obtém detalhes do pagamento"""
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM payments WHERE id = ?', (payment_id,)).fetchone()
        return dict(row) if row else None


def approve_payment(payment_id: int) -> bool:
    """Aprova um pagamento e libera os créditos ou VIP correspondentes"""
    payment = get_payment_by_id(payment_id)
    if not payment or payment.get('status') == 'aprovado':
        return False
        
    user_id = payment['user_id']
    tipo = payment['tipo']
    
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE payments 
            SET status = 'aprovado', approved_at = ? 
            WHERE id = ?
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), payment_id))
        conn.commit()
        
    if tipo == 'vip_mensal':
        activate_vip_plan(user_id, days=30)
    elif tipo == 'avulso':
        add_user_credits(user_id, amount=1)
        
    return True


def get_all_payments() -> List[Dict[str, Any]]:
    """Listar todos os pagamentos com dados do usuário para o painel admin"""
    with get_db_connection() as conn:
        rows = conn.execute('''
            SELECT p.*, u.email as user_email, u.name as user_name
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.id
            ORDER BY p.id DESC
        ''').fetchall()
        return [dict(r) for r in rows]


# ==========================================
# CONFORMIDADE LGPD (LEI Nº 13.709/2018)
# ==========================================

def export_user_data(user_id: int) -> Dict[str, Any]:
    """Portabilidade de dados (Art. 18, V da LGPD)"""
    user = get_user_by_id(user_id)
    if not user:
        return {}
    
    # Sanitizar dados removendo hashes internos
    user_sanitized = {k: v for k, v in user.items() if k not in ('password_hash',)}
    bets = listar_apostas(user_id=user_id)
    
    return {
        'lgpd_declaracao': 'Relatório Oficial de Portabilidade de Dados Pessoais — Art. 18, V da LGPD',
        'data_solicitacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'titular': user_sanitized,
        'total_apostas_registradas': len(bets),
        'historico_apostas': bets
    }


def delete_user_and_data(user_id: int) -> bool:
    """Direito à eliminação dos dados pessoais / Esquecimento (Art. 18, VI da LGPD)"""
    with get_db_connection() as conn:
        # 1. Excluir todas as apostas do titular
        conn.execute('DELETE FROM user_bets WHERE user_id = ?', (user_id,))
        # 2. Anonimizar pagamentos para fins de auditoria fiscal/contábil (Art. 16, I da LGPD)
        conn.execute('''
            UPDATE payments 
            SET user_id = NULL, pix_copia_cola = 'ANONIMIZADO_LGPD' 
            WHERE user_id = ?
        ''', (user_id,))
        # 3. Excluir conta do usuário
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
    return True





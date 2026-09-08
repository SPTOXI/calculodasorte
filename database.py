"""
Módulo de Banco de Dados SQLite para Gestão de Usuários e Autenticação
Projeto Calculadora da Sorte
"""

import os
import sqlite3
from datetime import datetime
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
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_blocked INTEGER NOT NULL DEFAULT 0,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
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
            role='admin',
            must_change_password=1
        )
        print(f"[DB] Administrador padrão criado: {email}")


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
    """Listar todos os usuários"""
    with get_db_connection() as conn:
        rows = conn.execute(
            'SELECT id, email, role, is_blocked, must_change_password, created_at, last_login '
            'FROM users ORDER BY id ASC'
        ).fetchall()
        return [dict(r) for r in rows]


def create_user(
    email: str, 
    password: str, 
    role: str = 'user', 
    must_change_password: int = 0
) -> Dict[str, Any]:
    """Criar novo usuário no sistema"""
    email_clean = email.strip().lower()
    if not email_clean or '@' not in email_clean:
        raise ValueError("E-mail inválido")
    
    if len(password) < 4:
        raise ValueError("A senha deve conter pelo menos 4 caracteres")

    pwd_hash = generate_password_hash(password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (email, password_hash, role, is_blocked, must_change_password)
            VALUES (?, ?, ?, 0, ?)
        ''', (email_clean, pwd_hash, role, must_change_password))
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


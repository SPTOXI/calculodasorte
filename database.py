class PostgresConnAdapter:
    def __init__(self, conn):
        self.conn = conn
    
    def execute(self, query, params=None):
        cursor = self.conn.cursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
        
    def cursor(self):
        return self.conn.cursor()
        
    def commit(self):
        self.conn.commit()
        
    def close(self):
        pass # A pool gerencia o fechamento real

"""
Módulo de Banco de Dados SQLite para Gestão de Usuários e Autenticação
Projeto Calculadora da Sorte
"""

import json
import os
import re
import secrets
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from .pix_utils import validar_payload_pix, gerar_qrcode_pix_png_base64
except ImportError:
    from pix_utils import validar_payload_pix, gerar_qrcode_pix_png_base64



from contextlib import contextmanager




def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Obtém configuração persistente do sistema"""
    try:
        with get_db_connection() as conn:
            row = conn.execute('SELECT value FROM system_settings WHERE key = %s', (key,)).fetchone()
            return row['value'] if row else default
    except Exception:
        return default


def set_setting(key: str, value: str) -> bool:
    """Salva ou atualiza configuração persistente do sistema e sincroniza com a nuvem"""
    try:
        with get_db_connection() as conn:
            
            conn.execute('''
                INSERT INTO system_settings (key, value, updated_at) 
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            ''', (key, str(value)))
            conn.commit()
        return True
    except Exception as e:
        print(f"[SETTINGS] Erro ao salvar configuração {key}: {e}")
        return False


def salvar_ultimo_resultado_db(loteria_type: str, dados: Dict[str, Any]) -> bool:
    """Salva o último resultado completo da loteria no banco de dados persistente (PostgreSQL / Supabase)"""
    try:
        payload = json.dumps(dados, ensure_ascii=False)
        return set_setting(f'resultado_{loteria_type}', payload)
    except Exception as e:
        print(f"[DB] Erro ao salvar ultimo resultado de {loteria_type}: {e}")
        return False


def obter_ultimo_resultado_db(loteria_type: str) -> Optional[Dict[str, Any]]:
    """Obtém o último resultado completo da loteria salvo no banco de dados persistente"""
    try:
        val = get_setting(f'resultado_{loteria_type}')
        if val:
            dados = json.loads(val)
            if isinstance(dados, dict) and dados.get('numero'):
                return dados
    except Exception as e:
        print(f"[DB] Erro ao obter ultimo resultado de {loteria_type}: {e}")
    return None


import urllib.parse

def clean_db_url(url):
    if not url: return url
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    valid_keys = {'sslmode', 'connect_timeout', 'application_name', 'options', 'keepalives', 'keepalives_idle', 'keepalives_interval', 'keepalives_count'}
    new_query = {k: v[0] for k, v in query.items() if k in valid_keys}
    parsed = parsed._replace(query=urllib.parse.urlencode(new_query))
    return urllib.parse.urlunparse(parsed)

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
DATABASE_URL = clean_db_url(DATABASE_URL)
if not DATABASE_URL:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
        DATABASE_URL = clean_db_url(DATABASE_URL)
    except ImportError:
        pass

_db_pool = None

def get_pool():
    global _db_pool
    if _db_pool is None:
        if not DATABASE_URL:
            raise ValueError('DATABASE_URL or POSTGRES_URL is not set')
        _db_pool = ThreadedConnectionPool(1, 20, DATABASE_URL, cursor_factory=RealDictCursor)
    return _db_pool

@contextmanager
def get_db_connection(auto_sync: bool = True):
    pool = get_pool()
    raw_conn = pool.getconn()
    conn = PostgresConnAdapter(raw_conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        pool.putconn(raw_conn)


def init_db():
    """Inicializa as tabelas do banco de dados na Supabase"""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL DEFAULT 'Apostador',
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                plan TEXT NOT NULL DEFAULT 'free',
                credits INTEGER NOT NULL DEFAULT 0,
                vip_expires_at TIMESTAMP,
                is_blocked INTEGER NOT NULL DEFAULT 0,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                accepted_terms_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email_nocase ON users (LOWER(email))")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_logs (
                id SERIAL PRIMARY KEY,
                loteria_type TEXT NOT NULL,
                concurso INTEGER,
                data_sorteio TEXT,
                status TEXT NOT NULL,
                mensagem TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_bets (
                id SERIAL PRIMARY KEY,
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
        """)
        conn.execute("ALTER TABLE user_bets ADD COLUMN IF NOT EXISTS concurso_alvo INTEGER")
        conn.execute("ALTER TABLE user_bets ADD COLUMN IF NOT EXISTS notificado_em TIMESTAMP")
        conn.execute("ALTER TABLE user_bets ADD COLUMN IF NOT EXISTS trevos_json TEXT")
        conn.execute("ALTER TABLE user_bets ADD COLUMN IF NOT EXISTS complementos_json TEXT")
        conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avisos_email INTEGER NOT NULL DEFAULT 1")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                loteria_type TEXT,
                valor NUMERIC NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                pix_copia_cola TEXT,
                pix_txid TEXT,
                pix_qr_code_base64 TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_logs (
                id SERIAL PRIMARY KEY,
                user_ident TEXT NOT NULL,
                loteria_nome TEXT,
                pergunta TEXT NOT NULL,
                resposta TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_errors (
                id SERIAL PRIMARY KEY,
                module TEXT NOT NULL,
                error_message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS concursos_importados (
                loteria_type TEXT NOT NULL,
                concurso INTEGER NOT NULL,
                data_sorteio TEXT,
                dezenas_json TEXT NOT NULL,
                segundo_json TEXT,
                trevos_json TEXT,
                complemento TEXT,
                importado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (loteria_type, concurso)
            )
        """)
        conn.commit()

    seed_admin()



def seed_admin(email: str = 'silvio.luis.morais@gmail.com'):
    """Garante a existência do usuário administrador padrão"""
    user = get_user_by_email(email)
    if not user:
        # Nunca usar senha fixa: quem logasse primeiro com ela assumiria a conta de admin
        password = os.environ.get('ADMIN_INITIAL_PASSWORD') or secrets.token_urlsafe(12)
        if not os.environ.get('ADMIN_INITIAL_PASSWORD'):
            print(f"[DB] Senha inicial do administrador gerada (troque no primeiro login): {password}")
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
                WHERE email = %s
            ''', (email,))
            conn.commit()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Buscar usuário por ID com fallback para sincronização na nuvem"""
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = %s', (user_id,)).fetchone()
        if row:
            return dict(row)


    return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Buscar usuário por e-mail (case-insensitive) com fallback para sincronização na nuvem"""
    if not email:
        return None
    email_clean = email.strip().lower()
    with get_db_connection() as conn:
        row = conn.execute(
            'SELECT * FROM users WHERE LOWER(email) = %s', 
            (email_clean,)
        ).fetchone()
        if row:
            return dict(row)


    return None


def get_all_users() -> List[Dict[str, Any]]:
    """Listar todos os usuários com dados de plano e créditos (sincronizado com a nuvem)"""
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
    credits: int = 0,
    must_change_password: int = 0,
    accepted_terms: bool = True
) -> Dict[str, Any]:
    """Criar novo usuário no sistema e sincronização em nuvem"""
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
            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s) RETURNING id
        ''', (email_clean, name_clean, pwd_hash, role, plan, credits, must_change_password, terms_date))
        user_id = cursor.fetchone()['id']
        conn.commit()
        
    synced = sync_db_to_cloud()
    if synced:
        print(f"[DB] Novo usuário cadastrado ({email_clean}) e sincronizado com a nuvem.")
    else:
        print(f"[DB] Novo usuário cadastrado ({email_clean}) localmente.")
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
        fields.append("email = %s")
        values.append(email_clean)

    if password is not None and password.strip():
        if len(password.strip()) < 4:
            raise ValueError("A senha deve conter pelo menos 4 caracteres")
        fields.append("password_hash = %s")
        values.append(generate_password_hash(password.strip()))

    if role is not None:
        if role not in ('admin', 'user'):
            raise ValueError("Perfil inválido (deve ser admin ou user)")
        fields.append("role = %s")
        values.append(role)

    if not fields:
        return get_user_by_id(user_id)

    values.append(user_id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE id = %s"

    with get_db_connection() as conn:
        conn.execute(query, values)
        conn.commit()

    sync_db_to_cloud()
    return get_user_by_id(user_id)


def toggle_block_user(user_id: int) -> bool:
    """Alternar status de bloqueio do usuário (retorna novo estado: True se bloqueado)"""
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Usuário não encontrado")

    new_status = 0 if user['is_blocked'] else 1
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET is_blocked = %s WHERE id = %s', (new_status, user_id))
        conn.commit()

    sync_db_to_cloud()
    return bool(new_status)


def delete_user(user_id: int) -> bool:
    """Excluir usuário"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        success = cursor.rowcount > 0

    if success:
        sync_db_to_cloud()
    return success


def update_password(user_id: int, new_password: str) -> bool:
    """Alterar senha do usuário e resetar flag must_change_password"""
    if len(new_password) < 4:
        raise ValueError("A nova senha deve ter pelo menos 4 caracteres")

    pwd_hash = generate_password_hash(new_password)
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE users 
            SET password_hash = %s, must_change_password = 0 
            WHERE id = %s
        ''', (pwd_hash, user_id))
        conn.commit()
    sync_db_to_cloud()
    return True


def set_must_change_password(user_id: int, flag: int = 1):
    """Define flag se usuário deve trocar de senha"""
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET must_change_password = %s WHERE id = %s', (flag, user_id))
        conn.commit()
    sync_db_to_cloud()



def record_login(user_id: int):
    """Registrar data/hora do login"""
    with get_db_connection() as conn:
        conn.execute(
            'UPDATE users SET last_login = %s WHERE id = %s', 
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)
        )
        conn.commit()
    sync_db_to_cloud()


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
            VALUES (%s, %s, %s, %s, %s)
        ''', (loteria_type, concurso, data_sorteio, status, mensagem))
        conn.commit()


def salvar_concursos_importados(loteria_type: str, concursos: List[Dict[str, Any]]) -> int:
    """Grava (ou substitui) concursos importados por planilha. Retorna quantos foram gravados."""
    if not concursos:
        return 0
    from psycopg2.extras import execute_values
    linhas = [(
        loteria_type, c['concurso'], c.get('data'), json.dumps(c['dezenas']),
        json.dumps(c['segundo']) if c.get('segundo') else None,
        json.dumps(c['trevos']) if c.get('trevos') else None,
        c.get('complemento'),
    ) for c in concursos]
    with get_db_connection() as conn:
        cur = conn.cursor()
        execute_values(cur, '''
            INSERT INTO concursos_importados
                (loteria_type, concurso, data_sorteio, dezenas_json, segundo_json, trevos_json, complemento)
            VALUES %s
            ON CONFLICT (loteria_type, concurso) DO UPDATE SET
                data_sorteio = EXCLUDED.data_sorteio,
                dezenas_json = EXCLUDED.dezenas_json,
                segundo_json = EXCLUDED.segundo_json,
                trevos_json = EXCLUDED.trevos_json,
                complemento = EXCLUDED.complemento,
                importado_em = CURRENT_TIMESTAMP
        ''', linhas, page_size=500)
        conn.commit()
    return len(concursos)


def listar_concursos_importados(loteria_type: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute('''
            SELECT concurso, data_sorteio, dezenas_json, segundo_json, trevos_json, complemento
            FROM concursos_importados WHERE loteria_type = %s ORDER BY concurso
        ''', (loteria_type,)).fetchall()
    return [{
        'concurso': r['concurso'],
        'data': r['data_sorteio'],
        'dezenas': json.loads(r['dezenas_json']),
        'segundo': json.loads(r['segundo_json']) if r['segundo_json'] else [],
        'trevos': json.loads(r['trevos_json']) if r['trevos_json'] else [],
        'complemento': r['complemento'],
    } for r in rows]


def resumo_concursos_importados() -> Dict[str, Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute('''
            SELECT loteria_type, COUNT(*) AS total, MIN(concurso) AS primeiro, MAX(concurso) AS ultimo,
                   MAX(importado_em) AS importado_em
            FROM concursos_importados GROUP BY loteria_type
        ''').fetchall()
    return {r['loteria_type']: {
        'total': r['total'], 'primeiro': r['primeiro'], 'ultimo': r['ultimo'],
        'importado_em': r['importado_em'].strftime('%d/%m/%Y %H:%M') if r['importado_em'] else None,
    } for r in rows}


def excluir_concursos_importados(loteria_type: str) -> int:
    with get_db_connection() as conn:
        cur = conn.execute('DELETE FROM concursos_importados WHERE loteria_type = %s', (loteria_type,))
        n = cur.rowcount
        conn.commit()
    return n


def get_latest_sync_logs(limit: int = 20) -> List[Dict[str, Any]]:
    """Buscar últimos logs de sincronização"""
    with get_db_connection() as conn:
        rows = conn.execute(
            'SELECT * FROM sync_logs ORDER BY id DESC LIMIT %s', 
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ==========================================
# GESTÃO DE HISTÓRICO DE APOSTAS DO USUÁRIO
# ==========================================

def _json_opcional(d: Dict[str, Any], coluna: str):
    try:
        return json.loads(d[coluna]) if d.get(coluna) else None
    except Exception:
        return None


def _trevos_da_aposta(d: Dict[str, Any]) -> Optional[List[List[int]]]:
    """Trevos escolhidos em cada jogo da +Milionária (None quando a aposta não os registrou)."""
    return _json_opcional(d, 'trevos_json')


def salvar_aposta(
    loteria_type: str,
    modalidade: str,
    jogos: List[List[int]],
    dezenas_por_jogo: int,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    titulo: Optional[str] = None,
    concurso_alvo: Optional[int] = None,
    trevos: Optional[List[List[int]]] = None,
    complementos: Optional[List[Optional[str]]] = None
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
            (user_id, session_id, loteria_type, titulo, modalidade, quantidade_jogos, dezenas_por_jogo, jogos_json, concurso_alvo,
             trevos_json, complementos_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        ''', (user_id, session_id, loteria_type, titulo, modalidade, len(jogos), dezenas_por_jogo, jogos_json, concurso_alvo,
              json.dumps(trevos) if trevos else None, json.dumps(complementos) if complementos else None))
        last_id = cursor.fetchone()['id']
        conn.commit()
    sync_db_to_cloud()
    return last_id


def listar_apostas(
    loteria_type: Optional[str] = None,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lista apostas do usuário logado ou da sessão atual"""
    import json
    if not user_id and not session_id:
        return []
    with get_db_connection() as conn:
        query = "SELECT * FROM user_bets WHERE "
        params = []

        if user_id:
            query += "(user_id = %s OR session_id = %s) "
            params.extend([user_id, session_id or ''])
        else:
            query += "session_id = %s "
            params.append(session_id)

        if loteria_type:
            query += "AND loteria_type = %s "
            params.append(loteria_type)

        query += "ORDER BY id DESC LIMIT %s"
        params.append(limit)

        rows = conn.execute(query, tuple(params)).fetchall()
        resultado = []
        for r in rows:
            d = dict(r)
            try:
                d['jogos'] = json.loads(d['jogos_json'])
            except Exception:
                d['jogos'] = []
            d['trevos'] = _trevos_da_aposta(d)
            d['complementos'] = _json_opcional(d, 'complementos_json')
            resultado.append(d)
        return resultado


def apostas_para_notificar(loteria_type: str, desde_concurso: int, ate_concurso: int) -> List[Dict[str, Any]]:
    """Apostas de usuários cadastrados, já sorteadas e ainda não processadas pelo aviso por e-mail."""
    with get_db_connection() as conn:
        rows = conn.execute('''
            SELECT b.*, u.email, u.name, u.avisos_email
            FROM user_bets b JOIN users u ON u.id = b.user_id
            WHERE b.loteria_type = %s AND b.concurso_alvo BETWEEN %s AND %s
              AND b.notificado_em IS NULL AND u.is_blocked = 0
            ORDER BY b.user_id, b.id
        ''', (loteria_type, desde_concurso, ate_concurso)).fetchall()
    resultado = []
    for r in rows:
        d = dict(r)
        try:
            d['jogos'] = json.loads(d['jogos_json'])
        except Exception:
            d['jogos'] = []
        d['trevos'] = _trevos_da_aposta(d)
        d['complementos'] = _json_opcional(d, 'complementos_json')
        resultado.append(d)
    return resultado


def marcar_apostas_notificadas(aposta_ids: List[int]):
    if not aposta_ids:
        return
    with get_db_connection() as conn:
        conn.execute('UPDATE user_bets SET notificado_em = CURRENT_TIMESTAMP WHERE id = ANY(%s)', (list(aposta_ids),))
        conn.commit()


def set_avisos_email(user_id: int, ativo: bool):
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET avisos_email = %s WHERE id = %s', (1 if ativo else 0, user_id))
        conn.commit()


def atualizar_complementos_aposta(aposta_id: int, complementos: List[Optional[str]]):
    with get_db_connection() as conn:
        conn.execute('UPDATE user_bets SET complementos_json = %s WHERE id = %s',
                     (json.dumps(complementos), aposta_id))
        conn.commit()


def obter_aposta(aposta_id: int) -> Optional[Dict[str, Any]]:
    """Obtém detalhes completos de uma aposta por ID"""
    import json
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM user_bets WHERE id = %s", (aposta_id,)).fetchone()
        if row:
            d = dict(row)
            try:
                d['jogos'] = json.loads(d['jogos_json'])
            except Exception:
                d['jogos'] = []
            d['trevos'] = _trevos_da_aposta(d)
            d['complementos'] = _json_opcional(d, 'complementos_json')
            return d
        return None


def excluir_aposta(aposta_id: int, user_id: Optional[int] = None, session_id: Optional[str] = None) -> bool:
    """Exclui aposta garantindo autenticação por usuário ou sessão"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM user_bets WHERE id = %s AND (user_id = %s OR session_id = %s)", (aposta_id, user_id, session_id or ''))
        elif session_id:
            cursor.execute("DELETE FROM user_bets WHERE id = %s AND session_id = %s", (aposta_id, session_id))
        else:
            cursor.execute("DELETE FROM user_bets WHERE id = %s", (aposta_id,))
        conn.commit()
        success = cursor.rowcount > 0

    if success:
        sync_db_to_cloud()
    return success


# ==========================================
# CONTROLE DE ACESSO, CRÉDITOS E MONETIZAÇÃO
# ==========================================

def _como_datetime(valor) -> Optional[datetime]:
    """vip_expires_at vem do Postgres como datetime (TIMESTAMP), mas registros antigos podem ser texto."""
    if isinstance(valor, datetime):
        return valor
    if valor:
        try:
            return datetime.strptime(str(valor), '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
    return None


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
    if user.get('plan') in ['vip_mensal', 'vip_24h']:
        vip_expires_at = user.get('vip_expires_at')
        current_plan = user.get('plan', 'vip_mensal')
        if not vip_expires_at:
            return {
                'has_access': True, 
                'reason': 'vip', 
                'credits': user.get('credits', 0), 
                'is_vip': True, 
                'plan': current_plan,
                'name': user.get('name', 'Apostador VIP')
            }
        exp_date = _como_datetime(vip_expires_at)
        if exp_date and datetime.now() <= exp_date:
            return {
                'has_access': True, 
                'reason': 'vip', 
                'credits': user.get('credits', 0), 
                'is_vip': True, 
                'plan': current_plan, 
                'expires_at': exp_date.strftime('%Y-%m-%d %H:%M:%S'),
                'name': user.get('name', 'Apostador VIP')
            }

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
            conn.execute('UPDATE users SET credits = credits - 1 WHERE id = %s AND credits > 0', (user_id,))
            conn.commit()
        return True

    return False


def activate_vip_plan(user_id: int, days: int = 30, plan_name: str = 'vip_mensal'):
    """Ativa ou renova plano VIP por X dias"""
    now = datetime.now()
    user = get_user_by_id(user_id)
    current_exp = user.get('vip_expires_at') if user else None
    current_plan = user.get('plan') if user else None
    
    base_date = now
    parsed = _como_datetime(current_exp)
    vigente = bool(parsed and parsed > now)
    if vigente:
        base_date = parsed

    # Quem tem VIP mensal ainda vigente e compra 24 h continua mensal (só ganha +1 dia);
    # um mensal já vencido não pode voltar a ser mensal comprando o avulso
    if current_plan == 'vip_mensal' and plan_name == 'vip_24h' and vigente:
        plan_name = 'vip_mensal'
            
    new_exp = (base_date + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE users 
            SET plan = %s, vip_expires_at = %s 
            WHERE id = %s
        ''', (plan_name, new_exp, user_id))
        conn.commit()


def add_user_credits(user_id: int, amount: int = 1):
    """Adiciona créditos de análise ao usuário"""
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET credits = credits + %s WHERE id = %s', (amount, user_id))
        conn.commit()


PIX_KEY_DEFAULT = os.environ.get('PIX_KEY', 'silvio.luis.morais@gmail.com')
PIX_BENEFICIARIO_DEFAULT = os.environ.get('PIX_BENEFICIARIO', 'Calculo da Sorte')
PIX_CIDADE_DEFAULT = os.environ.get('PIX_CIDADE', 'SAO PAULO')


def normalizar_chave_pix(chave: str, tipo: Optional[str] = None) -> str:
    """
    Normaliza a chave PIX conforme as normas estritas do BACEN:
    - CPF: apenas 11 dígitos
    - CNPJ: apenas 14 dígitos
    - Telefone: formato internacional com '+' (+55DDD9XXXXXXXX)
    - E-mail: minúsculas e sem espaços
    - Aleatória (EVP): formato UUID minúsculo
    """
    if not chave:
        return ''
    ch = chave.strip()
    
    # Se contém @, é email
    if '@' in ch:
        return ch.lower()
    
    # Se tem formato UUID
    if re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', ch):
        return ch.lower()
        
    numeros = re.sub(r'\D', '', ch)
    
    if tipo == 'telefone' or ch.startswith('+') or '(' in ch or ')' in ch:
        if len(numeros) in (10, 11):
            return f"+55{numeros}"
        elif len(numeros) in (12, 13) and numeros.startswith('55'):
            return f"+{numeros}"
        return f"+{numeros}" if not ch.startswith('+') else ch
        
    if tipo == 'cnpj' or len(numeros) == 14:
        return numeros
        
    if tipo == 'cpf' or (len(numeros) == 11 and ('.' in ch or '-' in ch or not ch.startswith('+'))):
        return numeros
        
    # Se tem 12 ou 13 dígitos começando com 55 e não é CNPJ
    if len(numeros) in (12, 13) and numeros.startswith('55'):
        return f"+{numeros}"
        
    return ch


def identificar_tipo_chave_pix(chave: str) -> str:
    """Identifica o tipo de chave PIX (email, telefone, cpf, cnpj, aleatoria ou desconhecido)"""
    if not chave:
        return 'desconhecido'
    ch = chave.strip()
    if '@' in ch:
        return 'email'
    if re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', ch):
        return 'aleatoria'
    numeros = re.sub(r'\D', '', ch)
    if ch.startswith('+') or '(' in ch or ')' in ch or (len(numeros) in (12, 13) and numeros.startswith('55')):
        return 'telefone'
    if len(numeros) == 14:
        return 'cnpj'
    if len(numeros) == 11:
        return 'cpf'
    return 'desconhecido'


def get_pix_config() -> Dict[str, str]:
    """Retorna as configurações ativas de recebimento PIX (chave, beneficiário, cidade, tipo)"""
    chave = get_setting('pix_key', PIX_KEY_DEFAULT) or PIX_KEY_DEFAULT
    beneficiario = get_setting('pix_beneficiario', PIX_BENEFICIARIO_DEFAULT) or PIX_BENEFICIARIO_DEFAULT
    cidade = get_setting('pix_cidade', PIX_CIDADE_DEFAULT) or PIX_CIDADE_DEFAULT
    chave_norm = normalizar_chave_pix(chave)
    tipo = identificar_tipo_chave_pix(chave_norm)
    return {
        'chave': chave_norm,
        'chave_raw': chave,
        'beneficiario': beneficiario,
        'cidade': cidade,
        'tipo': tipo
    }


def save_pix_config(chave: str, beneficiario: str = '', cidade: str = '') -> Dict[str, Any]:
    """Salva novas configurações PIX persistentes no banco e sincroniza com a nuvem"""
    chave_norm = normalizar_chave_pix(chave)
    set_setting('pix_key', chave_norm)
    if beneficiario:
        set_setting('pix_beneficiario', beneficiario.strip()[:25])
    if cidade:
        set_setting('pix_cidade', cidade.strip()[:15])
    return get_pix_config()


def calcular_crc16_ccitt(payload: str) -> str:
    """Calcula o checksum CRC16-CCITT (polinômio 0x1021, valor inicial 0xFFFF) conforme especificação BACEN para PIX"""
    crc = 0xFFFF
    for byte in payload.encode('utf-8'):
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def gerar_pix_copia_e_cola(chave: str, nome: str, cidade: str, valor: float, txid: str = '***') -> str:
    """Generate the official PIX Copy‑and‑Paste payload (EMVCo / BR Code).
    Includes validation of required fields and CRC integrity.
    """
    import unicodedata
    # Normalizar chave
    chave_clean = normalizar_chave_pix(chave)
    # Normalizar nome e cidade para ASCII sem acentos (requisito universal de compatibilidade bancária)
    nome_norm = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    cidade_norm = unicodedata.normalize('NFKD', cidade).encode('ASCII', 'ignore').decode('ASCII')
    nome_clean = (nome_norm or 'Calculo da Sorte')[:25]
    cidade_clean = (cidade_norm or 'SAO PAULO')[:15]
    # Tag 00: Payload Format Indicator
    p_format = "000201"
    # Tag 01: Point of Initiation Method (11 = Estático / Reutilizável - mandatório pelo BACEN)
    p_init = "010211"
    # Tag 26: Merchant Account Information
    gui = "0014br.gov.bcb.pix"
    key_tag = f"01{len(chave_clean):02d}{chave_clean}"
    merchant_info = gui + key_tag
    tag_26 = f"26{len(merchant_info):02d}{merchant_info}"
    # Tag 52: Merchant Category Code
    tag_52 = "52040000"
    # Tag 53: Transaction Currency (986 = Real brasileiro)
    tag_53 = "5303986"
    # Tag 54: Transaction Amount
    val_str = f"{valor:.2f}"
    tag_54 = f"54{len(val_str):02d}{val_str}"
    # Tag 58: Country Code
    tag_58 = "5802BR"
    # Tag 59: Merchant Name
    tag_59 = f"59{len(nome_clean):02d}{nome_clean}"
    # Tag 60: Merchant City
    tag_60 = f"60{len(cidade_clean):02d}{cidade_clean}"
    # Tag 62: Additional Data Field (txid - '***' é o padrão BACEN para QR estático sem API de conciliação)
    txid_clean = (txid or '***')[:25]
    subtag_05 = f"05{len(txid_clean):02d}{txid_clean}"
    tag_62 = f"62{len(subtag_05):02d}{subtag_05}"
    # Tag 63: CRC16 (Payload com tag 6304 antes do cálculo)
    raw = p_format + p_init + tag_26 + tag_52 + tag_53 + tag_54 + tag_58 + tag_59 + tag_60 + tag_62 + "6304"
    crc = calcular_crc16_ccitt(raw)
    payload = raw + crc
    # Validate payload integrity
    if not validar_payload_pix(payload):
        raise ValueError('Payload PIX inválido ou CRC incorreto')
    return payload
    """
    Gera o payload oficial PIX Copia e Cola no padrão EMVCo / BR Code estabelecido pelo Banco Central do Brasil.
    Garante tags TLV (Tag-Length-Value) rigorosamente corretas, inclusão da Tag 01 (010211 estático) e checksum CRC-16.
    """
    import unicodedata

    # Normalizar chave conforme tipo
    chave_clean = normalizar_chave_pix(chave)

    # Normalizar nome e cidade para ASCII sem acentos (requisito universal de compatibilidade bancária)
    nome_norm = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    cidade_norm = unicodedata.normalize('NFKD', cidade).encode('ASCII', 'ignore').decode('ASCII')
    nome_clean = (nome_norm or 'Calculo da Sorte')[:25]
    cidade_clean = (cidade_norm or 'SAO PAULO')[:15]

    # Tag 00: Payload Format Indicator
    p_format = "000201"

    # Tag 01: Point of Initiation Method (11 = Estático / Reutilizável - mandatório pelo BACEN)
    p_init = "010211"

    # Tag 26: Merchant Account Information
    gui = "0014br.gov.bcb.pix"
    key_tag = f"01{len(chave_clean):02d}{chave_clean}"
    merchant_info = gui + key_tag
    tag_26 = f"26{len(merchant_info):02d}{merchant_info}"

    # Tag 52: Merchant Category Code
    tag_52 = "52040000"

    # Tag 53: Transaction Currency (986 = Real brasileiro)
    tag_53 = "5303986"

    # Tag 54: Transaction Amount
    val_str = f"{valor:.2f}"
    tag_54 = f"54{len(val_str):02d}{val_str}"

    # Tag 58: Country Code
    tag_58 = "5802BR"

    # Tag 59: Merchant Name
    tag_59 = f"59{len(nome_clean):02d}{nome_clean}"

    # Tag 60: Merchant City
    tag_60 = f"60{len(cidade_clean):02d}{cidade_clean}"

    # Tag 62: Additional Data Field (txid - '***' é o padrão BACEN para QR estático sem API de conciliação)
    txid_clean = (txid or '***')[:25]
    subtag_05 = f"05{len(txid_clean):02d}{txid_clean}"
    tag_62 = f"62{len(subtag_05):02d}{subtag_05}"

    # Tag 63: CRC16 (Payload com tag 6304 antes do cálculo)
    raw = p_format + p_init + tag_26 + tag_52 + tag_53 + tag_54 + tag_58 + tag_59 + tag_60 + tag_62 + "6304"
    crc = calcular_crc16_ccitt(raw)
    return raw + crc


def gerar_qrcode_pix_base64(pix_code: str) -> str:
    """Generate a PNG QR code for a PIX payload and return as base64 data URI using the PNG helper."""
    return gerar_qrcode_pix_png_base64(pix_code)


def create_payment(user_id: int, tipo: str, valor: float, loteria_type: Optional[str] = None) -> Dict[str, Any]:
    """Registra uma intenção de pagamento PIX e gera payload oficial Copia e Cola e QR Code vetorial com a chave configurada"""
    import random
    import string
    txid = 'CS' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    pix_cfg = get_pix_config()
    pix_copia_cola = gerar_pix_copia_e_cola(
        chave=pix_cfg['chave'],
        nome=pix_cfg['beneficiario'],
        cidade=pix_cfg['cidade'],
        valor=valor,
        txid='***'
    )
    pix_qr_code_base64 = gerar_qrcode_pix_base64(pix_copia_cola)
    
    with get_db_connection() as conn:
        
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO payments (user_id, tipo, loteria_type, valor, status, pix_copia_cola, pix_txid, pix_qr_code_base64)
            VALUES (%s, %s, %s, %s, 'pendente', %s, %s, %s) RETURNING id
        ''', (user_id, tipo, loteria_type, valor, pix_copia_cola, txid, pix_qr_code_base64))
        payment_id = cursor.fetchone()['id']
        conn.commit()
        
    sync_db_to_cloud()
    return get_payment_by_id(payment_id)


def get_payment_by_id(payment_id: int) -> Optional[Dict[str, Any]]:
    """Obtém detalhes do pagamento garantindo disponibilização do QR Code oficial"""
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM payments WHERE id = %s', (payment_id,)).fetchone()
        if row:
            res = dict(row)
            if not res.get('pix_qr_code_base64') and res.get('pix_copia_cola'):
                res['pix_qr_code_base64'] = gerar_qrcode_pix_base64(res['pix_copia_cola'])
            return res

    if os.environ.get('VERCEL') and sync_db_from_cloud(force=True):
        with get_db_connection() as conn:
            row = conn.execute('SELECT * FROM payments WHERE id = %s', (payment_id,)).fetchone()
            if row:
                res = dict(row)
                if not res.get('pix_qr_code_base64') and res.get('pix_copia_cola'):
                    res['pix_qr_code_base64'] = gerar_qrcode_pix_base64(res['pix_copia_cola'])
                return res

    return None


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
            SET status = 'aprovado', approved_at = %s 
            WHERE id = %s
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), payment_id))
        conn.commit()
        
    if tipo == 'vip_mensal':
        activate_vip_plan(user_id, days=30, plan_name='vip_mensal')
    elif tipo == 'avulso':
        activate_vip_plan(user_id, days=1, plan_name='vip_24h')
    elif tipo in ['analise', 'analise_1', 'credito']:
        add_user_credits(user_id, amount=1)
        
    sync_db_to_cloud()
    return True


def get_all_payments() -> List[Dict[str, Any]]:
    """Listar todos os pagamentos com dados do usuário para o painel admin (sincronizado na nuvem)"""
    with get_db_connection() as conn:
        # Cancela pagamentos pendentes criados há mais de 24 horas
        limite_tempo = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('''
            UPDATE payments
            SET status = 'cancelado'
            WHERE status = 'pendente' AND created_at < %s
        ''', (limite_tempo,))
        conn.commit()

        rows = conn.execute('''
            SELECT p.*, u.email as user_email, u.name as user_name
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.id
            ORDER BY p.id DESC
        ''').fetchall()
        return [dict(r) for r in rows]

def delete_payment(payment_id: int) -> bool:
    """Exclui um pagamento do banco de dados (ex: cancelados ou rejeitados)"""
    with get_db_connection() as conn:
        conn.execute('DELETE FROM payments WHERE id = %s', (payment_id,))
        conn.commit()
    sync_db_to_cloud()
    return True


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
        conn.execute('DELETE FROM user_bets WHERE user_id = %s', (user_id,))
        # 2. Anonimizar pagamentos para fins de auditoria fiscal/contábil (Art. 16, I da LGPD)
        conn.execute('''
            UPDATE payments 
            SET user_id = NULL, pix_copia_cola = 'ANONIMIZADO_LGPD' 
            WHERE user_id = %s
        ''', (user_id,))
        # 3. Excluir conta do usuário
        conn.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
    sync_db_to_cloud()
    return True






def sync_db_to_cloud(*args, **kwargs):
    return True

def sync_db_from_cloud(*args, **kwargs):
    return True


def log_chat_message(user_ident: str, loteria_nome: str, mensagem_usuario: str, resposta_ia: str):
    """Grava as conversas do chat de suporte no banco"""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO chat_logs (user_ident, loteria_nome, pergunta, resposta) VALUES (%s, %s, %s, %s)",
                (user_ident, loteria_nome, mensagem_usuario, resposta_ia)
            )
            conn.commit()
    except Exception as e:
        print(f"Erro ao gravar log do chat: {e}")

def get_all_chat_logs(limit: int = 50) -> list:
    """Recupera logs do chat de suporte"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM chat_logs ORDER BY created_at DESC LIMIT %s", (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Erro ao listar logs do chat: {e}")
        return []


def log_system_error(module: str, error_message: str):
    """Grava erros críticos do sistema (APIs, Motor Heurístico, etc) no banco"""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO system_errors (module, error_message) VALUES (%s, %s)",
                (module, str(error_message))
            )
            conn.commit()
    except Exception as e:
        print(f"Erro falho ao gravar log de erro no sistema: {e}")

def get_system_errors(limit: int = 50) -> list:
    """Recupera os últimos erros do sistema"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM system_errors ORDER BY created_at DESC LIMIT %s", (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Erro ao listar erros do sistema: {e}")
        return []

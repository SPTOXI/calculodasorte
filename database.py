"""
Módulo de Banco de Dados SQLite para Gestão de Usuários e Autenticação
Projeto Calculadora da Sorte
"""

import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash

import blob_storage

ORIGINAL_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
if os.environ.get('VERCEL'):
    DATA_DIR = os.path.join('/tmp', 'data')
else:
    DATA_DIR = ORIGINAL_DATA_DIR

DB_PATH = os.path.join(DATA_DIR, 'database.db')

from contextlib import contextmanager

_LAST_CLOUD_SYNC = 0.0

def sync_db_from_cloud(force: bool = False) -> bool:
    """Sincroniza o banco local com a versão persistente na nuvem (Vercel Blob)"""
    global _LAST_CLOUD_SYNC
    now = time.time()
    if not force and (now - _LAST_CLOUD_SYNC < 4.0):
        return False
    
    if not blob_storage.get_blob_token():
        return False

    success = blob_storage.download_blob('database.db', DB_PATH)
    if success:
        _LAST_CLOUD_SYNC = now
    return success


def sync_db_to_cloud() -> bool:
    """Envia o banco local atualizado para o Vercel Blob"""
    global _LAST_CLOUD_SYNC
    if not blob_storage.get_blob_token():
        if os.environ.get('VERCEL'):
            print("[DB] AVISO: BLOB_READ_WRITE_TOKEN não configurado no Vercel. Alterações não serão persistidas entre instâncias.")
        return False
    
    success = blob_storage.upload_blob(DB_PATH, 'database.db')
    if success:
        _LAST_CLOUD_SYNC = time.time()
    else:
        print("[DB] ERRO: Falha ao sincronizar banco local com Vercel Blob.")
    return success


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
    """Inicializa as tabelas do banco de dados e cria o administrador padrão com suporte a Vercel Blob"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if os.environ.get('VERCEL') or not os.path.exists(DB_PATH):
        bundled_db = os.path.join(ORIGINAL_DATA_DIR, 'database.db')
        if not os.path.exists(DB_PATH) and os.path.exists(bundled_db):
            try:
                import shutil
                shutil.copy2(bundled_db, DB_PATH)
                print(f"[DB] Banco inicial copiado de {bundled_db} para {DB_PATH}")
            except Exception as e:
                print(f"[DB] Aviso ao copiar banco empacotado: {e}")
        
        sync_db_from_cloud(force=True)

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
        
        # Índice Case-Insensitive para consultas de e-mail de alta performance e resiliência mobile
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email_nocase ON users (email COLLATE NOCASE)')
        
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
                pix_qr_code_base64 TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Migração segura para bases existentes
        try:
            cursor.execute('ALTER TABLE payments ADD COLUMN pix_qr_code_base64 TEXT')
        except Exception:
            pass
        
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
    """Buscar usuário por ID com fallback para sincronização na nuvem"""
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if row:
            return dict(row)

    # Se não encontrou localmente no container serverless, busca versão mais recente na nuvem
    if (os.environ.get('VERCEL') or blob_storage.get_blob_token()) and sync_db_from_cloud(force=True):
        with get_db_connection() as conn:
            row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
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
            'SELECT * FROM users WHERE LOWER(email) = ?', 
            (email_clean,)
        ).fetchone()
        if row:
            return dict(row)

    # Se não encontrou localmente no container serverless, busca versão mais recente na nuvem
    if (os.environ.get('VERCEL') or blob_storage.get_blob_token()) and sync_db_from_cloud(force=True):
        with get_db_connection() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE LOWER(email) = ?', 
                (email_clean,)
            ).fetchone()
            if row:
                print(f"[DB] Usuário {email_clean} localizado com sucesso após sincronização em nuvem.")
                return dict(row)

    return None


def get_all_users() -> List[Dict[str, Any]]:
    """Listar todos os usuários com dados de plano e créditos (sincronizado com a nuvem)"""
    if os.environ.get('VERCEL') or blob_storage.get_blob_token():
        sync_db_from_cloud(force=True)
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
    """Criar novo usuário no sistema com crédito de cortesia e sincronização em nuvem"""
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

    sync_db_to_cloud()
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

    sync_db_to_cloud()
    return bool(new_status)


def delete_user(user_id: int) -> bool:
    """Excluir usuário"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
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
            SET password_hash = ?, must_change_password = 0 
            WHERE id = ?
        ''', (pwd_hash, user_id))
        conn.commit()
    sync_db_to_cloud()
    return True


def set_must_change_password(user_id: int, flag: int = 1):
    """Define flag se usuário deve trocar de senha"""
    with get_db_connection() as conn:
        conn.execute('UPDATE users SET must_change_password = ? WHERE id = ?', (flag, user_id))
        conn.commit()
    sync_db_to_cloud()



def record_login(user_id: int):
    """Registrar data/hora do login"""
    with get_db_connection() as conn:
        conn.execute(
            'UPDATE users SET last_login = ? WHERE id = ?', 
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
        last_id = cursor.lastrowid
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
        success = cursor.rowcount > 0

    if success:
        sync_db_to_cloud()
    return success


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


PIX_KEY_DEFAULT = os.environ.get('PIX_KEY', 'silvio.luis.morais@gmail.com')
PIX_BENEFICIARIO_DEFAULT = os.environ.get('PIX_BENEFICIARIO', 'Calculo da Sorte')
PIX_CIDADE_DEFAULT = os.environ.get('PIX_CIDADE', 'SAO PAULO')


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
    """
    Gera o payload oficial PIX Copia e Cola no padrão EMVCo / BR Code estabelecido pelo Banco Central do Brasil.
    Garante tags TLV (Tag-Length-Value) rigorosamente corretas e checksum CRC-16/CCITT-FALSE.
    """
    import unicodedata

    # Normalizar nome e cidade para ASCII sem acentos (requisito universal de compatibilidade bancária)
    nome_norm = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    cidade_norm = unicodedata.normalize('NFKD', cidade).encode('ASCII', 'ignore').decode('ASCII')
    nome_clean = (nome_norm or 'Calculo da Sorte')[:25]
    cidade_clean = (cidade_norm or 'SAO PAULO')[:15]

    # Tag 00: Payload Format Indicator
    p_format = "000201"

    # Tag 26: Merchant Account Information
    gui = "0014br.gov.bcb.pix"
    key_tag = f"01{len(chave):02d}{chave}"
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

    # Tag 62: Additional Data Field (txid)
    txid_clean = txid[:25] if txid else '***'
    subtag_05 = f"05{len(txid_clean):02d}{txid_clean}"
    tag_62 = f"62{len(subtag_05):02d}{subtag_05}"

    # Tag 63: CRC16 (Payload sem os 4 dígitos do checksum)
    raw = p_format + tag_26 + tag_52 + tag_53 + tag_54 + tag_58 + tag_59 + tag_60 + tag_62 + "6304"
    crc = calcular_crc16_ccitt(raw)
    return raw + crc


def gerar_qrcode_pix_base64(pix_code: str) -> str:
    """Gera imagem vetorial SVG de alta resolução legível por qualquer app bancário, codificada em data URI base64"""
    if not pix_code:
        return ""
    try:
        import qrcode
        import qrcode.image.svg
        import io
        import base64

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(pix_code)
        qr.make(fit=True)

        factory = qrcode.image.svg.SvgPathImage
        img = qr.make_image(image_factory=factory)
        stream = io.BytesIO()
        img.save(stream)
        svg_bytes = stream.getvalue()
        svg_base64 = base64.b64encode(svg_bytes).decode('ascii')
        return f"data:image/svg+xml;base64,{svg_base64}"
    except Exception as e:
        print(f"[QRCODE] Erro ao gerar QR Code vetorial: {e}")
        return ""


def create_payment(user_id: int, tipo: str, valor: float, loteria_type: Optional[str] = None) -> Dict[str, Any]:
    """Registra uma intenção de pagamento PIX e gera payload oficial Copia e Cola e QR Code vetorial"""
    import random
    import string
    txid = 'CS' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    pix_copia_cola = gerar_pix_copia_e_cola(
        chave=PIX_KEY_DEFAULT,
        nome=PIX_BENEFICIARIO_DEFAULT,
        cidade=PIX_CIDADE_DEFAULT,
        valor=valor,
        txid=txid
    )
    pix_qr_code_base64 = gerar_qrcode_pix_base64(pix_copia_cola)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO payments (user_id, tipo, loteria_type, valor, status, pix_copia_cola, pix_txid, pix_qr_code_base64)
            VALUES (?, ?, ?, ?, 'pendente', ?, ?, ?)
        ''', (user_id, tipo, loteria_type, valor, pix_copia_cola, txid, pix_qr_code_base64))
        conn.commit()
        payment_id = cursor.lastrowid
        
    sync_db_to_cloud()
    return get_payment_by_id(payment_id)


def get_payment_by_id(payment_id: int) -> Optional[Dict[str, Any]]:
    """Obtém detalhes do pagamento garantindo disponibilização do QR Code oficial"""
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM payments WHERE id = ?', (payment_id,)).fetchone()
        if row:
            res = dict(row)
            if not res.get('pix_qr_code_base64') and res.get('pix_copia_cola'):
                res['pix_qr_code_base64'] = gerar_qrcode_pix_base64(res['pix_copia_cola'])
            return res

    if os.environ.get('VERCEL') and sync_db_from_cloud(force=True):
        with get_db_connection() as conn:
            row = conn.execute('SELECT * FROM payments WHERE id = ?', (payment_id,)).fetchone()
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
            SET status = 'aprovado', approved_at = ? 
            WHERE id = ?
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), payment_id))
        conn.commit()
        
    if tipo == 'vip_mensal':
        activate_vip_plan(user_id, days=30)
    elif tipo == 'avulso':
        add_user_credits(user_id, amount=1)
        
    sync_db_to_cloud()
    return True


def get_all_payments() -> List[Dict[str, Any]]:
    """Listar todos os pagamentos com dados do usuário para o painel admin (sincronizado na nuvem)"""
    if os.environ.get('VERCEL') or blob_storage.get_blob_token():
        sync_db_from_cloud(force=True)
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
    sync_db_to_cloud()
    return True





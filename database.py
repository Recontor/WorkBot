import sqlite3
from contextlib import contextmanager
import config

DB_NAME = "exchange_bot.db"

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_connection() as conn:
        # Таблиця курсів (Купівля, Продаж, Опт Купівля, Опт Продаж)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rates (
                currency TEXT PRIMARY KEY,
                buy REAL, 
                sell REAL, 
                buy_opt REAL, 
                sell_opt REAL
            )
        """)
        
        # Таблиця користувачів
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                language_code TEXT,
                is_premium INTEGER,
                is_banned INTEGER DEFAULT 0,
                trust_level INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Активні адмін-сесії
        conn.execute("""
            CREATE TABLE IF NOT EXISTS active_admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Налаштування (Турбо-режим, Крос-курси текстом, Нотатки)
        conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        
        # Дефолтні налаштування
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('turbo_mode', 'off')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_note', 'Ваші нотатки тут...')")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('cross_rates_info', 'USD/EUR: 0.92')")

        # Логи та Заявки
        conn.execute("CREATE TABLE IF NOT EXISTS message_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message_text TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS exchange_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, contact TEXT, details TEXT, status TEXT DEFAULT 'new', timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        
        conn.commit()

# --- ФУНКЦІЇ КУРСІВ ---

def set_rate(currency, buy, sell, buy_opt, sell_opt):
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO rates VALUES (?, ?, ?, ?, ?)", 
                     (currency, buy, sell, buy_opt, sell_opt))
        conn.commit()

def get_rate(currency):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT buy, sell, buy_opt, sell_opt FROM rates WHERE currency = ?", (currency,))
        res = cursor.fetchone()
        return dict(res) if res else None

def update_cross_rates_text(text):
    with get_connection() as conn:
        conn.execute("UPDATE settings SET value = ? WHERE key = 'cross_rates_info'", (text,))
        conn.commit()
        
# --- РОБОТА З КОРИСТУВАЧАМИ ---

def register_user_activity(user_id, username, full_name, lang, is_premium):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, full_name, language_code, is_premium, last_activity)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET 
                username=excluded.username, 
                full_name=excluded.full_name,
                last_activity=CURRENT_TIMESTAMP
        """, (user_id, username, full_name, lang, 1 if is_premium else 0))
        conn.commit()

def get_user(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        return dict(res) if res else {'trust_level': 1, 'is_banned': 0}

def get_user_full_info(user_id):
    return get_user(user_id)

def ban_user(user_id):
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        conn.commit()

def is_user_banned(user_id):
    user = get_user(user_id)
    return user.get('is_banned') == 1

def set_trust_level(user_id, level):
    with get_connection() as conn:
        conn.execute("UPDATE users SET trust_level = ? WHERE user_id = ?", (level, user_id))
        conn.commit()

def get_all_users():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row['user_id'] for row in cursor.fetchall()]

# --- АДМІН-ФУНКЦІЇ ТА НАЛАШТУВАННЯ ---

def register_admin_session(user_id, username):
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO active_admins (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()

def get_active_admins():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM active_admins")
        return [row['user_id'] for row in cursor.fetchall()]

def logout_admin(user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM active_admins WHERE user_id = ?", (user_id,))
        conn.commit()

def set_setting(key, value):
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()

def get_setting(key):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        res = cursor.fetchone()
        return res['value'] if res else None

def set_turbo_mode(status):
    with get_connection() as conn:
        conn.execute("UPDATE settings SET value = ? WHERE key = 'turbo_mode'", (status,))
        conn.commit()

def update_note(text):
    with get_connection() as conn:
        conn.execute("UPDATE settings SET value = ? WHERE key = 'admin_note'", (text,))
        conn.commit()

def get_note():
    return get_setting('admin_note')

# --- ЗАЯВКИ ТА ЛОГИ ---

def save_exchange_request(user_id, username, contact, details):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO exchange_requests (user_id, username, contact, details) VALUES (?, ?, ?, ?)",
                       (user_id, username, contact, details))
        conn.commit()
        return cursor.lastrowid

def log_message(user_id, text):
    with get_connection() as conn:
        conn.execute("INSERT INTO message_logs (user_id, message_text) VALUES (?, ?)", (user_id, text))
        conn.commit()

def get_user_logs(user_id, limit=10):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT message_text as msg, timestamp FROM message_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?", 
                       (user_id, limit))
        return [dict(row) for row in cursor.fetchall()]
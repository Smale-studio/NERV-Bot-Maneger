import sqlite3
import os
from datetime import datetime, timedelta
from config import DB_PATH, MAX_MEMORY_CHARS, MEMORY_DAYS


# ══════════════════════════════════════════
#               INIT
# ══════════════════════════════════════════

def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                char_count  INTEGER DEFAULT 0,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS thinking (
                chat_id   INTEGER PRIMARY KEY,
                query     TEXT,
                melchior  TEXT,
                balthasar TEXT,
                caspar    TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_msg_chat ON messages(chat_id);
            CREATE INDEX IF NOT EXISTS idx_msg_time ON messages(timestamp);
        """)
        c.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance','false')")
        c.commit()


# ══════════════════════════════════════════
#               MESSAGES
# ══════════════════════════════════════════

def add_message(chat_id: int, role: str, content: str) -> bool:
    """Добавляет сообщение. Возвращает True если была автоочистка."""
    char_count = len(content)
    with _conn() as c:
        c.execute(
            "INSERT INTO messages (chat_id, role, content, char_count) VALUES (?,?,?,?)",
            (chat_id, role, content, char_count)
        )
        c.commit()

        total = c.execute(
            "SELECT SUM(char_count) FROM messages WHERE chat_id=?", (chat_id,)
        ).fetchone()[0] or 0

        if total > MAX_MEMORY_CHARS:
            # Удаляем старейшую половину сообщений чата
            c.execute("""
                DELETE FROM messages WHERE id IN (
                    SELECT id FROM messages WHERE chat_id=?
                    ORDER BY timestamp ASC
                    LIMIT (SELECT COUNT(*)/2 FROM messages WHERE chat_id=?)
                )
            """, (chat_id, chat_id))
            c.commit()
            return True
    return False


def get_context(chat_id: int, n: int = 3) -> list[dict]:
    """Возвращает последние n сообщений чата."""
    with _conn() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE chat_id=? ORDER BY timestamp DESC LIMIT ?",
            (chat_id, n)
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def clear_chat(chat_id: int):
    with _conn() as c:
        c.execute("DELETE FROM messages  WHERE chat_id=?", (chat_id,))
        c.execute("DELETE FROM thinking  WHERE chat_id=?", (chat_id,))
        c.commit()


def clear_all():
    with _conn() as c:
        c.execute("DELETE FROM messages")
        c.execute("DELETE FROM thinking")
        c.commit()


def cleanup_old():
    """Удаляет сообщения старше MEMORY_DAYS."""
    cutoff = (datetime.now() - timedelta(days=MEMORY_DAYS)).isoformat()
    with _conn() as c:
        c.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
        c.commit()


# ══════════════════════════════════════════
#               THINKING
# ══════════════════════════════════════════

def save_thinking(chat_id: int, query: str,
                  melchior: str, balthasar: str, caspar: str):
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO thinking
              (chat_id, query, melchior, balthasar, caspar, timestamp)
            VALUES (?,?,?,?,?, CURRENT_TIMESTAMP)
        """, (chat_id, query, melchior, balthasar, caspar))
        c.commit()


def get_thinking(chat_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT query, melchior, balthasar, caspar FROM thinking WHERE chat_id=?",
            (chat_id,)
        ).fetchone()
    if row:
        return {"query": row[0], "melchior": row[1],
                "balthasar": row[2], "caspar": row[3]}
    return None


# ══════════════════════════════════════════
#               SETTINGS
# ══════════════════════════════════════════

def get_maintenance() -> bool:
    with _conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key='maintenance'").fetchone()
    return row[0] == "true" if row else False


def set_maintenance(enabled: bool):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO settings VALUES ('maintenance',?)",
                  ("true" if enabled else "false",))
        c.commit()


def get_stats() -> dict:
    with _conn() as c:
        msgs   = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        chats  = c.execute("SELECT COUNT(DISTINCT chat_id) FROM messages").fetchone()[0]
        chars  = c.execute("SELECT SUM(char_count) FROM messages").fetchone()[0] or 0
    return {"messages": msgs, "chats": chats, "chars": chars}


# ══════════════════════════════════════════
#         WHITELIST / BLACKLIST
# ══════════════════════════════════════════

def get_access_mode() -> str:
    with _conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key='access_mode'").fetchone()
    return row[0] if row else "off"


def set_access_mode(mode: str):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO settings VALUES ('access_mode', ?)", (mode,))
        c.commit()


def add_to_list(list_name: str, chat_id: int):
    with _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS chat_list (chat_id INTEGER NOT NULL, list TEXT NOT NULL, PRIMARY KEY (chat_id, list))")
        c.execute("INSERT OR IGNORE INTO chat_list (chat_id, list) VALUES (?, ?)", (chat_id, list_name))
        c.commit()


def remove_from_list(list_name: str, chat_id: int):
    with _conn() as c:
        c.execute("DELETE FROM chat_list WHERE chat_id=? AND list=?", (chat_id, list_name))
        c.commit()


def get_list(list_name: str) -> list:
    with _conn() as c:
        try:
            rows = c.execute("SELECT chat_id FROM chat_list WHERE list=?", (list_name,)).fetchall()
        except Exception:
            return []
    return [r[0] for r in rows]


def is_chat_allowed(chat_id: int) -> bool:
    mode = get_access_mode()
    if mode == "off":
        return True
    if mode == "whitelist":
        return chat_id in get_list("whitelist")
    if mode == "blacklist":
        return chat_id not in get_list("blacklist")
    return True

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Telegram ──────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")

# ── OpenRouter ────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ── Admin ─────────────────────────────────
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # твой Telegram user ID

# ── Models ────────────────────────────────
DEEPSEEK_MODEL = "deepseek/deepseek-chat"
VISION_MODEL_FREE  = "google/gemma-4-26b-a4b-it:free"
VISION_MODEL_PAID  = "google/gemma-4-26b-a4b-it"
ADMIN_TITLE        = "Командующий"
QWEN_VL_MODEL  = "qwen/qwen-vl-plus"

# ── Database ──────────────────────────────
DB_PATH = "data/magi_bot.db"

# ── Memory settings ───────────────────────
MAX_MEMORY_CHARS  = 2_000_000   # символов на чат до автоочистки
MEMORY_DAYS       = 30          # дней хранения сообщений
CONTEXT_MESSAGES  = 3           # сколько последних сообщений отдавать AI

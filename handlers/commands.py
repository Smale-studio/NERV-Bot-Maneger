import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_ID, CONTEXT_MESSAGES
from database import (
    get_context, add_message, clear_chat, clear_all,
    get_thinking, save_thinking, get_maintenance, is_chat_allowed,
)
from magi_ai import magi_council
from handlers.safe_send import safe_reply, safe_edit

logger = logging.getLogger(__name__)

MAX_TG = 3800  # Telegram limit ~4096, держим запас


def _truncate(text: str, limit: int = MAX_TG) -> str:
    if len(text) > limit:
        return text[:limit] + "\n…_(сокращено)_"
    return text


# ══════════════════════════════════════════
#  /help  /start
# ══════════════════════════════════════════

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot.username
    is_admin = update.effective_user.id == ADMIN_ID

    text = (
        "🔵 *MAGI — Суперкомпьютерная система NERV*\n\n"
        "*Как вызвать в группе:*\n"
        f"• @{bot} — обычный вопрос\n"
        "• Ответить на сообщение бота\n"
        "• В личке — просто пиши\n\n"
        "*Команды:*\n"
        "`/think вопрос` — Совет трёх MAGI\n"
        "`/view_thinking` — Последнее рассуждение совета\n"
        "`/help` — Это сообщение"
    )

    if is_admin:
        text += (
            "\n\n*Команды администратора:*\n"
            "`/power_off` — Режим обслуживания (только ты)\n"
            "`/power_on` — Вернуть обычную работу\n"
            "`/stats` — Статистика бота\n"
            "`/clear` — Очистить память этого чата\n"
            "`/clear all` — Очистить всю память\n"
            "`/clear chat_id` — Очистить память по ID\n\n"
            "*Списки доступа (взаимоисключающие):*\n"
            "`/whitelist_on` — Включить белый список\n"
            "`/blacklist_on` — Включить чёрный список\n"
            "`/access_off` — Выключить фильтрацию\n"
            "`/whitelist_add [id]` — Добавить чат\n"
            "`/whitelist_remove [id]` — Убрать чат\n"
            "`/blacklist_add [id]` — Добавить чат\n"
            "`/blacklist_remove [id]` — Убрать чат\n"
            "`/access_status` — Текущий режим и списки"
        )

    try:
        await safe_reply(update.message, text)
    except Exception as e:
        logger.error(f"help_command failed: {e}")


# ══════════════════════════════════════════
#  /clear
# ══════════════════════════════════════════

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🔴 Только администратор может очищать память.")
        return

    args = context.args

    if args and args[0] == "all":
        clear_all()
        await safe_reply(update.message, "🗑 Вся память очищена.")

    elif args and args[0].lstrip("-").isdigit():
        cid = int(args[0])
        clear_chat(cid)
        await safe_reply(update.message, f"🗑 Память чата `{cid}` очищена.")

    else:
        clear_chat(update.effective_chat.id)
        await safe_reply(update.message, "🗑 Память этого чата очищена.")


# ══════════════════════════════════════════
#  /think
# ══════════════════════════════════════════

async def think_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id != ADMIN_ID and not is_chat_allowed(chat_id):
        return

    if get_maintenance() and user_id != ADMIN_ID:
        return

    # Получаем запрос: из аргументов или цитируемого сообщения
    query = " ".join(context.args).strip() if context.args else ""
    if not query and update.message.reply_to_message:
        query = (update.message.reply_to_message.text or "").strip()
    if not query:
        await safe_reply(update.message, "💡 Укажи вопрос: `/think Стоит ли мне...`")
        return

    # Начальный статус
    status_lines = {
        "melchior":  "🟡 Melchior думает . . .",
        "balthasar": "🟡 Balthasar думает . . .",
        "caspar":    "🟡 Caspar думает . . .",
    }

    def build_status(done: set) -> str:
        lines = ["🔵 *MAGI приступили к работе...*\n"]
        icons = {
            "melchior":  ("✅ Melchior закончил",      "🟡 Melchior думает . . ."),
            "balthasar": ("✅ Balthasar закончила",     "🟡 Balthasar думает . . ."),
            "caspar":    ("✅ Caspar закончил",         "🟡 Caspar думает . . ."),
        }
        for name, (done_txt, wait_txt) in icons.items():
            lines.append(done_txt if name in done else wait_txt)
        lines.append("\n⏳ Chairman ждёт решений совета . . .")
        return "\n".join(lines)

    status_msg = await safe_reply(update.message, build_status(set()))

    completed: set[str] = set()

    async def on_complete(name: str, _result: str):
        completed.add(name)
        await safe_edit(status_msg, build_status(completed))

    ctx = get_context(chat_id, CONTEXT_MESSAGES)

    try:
        results = await magi_council(query, ctx, on_complete=on_complete)
    except Exception as e:
        await safe_edit(status_msg, f"🔴 Ошибка MAGI: {e}")
        return

    # Сохраняем рассуждения (только последнее на чат)
    save_thinking(chat_id, query,
                  results["melchior"], results["balthasar"], results["caspar"])

    # Сохраняем в общую память
    add_message(chat_id, "user", query)
    add_message(chat_id, "assistant", results["chairman"])

    chairman_text = _truncate(results["chairman"])
    final = (
        "🔵 *MAGI — Решение принято*\n\n"
        "✅ Melchior закончил\n"
        "✅ Balthasar закончила\n"
        "✅ Caspar закончил\n\n"
        f"*Chairman:*\n{chairman_text}"
    )

    edited = await safe_edit(status_msg, final)
    if edited is None:
        await safe_reply(update.message, final)


# ══════════════════════════════════════════
#  /view_thinking
# ══════════════════════════════════════════

async def view_thinking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id != ADMIN_ID and not is_chat_allowed(chat_id):
        return

    if get_maintenance() and user_id != ADMIN_ID:
        return

    t = get_thinking(chat_id)
    if not t:
        await safe_reply(update.message, "🔵 Нет сохранённых рассуждений для этого чата.")
        return

    header = f"_Вопрос: {t['query']}_\n\n" if t.get("query") else ""

    for label, key in [("Melchior", "melchior"),
                        ("Balthasar", "balthasar"),
                        ("Caspar", "caspar")]:
        text = _truncate(f"🔵 *{label}:*\n{header}{t[key]}")
        await safe_reply(update.message, text)

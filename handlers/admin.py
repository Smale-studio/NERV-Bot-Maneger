from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from database import (
    get_maintenance, set_maintenance, get_stats,
    get_access_mode, set_access_mode,
    add_to_list, remove_from_list, get_list,
)
from handlers.safe_send import safe_reply


def _is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID


def _target_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Берёт chat_id из аргумента команды, иначе — текущий чат."""
    if context.args and context.args[0].lstrip("-").isdigit():
        return int(context.args[0])
    return update.effective_chat.id


async def power_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    set_maintenance(True)
    await safe_reply(
        update.message,
        "🔧 Режим обслуживания *ВКЛЮЧЁН*.\nБот отвечает только тебе.",
    )


async def power_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    set_maintenance(False)
    await safe_reply(
        update.message,
        "✅ Режим обслуживания *ВЫКЛЮЧЕН*.\nБот снова отвечает всем.",
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    s = get_stats()
    maintenance = get_maintenance()
    mode = get_access_mode()
    text = (
        f"📊 *Статистика MAGI*\n\n"
        f"Сообщений в памяти: `{s['messages']}`\n"
        f"Активных чатов: `{s['chats']}`\n"
        f"Символов в памяти: `{s['chars']:,}`\n"
        f"Обслуживание: {'🔧 ВКЛ' if maintenance else '✅ ВЫКЛ'}\n"
        f"Режим доступа: `{mode}`"
    )
    await safe_reply(update.message, text)


# ══════════════════════════════════════════
#         WHITELIST / BLACKLIST
# ══════════════════════════════════════════

async def whitelist_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    set_access_mode("whitelist")
    await safe_reply(
        update.message,
        "✅ Режим *белого списка* включён.\nЧёрный список отключён автоматически.\n"
        "Бот теперь работает только в чатах из белого списка.",
    )


async def blacklist_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    set_access_mode("blacklist")
    await safe_reply(
        update.message,
        "✅ Режим *чёрного списка* включён.\nБелый список отключён автоматически.\n"
        "Бот теперь работает везде, кроме чатов из чёрного списка.",
    )


async def access_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    set_access_mode("off")
    await safe_reply(update.message, "✅ Фильтрация по спискам отключена. Бот работает везде.")


async def whitelist_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    cid = _target_chat_id(update, context)
    add_to_list("whitelist", cid)
    await safe_reply(update.message, f"✅ Чат `{cid}` добавлен в белый список.")


async def whitelist_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    cid = _target_chat_id(update, context)
    remove_from_list("whitelist", cid)
    await safe_reply(update.message, f"🗑 Чат `{cid}` удалён из белого списка.")


async def blacklist_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    cid = _target_chat_id(update, context)
    add_to_list("blacklist", cid)
    await safe_reply(update.message, f"✅ Чат `{cid}` добавлен в чёрный список.")


async def blacklist_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    cid = _target_chat_id(update, context)
    remove_from_list("blacklist", cid)
    await safe_reply(update.message, f"🗑 Чат `{cid}` удалён из чёрного списка.")


async def access_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    mode = get_access_mode()
    wl = get_list("whitelist")
    bl = get_list("blacklist")
    wl_text = "\n".join(f"`{cid}`" for cid in wl) or "_пусто_"
    bl_text = "\n".join(f"`{cid}`" for cid in bl) or "_пусто_"
    text = (
        f"📋 *Списки доступа*\n\n"
        f"Активный режим: `{mode}`\n\n"
        f"*Белый список:*\n{wl_text}\n\n"
        f"*Чёрный список:*\n{bl_text}"
    )
    await safe_reply(update.message, text)

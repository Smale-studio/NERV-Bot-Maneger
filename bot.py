import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
)
from config import TELEGRAM_TOKEN
from database import init_db
from handlers.commands  import (
    help_command, clear_command, think_command, view_thinking_command,
)
from handlers.messages  import handle_message
from handlers.admin     import (
    power_off_command, power_on_command, stats_command,
    whitelist_on_command, blacklist_on_command, access_off_command,
    whitelist_add_command, whitelist_remove_command,
    blacklist_add_command, blacklist_remove_command,
    access_status_command,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context):
    """Логирует все необработанные исключения, чтобы они не пропадали тихо."""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)


def main():
    init_db()
    logger.info("База данных инициализирована")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_error_handler(error_handler)

    # ── Команды ───────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",         help_command))
    app.add_handler(CommandHandler("help",          help_command))
    app.add_handler(CommandHandler("power_off",     power_off_command))
    app.add_handler(CommandHandler("power_on",      power_on_command))
    app.add_handler(CommandHandler("stats",         stats_command))
    app.add_handler(CommandHandler("whitelist_on",     whitelist_on_command))
    app.add_handler(CommandHandler("blacklist_on",     blacklist_on_command))
    app.add_handler(CommandHandler("access_off",       access_off_command))
    app.add_handler(CommandHandler("whitelist_add",    whitelist_add_command))
    app.add_handler(CommandHandler("whitelist_remove", whitelist_remove_command))
    app.add_handler(CommandHandler("blacklist_add",    blacklist_add_command))
    app.add_handler(CommandHandler("blacklist_remove", blacklist_remove_command))
    app.add_handler(CommandHandler("access_status",    access_status_command))
    app.add_handler(CommandHandler("clear",         clear_command))
    app.add_handler(CommandHandler("think",         think_command))
    app.add_handler(CommandHandler("view_thinking", view_thinking_command))

    # ── Обычные сообщения: текст + фото + видео + документы-медиа ────────
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.VIDEO_NOTE
         | filters.Document.IMAGE | filters.Document.VIDEO) & ~filters.COMMAND,
        handle_message,
    ))

    logger.info("MAGI Bot запущен. Ожидание сообщений...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

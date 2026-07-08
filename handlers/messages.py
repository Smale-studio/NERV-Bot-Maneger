import base64
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatType

from config import ADMIN_ID, CONTEXT_MESSAGES, ADMIN_TITLE
from database import add_message, get_context, get_maintenance, cleanup_old, is_chat_allowed
from magi_ai import chairman_response, vision_response
from handlers.safe_send import safe_reply

logger = logging.getLogger(__name__)


def _should_respond(update: Update, bot_username: str) -> bool:
    """Проверяет, должен ли бот ответить на это сообщение."""
    msg = update.message
    if not msg:
        return False

    # В личке — всегда отвечать
    if msg.chat.type == ChatType.PRIVATE:
        return True

    # Упоминание @бота в тексте или подписи
    text = msg.text or msg.caption or ""
    if f"@{bot_username}" in text:
        return True

    # Ответ на сообщение бота
    if (msg.reply_to_message
            and msg.reply_to_message.from_user
            and msg.reply_to_message.from_user.username == bot_username):
        return True

    return False


def _author_label(user, user_id: int) -> str:
    """Формирует подпись автора: имя (+username) и метку Командующего для админа."""
    name = user.first_name or "Пользователь"
    if user.username:
        label = f"{name} (@{user.username})"
    else:
        label = f"{name} [ID:{user_id}]"
    if user_id == ADMIN_ID:
        label = f"{label} [{ADMIN_TITLE.upper()}]"
    return label


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    user_id  = update.effective_user.id
    chat_id  = msg.chat_id
    bot_name = context.bot.username

    # ── Чёрный/белый список — админ всегда в обход ────────────────────────
    if user_id != ADMIN_ID and not is_chat_allowed(chat_id):
        return

    # ── Сохраняем ВСЕ сообщения для контекста ────────────────────────────
    raw_text = msg.text or msg.caption or ""
    if raw_text:
        label = _author_label(msg.from_user, user_id)
        add_message(chat_id, "user", f"{label}: {raw_text}")

    # Периодическая очистка устаревших записей
    if msg.message_id % 150 == 0:
        cleanup_old()

    # ── Проверяем режим обслуживания ──────────────────────────────────────
    if get_maintenance() and user_id != ADMIN_ID:
        return

    # ── Проверяем, нужно ли отвечать ─────────────────────────────────────
    if not _should_respond(update, bot_name):
        return

    ctx = get_context(chat_id, CONTEXT_MESSAGES)

    # Убираем упоминание бота из текста запроса
    query = raw_text.replace(f"@{bot_name}", "").strip()

    # ── Видео / видео-заметка ─────────────────────────────────────────────
    if msg.video or msg.video_note or (
        msg.document and msg.document.mime_type
        and msg.document.mime_type.startswith("video/")
    ):
        await _handle_media(update, context, query, ctx, chat_id, is_video=True)
        return

    # ── Фото / изображение-документ ───────────────────────────────────────
    if msg.photo or (msg.document and msg.document.mime_type
                     and msg.document.mime_type.startswith("image/")):
        await _handle_media(update, context, query, ctx, chat_id, is_video=False)
        return

    if not query:
        return

    # ── В группе передаём AI кто именно сейчас обращается ────────────────
    if msg.chat.type != ChatType.PRIVATE:
        ai_query = f"{label}: {query}"
    else:
        ai_query = query

    # ── Если это реплай на чужое сообщение — добавляем его в контекст ────
    if msg.reply_to_message and msg.reply_to_message.from_user:
        replied_user = msg.reply_to_message.from_user
        replied_text = msg.reply_to_message.text or msg.reply_to_message.caption or ""
        if replied_text and replied_user.username != bot_name:
            replied_label = _author_label(replied_user, replied_user.id)
            ai_query = f"[В ответ на: {replied_label}: «{replied_text[:200]}»]\n{ai_query}"

    # ── Обычный текстовый запрос → Chairman ──────────────────────────────
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    response = await chairman_response(ai_query, ctx)
    add_message(chat_id, "assistant", response)

    await safe_reply(msg, response)


async def _handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        caption: str, ctx: list, chat_id: int, is_video: bool):
    msg = update.message
    await context.bot.send_chat_action(
        chat_id=chat_id, action="upload_video" if is_video else "typing"
    )

    try:
        if is_video:
            if msg.video:
                file_obj   = await context.bot.get_file(msg.video.file_id)
                media_type = msg.video.mime_type or "video/mp4"
            elif msg.video_note:
                file_obj   = await context.bot.get_file(msg.video_note.file_id)
                media_type = "video/mp4"
            else:
                file_obj   = await context.bot.get_file(msg.document.file_id)
                media_type = msg.document.mime_type
        else:
            if msg.photo:
                file_obj   = await context.bot.get_file(msg.photo[-1].file_id)
                media_type = "image/jpeg"
            else:
                file_obj   = await context.bot.get_file(msg.document.file_id)
                media_type = msg.document.mime_type

        raw_bytes = await file_obj.download_as_bytearray()
        b64       = base64.b64encode(raw_bytes).decode()

        response = await vision_response(b64, media_type, caption, ctx, is_video=is_video)
        add_message(chat_id, "assistant", response)

        await safe_reply(msg, response)

    except Exception as e:
        logger.error(f"Media error: {e}")
        kind = "видео" if is_video else "изображение"
        await msg.reply_text(f"🔴 Не удалось обработать {kind}.")

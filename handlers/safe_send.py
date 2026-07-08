import logging

logger = logging.getLogger(__name__)


async def safe_reply(message, text: str, parse_mode: str = "Markdown"):
    """Отвечает на сообщение; если Markdown не парсится — отправляет как обычный текст."""
    try:
        return await message.reply_text(text, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"Markdown parse failed, falling back to plain text: {e}")
        return await message.reply_text(text)


async def safe_send(bot, chat_id: int, text: str, parse_mode: str = "Markdown", **kwargs):
    """Отправляет сообщение; если Markdown не парсится — отправляет как обычный текст."""
    try:
        return await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        logger.warning(f"Markdown parse failed, falling back to plain text: {e}")
        return await bot.send_message(chat_id=chat_id, text=text, **kwargs)


async def safe_edit(message, text: str, parse_mode: str = "Markdown", **kwargs):
    """Редактирует сообщение; если Markdown не парсится или текст не изменился — гасит ошибку."""
    try:
        return await message.edit_text(text, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        msg = str(e).lower()
        if "not modified" in msg:
            return None
        logger.warning(f"Markdown parse failed on edit, falling back to plain text: {e}")
        try:
            return await message.edit_text(text, **kwargs)
        except Exception as e2:
            if "not modified" in str(e2).lower():
                return None
            logger.error(f"Edit failed entirely: {e2}")
            return None

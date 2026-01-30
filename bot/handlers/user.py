import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка ответов админа на сообщения клиентов.

    Сценарий:
    1. Пользователь пишет боту в режиме чата с админом.
    2. Бот отправляет админу сообщение в формате:
       ID: <user_id>, Имя, Username, Текст.
    3. Админ отвечает *ответом* на это сообщение.
    4. Бот парсит ID пользователя из текста и отправляет ему ответ.
    """
    message = update.message

    if not message or not message.reply_to_message:
        return

    original = message.reply_to_message
    original_text = original.text or ""

    # Ищем строку с ID: <число>
    match = re.search(r"ID:\s*<code>(\d+)</code>|ID:\s*(\d+)", original_text)
    if not match:
        logger.debug("Не удалось извлечь ID пользователя из сообщения, пропускаем ответ админа")
        return

    user_id_str = match.group(1) or match.group(2)
    try:
        user_id = int(user_id_str)
    except ValueError:
        logger.debug("Извлечён некорректный ID пользователя, пропускаем ответ админа")
        return

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "*Ответ администратора:*\n\n"
                f"{message.text}"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить ответ администратора пользователю {user_id}: {e}")
        try:
            await message.reply_text(
                "❌ Не удалось доставить ответ пользователю. Возможно, он заблокировал бота."
            )
        except Exception:
            pass


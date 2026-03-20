import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.support_chat import support_chat

logger = logging.getLogger(__name__)

def _escape_html(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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

    if not message:
        return

    user_id = None

    if message.reply_to_message:
        chat_id = message.chat_id
        msg_id = message.reply_to_message.message_id
        user_id = support_chat.get_user_by_admin_message(chat_id, msg_id)

    if user_id is None:
        user_id = support_chat.get_admin_target(admin_id=update.effective_user.id)

    if user_id is None:
        return

    try:
        if not message.text:
            return

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "<b>Ответ администратора</b>\n\n"
                f"{_escape_html(message.text)}"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Не удалось отправить ответ администратора пользователю {user_id}: {e}")
        try:
            await message.reply_text(
                "❌ Не удалось доставить ответ пользователю. Возможно, он заблокировал бота."
            )
        except Exception:
            pass


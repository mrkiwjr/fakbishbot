import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка ответов админа на пересланные сообщения пользователей.

    Сценарий:
    1. Пользователь пишет боту в режиме чата с админом.
    2. Бот пересылает сообщение админу (forward_message).
    3. Админ отвечает *ответом* на пересланное сообщение.
    4. Бот берёт forward_from.id из reply_to_message и отправляет ответ пользователю.
    """
    message = update.message

    if not message or not message.reply_to_message:
        return

    original = message.reply_to_message

    # Для пересланных сообщений forward_from содержит исходного пользователя
    if not original.forward_from:
        logger.debug("Ответ админа не на пересланное сообщение пользователя, пропускаем")
        return

    user = original.forward_from
    user_id = user.id

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "💬 *Ответ от администратора:*\n\n"
                f"{message.text}"
            ),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Не удалось отправить ответ администратора пользователю {user_id}: {e}")
        try:
            await message.reply_text(
                "❌ Не удалось доставить ответ пользователю. Возможно, он заблокировал бота."
            )
        except Exception:
            pass


import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes, BaseHandler

logger = logging.getLogger(__name__)


class MessageCleanupMiddleware:

    def __init__(self):
        self.tracked_messages = {}

    async def track_bot_message(self, chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
        await self.cleanup_all_except(chat_id, message_id, context)

        if chat_id not in self.tracked_messages:
            self.tracked_messages[chat_id] = set()
        self.tracked_messages[chat_id] = {message_id}

        context.user_data["active_menu_message"] = message_id

    async def cleanup_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        try:
            if update.message.text and update.message.text.startswith('/'):
                await update.message.delete()
                logger.info(f"Удалена команда: {update.message.text}")
        except Exception as e:
            logger.debug(f"Не удалось удалить команду: {e}")

    async def cleanup_old_messages(self, chat_id: int, keep_message_id: Optional[int], context: ContextTypes.DEFAULT_TYPE):
        if chat_id not in self.tracked_messages:
            return

        messages_to_delete = self.tracked_messages[chat_id].copy()

        if keep_message_id:
            messages_to_delete.discard(keep_message_id)

        for msg_id in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                self.tracked_messages[chat_id].discard(msg_id)
                logger.info(f"Удалено старое сообщение: {msg_id}")
            except Exception as e:
                logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")
                self.tracked_messages[chat_id].discard(msg_id)

    async def cleanup_all_except(self, chat_id: int, keep_message_id: int, context: ContextTypes.DEFAULT_TYPE):
        if chat_id not in self.tracked_messages:
            return

        messages_to_delete = self.tracked_messages[chat_id].copy()
        messages_to_delete.discard(keep_message_id)

        for msg_id in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                logger.info(f"Удалено старое сообщение: {msg_id}")
            except Exception as e:
                logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")


message_cleanup = MessageCleanupMiddleware()

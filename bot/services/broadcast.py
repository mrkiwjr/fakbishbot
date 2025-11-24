import asyncio
import logging
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

from bot.config import MESSAGE_DELAY_SECONDS
from bot.services.database import db

logger = logging.getLogger(__name__)


class BroadcastService:
    @staticmethod
    async def send_broadcast(bot: Bot, message: str, photo_file_id: Optional[str] = None) -> dict:
        users = await db.get_all_users()
        sent = 0
        failed = 0
        failed_users = []

        for user in users:
            user_id = user["user_id"]
            try:
                if photo_file_id:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=photo_file_id,
                        caption=message if message else None
                    )
                else:
                    await bot.send_message(user_id, message)

                sent += 1
                await asyncio.sleep(MESSAGE_DELAY_SECONDS)

            except TelegramError as e:
                failed += 1
                failed_users.append(user_id)
                logger.warning(f"Не удалось отправить рассылку пользователю {user_id}: {e}")

        logger.info(f"Рассылка завершена: отправлено {sent}, ошибок {failed}")

        return {
            "sent": sent,
            "failed": failed,
            "failed_users": failed_users
        }


broadcast_service = BroadcastService()

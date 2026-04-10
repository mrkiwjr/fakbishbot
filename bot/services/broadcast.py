import asyncio
import logging
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

from bot.config import MESSAGE_DELAY_SECONDS
from bot.services.database import db

logger = logging.getLogger(__name__)

BROADCAST_BATCH_SIZE = 100


class BroadcastService:
    @staticmethod
    async def send_broadcast(bot: Bot, message: str, photo_file_id: Optional[str] = None, video_file_id: Optional[str] = None) -> dict:
        user_ids = await db.get_all_user_ids()
        sent = 0
        failed_count = 0

        for i in range(0, len(user_ids), BROADCAST_BATCH_SIZE):
            batch = user_ids[i:i + BROADCAST_BATCH_SIZE]
            for user_id in batch:
                try:
                    if video_file_id:
                        await bot.send_video(
                            chat_id=user_id,
                            video=video_file_id,
                            caption=message if message else None,
                            supports_streaming=True
                        )
                    elif photo_file_id:
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
                    failed_count += 1
                    logger.warning(f"Не удалось отправить рассылку пользователю {user_id}: {e}")

        logger.info(f"Рассылка завершена: отправлено {sent}, ошибок {failed_count}")

        return {
            "sent": sent,
            "failed": failed_count,
        }


broadcast_service = BroadcastService()

import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

from bot.config import MESSAGE_DELAY_SECONDS
from bot.services.database import db


class BroadcastService:
    @staticmethod
    async def send_broadcast(bot: Bot, message: str, photo_file_id: Optional[str] = None) -> dict:
        users = await db.get_all_users()
        sent = 0
        failed = 0
        failed_users = []

        for user in users:
            try:
                if photo_file_id:
                    await bot.send_photo(
                        chat_id=user["user_id"],
                        photo=photo_file_id,
                        caption=message if message else None
                    )
                else:
                    await bot.send_message(user["user_id"], message)

                sent += 1
                await asyncio.sleep(MESSAGE_DELAY_SECONDS)
            except TelegramError as e:
                failed += 1
                failed_users.append(user["user_id"])

        return {
            "sent": sent,
            "failed": failed,
            "failed_users": failed_users
        }


broadcast_service = BroadcastService()

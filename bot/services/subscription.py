import logging
from telegram import Bot
from telegram.error import TelegramError

from bot.config import CHANNEL_ID

logger = logging.getLogger(__name__)


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except TelegramError as e:
        logger.error(f"Ошибка проверки подписки для user_id={user_id}, channel_id={CHANNEL_ID}: {e}")
        return False

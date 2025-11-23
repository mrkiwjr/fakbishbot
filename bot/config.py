import os
from typing import Final
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: Final[str] = os.getenv("BOT_TOKEN", "")
ADMIN_ID: Final[int] = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID: Final[int] = int(os.getenv("CHANNEL_ID", "-1002243728868"))
CHANNEL_USERNAME: Final[str] = os.getenv("CHANNEL_USERNAME", "@katanaistra")

DATABASE_PATH: Final[str] = "data/database.db"
LOGS_PATH: Final[str] = "data/bot.log"
BACKUP_DIR: Final[str] = "data/backups"

BROADCAST_COOLDOWN_MINUTES: Final[int] = 2
MESSAGE_DELAY_SECONDS: Final[float] = 0.3

PROMO_CHECK_INTERVAL_HOURS: Final[int] = 24

# Бронирование и уведомления
ADMIN_USERNAME = "@katana8pro"
NOTIFICATION_CHAT_ID = -1001712750879
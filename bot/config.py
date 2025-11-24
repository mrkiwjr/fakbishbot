import os
from typing import Final, Optional
from dotenv import load_dotenv

load_dotenv()

def _find_photo_path(base_dir: str, name: str) -> Optional[str]:
    for ext in ['.jpg', '.JPG', '.jpeg', '.JPEG', '.png', '.PNG']:
        path = os.path.join(base_dir, f"{name}{ext}")
        if os.path.exists(path):
            return path
    return None

BOT_TOKEN: Final[str] = os.getenv("BOT_TOKEN", "")
ADMIN_ID: Final[int] = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID: Final[int] = int(os.getenv("CHANNEL_ID", "0"))
CHANNEL_USERNAME: Final[str] = os.getenv("CHANNEL_USERNAME", "")

DATABASE_PATH: Final[str] = "data/database.db"
LOGS_PATH: Final[str] = "data/bot.log"
BACKUP_DIR: Final[str] = "data/backups"

BROADCAST_COOLDOWN_MINUTES: Final[int] = 2
MESSAGE_DELAY_SECONDS: Final[float] = 0.3

PROMO_CHECK_INTERVAL_HOURS: Final[int] = 24

ADMIN_USERNAME: Final[str] = os.getenv("ADMIN_USERNAME", "")
NOTIFICATION_CHAT_ID: Final[int] = int(os.getenv("NOTIFICATION_CHAT_ID", "0"))

DEFAULT_PROMO_DAYS: Final[int] = 7
MIN_PROMO_DAYS: Final[int] = 1
MAX_PROMO_DAYS: Final[int] = 365
MAX_PROMO_CODE_LENGTH: Final[int] = 100

MENU_PHOTOS_DIR: Final[str] = os.path.join(os.path.dirname(__file__), "media", "menu")

def _init_menu_photos() -> dict[str, Optional[str]]:
    photos = {}
    for key in ["main", "promo", "book_pc", "promotions", "tariffs", "feedback", "help"]:
        photos[key] = _find_photo_path(MENU_PHOTOS_DIR, key)
    return photos

MENU_PHOTOS: Final[dict[str, Optional[str]]] = _init_menu_photos()
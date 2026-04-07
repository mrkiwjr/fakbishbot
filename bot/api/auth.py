import hmac
import hashlib
import json
import time
from urllib.parse import parse_qs, unquote

from bot.config import BOT_TOKEN, ADMIN_ID
from bot.services.database import db

MAX_AUTH_AGE_SECONDS = 86400


def validate_init_data(init_data: str) -> dict | None:
    """Валидация Telegram WebApp initData. Возвращает данные пользователя или None."""
    try:
        parsed = parse_qs(init_data, keep_blank_values=True)
        received_hash = parsed.get("hash", [None])[0]

        if not received_hash:
            return None

        data_pairs = []
        for key, values in parsed.items():
            if key == "hash":
                continue
            data_pairs.append(f"{key}={values[0]}")

        data_pairs.sort()
        data_check_string = "\n".join(data_pairs)

        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        auth_date = int(parsed.get("auth_date", ["0"])[0])
        if time.time() - auth_date > MAX_AUTH_AGE_SECONDS:
            return None

        user_data_raw = parsed.get("user", [None])[0]
        if not user_data_raw:
            return None

        return json.loads(unquote(user_data_raw))

    except Exception:
        return None


async def check_admin(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    return await db.is_admin(user_id)


def check_super_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

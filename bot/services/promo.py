from datetime import datetime, timedelta
from typing import Optional

from bot.services.database import db


class PromoService:
    @staticmethod
    async def get_current_promo() -> Optional[dict]:
        active_promos = await db.get_active_promos()
        if not active_promos:
            return None
        return active_promos[0]

    @staticmethod
    async def can_receive_promo(user_id: int) -> tuple[bool, Optional[str]]:
        current_promo = await PromoService.get_current_promo()

        if not current_promo:
            return False, "no_promo"

        if await db.check_promo_usage(user_id, current_promo["code"]):
            return False, "already_received"

        return True, None

    @staticmethod
    async def give_promo_to_user(user_id: int) -> Optional[dict]:
        can_receive, reason = await PromoService.can_receive_promo(user_id)

        if not can_receive:
            return None

        current_promo = await PromoService.get_current_promo()
        await db.record_promo_usage(user_id, current_promo["code"])

        return current_promo

    @staticmethod
    async def create_promo(code: str, days_valid: int = 7) -> bool:
        expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")
        return await db.add_promo(code, expiry_date)

    @staticmethod
    async def get_all_promos() -> list[dict]:
        return await db.get_all_promos()

    @staticmethod
    async def delete_promo(code: str) -> bool:
        return await db.delete_promo(code)

    @staticmethod
    async def deactivate_promo(code: str) -> bool:
        return await db.deactivate_promo(code)


promo_service = PromoService()

from datetime import datetime, timedelta
from typing import Optional

from bot.services.database import db


class PromoService:
    @staticmethod
    def get_current_promo() -> Optional[dict]:
        active_promos = db.get_active_promos()
        if not active_promos:
            return None
        return active_promos[0]

    @staticmethod
    def can_receive_promo(user_id: int) -> tuple[bool, Optional[str]]:
        current_promo = PromoService.get_current_promo()

        if not current_promo:
            return False, "no_promo"

        if db.check_promo_usage(user_id, current_promo["code"]):
            return False, "already_received"

        return True, None

    @staticmethod
    def give_promo_to_user(user_id: int) -> Optional[dict]:
        can_receive, reason = PromoService.can_receive_promo(user_id)

        if not can_receive:
            return None

        current_promo = PromoService.get_current_promo()
        db.record_promo_usage(user_id, current_promo["code"])

        return current_promo

    @staticmethod
    def create_promo(code: str, days_valid: int = 7) -> bool:
        expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")
        return db.add_promo(code, expiry_date)

    @staticmethod
    def get_all_promos() -> list[dict]:
        return db.get_all_promos()

    @staticmethod
    def delete_promo(code: str) -> bool:
        return db.delete_promo(code)

    @staticmethod
    def deactivate_promo(code: str) -> bool:
        return db.deactivate_promo(code)


promo_service = PromoService()

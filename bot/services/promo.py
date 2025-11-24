import random
from datetime import datetime, timedelta
from typing import Optional, Tuple

from bot.services.database import db


class PromoService:
    def __init__(self):
        self.db = db

    async def get_random_active_promo(self) -> Optional[dict]:
        """Получить случайный активный неиспользованный промокод"""
        unused_promos = await db.get_unused_active_promos()
        if not unused_promos:
            return None

        promo = random.choice(unused_promos)
        return {
            "code": promo["code"],
            "expiry_date": promo["expiry_date"]
        }

    async def can_receive_promo(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """Проверить может ли пользователь получить промокод"""
        has_received = await db.has_user_received_any_promo(user_id)

        if has_received:
            return False, "already_received"

        unused_promos = await db.get_unused_active_promos()
        if not unused_promos:
            return False, "no_promo"

        return True, None

    async def give_promo_to_user(self, user_id: int) -> Optional[dict]:
        """Выдать промокод пользователю"""
        can_receive, reason = await self.can_receive_promo(user_id)

        if not can_receive:
            return None

        # Получаем случайный промокод
        promo = await self.get_random_active_promo()
        if not promo:
            return None

        # Записываем что пользователь получил промокод
        await self.mark_promo_received(user_id, promo["code"])

        return promo

    async def mark_promo_received(self, user_id: int, promo_code: str):
        """Отметить что пользователь получил промокод"""
        await db.record_promo_usage(user_id, promo_code)

    async def get_last_received_promo(self, user_id: int) -> Optional[dict]:
        """Получить последний полученный промокод пользователя"""
        return await db.get_last_user_promo(user_id)

    async def get_current_promo(self) -> Optional[dict]:
        """Получить текущий активный промокод (для обратной совместимости)"""
        active_promos = await db.get_active_promos()
        if not active_promos:
            return None
        return active_promos[0]

    async def create_promo(self, code: str, days_valid: int = 7) -> bool:
        """Создать новый промокод"""
        expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")
        return await db.add_promo(code, expiry_date)

    async def create_promo_with_date(self, code: str, expiry_date: str) -> bool:
        """Создать промокод с конкретной датой окончания"""
        return await db.add_promo(code, expiry_date)

    async def get_all_promos(self) -> list[dict]:
        """Получить все промокоды"""
        return await db.get_all_promos()

    async def delete_promo(self, code: str) -> bool:
        """Удалить промокод"""
        return await db.delete_promo(code)

    async def deactivate_promo(self, code: str) -> bool:
        """Деактивировать промокод"""
        return await db.deactivate_promo(code)


# Создаем экземпляр сервиса
promo_service = PromoService()

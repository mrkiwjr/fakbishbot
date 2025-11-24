import random
from datetime import datetime, timedelta
from typing import Optional, Tuple

from bot.services.database import db


class PromoService:
    def __init__(self):
        self.db = db

    async def get_random_active_promo(self) -> Optional[dict]:
        """Получить случайный активный промокод"""
        active_promos = await db.get_active_promos()
        if not active_promos:
            return None
            
        # Выбираем случайный промокод из активных
        promo = random.choice(active_promos)
        return {
            "code": promo["code"],
            "expiry_date": promo["expiry_date"]
        }

    async def can_receive_promo(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """Проверить может ли пользователь получить промокод"""
        # Проверяем получал ли пользователь промокод на этой неделе
        has_received = await self.has_received_promo_this_week(user_id)
        
        if has_received:
            return False, "already_received"

        # Проверяем есть ли активные промокоды
        active_promos = await db.get_active_promos()
        if not active_promos:
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
        query = """
        INSERT OR REPLACE INTO user_promocodes (user_id, promo_code, received_at)
        VALUES (?, ?, datetime('now'))
        """
        await self.db.execute(query, (user_id, promo_code))
        await self.db.commit()

    async def has_received_promo_this_week(self, user_id: int) -> bool:
        """Проверить получал ли пользователь промокод на этой неделе"""
        query = """
        SELECT received_at FROM user_promocodes 
        WHERE user_id = ? AND date(received_at) >= date('now', 'weekday 0', '-7 days')
        ORDER BY received_at DESC 
        LIMIT 1
        """
        
        async with self.db.execute(query, (user_id,)) as cursor:
            result = await cursor.fetchone()
            
        return result is not None

    async def get_last_received_promo(self, user_id: int) -> Optional[dict]:
        """Получить последний полученный промокод пользователя"""
        query = """
        SELECT up.promo_code, up.received_at, p.expiry_date
        FROM user_promocodes up
        JOIN promocodes p ON up.promo_code = p.code
        WHERE up.user_id = ?
        ORDER BY up.received_at DESC 
        LIMIT 1
        """
        
        async with self.db.execute(query, (user_id,)) as cursor:
            result = await cursor.fetchone()
            
        if result:
            return {
                "code": result[0],
                "received_at": result[1],
                "expiry_date": result[2]
            }
        return None

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

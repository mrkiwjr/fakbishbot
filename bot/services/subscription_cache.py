import logging
import time
from typing import Optional
from telegram import Bot

logger = logging.getLogger(__name__)


class SubscriptionCache:
    """Кеш для проверки подписки с TTL"""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 минут по умолчанию
        self.cache: dict[int, tuple[bool, float]] = {}
        self.ttl = ttl_seconds
    
    def get(self, user_id: int) -> Optional[bool]:
        """Получить закешированное значение подписки"""
        if user_id in self.cache:
            is_subscribed, cached_time = self.cache[user_id]
            if time.time() - cached_time < self.ttl:
                return is_subscribed
            else:
                # Истек срок действия, удаляем из кеша
                del self.cache[user_id]
        return None
    
    def set(self, user_id: int, is_subscribed: bool):
        """Сохранить результат проверки подписки в кеш"""
        self.cache[user_id] = (is_subscribed, time.time())
        
        # Ограничиваем размер кеша (удаляем старые записи если кеш больше 1000 записей)
        if len(self.cache) > 1000:
            current_time = time.time()
            # Удаляем записи, которые истекли
            expired_keys = [
                uid for uid, (_, cached_time) in self.cache.items()
                if current_time - cached_time >= self.ttl
            ]
            for key in expired_keys:
                del self.cache[key]
            
            # Если все еще слишком много, удаляем самые старые
            if len(self.cache) > 1000:
                sorted_items = sorted(
                    self.cache.items(),
                    key=lambda x: x[1][1]  # Сортировка по времени кеширования
                )
                # Удаляем 100 самых старых записей
                for key, _ in sorted_items[:100]:
                    del self.cache[key]


# Глобальный экземпляр кеша
subscription_cache = SubscriptionCache(ttl_seconds=300)  # 5 минут


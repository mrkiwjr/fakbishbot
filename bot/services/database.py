import os
import aiosqlite
from datetime import datetime
from typing import Optional

from bot.config import DATABASE_PATH


class Database:
    def __init__(self):
        self._ensure_data_dir()
        self.db_path = DATABASE_PATH

    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    username TEXT,
                    joined_at TEXT NOT NULL
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS promos (
                    code TEXT PRIMARY KEY,
                    expiry_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS promo_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    promo_code TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (promo_code) REFERENCES promos(code) ON DELETE CASCADE,
                    UNIQUE(user_id, promo_code)
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    username TEXT,
                    added_at TEXT NOT NULL,
                    added_by INTEGER NOT NULL
                )
            """)

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_promo_expiry ON promos(expiry_date)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_promo_active ON promos(active)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON promo_usage(user_id)")

            await self._migrate_promo_usage_table(conn)

            await conn.commit()

    async def _migrate_promo_usage_table(self, conn):
        cursor = await conn.execute("PRAGMA table_info(promo_usage)")
        columns = await cursor.fetchall()

        if not columns:
            return

        cursor = await conn.execute("PRAGMA foreign_key_list(promo_usage)")
        foreign_keys = await cursor.fetchall()

        has_promo_fk = any(fk[3] == 'promos' for fk in foreign_keys)

        if has_promo_fk:
            return

        await conn.execute("PRAGMA foreign_keys=OFF")

        await conn.execute("""
            CREATE TABLE promo_usage_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                promo_code TEXT NOT NULL,
                received_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (promo_code) REFERENCES promos(code) ON DELETE CASCADE,
                UNIQUE(user_id, promo_code)
            )
        """)

        await conn.execute("""
            INSERT INTO promo_usage_new (id, user_id, promo_code, received_at)
            SELECT id, user_id, promo_code, received_at
            FROM promo_usage
        """)

        await conn.execute("DROP TABLE promo_usage")
        await conn.execute("ALTER TABLE promo_usage_new RENAME TO promo_usage")

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON promo_usage(user_id)")

        await conn.execute("PRAGMA foreign_keys=ON")

    async def add_user(self, user_id: int, first_name: str, username: Optional[str] = None) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                await conn.execute(
                    "INSERT INTO users (user_id, first_name, username, joined_at) VALUES (?, ?, ?, ?)",
                    (user_id, first_name, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                await conn.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def get_user(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_by_id(user_id: int):
        query = "SELECT * FROM users WHERE user_id = $1"
        row = await database.fetchrow(query, user_id)
        return dict(row) if row else None

    async def get_all_users(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM users") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_users_count(self) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT COUNT(*) FROM users") as cursor:
                result = await cursor.fetchone()
                return result[0]

    async def add_promo(self, code: str, expiry_date: str) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                await conn.execute(
                    "INSERT INTO promos (code, expiry_date, created_at, active) VALUES (?, ?, ?, 1)",
                    (code, expiry_date, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                await conn.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def get_active_promos(self) -> list[dict]:
        now = datetime.now().strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM promos WHERE active = 1 AND expiry_date >= ? ORDER BY created_at DESC",
                (now,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_promos(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM promos ORDER BY created_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def deactivate_promo(self, code: str) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("UPDATE promos SET active = 0 WHERE code = ?", (code,))
            await conn.commit()
            return conn.total_changes > 0

    async def delete_promo(self, code: str) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM promos WHERE code = ?", (code,))
            await conn.commit()
            return conn.total_changes > 0

    async def record_promo_usage(self, user_id: int, promo_code: str):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "INSERT INTO promo_usage (user_id, promo_code, received_at) VALUES (?, ?, ?)",
                (user_id, promo_code, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            await conn.commit()

    async def check_promo_usage(self, user_id: int, promo_code: str) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                "SELECT 1 FROM promo_usage WHERE user_id = ? AND promo_code = ?",
                (user_id, promo_code)
            ) as cursor:
                result = await cursor.fetchone()
                return result is not None

    async def get_user_promo_history(self, user_id: int) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM promo_usage WHERE user_id = ? ORDER BY received_at DESC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ДОБАВЛЕННЫЕ МЕТОДЫ ДЛЯ НОВОГО ФУНКЦИОНАЛА

    async def has_user_received_any_promo(self, user_id: int) -> bool:
        """Проверить получал ли пользователь активный промокод"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("""
                SELECT 1 FROM promo_usage pu
                JOIN promos p ON pu.promo_code = p.code
                WHERE pu.user_id = ?
                LIMIT 1
            """, (user_id,)) as cursor:
                result = await cursor.fetchone()
                return result is not None

    async def get_last_user_promo(self, user_id: int) -> Optional[dict]:
        """Получить последний активный промокод пользователя"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT pu.promo_code, pu.received_at, p.expiry_date
                FROM promo_usage pu
                JOIN promos p ON pu.promo_code = p.code
                WHERE pu.user_id = ?
                ORDER BY pu.received_at DESC
                LIMIT 1
            """, (user_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {
                        "code": result["promo_code"],
                        "received_at": result["received_at"],
                        "expiry_date": result["expiry_date"]
                    }
                return None

    async def get_unused_active_promos(self) -> list[dict]:
        """Получить список активных неиспользованных промокодов"""
        now = datetime.now().strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT p.code, p.expiry_date, p.created_at
                FROM promos p
                LEFT JOIN promo_usage pu ON p.code = pu.promo_code
                WHERE p.active = 1
                  AND p.expiry_date >= ?
                  AND pu.promo_code IS NULL
                ORDER BY p.created_at DESC
            """, (now,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_promo_usage_with_users(self) -> list[dict]:
        """Получить историю использования промокодов с информацией о пользователях"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT
                    pu.promo_code,
                    pu.user_id,
                    u.first_name,
                    u.username,
                    pu.received_at,
                    p.expiry_date
                FROM promo_usage pu
                JOIN users u ON pu.user_id = u.user_id
                JOIN promos p ON pu.promo_code = p.code
                ORDER BY pu.received_at DESC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def execute(self, query: str, params: tuple = ()):
        """Универсальный метод для выполнения SQL запросов"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor

    async def add_admin(self, user_id: int, first_name: str, added_by: int, username: Optional[str] = None) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                await conn.execute(
                    "INSERT INTO admins (user_id, first_name, username, added_at, added_by) VALUES (?, ?, ?, ?, ?)",
                    (user_id, first_name, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), added_by)
                )
                await conn.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def remove_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await conn.commit()
            return conn.total_changes > 0

    async def is_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                "SELECT 1 FROM admins WHERE user_id = ?", (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result is not None

    async def get_all_admins(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM admins ORDER BY added_at DESC") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_admin(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM admins WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def delete_expired_promos(self) -> int:
        """Удаляет истекшие промокоды из БД"""
        now = datetime.now().strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "DELETE FROM promos WHERE expiry_date < ?",
                (now,)
            )
            await conn.commit()
            return cursor.rowcount


db = Database()

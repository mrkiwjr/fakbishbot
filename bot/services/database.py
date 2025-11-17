import json
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

from bot.config import DATABASE_PATH


@dataclass
class User:
    user_id: int
    first_name: str
    username: Optional[str]
    joined_at: str


@dataclass
class Promo:
    code: str
    expiry_date: str
    created_at: str
    active: bool = True


@dataclass
class PromoUsage:
    user_id: int
    promo_code: str
    received_at: str


class Database:
    def __init__(self):
        self._ensure_data_dir()
        self.data = self._load()

    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    def _load(self) -> dict:
        if not os.path.exists(DATABASE_PATH):
            return {"users": [], "promos": [], "promo_usage": []}

        try:
            with open(DATABASE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"users": [], "promos": [], "promo_usage": []}

    def _save(self):
        with open(DATABASE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_user(self, user_id: int, first_name: str, username: Optional[str] = None):
        if not self.get_user(user_id):
            user = User(
                user_id=user_id,
                first_name=first_name,
                username=username,
                joined_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            self.data["users"].append(asdict(user))
            self._save()
            return True
        return False

    def get_user(self, user_id: int) -> Optional[dict]:
        for user in self.data["users"]:
            if user["user_id"] == user_id:
                return user
        return None

    def get_all_users(self) -> list[dict]:
        return self.data["users"]

    def get_users_count(self) -> int:
        return len(self.data["users"])

    def add_promo(self, code: str, expiry_date: str) -> bool:
        promo = Promo(
            code=code,
            expiry_date=expiry_date,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            active=True
        )
        self.data["promos"].append(asdict(promo))
        self._save()
        return True

    def get_active_promos(self) -> list[dict]:
        now = datetime.now().strftime("%Y-%m-%d")
        return [
            promo for promo in self.data["promos"]
            if promo["active"] and promo["expiry_date"] >= now
        ]

    def get_all_promos(self) -> list[dict]:
        return self.data["promos"]

    def deactivate_promo(self, code: str) -> bool:
        for promo in self.data["promos"]:
            if promo["code"] == code:
                promo["active"] = False
                self._save()
                return True
        return False

    def delete_promo(self, code: str) -> bool:
        initial_length = len(self.data["promos"])
        self.data["promos"] = [p for p in self.data["promos"] if p["code"] != code]

        if len(self.data["promos"]) < initial_length:
            self._save()
            return True
        return False

    def record_promo_usage(self, user_id: int, promo_code: str):
        usage = PromoUsage(
            user_id=user_id,
            promo_code=promo_code,
            received_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.data["promo_usage"].append(asdict(usage))
        self._save()

    def check_promo_usage(self, user_id: int, promo_code: str) -> bool:
        for usage in self.data["promo_usage"]:
            if usage["user_id"] == user_id and usage["promo_code"] == promo_code:
                return True
        return False

    def get_user_promo_history(self, user_id: int) -> list[dict]:
        return [
            usage for usage in self.data["promo_usage"]
            if usage["user_id"] == user_id
        ]


db = Database()

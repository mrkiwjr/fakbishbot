import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class SupportSession:
    user_id: int
    admin_id: int
    started_at: float


class SupportChatService:
    """
    Простая in-memory модель саппорт-чата:
    - pending: пользователь запросил чат, админ ещё не принял
    - active: админ принял чат, можно обмениваться сообщениями

    Важно: хранится в памяти процесса. После перезапуска бота активные чаты обнуляются.
    """

    def __init__(self):
        self.pending_users: set[int] = set()
        self.active_sessions: dict[int, SupportSession] = {}  # user_id -> session
        self.admin_current_target: dict[int, int] = {}  # admin_id -> user_id
        self.admin_message_to_user: dict[tuple[int, int], int] = {}  # (chat_id, message_id) -> user_id
        self.user_chat_message_ids: dict[int, list[tuple[int, int]]] = {}  # user_id -> [(chat_id, msg_id), ...]

    def is_pending(self, user_id: int) -> bool:
        return user_id in self.pending_users

    def set_pending(self, user_id: int) -> None:
        self.pending_users.add(user_id)

    def clear_pending(self, user_id: int) -> None:
        self.pending_users.discard(user_id)

    def is_active(self, user_id: int) -> bool:
        return user_id in self.active_sessions

    def start(self, user_id: int, admin_id: int) -> None:
        self.clear_pending(user_id)
        self.active_sessions[user_id] = SupportSession(
            user_id=user_id,
            admin_id=admin_id,
            started_at=time.time(),
        )
        self.admin_current_target[admin_id] = user_id

    def end(self, user_id: int) -> None:
        session = self.active_sessions.pop(user_id, None)
        if session:
            # если у админа был выбран именно этот пользователь — сбрасываем
            if self.admin_current_target.get(session.admin_id) == user_id:
                self.admin_current_target.pop(session.admin_id, None)
        self.clear_pending(user_id)
        self.user_chat_message_ids.pop(user_id, None)

    def add_message_with_end_button(self, user_id: int, chat_id: int, message_id: int) -> None:
        """Добавить сообщение с кнопкой «Завершить чат» для последующего снятия со всех."""
        if user_id not in self.user_chat_message_ids:
            self.user_chat_message_ids[user_id] = []
        self.user_chat_message_ids[user_id].append((chat_id, message_id))

    def get_message_ids_with_end_button(self, user_id: int) -> list[tuple[int, int]]:
        """Список (chat_id, message_id) сообщений с кнопкой «Завершить чат» для пользователя."""
        return self.user_chat_message_ids.get(user_id, [])

    def get_admin_target(self, admin_id: int) -> Optional[int]:
        return self.admin_current_target.get(admin_id)

    def set_admin_target(self, admin_id: int, user_id: int) -> None:
        self.admin_current_target[admin_id] = user_id

    def link_admin_message(self, chat_id: int, message_id: int, user_id: int) -> None:
        """Связать сообщение админу с пользователем (для ответа реплаем)."""
        self.admin_message_to_user[(chat_id, message_id)] = user_id

    def get_user_by_admin_message(self, chat_id: int, message_id: int) -> Optional[int]:
        """Получить user_id по сообщению, на которое админ отвечает."""
        return self.admin_message_to_user.get((chat_id, message_id))


support_chat = SupportChatService()


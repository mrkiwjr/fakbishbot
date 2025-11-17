from typing import Final

WELCOME_MESSAGE: Final[str] = (
    "Добро пожаловать!\n\n"
    "Для получения промокодов необходимо подписаться на канал: {channel}\n\n"
    "После подписки используйте /promo для получения промокода."
)

NOT_SUBSCRIBED_MESSAGE: Final[str] = (
    "Вы не подписаны на канал {channel}\n\n"
    "Подпишитесь и попробуйте снова."
)

PROMO_RECEIVED_MESSAGE: Final[str] = (
    "Ваш промокод: {code}\n\n"
    "Срок действия: до {expiry_date}"
)

PROMO_ALREADY_RECEIVED_MESSAGE: Final[str] = (
    "Вы уже получили промокод на этой неделе.\n"
    "Следующий промокод будет доступен: {next_available}"
)

NO_ACTIVE_PROMO_MESSAGE: Final[str] = (
    "В данный момент нет активных промокодов.\n"
    "Ожидайте новых предложений!"
)

ADMIN_ONLY_MESSAGE: Final[str] = "Эта команда доступна только администратору."

BROADCAST_STARTED_MESSAGE: Final[str] = "Начинаю рассылку для {count} пользователей..."
BROADCAST_COMPLETED_MESSAGE: Final[str] = (
    "Рассылка завершена\n\n"
    "Отправлено: {sent}\n"
    "Ошибок: {failed}"
)

HELP_USER_MESSAGE: Final[str] = (
    "Доступные команды:\n\n"
    "/start - начать работу с ботом\n"
    "/promo - получить промокод\n"
    "/help - показать это сообщение"
)

HELP_ADMIN_MESSAGE: Final[str] = (
    "Админ команды:\n\n"
    "/admin - открыть админ панель\n"
    "/broadcast <текст> - рассылка сообщения\n"
    "/stats - статистика бота\n"
    "/help - показать это сообщение"
)

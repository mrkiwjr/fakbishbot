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
    "/help - показать справку"
)

HELP_ADMIN_MESSAGE: Final[str] = (
    "Команды администратора:\n\n"
    "/start - главное меню пользователя\n"
    "/admin - панель администратора\n"
    "/help - показать справку\n\n"
    "Функции админ панели:\n"
    "• Добавление промокодов\n"
    "• Просмотр и удаление промокодов\n"
    "• Статистика бота\n"
    "• Рассылка сообщений с фото"
)

MENU_MAIN: Final[str] = (
    "Главное меню\n\n"
    "Выберите действие:"
)

MENU_PROMO: Final[str] = (
    "Получение промокода\n\n"
    "Для получения промокода необходимо быть подписанным на наш канал."
)

MENU_HELP: Final[str] = "Помощь"

MENU_SUBSCRIBE: Final[str] = "Проверка подписки"

ADMIN_PANEL_MAIN: Final[str] = (
    "Админ панель\n\n"
    "Выберите действие:"
)

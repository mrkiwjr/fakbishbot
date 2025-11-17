# KATANA Promo Bot

Telegram-бот для раздачи промокодов подписчикам канала KATANA. Один юзер получает один код за период. Подписка обязательна.

## Технологический стек

```
Python 3.11
python-telegram-bot 21.9
aiosqlite 0.20.0
Docker + Docker Compose
```

## Быстрый старт

### Локальный запуск

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполнить `.env`:
```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_ID=796891410
CHANNEL_ID=-1002243728868
CHANNEL_USERNAME=@katanaistra
```

Запуск:
```bash
python main.py
```

### Docker

```bash
make build    # собрать контейнер
make up       # запустить
make down     # остановить
make logs     # посмотреть логи
make restart  # перезапустить
```

## Архитектура

### Структура проекта

```
.
├── bot/
│   ├── handlers/
│   │   ├── admin.py        # ConversationHandler для добавления промо
│   │   ├── user.py         # /start, /promo, /help
│   │   └── menu.py         # inline-клавиатуры админ-панели
│   ├── services/
│   │   ├── database.py     # SQLite через aiosqlite
│   │   ├── promo.py        # валидация, выдача, проверка использования
│   │   ├── subscription.py # проверка подписки через getChatMember
│   │   └── broadcast.py    # массовые рассылки с rate limiting
│   ├── middleware/         # middleware для логирования/контроля
│   ├── config.py           # env-переменные, константы окружения
│   └── constants.py        # текстовые шаблоны сообщений
├── data/                   # база, логи, бэкапы
├── main.py                 # точка входа
└── requirements.txt
```

## Команды бота

**Пользовательские:**
- `/start` - регистрация
- `/promo` - получить промокод
- `/help` - инструкция
- `/broadcast` - запрос на рассылку (для админа)

**Админские:**
- Вся работа через inline-кнопки после `/start`
- Панель управления с навигацией

## Ключевые ограничения

- Rate limiting: 0.3 сек между сообщениями при broadcast
- Cooldown для рассылок: 2 минуты между запросами
- Один промокод на юзера за период (constraint на уровне БД)
- Проверка подписки перед каждой выдачей
- Автоматическая деактивация истекших промо (проверка раз в 24ч)

## Конфигурация

Все настройки в `bot/config.py`:

```python
CHANNEL_ID = -1002243728868
CHANNEL_USERNAME = @katanaistra
BROADCAST_COOLDOWN_MINUTES = 2
MESSAGE_DELAY_SECONDS = 0.3
PROMO_CHECK_INTERVAL_HOURS = 24
```

Тексты сообщений в `bot/constants.py` с `.format()` плейсхолдерами.


## Логи

Логи пишутся в `data/bot.log`.

При запуске через Docker:
```bash
make logs
```
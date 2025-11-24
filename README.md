# KATANA Promo Bot

Бот для раздачи промокодов подписчикам канала KATANA (@katanaistra). Один промокод на пользователя. При удалении промокода из админки пользователь может получить новый.

## Стек

```
Python 3.11
python-telegram-bot 21.9
aiosqlite 0.20.0
Docker + Docker Compose
```

## Установка

### Локально

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Заполнить `.env`:
```env
BOT_TOKEN=токен_от_botfather
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
make build
make up
make logs
```

## Структура

```
bot/
├── handlers/
│   ├── admin.py        # ConversationHandler для админки
│   └── menu.py         # Inline-клавиатуры + callback handlers
├── services/
│   ├── database.py     # SQLite: users, promos, promo_usage
│   ├── promo.py        # Логика выдачи промокодов
│   ├── subscription.py # Проверка подписки на канал
│   ├── broadcast.py    # Рассылки с rate limiting
│   └── photo_cache.py  # Кеширование file_id для фото меню
├── media/menu/         # Изображения для inline-меню
├── config.py           # Env-переменные
└── constants.py        # Тексты сообщений
```

## Основные функции

**Пользователям:**
- Получение промокода (требуется подписка)
- Меню с навигацией по разделам

**Админам:**
- Добавление промокодов (одиночное/массовое)
- Удаление промокодов
- Просмотр статистики
- Рассылки с фото

## Логика работы с промокодами

- При удалении промокода из БД запись в `promo_usage` удаляется каскадно (`ON DELETE CASCADE`)
- Пользователь может получить новый промокод после удаления старого
- Проверка `has_user_received_any_promo` использует JOIN с таблицей `promos`
- Истекшие промокоды удаляются автоматически раз в 24 часа

## Настройки

Основные константы в `bot/config.py`:
- `BROADCAST_COOLDOWN_MINUTES = 2` - кулдаун между рассылками
- `MESSAGE_DELAY_SECONDS = 0.3` - задержка при broadcast
- `PROMO_CHECK_INTERVAL_HOURS = 24` - интервал проверки истекших промо

Все тексты сообщений в `bot/constants.py`.
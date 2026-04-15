# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot + Web App для компьютерного клуба KATANA (@katanaistra, ID: -1002243728868). Бот раздает промокоды подписчикам канала (один в неделю), веб-приложение — админка и пользовательский интерфейс для бронирования, тарифов, отзывов.

## Development Setup

### Bot (Python)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 main.py
```

### Webapp (React)

```bash
cd webapp
npm install
npm run dev      # dev server с HMR
npm run build    # tsc + vite build → webapp/dist/
npm run lint     # eslint
```

### Docker Deployment

```bash
make build    # собрать контейнер
make up       # запустить
make down     # остановить
make logs     # логи
make restart  # перезапуск
```

Docker контейнер ограничен 256MB RAM (mem_limit в docker-compose.yml).

### Environment Variables

Обязательные в `.env`:
- `BOT_TOKEN` — токен от @BotFather
- `ADMIN_ID` — Telegram user ID суперадмина (796891410)
- `CHANNEL_ID` — ID канала (-1002243728868)
- `CHANNEL_USERNAME` — юзернейм канала (@katanaistra)

Опциональные:
- `PROXY_URL` — SOCKS5 прокси для Telegram API
- `WEBAPP_URL` — URL веб-приложения (default: https://katana-bot.duckdns.org)
- `NOTIFICATION_CHAT_ID` — чат для уведомлений о бронях/отзывах
- `ADMIN_USERNAME` — юзернейм админа для показа пользователям
- `DEV_MODE=1` — разрешает API запросы с `X-Telegram-Init-Data: dev` с localhost

## Architecture

Два процесса в одном контейнере: Telegram bot (python-telegram-bot polling) + aiohttp API сервер на порту 8080.

### Bot Layer

**Handlers** (`bot/handlers/`):
- `menu.py` — пользовательское меню: инлайн-клавиатуры, навигация, отправка фото меню
- `admin.py` — ConversationHandler для админских multi-step диалогов
- `user.py` — обработка ответов админа на сообщения пользователей (support chat)

**Handler Registration Order** в `main.py:setup_handlers()`:
1. Command handlers (`/start`, `/help`, `/admin`)
2. ConversationHandler (admin dialogs, `allow_reentry=True`)
3. General CallbackQueryHandler (catch-all для inline кнопок меню)
4. Admin reply MessageHandler (фильтр по ADMIN_ID)
5. User text MessageHandler (catch-all)

ConversationHandler states: `AWAITING_PROMO_CODE`, `AWAITING_PROMO_DAYS`, `AWAITING_PROMO_FILE`, `AWAITING_FILE_EXPIRY_DATE`, `AWAITING_FILE_EXPIRY_TIME`, `AWAITING_BROADCAST_TEXT`, `AWAITING_BROADCAST_PHOTO`, `AWAITING_BROADCAST_CONFIRM`, `AWAITING_BROADCAST_SCHEDULE`, `AWAITING_ADMIN_ID`, `ADMIN_MAIN`.

### API Layer (`bot/api/`)

aiohttp сервер стартует вместе с ботом в `init_application()`.
- `server.py` — создание и запуск aiohttp app
- `routes.py` — все API эндпоинты, middleware (CORS, auth, rate limiting)
- `auth.py` — валидация Telegram WebApp initData (HMAC-SHA256), проверка admin/super_admin

Аутентификация: заголовок `X-Telegram-Init-Data` с Telegram initData. В DEV_MODE принимает `dev` с localhost.

Авторизация двухуровневая: `@require_admin` (super_admin + admins из БД), `@require_super_admin` (только ADMIN_ID).

API endpoints: `/api/health`, `/api/admin/*` (stats, promos CRUD, users, broadcast, admins CRUD, scheduled broadcasts), `/api/booking`, `/api/feedback`.

### Service Layer (`bot/services/`)

- `database.py` — SQLite через aiosqlite. Таблицы: users, promos, promo_usage, admins
- `promo.py` — бизнес-логика промокодов: создание, выдача, проверка лимита (раз в неделю)
- `subscription.py` — проверка подписки на канал через Telegram API
- `broadcast.py` — рассылка с задержкой 0.3с между сообщениями, поддержка фото/видео
- `scheduler.py` — in-memory планировщик отложенных рассылок (asyncio.call_later). Не персистентный — при рестарте отложенные рассылки теряются
- `photo_cache.py` — кеширование file_id фото меню
- `support_chat.py` — пересылка сообщений пользователь <-> админ

### Webapp (`webapp/`)

React 19 + Vite + Tailwind CSS 4 + react-router-dom. Telegram Mini App через @tma.js/sdk-react.

Страницы: Home, Booking, Tariffs, Promos, PromoCode, AdminPanel.

API клиент: `webapp/src/lib/api.ts` — обертка над fetch с автоматической подстановкой initData.

### Data Persistence

SQLite (`data/database.db`):
```sql
users (user_id PRIMARY KEY, first_name, username, joined_at)
promos (code PRIMARY KEY, expiry_date, created_at, active)
promo_usage (id AUTOINCREMENT, user_id, promo_code, received_at, UNIQUE(user_id, promo_code))
admins (user_id PRIMARY KEY, first_name, username, added_at, added_by)
```

Логи: `data/bot.log` (RotatingFileHandler, 10MB, 3 backups).

## Key Constraints

- Один промокод в неделю на пользователя (`check_promo_usage_this_week()`)
- Подписка на канал обязательна перед выдачей промокода
- Rate limiting: API 10 req/min на ключ, broadcast cooldown 120с, booking 5 req/min, feedback 3 req/min
- Автоочистка истекших промокодов каждые 24ч (job_queue)
- Фото меню ищутся в `bot/media/menu/` по имени с расширениями jpg/jpeg/png

## Development Guidelines

### Communication and Code Style
- Коммуникация только на русском языке
- Писать как senior Python backend разработчик
- Только деловой стиль, без эмодзи
- Применять принципы SOLID, DRY, KISS
- Не дублировать существующий код, функции и методы
- Не оставлять комментарии после `#`
- Докстринги короткие, емкие, только по делу

### Logging
- Логи строго понятные и ёмкие
- Следовать формату существующих логов в проекте
- Используется стандартный `logging` модуль с файловым и консольным выводом
- API логи с префиксом `[API]`

### Project Structure
- Точка входа: `main.py`
- Конфигурация: `.env` файл
- Не трогать `Makefile`
- Не трогать `README.md`
- Не создавать документацию (*.md файлы) без четких указаний пользователя

### Development Workflow
- Каждый раз тщательно изучать существующий код перед внесением изменений
- Четко планировать реализацию
- Удалять тестовые скрипты после тестирования, не засорять проект

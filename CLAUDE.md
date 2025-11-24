# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot for distributing promo codes to subscribers of the KATANA channel (@katanaistra, ID: -1002243728868). The bot enforces one promo code per user per week and requires channel subscription before code distribution.

## Development Setup

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

Required environment variables in `.env`:
- `BOT_TOKEN` - Telegram bot token from @BotFather
- `ADMIN_ID` - Telegram user ID for admin access (hardcoded: 796891410)
- `CHANNEL_ID` - Target channel ID (-1002243728868)
- `CHANNEL_USERNAME` - Target channel username (@katanaistra)

Run the bot:
```bash
python main.py
```

### Docker Deployment

```bash
make build    # build container
make up       # start bot
make down     # stop bot
make logs     # view logs
make restart  # restart bot
```

## Architecture

### Handler Flow
- User menu handlers (`bot/handlers/menu.py`) process main menu navigation with inline keyboards and callback queries
- Admin handlers (`bot/handlers/admin.py`) use ConversationHandler for multi-step dialogs (adding promos, broadcasting messages)
- Admin panel uses inline keyboards with callback queries for interactive menu navigation
- All handlers integrated in `main.py` via `setup_handlers()` function

### ConversationHandler States
Admin workflow managed through distinct conversation states:
- `AWAITING_PROMO_CODE` - collecting promo code text
- `AWAITING_PROMO_DAYS` - collecting expiry days
- `AWAITING_PROMO_FILE` - uploading bulk promo file
- `AWAITING_BROADCAST_TEXT` - collecting broadcast message text
- `AWAITING_BROADCAST_PHOTO` - collecting optional broadcast photo
- `AWAITING_BROADCAST_CONFIRM` - confirming broadcast before send

### Service Layer Pattern
- `database.py` - SQLite persistence via aiosqlite with three tables: users, promos, promo_usage
  - Unique constraint on `(user_id, promo_code)` in promo_usage prevents duplicate claims
  - Indexes on `expiry_date`, `active`, and `user_id` for query optimization
- `promo.py` - Business logic: validates promo availability, checks weekly eligibility, records usage, random promo selection
- `subscription.py` - Telegram API calls to verify channel membership via `get_chat_member`
- `broadcast.py` - Iterates users with delay (`MESSAGE_DELAY_SECONDS = 0.3`) to avoid rate limits
- `message_control.py` - Middleware for message cleanup and tracking

### Configuration Separation
- `bot/config.py` - Loads environment variables, defines channel constants, file paths, timing constants
- `bot/constants.py` - All user-facing message templates with `.format()` placeholders

### Data Persistence
Database structure (SQLite):
```sql
users (user_id PRIMARY KEY, first_name, username, joined_at)
promos (code PRIMARY KEY, expiry_date, created_at, active)
promo_usage (id AUTOINCREMENT, user_id, promo_code, received_at, UNIQUE(user_id, promo_code))
```

Database path: `data/database.db`
Logs path: `data/bot.log`

## Key Constraints

- Weekly promo limit enforced via `check_promo_usage_this_week()` using SQLite date functions
- Subscription verification (`check_subscription`) must pass before promo distribution
- Promo usage tracked per user-promo pair via UNIQUE constraint
- Admin access controlled by exact `ADMIN_ID` match in handlers via `@admin_required` decorator
- Broadcast rate limiting: 0.3s delay between messages, 2-minute cooldown between broadcast requests
- Automatic promo expiry check every 24 hours (configurable via `PROMO_CHECK_INTERVAL_HOURS`)

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
- Примеры из кодабазы:
  ```python
  logger.info("Запуск бота...")
  logger.error(f"Ошибка при запуске бота: {e}")
  ```

### Project Structure
- Точка входа: `main.py`
- Конфигурация: `.env` файл
- Не трогать `Makefile`
- Не трогать `README.md`
- Не создавать документацию (*.md файлы) без четких указаний пользователя

### Handler Registration Order
Order matters in `main.py:setup_handlers()`:
1. Command handlers (`/start`, `/help`, `/admin`)
2. General callback query handlers
3. Message handlers
4. ConversationHandler (must be last to avoid capturing callbacks from other handlers)

### Development Workflow
- Каждый раз тщательно изучать существующий код перед внесением изменений
- Четко планировать реализацию
- Удалять тестовые скрипты после тестирования, не засорять проект

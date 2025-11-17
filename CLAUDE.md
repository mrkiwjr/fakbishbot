# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot for distributing promo codes to subscribers of the KATANA channel (@katanaistra, ID: -1002243728868). The bot enforces one promo code per user per promo period and requires channel subscription before code distribution.

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

Run the bot:
```bash
python main.py
```

## Architecture

### Handler Flow
- User handlers (`bot/handlers/user.py`) process commands: `/start`, `/promo`, `/help`, `/broadcast`
- Admin handlers (`bot/handlers/admin.py`) use ConversationHandler for multi-step dialogs (adding promos)
- Admin panel uses inline keyboards with callback queries for interactive menu navigation

### Service Layer Pattern
- `database.py` - JSON-based storage in `data/database.json` with three collections: users, promos, promo_usage
- `promo.py` - Business logic: validates promo availability, checks user eligibility, records usage
- `subscription.py` - Telegram API calls to verify channel membership via `get_chat_member`
- `broadcast.py` - Iterates users with delay (`MESSAGE_DELAY_SECONDS`) to avoid rate limits

### Configuration Separation
- `bot/config.py` - Loads environment variables, defines channel constants, file paths
- `bot/constants.py` - All user-facing message templates with `.format()` placeholders

### Data Persistence
Database structure (JSON):
```json
{
  "users": [{"user_id": int, "first_name": str, "username": str, "joined_at": str}],
  "promos": [{"code": str, "expiry_date": str, "created_at": str, "active": bool}],
  "promo_usage": [{"user_id": int, "promo_code": str, "received_at": str}]
}
```

## Key Constraints

- Subscription verification (`check_subscription`) must pass before promo distribution
- Promo usage is tracked per user-promo pair to enforce one-time use
- Admin access controlled by exact `ADMIN_ID` match in handlers
- ConversationHandler states (`PROMO_CODE`, `PROMO_DAYS`) manage admin promo creation workflow

## Development Guidelines

### Code Style
- Вся коммуникация строго на русском языке
- Писать как senior Python backend разработчик
- Деловой стиль, без эмодзи
- Применять принципы SOLID, DRY, KISS
- Не дублировать существующий код, функции и методы
- Не оставлять комментарии после `#`
- Докстринги должны быть короткими, емкими, только по делу

### Logging
- Логи должны быть понятными и ёмкими
- Следовать существующему формату в проекте

### Project Structure
- Точка входа: `main.py`
- Конфигурация: `.env` файл
- Не изменять `Makefile` (если существует)
- Не изменять `README.md` без явного запроса
- Не создавать документацию (*.md файлы) без явного указания пользователя

### Development Workflow
- Тщательно изучать существующий код перед внесением изменений
- Четко планировать реализацию
- Удалять тестовые скрипты после тестирования, не засорять проект

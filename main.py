import os
import logging

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

from bot.config import BOT_TOKEN, ADMIN_ID, LOGS_PATH
from bot.handlers.user import start, promo, help_command, broadcast
from bot.handlers.admin import (
    admin_panel,
    button_callback,
    receive_promo_code,
    receive_promo_days,
    cancel,
    PROMO_CODE,
    PROMO_DAYS
)


def setup_logging():
    os.makedirs(os.path.dirname(LOGS_PATH), exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOGS_PATH, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в .env файле")

    if ADMIN_ID == 0:
        raise ValueError("ADMIN_ID не установлен в .env файле")

    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Запуск бота...")

    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback)],
        states={
            PROMO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_code)],
            PROMO_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_days)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("promo", promo))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)

    logger.info("Бот запущен успешно")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()

import os
import logging

from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

from bot.config import BOT_TOKEN, ADMIN_ID, LOGS_PATH
from bot.services.database import db
from bot.handlers.menu import menu_start, menu_callback, help_command, handle_book_pc_message
from bot.handlers.admin import (
    admin_panel,
    button_callback,
    receive_promo_code,
    receive_promo_days,
    receive_broadcast_text,
    receive_broadcast_photo,
    handle_broadcast_photo_choice,
    confirm_broadcast,
    cancel,
    AWAITING_PROMO_CODE,
    AWAITING_PROMO_DAYS,
    AWAITING_BROADCAST_TEXT,
    AWAITING_BROADCAST_PHOTO,
    AWAITING_BROADCAST_CONFIRM,
    ADMIN_MAIN
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


async def setup_bot_commands(application: Application):
    user_commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("help", "Показать справку"),
    ]

    admin_commands = [
        BotCommand("start", "Главное меню"),
        BotCommand("admin", "Панель администратора"),
        BotCommand("help", "Показать справку"),
    ]

    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))


async def init_application(application: Application):
    await db.init_db()
    await setup_bot_commands(application)


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в .env файле")

    if ADMIN_ID == 0:
        raise ValueError("ADMIN_ID не установлен в .env файле")

    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Запуск бота...")

    application = Application.builder().token(BOT_TOKEN).post_init(init_application).build()

    admin_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern="^(admin_main|add_promo|list_promos|stats|broadcast_menu|delete_promo_menu|delete_.*|cancel)$")],
        states={
            AWAITING_PROMO_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_code),
                CallbackQueryHandler(button_callback, pattern=f"^{ADMIN_MAIN}$")
            ],
            AWAITING_PROMO_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_days),
                CallbackQueryHandler(button_callback, pattern=f"^{ADMIN_MAIN}$")
            ],
            AWAITING_BROADCAST_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast_text),
                CallbackQueryHandler(button_callback, pattern=f"^{ADMIN_MAIN}$")
            ],
            AWAITING_BROADCAST_PHOTO: [
                MessageHandler(filters.PHOTO, receive_broadcast_photo),
                CallbackQueryHandler(handle_broadcast_photo_choice, pattern="^(add_photo|skip_photo)$"),
                CallbackQueryHandler(button_callback, pattern=f"^{ADMIN_MAIN}$")
            ],
            AWAITING_BROADCAST_CONFIRM: [
                CallbackQueryHandler(confirm_broadcast, pattern="^broadcast_confirm$"),
                CallbackQueryHandler(button_callback, pattern=f"^{ADMIN_MAIN}$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    application.add_handler(CommandHandler("start", menu_start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(admin_conv_handler)
    application.add_handler(CallbackQueryHandler(menu_callback))
    
    # ДОБАВЛЯЕМ ЭТУ СТРОКУ - обработчик текстовых сообщений для бронирования
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_book_pc_message
    ))

    logger.info("Бот запущен успешно")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
    
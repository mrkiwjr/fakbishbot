import os
import logging
from logging.handlers import RotatingFileHandler

from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.error import TimedOut, NetworkError

from bot.config import BOT_TOKEN, PROXY_URL, ADMIN_ID, LOGS_PATH, PROMO_CHECK_INTERVAL_HOURS
from bot.services.database import db
from bot.api.server import start_api_server
from bot.handlers.menu import (
    menu_start,
    handle_leave_feedback,
    handle_text_message,
    menu_callback,
    help_command,
    FEEDBACK,
)
from bot.handlers.user import handle_admin_reply
from bot.handlers.admin import (
    admin_panel,
    button_callback,
    receive_promo_code,
    receive_promo_days,
    receive_promo_file,
    receive_broadcast_text,
    receive_broadcast_photo,
    handle_broadcast_photo_choice,
    confirm_broadcast,
    receive_admin_id,
    receive_file_expiry_date,
    receive_file_expiry_time,
    cancel,
    AWAITING_PROMO_CODE,
    AWAITING_PROMO_DAYS,
    AWAITING_PROMO_FILE,
    AWAITING_BROADCAST_TEXT,
    AWAITING_BROADCAST_PHOTO,
    AWAITING_BROADCAST_CONFIRM,
    AWAITING_ADMIN_ID,
    AWAITING_FILE_EXPIRY_DATE,
    AWAITING_FILE_EXPIRY_TIME,
    ADMIN_MAIN
)


def setup_logging():
    """Настройка логирования с ротацией файлов"""
    os.makedirs(os.path.dirname(LOGS_PATH), exist_ok=True)

    file_handler = RotatingFileHandler(
        LOGS_PATH,
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            file_handler,
            logging.StreamHandler()
        ]
    )


async def setup_bot_commands(application: Application):
    """Настройка команд бота"""
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


async def cleanup_expired_promos(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача для автоматической очистки истекших промокодов"""
    logger = logging.getLogger(__name__)
    try:
        deleted_count = await db.delete_expired_promos()
        if deleted_count > 0:
            logger.info(f"Удалено истекших промокодов: {deleted_count}")
        else:
            logger.debug("Истекших промокодов для удаления не найдено")
    except Exception as e:
        logger.error(f"Ошибка при очистке истекших промокодов: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок для логирования таймаутов и других сетевых ошибок"""
    logger = logging.getLogger(__name__)
    
    error = context.error
    
    if isinstance(error, TimedOut):
        logger.warning(f"Таймаут при обработке обновления: {error}")
    elif isinstance(error, NetworkError):
        logger.warning(f"Ошибка сети при обработке обновления: {error}")
    else:
        logger.error(f"Необработанная ошибка: {error}", exc_info=error)


async def shutdown_application(application: Application):
    """Корректное завершение приложения"""
    logger = logging.getLogger(__name__)

    api_runner = application.bot_data.get("api_runner")
    if api_runner:
        await api_runner.cleanup()
        logger.info("API сервер остановлен")

    await db.close()
    logger.info("Приложение остановлено, ресурсы освобождены")


async def init_application(application: Application):
    """Инициализация приложения"""
    logger = logging.getLogger(__name__)

    await db.init_db()
    await setup_bot_commands(application)

    api_runner = await start_api_server(bot=application.bot)
    application.bot_data["api_runner"] = api_runner

    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(
            cleanup_expired_promos,
            interval=PROMO_CHECK_INTERVAL_HOURS * 3600,
            first=10
        )
        logger.info(f"Запланирована автоматическая очистка промокодов каждые {PROMO_CHECK_INTERVAL_HOURS}ч")

        await cleanup_expired_promos(None)
        logger.info("Выполнена первичная очистка истекших промокодов")


def setup_handlers(application: Application):
    """Настройка всех обработчиков."""
    admin_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                button_callback,
                pattern="^(admin_main|add_promo|list_promos|promo_history|stats|broadcast_menu|delete_promo_menu|upload_promo_file|delete_.*|manage_admins|add_admin|remove_admin_menu|remove_admin_.*|cancel)$"
            )
        ],
        states={
            AWAITING_PROMO_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_code),
                CallbackQueryHandler(button_callback, pattern=f"^{ADMIN_MAIN}$")
            ],
            AWAITING_PROMO_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo_days),
                CallbackQueryHandler(button_callback, pattern=f"^{ADMIN_MAIN}$")
            ],
            AWAITING_PROMO_FILE: [
                MessageHandler(filters.Document.ALL, receive_promo_file),
                CallbackQueryHandler(button_callback, pattern=f"^{ADMIN_MAIN}$")
            ],
            AWAITING_FILE_EXPIRY_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_file_expiry_date),
                CallbackQueryHandler(button_callback, pattern=f"^{ADMIN_MAIN}$")
            ],
            AWAITING_FILE_EXPIRY_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_file_expiry_time),
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
            AWAITING_ADMIN_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_id),
                CallbackQueryHandler(button_callback, pattern="^manage_admins$")
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

    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.User(ADMIN_ID) & filters.TEXT & ~filters.COMMAND,
        handle_admin_reply
    ))

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_text_message
    ))


def main():
    """Точка входа."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в .env файле")

    if ADMIN_ID == 0:
        raise ValueError("ADMIN_ID не установлен в .env файле")

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Запуск бота...")

    try:
        builder = Application.builder().token(BOT_TOKEN).post_init(init_application).post_shutdown(shutdown_application)
        if PROXY_URL:
            builder = builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)
        application = builder.build()

        application.add_error_handler(error_handler)

        setup_handlers(application)

        logger.info("Бот запущен успешно")
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    main()
    
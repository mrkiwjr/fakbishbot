import os
import logging

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

from bot.config import BOT_TOKEN, ADMIN_ID, LOGS_PATH, PROMO_CHECK_INTERVAL_HOURS
from bot.services.database import db
from bot.handlers.menu import (
    menu_start, 
    menu_callback, 
    help_command, 
    handle_book_pc_message
)
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
    """Настройка логирования"""
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

    # Устанавливаем команды для всех пользователей
    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Устанавливаем специальные команды для администратора
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


async def init_application(application: Application):
    """Инициализация приложения"""
    logger = logging.getLogger(__name__)

    await db.init_db()
    await setup_bot_commands(application)

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
    """Настройка всех обработчиков"""
    
    # ConversationHandler для администратора
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

    # Основные обработчики команд
    application.add_handler(CommandHandler("start", menu_start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_panel))

    # ConversationHandler для администратора (ПЕРВЫМ среди callback handlers)
    application.add_handler(admin_conv_handler)

    # Обработчики callback запросов для пользовательского меню
    application.add_handler(CallbackQueryHandler(menu_callback))

    # Обработчики сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_book_pc_message
    ))


def main():
    """Основная функция запуска бота"""
    # Проверка обязательных переменных окружения
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в .env файле")

    if ADMIN_ID == 0:
        raise ValueError("ADMIN_ID не установлен в .env файле")

    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Запуск бота...")

    try:
        # Создание приложения
        application = Application.builder().token(BOT_TOKEN).post_init(init_application).build()

        # Настройка обработчиков
        setup_handlers(application)

        # Запуск бота
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
    
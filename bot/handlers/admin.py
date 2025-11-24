import os
from typing import Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from bot.config import ADMIN_ID
from bot.constants import ADMIN_ONLY_MESSAGE, ADMIN_PANEL_MAIN
from bot.services.database import db
from bot.services.promo import promo_service
from bot.middleware.message_cleanup import message_cleanup

AWAITING_PROMO_CODE, AWAITING_PROMO_DAYS, AWAITING_BROADCAST_TEXT, AWAITING_BROADCAST_PHOTO, AWAITING_BROADCAST_CONFIRM, AWAITING_PROMO_FILE = range(6)
ADMIN_MAIN = "admin_main"

PROMO_FILES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'promo_files')
os.makedirs(PROMO_FILES_DIR, exist_ok=True)

def admin_required(func):
    """Декоратор для проверки прав администратора"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text(ADMIN_ONLY_MESSAGE)
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    """Показать меню администратора"""
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить промокод", callback_data="add_promo"),
            InlineKeyboardButton("📋 Список промокодов", callback_data="list_promos")
        ],
        [
            InlineKeyboardButton("📁 Загрузить файл с промокодами", callback_data="upload_promo_file")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("📤 Рассылка", callback_data="broadcast_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit:
        query = update.callback_query
        await query.edit_message_text(
            text=ADMIN_PANEL_MAIN,
            reply_markup=reply_markup
        )
        await message_cleanup.track_bot_message(
            update.effective_chat.id,
            query.message.message_id,
            context
        )
    else:
        await update.message.reply_text(
            text=ADMIN_PANEL_MAIN,
            reply_markup=reply_markup
        )


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admin"""
    await message_cleanup.cleanup_user_command(update, context)

    response = await update.effective_chat.send_message(
        text=ADMIN_PANEL_MAIN,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Добавить промокод", callback_data="add_promo"),
                InlineKeyboardButton("📋 Список промокодов", callback_data="list_promos")
            ],
            [
                InlineKeyboardButton("📁 Загрузить файл с промокодами", callback_data="upload_promo_file")
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="stats"),
                InlineKeyboardButton("📤 Рассылка", callback_data="broadcast_menu")
            ]
        ])
    )

    await message_cleanup.track_bot_message(
        update.effective_chat.id,
        response.message_id,
        context
    )

async def receive_promo_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка загруженного файла с промокодами"""
    message_id = context.user_data.get("admin_message_id")
    
    if not update.message.document:
        await update.message.reply_text("❌ Пожалуйста, отправьте текстовый файл.")
        return AWAITING_PROMO_FILE
    
    document = update.message.document
    file_extension = document.file_name.split('.')[-1].lower() if document.file_name else ''
    
    if file_extension not in ['txt', 'text']:
        await update.message.reply_text("❌ Пожалуйста, отправьте текстовый файл (.txt)")
        return AWAITING_PROMO_FILE
    
    try:
        # Скачиваем файл
        file = await document.get_file()
        file_path = os.path.join(PROMO_FILES_DIR, f"promo_{document.file_name}")
        await file.download_to_drive(file_path)
        
        # Читаем промокоды из файла
        with open(file_path, 'r', encoding='utf-8') as f:
            promo_codes = [line.strip() for line in f if line.strip()]
        
        if not promo_codes:
            await update.message.reply_text("❌ Файл пуст или содержит только пустые строки")
            return AWAITING_PROMO_FILE
        
        # Сохраняем промокоды в базу
        added_count = 0
        days = 7  # По умолчанию 7 дней
        
        for code in promo_codes:
            if code and len(code) > 0 and await promo_service.create_promo(code, days):
                added_count += 1
        
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ *Файл успешно обработан!*\n\n"
            f"📁 Файл: `{document.file_name}`\n"
            f"🎫 Промокодов в файле: `{len(promo_codes)}`\n"
            f"✅ Добавлено в базу: `{added_count}`\n"
            f"📅 Срок действия: `{days}` дней",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Удаляем служебные сообщения
        await update.message.delete()
        if message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=message_id
                )
            except Exception:
                pass
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке файла: `{str(e)}`", parse_mode='Markdown')
        return AWAITING_PROMO_FILE
    

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data == ADMIN_MAIN:
        await show_admin_menu(update, context, edit=True)
        return ConversationHandler.END

    elif query.data == "add_promo":
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Введите промокод:",
            reply_markup=reply_markup
        )
        context.user_data["admin_message_id"] = query.message.message_id
        return AWAITING_PROMO_CODE

    elif query.data == "upload_promo_file":
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Отправьте текстовый файл с промокодами (каждый промокод на новой строке):",
            reply_markup=reply_markup
        )
        context.user_data["admin_message_id"] = query.message.message_id
        return AWAITING_PROMO_FILE

    elif query.data == "list_promos":
        promos = await promo_service.get_all_promos()
        if not promos:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=ADMIN_MAIN)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Промокоды не найдены", reply_markup=reply_markup)
            return ConversationHandler.END

        text = "📋 Список промокодов:\n\n"
        for promo in promos:
            status = "✅" if promo["active"] else "❌"
            text += f"{status} *{promo['code']}*\n"
            text += f"   📅 Срок: до {promo['expiry_date']}\n"
            text += f"   🕐 Создан: {promo['created_at']}\n\n"

        keyboard = [
            [InlineKeyboardButton("🗑 Удалить промокод", callback_data="delete_promo_menu")],
            [InlineKeyboardButton("🔙 Назад", callback_data=ADMIN_MAIN)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return ConversationHandler.END

    elif query.data == "delete_promo_menu":
        promos = await promo_service.get_all_promos()
        keyboard = []
        for promo in promos:
            keyboard.append([InlineKeyboardButton(
                f"🗑 {promo['code']}",
                callback_data=f"delete_{promo['code']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="list_promos")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите промокод для удаления:", reply_markup=reply_markup)

    elif query.data.startswith("delete_"):
        code = query.data.replace("delete_", "")
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if await promo_service.delete_promo(code):
            await query.edit_message_text(f"✅ Промокод *{code}* удален", reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Ошибка удаления", reply_markup=reply_markup)
        return ConversationHandler.END

    elif query.data == "stats":
        users_count = await db.get_users_count()
        promos = await promo_service.get_all_promos()
        active_promos = len([p for p in promos if p["active"]])

        # Получаем статистику по файлам промокодов
        promo_files = await get_promo_files_stats()
        
        text = (
            f"📊 *Статистика бота*\n\n"
            f"👥 Пользователей: *{users_count}*\n"
            f"🎫 Всего промокодов: *{len(promos)}*\n"
            f"✅ Активных промокодов: *{active_promos}*\n"
            f"📁 Файлов с промокодами: *{len(promo_files)}*\n"
        )
        
        if promo_files:
            total_codes = sum(stats['count'] for stats in promo_files.values())
            text += f"📊 Промокодов в файлах: *{total_codes}*"

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return ConversationHandler.END

    elif query.data == "broadcast_menu":
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Введите текст сообщения для рассылки:",
            reply_markup=reply_markup
        )
        context.user_data["admin_message_id"] = query.message.message_id
        return AWAITING_BROADCAST_TEXT

    elif query.data == "cancel":
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ Отменено", reply_markup=reply_markup)
        return ConversationHandler.END


async def receive_promo_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка загруженного файла с промокодами"""
    message_id = context.user_data.get("admin_message_id")
    
    if not update.message.document:
        await update.message.reply_text("❌ Пожалуйста, отправьте текстовый файл.")
        return AWAITING_PROMO_FILE
    
    document = update.message.document
    file_extension = document.file_name.split('.')[-1].lower() if document.file_name else ''
    
    if file_extension not in ['txt', 'text']:
        await update.message.reply_text("❌ Пожалуйста, отправьте текстовый файл (.txt)")
        return AWAITING_PROMO_FILE
    
    try:
        # Скачиваем файл
        file = await document.get_file()
        file_path = os.path.join(PROMO_FILES_DIR, f"promo_{document.file_name}")
        await file.download_to_drive(file_path)
        
        # Читаем промокоды из файла
        with open(file_path, 'r', encoding='utf-8') as f:
            promo_codes = [line.strip() for line in f if line.strip()]
        
        if not promo_codes:
            await update.message.reply_text("❌ Файл пуст или содержит только пустые строки")
            return AWAITING_PROMO_FILE
        
        # Сохраняем промокоды в базу
        added_count = 0
        days = 7  # По умолчанию 7 дней
        
        for code in promo_codes:
            if code and len(code) > 0 and await promo_service.create_promo(code, days):
                added_count += 1
        
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ *Файл успешно обработан!*\n\n"
            f"📁 Файл: `{document.file_name}`\n"
            f"🎫 Промокодов в файле: `{len(promo_codes)}`\n"
            f"✅ Добавлено в базу: `{added_count}`\n"
            f"📅 Срок действия: `{days}` дней",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Удаляем служебные сообщения
        await update.message.delete()
        if message_id:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=message_id
                )
            except Exception:
                pass
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке файла: `{str(e)}`", parse_mode='Markdown')
        return AWAITING_PROMO_FILE


async def get_promo_files_stats():
    """Получить статистику по файлам с промокодами"""
    stats = {}
    try:
        for filename in os.listdir(PROMO_FILES_DIR):
            if filename.endswith('.txt'):
                file_path = os.path.join(PROMO_FILES_DIR, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    codes = [line.strip() for line in f if line.strip()]
                stats[filename] = {'count': len(codes)}
    except Exception:
        pass
    return stats


async def receive_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода промокода"""
    code = update.message.text.strip()
    message_id = context.user_data.get("admin_message_id")

    await update.message.delete()

    if message_id:
        context.user_data["new_promo_code"] = code

        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"Промокод: `{code}`\n\nВведите количество дней действия (например, 7):",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception:
            pass

        return AWAITING_PROMO_DAYS

    return ConversationHandler.END


async def receive_promo_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода количества дней"""
    message_id = context.user_data.get("admin_message_id")
    code = context.user_data.get("new_promo_code")

    await update.message.delete()

    try:
        days = int(update.message.text.strip())

        if await promo_service.create_promo(code, days):
            text = f"✅ Промокод `{code}` создан на *{days}* дней"
        else:
            text = "❌ Ошибка создания промокода"

    except ValueError:
        text = "❌ Неверный формат. Введите число."
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"Промокод: `{code}`\n\n{text}\n\nВведите корректное число дней:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception:
            pass

        return AWAITING_PROMO_DAYS

    keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception:
        pass

    context.user_data.clear()
    return ConversationHandler.END


async def receive_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста рассылки"""
    broadcast_text = update.message.text.strip()
    message_id = context.user_data.get("admin_message_id")

    await update.message.delete()

    if message_id:
        context.user_data["broadcast_text"] = broadcast_text

        keyboard = [
            [InlineKeyboardButton("📸 Добавить фото", callback_data="add_photo")],
            [InlineKeyboardButton("🚫 Без фото", callback_data="skip_photo")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        preview_text = broadcast_text[:200] + "..." if len(broadcast_text) > 200 else broadcast_text

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"📝 Текст рассылки сохранен:\n\n`{preview_text}`\n\nХотите добавить фото?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception:
            pass

        return AWAITING_BROADCAST_PHOTO

    return ConversationHandler.END


async def handle_broadcast_photo_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора добавления фото"""
    query = update.callback_query
    await query.answer()

    if query.data == "add_photo":
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📸 Отправьте фото для рассылки:",
            reply_markup=reply_markup
        )
        return AWAITING_BROADCAST_PHOTO

    elif query.data == "skip_photo":
        return await show_broadcast_confirmation(update, context, photo_file_id=None)


async def receive_broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото для рассылки"""
    message_id = context.user_data.get("admin_message_id")

    await update.message.delete()

    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data["broadcast_photo_id"] = photo.file_id

        return await show_broadcast_confirmation(update, context, photo_file_id=photo.file_id)

    return AWAITING_BROADCAST_PHOTO


async def show_broadcast_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, photo_file_id: Optional[str]):
    """Показать подтверждение рассылки"""
    message_id = context.user_data.get("admin_message_id")
    broadcast_text = context.user_data.get("broadcast_text", "")

    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="broadcast_confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    preview_text = broadcast_text[:200] + "..." if len(broadcast_text) > 200 else broadcast_text
    users_count = await db.get_users_count()

    confirmation_text = f"👁 *Предпросмотр рассылки:*\n\n`{preview_text}`\n\n"

    if photo_file_id:
        confirmation_text += "📸 *Фото:* прикреплено\n"

    confirmation_text += f"\n📊 Будет отправлено *{users_count}* пользователям.\n\n*Подтвердите отправку:*"

    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                text=confirmation_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=confirmation_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception:
        pass

    return AWAITING_BROADCAST_CONFIRM


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и отправка рассылки"""
    query = update.callback_query
    await query.answer()

    if query.data == "broadcast_confirm":
        message_id = context.user_data.get("admin_message_id")
        broadcast_text = context.user_data.get("broadcast_text")
        photo_file_id = context.user_data.get("broadcast_photo_id")

        if broadcast_text:
            await query.edit_message_text("📤 Рассылка запущена. Пожалуйста, подождите...")

            from bot.services.broadcast import broadcast_service
            result = await broadcast_service.send_broadcast(context.bot, broadcast_text, photo_file_id)

            keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=f"✅ *Рассылка завершена*\n\n📤 Отправлено: *{result['sent']}*\n❌ Ошибок: *{result['failed']}*",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception:
                pass

        context.user_data.clear()
        return ConversationHandler.END

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    await update.message.delete()

    message_id = context.user_data.get("admin_message_id")
    if message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="❌ Отменено"
            )
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END

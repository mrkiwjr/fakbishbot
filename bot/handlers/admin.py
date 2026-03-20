import os
import logging
import functools
from typing import Optional
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from bot.config import (
    ADMIN_ID,
    DEFAULT_PROMO_DAYS,
    MIN_PROMO_DAYS,
    MAX_PROMO_DAYS,
    MAX_PROMO_CODE_LENGTH
)
from bot.constants import ADMIN_ONLY_MESSAGE, ADMIN_PANEL_MAIN
from bot.services.database import db
from bot.services.promo import promo_service
from bot.middleware.message_cleanup import message_cleanup

logger = logging.getLogger(__name__)

AWAITING_PROMO_CODE, AWAITING_PROMO_DAYS, AWAITING_BROADCAST_TEXT, AWAITING_BROADCAST_PHOTO, AWAITING_BROADCAST_CONFIRM, AWAITING_PROMO_FILE, AWAITING_ADMIN_ID, AWAITING_FILE_EXPIRY_DATE, AWAITING_FILE_EXPIRY_TIME = range(9)
ADMIN_MAIN = "admin_main"

PROMO_FILES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'promo_files')
os.makedirs(PROMO_FILES_DIR, exist_ok=True)

async def is_user_admin(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    return await db.is_admin(user_id)


def is_super_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def admin_required(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await is_user_admin(update.effective_user.id):
            await update.message.reply_text(ADMIN_ONLY_MESSAGE)
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


def super_admin_required(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_super_admin(update.effective_user.id):
            if update.callback_query:
                await update.callback_query.answer("Эта функция доступна только главному администратору.", show_alert=True)
            else:
                await update.message.reply_text("Эта функция доступна только главному администратору.")
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    user_id = update.effective_user.id
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить промокод", callback_data="add_promo"),
            InlineKeyboardButton("📋 Список промокодов", callback_data="list_promos")
        ],
        [
            InlineKeyboardButton("📁 Загрузить файл с промокодами", callback_data="upload_promo_file")
        ],
        [
            InlineKeyboardButton("📜 История выдачи", callback_data="promo_history")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="stats"),
            InlineKeyboardButton("📤 Рассылка", callback_data="broadcast_menu")
        ]
    ]

    if is_super_admin(user_id):
        keyboard.append([
            InlineKeyboardButton("👥 Управление админами", callback_data="manage_admins")
        ])

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
        response = await update.effective_chat.send_message(
            text=ADMIN_PANEL_MAIN,
            reply_markup=reply_markup
        )
        await message_cleanup.track_bot_message(
            update.effective_chat.id,
            response.message_id,
            context
        )


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await message_cleanup.cleanup_user_command(update, context)
    await show_admin_menu(update, context, edit=False)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not await is_user_admin(update.effective_user.id):
        await query.answer("Эта команда доступна только администратору.", show_alert=True)
        return ConversationHandler.END

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
        return ConversationHandler.END

    elif query.data.startswith("delete_"):
        code = query.data.replace("delete_", "")
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if await promo_service.delete_promo(code):
            await query.edit_message_text(f"✅ Промокод *{code}* удален", reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Ошибка удаления", reply_markup=reply_markup)
        return ConversationHandler.END

    elif query.data == "promo_history":
        usage_history = await db.get_promo_usage_with_users()

        if not usage_history:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=ADMIN_MAIN)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("История выдачи промокодов пуста", reply_markup=reply_markup)
            return ConversationHandler.END

        text = "📜 *История выдачи промокодов*\n\n"
        for idx, entry in enumerate(usage_history[:20], 1):
            username = f"@{entry['username']}" if entry['username'] else "без username"
            text += (
                f"{idx}. *{entry['promo_code']}*\n"
                f"   👤 {entry['first_name']} ({username})\n"
                f"   🆔 User ID: `{entry['user_id']}`\n"
                f"   🕐 Выдан: {entry['received_at']}\n"
                f"   📅 Срок: до {entry['expiry_date']}\n\n"
            )

        if len(usage_history) > 20:
            text += f"_Показано 20 из {len(usage_history)} записей_"

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return ConversationHandler.END

    elif query.data == "stats":
        users_count = await db.get_users_count()
        promos = await promo_service.get_all_promos()
        active_promos = len([p for p in promos if p["active"]])
        unused_promos = await db.get_unused_active_promos()
        usage_history = await db.get_promo_usage_with_users()

        promo_files = await get_promo_files_stats()

        text = (
            f"📊 *Статистика бота*\n\n"
            f"👥 Пользователей: *{users_count}*\n"
            f"🎫 Всего промокодов: *{len(promos)}*\n"
            f"✅ Активных промокодов: *{active_promos}*\n"
            f"🆓 Неиспользованных активных: *{len(unused_promos)}*\n"
            f"📤 Выдано промокодов: *{len(usage_history)}*\n"
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

    elif query.data == "manage_admins":
        if not is_super_admin(update.effective_user.id):
            await query.answer("Эта функция доступна только главному администратору.", show_alert=True)
            return ConversationHandler.END

        admins = await db.get_all_admins()
        text = "👥 *Управление администраторами*\n\n"

        if admins:
            text += "📋 Список администраторов:\n\n"
            for admin in admins:
                username = f"@{admin['username']}" if admin['username'] else "без username"
                text += f"• {admin['first_name']} ({username})\n"
                text += f"  ID: `{admin['user_id']}`\n"
                text += f"  Добавлен: {admin['added_at']}\n\n"
        else:
            text += "Дополнительных администраторов нет\n\n"

        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
        ]

        if admins:
            keyboard.append([InlineKeyboardButton("🗑 Удалить админа", callback_data="remove_admin_menu")])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=ADMIN_MAIN)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return ConversationHandler.END

    elif query.data == "add_admin":
        if not is_super_admin(update.effective_user.id):
            await query.answer("Эта функция доступна только главному администратору.", show_alert=True)
            return ConversationHandler.END

        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="manage_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Введите username пользователя, которого хотите сделать администратором:\n\n"
            "Пример: `@jemappelleilya` или `jemappelleilya`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        context.user_data["admin_message_id"] = query.message.message_id
        return AWAITING_ADMIN_ID

    elif query.data == "remove_admin_menu":
        if not is_super_admin(update.effective_user.id):
            await query.answer("Эта функция доступна только главному администратору.", show_alert=True)
            return ConversationHandler.END

        admins = await db.get_all_admins()
        if not admins:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_admins")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Нет администраторов для удаления", reply_markup=reply_markup)
            return ConversationHandler.END

        keyboard = []
        for admin in admins:
            username = f"@{admin['username']}" if admin['username'] else admin['first_name']
            keyboard.append([InlineKeyboardButton(
                f"🗑 {username} (ID: {admin['user_id']})",
                callback_data=f"remove_admin_{admin['user_id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="manage_admins")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите администратора для удаления:", reply_markup=reply_markup)
        return ConversationHandler.END

    elif query.data.startswith("remove_admin_"):
        if not is_super_admin(update.effective_user.id):
            await query.answer("Эта функция доступна только главному администратору.", show_alert=True)
            return ConversationHandler.END

        admin_id = int(query.data.replace("remove_admin_", ""))
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if await db.remove_admin(admin_id):
            await query.edit_message_text(f"✅ Администратор (ID: `{admin_id}`) удален", reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ Ошибка удаления", reply_markup=reply_markup)
        return ConversationHandler.END

    elif query.data == "cancel":
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ Отменено", reply_markup=reply_markup)
        return ConversationHandler.END


async def receive_promo_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        file = await document.get_file()
        file_path = os.path.join(PROMO_FILES_DIR, f"promo_{document.file_name}")
        await file.download_to_drive(file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            promo_codes = [line.strip() for line in f if line.strip()]

        if not promo_codes:
            await update.message.reply_text("❌ Файл пуст или содержит только пустые строки")
            return AWAITING_PROMO_FILE

        invalid_codes = [code for code in promo_codes if len(code) > MAX_PROMO_CODE_LENGTH]
        valid_codes = [code for code in promo_codes if len(code) <= MAX_PROMO_CODE_LENGTH]

        context.user_data["promo_file_path"] = file_path
        context.user_data["promo_file_name"] = document.file_name
        context.user_data["promo_codes"] = valid_codes
        context.user_data["invalid_codes_count"] = len(invalid_codes)

        await update.message.delete()

        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=(
                    f"📁 Файл загружен: `{document.file_name}`\n"
                    f"🎫 Промокодов: `{len(valid_codes)}`\n\n"
                    f"Введите дату окончания срока действия:\n\n"
                    f"Формат: `ДД.МM.ГГ`\n"
                    f"Пример: `27.11.25`"
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение: {e}")

        return AWAITING_FILE_EXPIRY_DATE

    except Exception as e:
        logger.error(f"Ошибка при обработке файла с промокодами: {e}")
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

    if not code:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="❌ Промокод не может быть пустым. Введите промокод:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение: {e}")
        return AWAITING_PROMO_CODE

    if len(code) > MAX_PROMO_CODE_LENGTH:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"❌ Промокод слишком длинный (макс. {MAX_PROMO_CODE_LENGTH} символов). Введите другой промокод:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение: {e}")
        return AWAITING_PROMO_CODE

    if message_id:
        context.user_data["new_promo_code"] = code

        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"Промокод: `{code}`\n\nВведите количество дней действия ({MIN_PROMO_DAYS}-{MAX_PROMO_DAYS}):",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение: {e}")

        return AWAITING_PROMO_DAYS

    return ConversationHandler.END


async def receive_promo_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода количества дней"""
    message_id = context.user_data.get("admin_message_id")
    code = context.user_data.get("new_promo_code")

    await update.message.delete()

    try:
        days = int(update.message.text.strip())

        if days < MIN_PROMO_DAYS or days > MAX_PROMO_DAYS:
            text = f"❌ Количество дней должно быть от {MIN_PROMO_DAYS} до {MAX_PROMO_DAYS}"
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=f"Промокод: `{code}`\n\n{text}\n\nВведите корректное число дней ({MIN_PROMO_DAYS}-{MAX_PROMO_DAYS}):",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.debug(f"Не удалось отредактировать сообщение: {e}")

            return AWAITING_PROMO_DAYS

        if await promo_service.create_promo(code, days):
            text = f"✅ Промокод `{code}` создан на *{days}* дней"
        else:
            text = "❌ Ошибка создания промокода (возможно, промокод уже существует)"

    except ValueError:
        text = "❌ Неверный формат. Введите число"
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"Промокод: `{code}`\n\n{text}\n\nВведите корректное число дней ({MIN_PROMO_DAYS}-{MAX_PROMO_DAYS}):",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение: {e}")

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


async def receive_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_id = context.user_data.get("admin_message_id")
    await update.message.delete()

    input_text = update.message.text.strip()

    if not input_text:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="manage_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text="❌ Введите username или ID пользователя.\n\n"
                 "Примеры:\n"
                 "• `@jemappelleilya`\n"
                 "• `796891410`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return AWAITING_ADMIN_ID

    user_id = None
    username = None

    clean_input = input_text.strip().lower().replace("id", "").strip()

    if clean_input.isdigit():
        user_id = int(clean_input)
    elif input_text.startswith("@"):
        username = input_text.lstrip('@').lower()

    if not user_id and not username:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="manage_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text="❌ Введите корректный username или ID.\n\n"
                 "Примеры:\n"
                 "• `@jemappelleilya`\n"
                 "• `796891410`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return AWAITING_ADMIN_ID

    user = None
    if user_id:
        user = await db.get_user_by_id(user_id)
    elif username:
        user = await db.get_user_by_username(username)

    if not user:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="manage_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=f"❌ Пользователь не найден.\n\n"
                 f"Убедитесь, что он запускал бота (/start).",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return AWAITING_ADMIN_ID

    new_admin_id = user['user_id']
    first_name = user['first_name']
    username_to_show = user['username'] or "без username"

    if new_admin_id == ADMIN_ID:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text="❌ Этот пользователь уже является главным администратором",
            reply_markup=reply_markup
        )
        context.user_data.clear()
        return ConversationHandler.END

    if await db.is_admin(new_admin_id):
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_admins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text="❌ Этот пользователь уже является администратором",
            reply_markup=reply_markup
        )
        context.user_data.clear()
        return ConversationHandler.END

    if await db.add_admin(new_admin_id, first_name, ADMIN_ID, user['username']):
        text = f"✅ Пользователь *{first_name}* (@{username_to_show}) добавлен как администратор"
        logger.info(f"Добавлен новый администратор: {first_name} (ID: {new_admin_id})")
    else:
        text = "❌ Ошибка при добавлении администратора"

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="manage_admins")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=message_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    context.user_data.clear()
    return ConversationHandler.END


async def receive_file_expiry_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_id = context.user_data.get("admin_message_id")
    await update.message.delete()

    date_input = update.message.text.strip()

    try:
        date_obj = datetime.strptime(date_input, "%d.%m.%y")
        context.user_data["expiry_date_obj"] = date_obj

        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        file_name = context.user_data.get("promo_file_name", "файл")
        codes_count = len(context.user_data.get("promo_codes", []))

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=(
                    f"📁 Файл: `{file_name}`\n"
                    f"🎫 Промокодов: `{codes_count}`\n"
                    f"📅 Дата: `{date_obj.strftime('%d.%m.%y')}`\n\n"
                    f"Введите время окончания срока действия:\n\n"
                    f"Формат: `ЧЧ:ММ`\n"
                    f"Пример: `00:30` или `23:59`"
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение: {e}")

        return AWAITING_FILE_EXPIRY_TIME

    except ValueError:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=(
                    f"❌ Неверный формат даты\n\n"
                    f"Введите дату в формате `ДД.МM.ГГ`\n"
                    f"Пример: `27.11.25`"
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение: {e}")

        return AWAITING_FILE_EXPIRY_DATE


async def receive_file_expiry_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_id = context.user_data.get("admin_message_id")
    await update.message.delete()

    time_input = update.message.text.strip()

    try:
        time_obj = datetime.strptime(time_input, "%H:%M")
        date_obj = context.user_data.get("expiry_date_obj")

        expiry_datetime = date_obj.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
        expiry_date_str = expiry_datetime.strftime("%Y-%m-%d")

        promo_codes = context.user_data.get("promo_codes", [])
        invalid_count = context.user_data.get("invalid_codes_count", 0)
        file_name = context.user_data.get("promo_file_name", "файл")

        added_count = 0
        skipped_count = 0

        for code in promo_codes:
            if await promo_service.create_promo_with_date(code, expiry_date_str):
                added_count += 1
            else:
                skipped_count += 1

        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        result_text = (
            f"✅ *Файл успешно обработан!*\n\n"
            f"📁 Файл: `{file_name}`\n"
            f"🎫 Промокодов в файле: `{len(promo_codes)}`\n"
            f"✅ Добавлено в базу: `{added_count}`\n"
        )

        if skipped_count > 0:
            result_text += f"⚠️ Пропущено (дубликаты): `{skipped_count}`\n"

        if invalid_count > 0:
            result_text += f"⚠️ Пропущено (слишком длинные): `{invalid_count}`\n"

        result_text += f"\n📅 Срок действия: до `{expiry_datetime.strftime('%d.%m.%y %H:%M')}`"

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=result_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение: {e}")

        context.user_data.clear()
        logger.info(f"Добавлено {added_count} промокодов из файла {file_name} со сроком до {expiry_date_str}")
        return ConversationHandler.END

    except ValueError:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=(
                    f"❌ Неверный формат времени\n\n"
                    f"Введите время в формате `ЧЧ:ММ`\n"
                    f"Пример: `00:30` или `23:59`"
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Не удалось отредактировать сообщение: {e}")

        return AWAITING_FILE_EXPIRY_TIME


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

from typing import Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from bot.config import ADMIN_ID
from bot.constants import ADMIN_ONLY_MESSAGE, ADMIN_PANEL_MAIN
from bot.services.database import db
from bot.services.promo import promo_service
from bot.middleware.message_cleanup import message_cleanup

AWAITING_PROMO_CODE, AWAITING_PROMO_DAYS, AWAITING_BROADCAST_TEXT, AWAITING_BROADCAST_PHOTO, AWAITING_BROADCAST_CONFIRM = range(5)
ADMIN_MAIN = "admin_main"


def admin_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text(ADMIN_ONLY_MESSAGE)
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить промокод", callback_data="add_promo"),
            InlineKeyboardButton("📋 Список промокодов", callback_data="list_promos")
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
    await message_cleanup.cleanup_user_command(update, context)

    response = await update.effective_chat.send_message(
        text=ADMIN_PANEL_MAIN,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Добавить промокод", callback_data="add_promo"),
                InlineKeyboardButton("📋 Список промокодов", callback_data="list_promos")
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


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    elif query.data == "list_promos":
        promos = await promo_service.get_all_promos()
        if not promos:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=ADMIN_MAIN)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Промокоды не найдены", reply_markup=reply_markup)
            return ConversationHandler.END

        text = "Список промокодов:\n\n"
        for promo in promos:
            status = "✅" if promo["active"] else "❌"
            text += f"{status} {promo['code']}\n"
            text += f"   Срок: до {promo['expiry_date']}\n"
            text += f"   Создан: {promo['created_at']}\n\n"

        keyboard = [
            [InlineKeyboardButton("🗑 Удалить промокод", callback_data="delete_promo_menu")],
            [InlineKeyboardButton("🔙 Назад", callback_data=ADMIN_MAIN)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup)
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
            await query.edit_message_text(f"Промокод {code} удален", reply_markup=reply_markup)
        else:
            await query.edit_message_text("Ошибка удаления", reply_markup=reply_markup)
        return ConversationHandler.END

    elif query.data == "stats":
        users_count = await db.get_users_count()
        promos = await promo_service.get_all_promos()
        active_promos = len([p for p in promos if p["active"]])

        text = (
            f"Статистика бота\n\n"
            f"Пользователей: {users_count}\n"
            f"Всего промокодов: {len(promos)}\n"
            f"Активных промокодов: {active_promos}"
        )

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup)
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
        await query.edit_message_text("Отменено", reply_markup=reply_markup)
        return ConversationHandler.END


async def receive_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                text=f"Промокод: {code}\n\nВведите количество дней действия (например, 7):",
                reply_markup=reply_markup
            )
        except Exception:
            pass

        return AWAITING_PROMO_DAYS

    return ConversationHandler.END


async def receive_promo_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_id = context.user_data.get("admin_message_id")
    code = context.user_data.get("new_promo_code")

    await update.message.delete()

    try:
        days = int(update.message.text.strip())

        if await promo_service.create_promo(code, days):
            text = f"Промокод {code} создан на {days} дней"
        else:
            text = "Ошибка создания промокода"

    except ValueError:
        text = "Неверный формат. Введите число."
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"Промокод: {code}\n\n{text}\n\nВведите корректное число дней:",
                reply_markup=reply_markup
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
            reply_markup=reply_markup
        )
    except Exception:
        pass

    context.user_data.clear()
    return ConversationHandler.END


async def receive_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                text=f"Текст рассылки сохранен:\n\n{preview_text}\n\nХотите добавить фото?",
                reply_markup=reply_markup
            )
        except Exception:
            pass

        return AWAITING_BROADCAST_PHOTO

    return ConversationHandler.END


async def handle_broadcast_photo_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_photo":
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=ADMIN_MAIN)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Отправьте фото для рассылки:",
            reply_markup=reply_markup
        )
        return AWAITING_BROADCAST_PHOTO

    elif query.data == "skip_photo":
        return await show_broadcast_confirmation(update, context, photo_file_id=None)


async def receive_broadcast_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_id = context.user_data.get("admin_message_id")

    await update.message.delete()

    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data["broadcast_photo_id"] = photo.file_id

        return await show_broadcast_confirmation(update, context, photo_file_id=photo.file_id)

    return AWAITING_BROADCAST_PHOTO


async def show_broadcast_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, photo_file_id: Optional[str]):
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

    confirmation_text = f"Предпросмотр рассылки:\n\n{preview_text}\n\n"

    if photo_file_id:
        confirmation_text += "📸 Фото: прикреплено\n"

    confirmation_text += f"\n📊 Будет отправлено {users_count} пользователям.\n\nПодтвердите отправку:"

    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                text=confirmation_text,
                reply_markup=reply_markup
            )
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=confirmation_text,
                reply_markup=reply_markup
            )
    except Exception:
        pass

    return AWAITING_BROADCAST_CONFIRM


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "broadcast_confirm":
        message_id = context.user_data.get("admin_message_id")
        broadcast_text = context.user_data.get("broadcast_text")
        photo_file_id = context.user_data.get("broadcast_photo_id")

        if broadcast_text:
            await query.edit_message_text("Рассылка запущена. Пожалуйста, подождите...")

            from bot.services.broadcast import broadcast_service
            result = await broadcast_service.send_broadcast(context.bot, broadcast_text, photo_file_id)

            keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=ADMIN_MAIN)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=f"Рассылка завершена\n\n✅ Отправлено: {result['sent']}\n❌ Ошибок: {result['failed']}",
                    reply_markup=reply_markup
                )
            except Exception:
                pass

        context.user_data.clear()
        return ConversationHandler.END

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()

    message_id = context.user_data.get("admin_message_id")
    if message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text="Отменено"
            )
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END

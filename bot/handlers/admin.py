from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from bot.config import ADMIN_ID
from bot.constants import ADMIN_ONLY_MESSAGE
from bot.services.database import db
from bot.services.promo import promo_service

PROMO_CODE, PROMO_DAYS = range(2)


def admin_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text(ADMIN_ONLY_MESSAGE)
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Добавить промокод", callback_data="add_promo")],
        [InlineKeyboardButton("📋 Список промокодов", callback_data="list_promos")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("📤 Рассылка", callback_data="broadcast_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Админ панель\n\nВыберите действие:",
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_promo":
        await query.edit_message_text("Введите промокод:")
        return PROMO_CODE

    elif query.data == "list_promos":
        promos = promo_service.get_all_promos()
        if not promos:
            await query.edit_message_text("Промокоды не найдены")
            return ConversationHandler.END

        text = "Список промокодов:\n\n"
        for promo in promos:
            status = "✅" if promo["active"] else "❌"
            text += f"{status} {promo['code']}\n"
            text += f"   Срок: до {promo['expiry_date']}\n"
            text += f"   Создан: {promo['created_at']}\n\n"

        keyboard = [[InlineKeyboardButton("🗑 Удалить промокод", callback_data="delete_promo_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup)
        return ConversationHandler.END

    elif query.data == "delete_promo_menu":
        promos = promo_service.get_all_promos()
        keyboard = []
        for promo in promos:
            keyboard.append([InlineKeyboardButton(
                f"🗑 {promo['code']}",
                callback_data=f"delete_{promo['code']}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите промокод для удаления:", reply_markup=reply_markup)

    elif query.data.startswith("delete_"):
        code = query.data.replace("delete_", "")
        if promo_service.delete_promo(code):
            await query.edit_message_text(f"Промокод {code} удален")
        else:
            await query.edit_message_text("Ошибка удаления")
        return ConversationHandler.END

    elif query.data == "stats":
        users_count = db.get_users_count()
        promos = promo_service.get_all_promos()
        active_promos = len([p for p in promos if p["active"]])

        text = (
            f"Статистика бота\n\n"
            f"Пользователей: {users_count}\n"
            f"Всего промокодов: {len(promos)}\n"
            f"Активных промокодов: {active_promos}"
        )
        await query.edit_message_text(text)
        return ConversationHandler.END

    elif query.data == "broadcast_menu":
        await query.edit_message_text("Введите сообщение для рассылки:")
        context.user_data["awaiting_broadcast"] = True
        return ConversationHandler.END

    elif query.data == "cancel":
        await query.edit_message_text("Отменено")
        return ConversationHandler.END


async def receive_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    context.user_data["new_promo_code"] = code

    await update.message.reply_text("Введите количество дней действия промокода (например, 7):")
    return PROMO_DAYS


async def receive_promo_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
        code = context.user_data.get("new_promo_code")

        if promo_service.create_promo(code, days):
            await update.message.reply_text(f"Промокод {code} создан на {days} дней")
        else:
            await update.message.reply_text("Ошибка создания промокода")

    except ValueError:
        await update.message.reply_text("Неверный формат. Введите число.")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено")
    return ConversationHandler.END

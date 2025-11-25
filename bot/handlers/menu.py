from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest

from bot.config import CHANNEL_USERNAME, ADMIN_ID, ADMIN_USERNAME, NOTIFICATION_CHAT_ID
from bot.constants import (
    MENU_MAIN,
    NOT_SUBSCRIBED_MESSAGE,
    PROMO_RECEIVED_MESSAGE,
    PROMO_ALREADY_RECEIVED_MESSAGE,
    NO_ACTIVE_PROMO_MESSAGE,
    HELP_USER_MESSAGE,
    HELP_ADMIN_MESSAGE,
    BOOK_PC_MESSAGE,
    FEEDBACK_MESSAGE,
    PROMOTIONS_MESSAGE,
    TARIFFS_MESSAGE
)
from bot.services.database import db
from bot.services.subscription import check_subscription
from bot.services.promo import promo_service
from bot.middleware.message_cleanup import message_cleanup

MAIN, PROMO, HELP, BOOK_PC, FEEDBACK, PROMOTIONS, TARIFFS, AWAITING_FEEDBACK = range(8)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    keyboard = [
        [
            InlineKeyboardButton("🎁 Получить промокод", callback_data=str(PROMO)),
            InlineKeyboardButton("💻 Забронировать ПК", callback_data=str(BOOK_PC))
        ],
        [
            InlineKeyboardButton("💰 Акции", callback_data=str(PROMOTIONS)),
            InlineKeyboardButton("📊 Тарифы", callback_data=str(TARIFFS))
        ],
        [
            InlineKeyboardButton("📝 Обратная связь", callback_data=str(FEEDBACK)),
            InlineKeyboardButton("❓ Помощь", callback_data=str(HELP))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if edit:
        query = update.callback_query
        await query.edit_message_text(
            text=MENU_MAIN,
            reply_markup=reply_markup
        )
        await message_cleanup.track_bot_message(
            update.effective_chat.id,
            query.message.message_id,
            context
        )
    else:
        await update.message.reply_text(
            text=MENU_MAIN,
            reply_markup=reply_markup
        )


async def menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await db.add_user(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username
    )

    await message_cleanup.cleanup_user_command(update, context)

    response = await update.effective_chat.send_message(
        text=MENU_MAIN,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎁 Получить промокод", callback_data=str(PROMO)),
                InlineKeyboardButton("💻 Забронировать ПК", callback_data=str(BOOK_PC))
            ],
            [
                InlineKeyboardButton("💰 Акции", callback_data=str(PROMOTIONS)),
                InlineKeyboardButton("📊 Тарифы", callback_data=str(TARIFFS))
            ],
            [
                InlineKeyboardButton("📝 Обратная связь", callback_data=str(FEEDBACK)),
                InlineKeyboardButton("❓ Помощь", callback_data=str(HELP))
            ]
        ])
    )

    await message_cleanup.track_bot_message(
        update.effective_chat.id,
        response.message_id,
        context
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await message_cleanup.cleanup_user_command(update, context)

    if user_id == ADMIN_ID:
        text = HELP_ADMIN_MESSAGE
    else:
        text = HELP_USER_MESSAGE

    response = await update.effective_chat.send_message(text)

    await message_cleanup.track_bot_message(
        update.effective_chat.id,
        response.message_id,
        context
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == str(MAIN):
        await show_main_menu(update, context, edit=True)

    elif data == str(PROMO):
        await handle_promo(update, context)

    elif data == str(HELP):
        await handle_help(update, context)

    elif data == str(BOOK_PC):
        await handle_book_pc(update, context)

    elif data == str(FEEDBACK):
        await handle_feedback(update, context)

    elif data == str(PROMOTIONS):
        await handle_promotions(update, context)

    elif data == str(TARIFFS):
        await handle_tariffs(update, context)

    elif data == "subscribe_check":
        await handle_subscribe_check(update, context)

    elif data == "leave_feedback":
        await handle_leave_feedback(update, context)


async def handle_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    is_subscribed = await check_subscription(context.bot, user_id)

    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="subscribe_check")],
            [InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=NOT_SUBSCRIBED_MESSAGE.format(channel=CHANNEL_USERNAME),
            reply_markup=reply_markup
        )
        return

    # Проверяем получал ли пользователь промокод на этой неделе
    has_received = await promo_service.has_received_promo_this_week(user_id)
    
    if has_received:
        # Если получал - показываем его текущий промокод
        last_promo = await promo_service.get_last_received_promo(user_id)
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if last_promo:
            await query.edit_message_text(
                text=f"🎁 *Ваш промокод:*\n\n`{last_promo['code']}`\n\n"
                     f"📅 *Действует до:* {last_promo['expiry_date']}\n\n"
                     f"💡 *Промокод обновится в понедельник*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        return

    # Если не получал - выдаем новый случайный промокод
    received_promo = await promo_service.get_random_active_promo()
    
    if received_promo:
        # Отмечаем что пользователь получил промокод
        await promo_service.mark_promo_received(user_id, received_promo["code"])
        
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=str(MAIN))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=f"🎁 *Ваш промокод:*\n\n`{received_promo['code']}`\n\n"
                 f"📅 *Действует до:* {received_promo['expiry_date']}\n\n"
                 f"💡 *Сохраните этот промокод! Он будет доступен до конца недели*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="❌ *В данный момент нет доступных промокодов*\n\nПопробуйте позже или обратитесь к администратору",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if user_id == ADMIN_ID:
        text = HELP_ADMIN_MESSAGE
    else:
        text = HELP_USER_MESSAGE

    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup
    )


async def handle_book_pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=BOOK_PC_MESSAGE,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("💬 Оставить отзыв", callback_data="leave_feedback")],
        [InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=FEEDBACK_MESSAGE,
        reply_markup=reply_markup
    )


async def handle_leave_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса оставления отзыва"""
    query = update.callback_query
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=str(FEEDBACK))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="💬 *Введите ваш отзыв:*\n\nПожалуйста, напишите ваше мнение, предложение или замечание:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return AWAITING_FEEDBACK


async def handle_feedback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста отзыва"""
    user = update.effective_user
    feedback_text = update.message.text
    
    if update.message.chat.type != 'private':
        return ConversationHandler.END
    
    # Формируем сообщение для админа
    admin_message = f"💬 *НОВЫЙ ОТЗЫВ!*\n\n" \
                   f"*Пользователь:*\n" \
                   f"👤 {user.first_name}\n" \
                   f"📱 @{user.username if user.username else 'нет username'}\n" \
                   f"*Текст отзыва:*\n{feedback_text}\n\n" \
    
    try:
        # Отправляем отзыв админу в личные сообщения
        await context.bot.send_message(
            chat_id=ADMIN_USERNAME,
            text=admin_message,
            parse_mode='Markdown'
        )
        
        # Подтверждение пользователю
        await update.message.reply_text(
            "✅ *Спасибо за ваш отзыв!*\n\nВаши отзывы помогают нам становиться лучше! 🥷",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"Ошибка отправки отзыва: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при отправке отзыва. Пожалуйста, попробуйте позже."
        )
    
    # Возвращаем в главное меню
    await show_main_menu(update, context)
    return ConversationHandler.END


async def cancel_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена оставления отзыва"""
    await update.message.reply_text("❌ Отмена оставления отзыва.")
    await show_main_menu(update, context)
    return ConversationHandler.END


async def handle_promotions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=PROMOTIONS_MESSAGE,
        reply_markup=reply_markup
    )


async def handle_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=TARIFFS_MESSAGE,
        reply_markup=reply_markup
    )


async def handle_book_pc_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового сообщения с данными бронирования"""
    user = update.effective_user
    message_text = update.message.text
    

    if update.message.chat.type != 'private':
        return
    

    admin_message = f"🎯 *НОВАЯ БРОНЬ!*\n\n" \
                   f"*Клиент:*\n" \
                   f"👤 {user.first_name}\n" \
                   f"📱 @{user.username if user.username else 'нет username'}\n" \
                   f"*Данные брони:*\n`{message_text}`\n\n" \


    try:
        # Отправляем только в группу
        await context.bot.send_message(
            chat_id=NOTIFICATION_CHAT_ID,
            text=admin_message,
            parse_mode='Markdown'
        )
        
        # Подтверждение пользователю
        await update.message.reply_text(
            "✅ *Заявка принята!*\n\nМы получили ваши данные и скоро свяжемся с вами для подтверждения брони.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже или свяжитесь с администратором."
        )


async def handle_subscribe_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    is_subscribed = await check_subscription(context.bot, user_id)

    if is_subscribed:
        await handle_promo(update, context)
    else:
        keyboard = [
            [InlineKeyboardButton("Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("✅ Проверить подписку", callback_data="subscribe_check")],
            [InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await query.edit_message_text(
                text=NOT_SUBSCRIBED_MESSAGE.format(channel=CHANNEL_USERNAME),
                reply_markup=reply_markup
            )
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
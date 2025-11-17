from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from bot.config import CHANNEL_USERNAME, ADMIN_ID
from bot.constants import (
    MENU_MAIN,
    NOT_SUBSCRIBED_MESSAGE,
    PROMO_RECEIVED_MESSAGE,
    PROMO_ALREADY_RECEIVED_MESSAGE,
    NO_ACTIVE_PROMO_MESSAGE,
    HELP_USER_MESSAGE,
    HELP_ADMIN_MESSAGE
)
from bot.services.database import db
from bot.services.subscription import check_subscription
from bot.services.promo import promo_service
from bot.middleware.message_cleanup import message_cleanup


MAIN, PROMO, HELP = range(3)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    keyboard = [
        [
            InlineKeyboardButton("🎁 Получить промокод", callback_data=str(PROMO)),
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

    elif data == "subscribe_check":
        await handle_subscribe_check(update, context)


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

    can_receive, reason = await promo_service.can_receive_promo(user_id)

    if not can_receive:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if reason == "no_promo":
            await query.edit_message_text(
                text=NO_ACTIVE_PROMO_MESSAGE,
                reply_markup=reply_markup
            )
        elif reason == "already_received":
            current_promo = await promo_service.get_current_promo()
            await query.edit_message_text(
                text=PROMO_ALREADY_RECEIVED_MESSAGE.format(
                    next_available=current_promo["expiry_date"]
                ),
                reply_markup=reply_markup
            )
        return

    received_promo = await promo_service.give_promo_to_user(user_id)

    if received_promo:
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=str(MAIN))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=PROMO_RECEIVED_MESSAGE.format(
                code=received_promo["code"],
                expiry_date=received_promo["expiry_date"]
            ),
            reply_markup=reply_markup
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

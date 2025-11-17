from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from bot.config import CHANNEL_USERNAME, ADMIN_ID
from bot.constants import (
    WELCOME_MESSAGE,
    NOT_SUBSCRIBED_MESSAGE,
    PROMO_RECEIVED_MESSAGE,
    PROMO_ALREADY_RECEIVED_MESSAGE,
    NO_ACTIVE_PROMO_MESSAGE,
    HELP_USER_MESSAGE,
    HELP_ADMIN_MESSAGE,
    BROADCAST_STARTED_MESSAGE,
    BROADCAST_COMPLETED_MESSAGE,
    ADMIN_ONLY_MESSAGE
)
from bot.services.database import db
from bot.services.subscription import check_subscription
from bot.services.promo import promo_service
from bot.services.broadcast import broadcast_service


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    db.add_user(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username
    )

    keyboard = [
        [InlineKeyboardButton("Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        WELCOME_MESSAGE.format(channel=CHANNEL_USERNAME),
        reply_markup=reply_markup
    )


async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    is_subscribed = await check_subscription(context.bot, user_id)
    if not is_subscribed:
        keyboard = [
            [InlineKeyboardButton("Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            NOT_SUBSCRIBED_MESSAGE.format(channel=CHANNEL_USERNAME),
            reply_markup=reply_markup
        )
        return

    can_receive, reason = promo_service.can_receive_promo(user_id)

    if not can_receive:
        if reason == "no_promo":
            await update.message.reply_text(NO_ACTIVE_PROMO_MESSAGE)
        elif reason == "already_received":
            current_promo = promo_service.get_current_promo()
            await update.message.reply_text(
                PROMO_ALREADY_RECEIVED_MESSAGE.format(
                    next_available=current_promo["expiry_date"]
                )
            )
        return

    received_promo = promo_service.give_promo_to_user(user_id)

    if received_promo:
        await update.message.reply_text(
            PROMO_RECEIVED_MESSAGE.format(
                code=received_promo["code"],
                expiry_date=received_promo["expiry_date"]
            )
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        await update.message.reply_text(HELP_ADMIN_MESSAGE)
    else:
        await update.message.reply_text(HELP_USER_MESSAGE)


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(ADMIN_ONLY_MESSAGE)
        return

    if not context.args:
        await update.message.reply_text("Использование: /broadcast <текст сообщения>")
        return

    message = " ".join(context.args)
    users_count = db.get_users_count()

    await update.message.reply_text(
        BROADCAST_STARTED_MESSAGE.format(count=users_count)
    )

    result = await broadcast_service.send_broadcast(context.bot, message)

    await update.message.reply_text(
        BROADCAST_COMPLETED_MESSAGE.format(
            sent=result["sent"],
            failed=result["failed"]
        )
    )

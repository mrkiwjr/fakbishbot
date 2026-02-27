from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ContextTypes
from telegram.error import BadRequest, TimedOut, NetworkError
import os
import logging
import asyncio

from bot.config import CHANNEL_USERNAME, ADMIN_ID, ADMIN_USERNAME, NOTIFICATION_CHAT_ID, MENU_PHOTOS
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
from bot.services.photo_cache import photo_cache
from bot.services.support_chat import support_chat
from bot.middleware.message_cleanup import message_cleanup

logger = logging.getLogger(__name__)

MAIN, PROMO, HELP, BOOK_PC, FEEDBACK, PROMOTIONS, TARIFFS = range(7)

# Константы для обработки таймаутов
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1.0


def escape_html(text: str) -> str:
    """Экранирует специальные символы HTML для безопасного отображения в Telegram"""
    if not text:
        return ''
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;'))


async def send_text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    edit: bool = False,
    photo_key: str = None
):
    if photo_key:
        photo_path = MENU_PHOTOS.get(photo_key)
        if photo_path and os.path.exists(photo_path):
            is_valid, _ = photo_cache.validate_photo(photo_path)
            if is_valid:
                try:
                    cached_file_id = photo_cache.get_file_id(photo_key, photo_path)
                    response = None

                    if cached_file_id:
                        # Попытка отправки с retry логикой
                        for attempt in range(MAX_RETRY_ATTEMPTS):
                            try:
                                response = await update.effective_chat.send_photo(
                                    photo=cached_file_id,
                                    caption=text,
                                    reply_markup=reply_markup
                                )
                                break
                            except (TimedOut, NetworkError) as e:
                                if attempt < MAX_RETRY_ATTEMPTS - 1:
                                    logger.warning(f"Таймаут при отправке фото (попытка {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                                    await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                                else:
                                    raise
                    else:
                        with open(photo_path, 'rb') as photo_file:
                            for attempt in range(MAX_RETRY_ATTEMPTS):
                                try:
                                    response = await update.effective_chat.send_photo(
                                        photo=InputFile(photo_file),
                                        caption=text,
                                        reply_markup=reply_markup
                                    )
                                    if response.photo:
                                        new_file_id = response.photo[-1].file_id
                                        photo_cache.save_file_id(photo_key, photo_path, new_file_id)
                                    break
                                except (TimedOut, NetworkError) as e:
                                    if attempt < MAX_RETRY_ATTEMPTS - 1:
                                        logger.warning(f"Таймаут при отправке фото через файл (попытка {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                                        await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                                        photo_file.seek(0)
                                    else:
                                        raise

                    if response:
                        await message_cleanup.track_bot_message(
                            update.effective_chat.id,
                            response.message_id,
                            context
                        )
                        return response
                except (TimedOut, NetworkError) as e:
                    logger.warning(f"Ошибка сети при отправке фото для {photo_key}: {e}")
                except Exception as e:
                    logger.warning(f"Ошибка отправки фото для {photo_key}: {e}")

    # Отправка текстового сообщения с retry логикой
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            response = await update.effective_chat.send_message(
                text=text,
                reply_markup=reply_markup
            )
            break
        except (TimedOut, NetworkError) as e:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                logger.warning(f"Таймаут при отправке текстового сообщения (попытка {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
            else:
                logger.error(f"Не удалось отправить текстовое сообщение после {MAX_RETRY_ATTEMPTS} попыток: {e}")
                raise

    await message_cleanup.track_bot_message(
        update.effective_chat.id,
        response.message_id,
        context
    )
    return response


async def send_menu_with_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    photo_key: str,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    edit: bool = False,
    parse_mode: str = None
):
    photo_path = MENU_PHOTOS.get(photo_key)

    async def send_text_fallback():
        """Отправка текстового сообщения с retry логикой при таймаутах"""
        last_error = None
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                response = await update.effective_chat.send_message(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                await message_cleanup.track_bot_message(
                    update.effective_chat.id,
                    response.message_id,
                    context
                )
                return response
            except (TimedOut, NetworkError) as e:
                last_error = e
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    logger.warning(f"Таймаут при отправке сообщения (попытка {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                    await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                else:
                    logger.error(f"Не удалось отправить сообщение после {MAX_RETRY_ATTEMPTS} попыток: {e}")
                    raise
        
        if last_error:
            raise last_error

    if not photo_path or not os.path.exists(photo_path):
        logger.debug(f"Фото для {photo_key} не найдено, отправка текстового меню")
        return await send_text_fallback()

    is_valid, error_msg = photo_cache.validate_photo(photo_path)
    if not is_valid:
        logger.warning(f"Фото {photo_key} не прошло валидацию: {error_msg}")
        return await send_text_fallback()

    try:
        cached_file_id = photo_cache.get_file_id(photo_key, photo_path)

        if cached_file_id:
            # Попытка отправки с кешированным file_id с retry логикой
            success = False
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    response = await update.effective_chat.send_photo(
                        photo=cached_file_id,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                    logger.debug(f"Отправлено фото {photo_key} через кешированный file_id")
                    success = True
                    break
                except (TimedOut, NetworkError) as e:
                    if attempt < MAX_RETRY_ATTEMPTS - 1:
                        logger.warning(f"Таймаут при отправке фото с file_id (попытка {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                        await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                    else:
                        logger.warning(f"Не удалось отправить фото с file_id после {MAX_RETRY_ATTEMPTS} попыток, пробуем через файл")
                        break
                except Exception as cache_error:
                    logger.warning(f"Ошибка использования кешированного file_id для {photo_key}: {cache_error}")
                    break
            
            # Если не удалось отправить с file_id, пробуем через файл
            if not success:
                try:
                    with open(photo_path, 'rb') as photo_file:
                        for attempt in range(MAX_RETRY_ATTEMPTS):
                            try:
                                response = await update.effective_chat.send_photo(
                                    photo=InputFile(photo_file),
                                    caption=text,
                                    reply_markup=reply_markup,
                                    parse_mode=parse_mode
                                )
                                if response.photo:
                                    new_file_id = response.photo[-1].file_id
                                    photo_cache.save_file_id(photo_key, photo_path, new_file_id)
                                success = True
                                break
                            except (TimedOut, NetworkError) as e:
                                if attempt < MAX_RETRY_ATTEMPTS - 1:
                                    logger.warning(f"Таймаут при отправке фото через файл (попытка {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                                    await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                                    photo_file.seek(0)
                                else:
                                    logger.error(f"Не удалось отправить фото через файл после {MAX_RETRY_ATTEMPTS} попыток")
                                    return await send_text_fallback()
                except Exception as e:
                    logger.error(f"Ошибка при отправке фото через файл: {e}")
                    return await send_text_fallback()
        else:
            # Отправка фото без кеша с retry логикой
            success = False
            with open(photo_path, 'rb') as photo_file:
                for attempt in range(MAX_RETRY_ATTEMPTS):
                    try:
                        response = await update.effective_chat.send_photo(
                            photo=InputFile(photo_file),
                            caption=text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode
                        )

                        if response.photo:
                            new_file_id = response.photo[-1].file_id
                            photo_cache.save_file_id(photo_key, photo_path, new_file_id)
                            logger.info(f"Отправлено и кешировано фото {photo_key}")
                        success = True
                        break
                    except (TimedOut, NetworkError) as e:
                        if attempt < MAX_RETRY_ATTEMPTS - 1:
                            logger.warning(f"Таймаут при отправке фото (попытка {attempt + 1}/{MAX_RETRY_ATTEMPTS}): {e}")
                            await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                            photo_file.seek(0)
                        else:
                            logger.error(f"Не удалось отправить фото после {MAX_RETRY_ATTEMPTS} попыток: {e}")
                            return await send_text_fallback()

        if success:
            await message_cleanup.track_bot_message(
                update.effective_chat.id,
                response.message_id,
                context
            )
            return response
        else:
            return await send_text_fallback()

    except BadRequest as e:
        error_message = str(e).lower()
        if "image_process_failed" in error_message:
            logger.warning(f"Telegram не смог обработать изображение {photo_key}, отправка текстового меню")
        else:
            logger.error(f"Ошибка BadRequest при отправке меню с фото {photo_key}: {e}")
        return await send_text_fallback()

    except (TimedOut, NetworkError) as e:
        logger.error(f"Ошибка сети/таймаут при отправке меню с фото {photo_key}: {e}")
        return await send_text_fallback()

    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке меню с фото {photo_key}: {e}")
        return await send_text_fallback()


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    keyboard = [
        [
            InlineKeyboardButton("🎁 Промокод", callback_data=str(PROMO)),
            InlineKeyboardButton("💻 Бронь", callback_data=str(BOOK_PC))
        ],
        [
            InlineKeyboardButton("💰 Акции", callback_data=str(PROMOTIONS)),
            InlineKeyboardButton("📊 Тарифы", callback_data=str(TARIFFS))
        ],
        [
            InlineKeyboardButton("📝 Отзыв", callback_data=str(FEEDBACK)),
            InlineKeyboardButton("❓ Помощь", callback_data=str(HELP))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_menu_with_photo(update, context, "main", MENU_MAIN, reply_markup, edit=edit)


async def menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await db.add_user(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username
    )

    await message_cleanup.cleanup_user_command(update, context)

    keyboard = [
        [
            InlineKeyboardButton("🎁 Промокод", callback_data=str(PROMO)),
            InlineKeyboardButton("💻 Бронь", callback_data=str(BOOK_PC))
        ],
        [
            InlineKeyboardButton("💰 Акции", callback_data=str(PROMOTIONS)),
            InlineKeyboardButton("📊 Тарифы", callback_data=str(TARIFFS))
        ],
        [
            InlineKeyboardButton("📝 Отзыв", callback_data=str(FEEDBACK)),
            InlineKeyboardButton("❓ Помощь", callback_data=str(HELP))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_menu_with_photo(update, context, "main", MENU_MAIN, reply_markup)


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
        # Сбрасываем все режимы ввода при возврате в главное меню
        context.user_data.pop('booking_mode', None)
        context.user_data.pop('feedback_mode', None)
        context.user_data.pop('winter_drop_mode', None)
        await show_main_menu(update, context, edit=True)

    elif data == str(PROMO):
        await handle_promo(update, context)

    elif data == str(HELP):
        await handle_help(update, context)

    elif data == str(BOOK_PC):
        await handle_book_pc(update, context)

    elif data == str(FEEDBACK):
        # Сбрасываем режим отзыва при возврате в раздел отзывов
        context.user_data.pop('feedback_mode', None)
        await handle_feedback(update, context)

    elif data == str(PROMOTIONS):
        # Сбрасываем режим WINTER DROP при возврате в раздел акций
        context.user_data.pop('winter_drop_mode', None)
        await handle_promotions(update, context)

    elif data == str(TARIFFS):
        await handle_tariffs(update, context)

    elif data == "subscribe_check":
        await handle_subscribe_check(update, context)

    elif data == "leave_feedback":
        await handle_leave_feedback(update, context)

    elif data == "winter_drop":
        await handle_winter_drop(update, context)

    elif data == "contact_admin":
        await handle_contact_admin(update, context)

    elif data == "end_admin_chat":
        # Выходим из режима чата с админом и возвращаемся в раздел помощи
        context.user_data.pop('admin_chat_mode', None)
        await handle_help(update, context)

    elif data.startswith("support_accept:"):
        # Админ принял чат с пользователем
        try:
            user_id = int(data.split(":", 1)[1])
        except ValueError:
            return

        support_chat.start(user_id=user_id, admin_id=update.effective_user.id)

        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "*Диалог начат.*\n\n"
                    "Администратор подключился к обращению.\n"
                    "Вы можете продолжать переписку в этом диалоге."
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Не удалось уведомить пользователя о начале диалога: {e}")

        # Обновляем сообщение у админа
        keyboard = [[InlineKeyboardButton("Завершить чат", callback_data=f"support_end:{user_id}")]]
        await update.callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("support_reject:"):
        # Админ отклонил запрос
        try:
            user_id = int(data.split(":", 1)[1])
        except ValueError:
            return

        support_chat.end(user_id=user_id)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "Обращение получено, но в настоящий момент администратор недоступен.\n"
                    "Пожалуйста, повторите попытку позже."
                ),
            )
        except Exception:
            pass

        await update.callback_query.edit_message_reply_markup(reply_markup=None)

    elif data.startswith("support_end:"):
        # Завершение чата
        try:
            user_id = int(data.split(":", 1)[1])
        except ValueError:
            return

        support_chat.end(user_id=user_id)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "*Диалог завершён.*\n\n"
                    "При необходимости вы можете снова воспользоваться функцией связи с администратором."
                ),
                parse_mode="Markdown",
            )
        except Exception:
            pass

        await update.callback_query.edit_message_reply_markup(reply_markup=None)


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

        await send_text_message(
            update,
            context,
            NOT_SUBSCRIBED_MESSAGE.format(channel=CHANNEL_USERNAME),
            reply_markup,
            edit=True,
            photo_key="promo"
        )
        return

    # ПРОВЕРЯЕМ используя существующий метод can_receive_promo
    can_receive, reason = await promo_service.can_receive_promo(user_id)
    
    if not can_receive:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if reason == "no_promo":
            await send_text_message(
                update,
                context,
                NO_ACTIVE_PROMO_MESSAGE,
                reply_markup,
                edit=True,
                photo_key="promo"
            )
        elif reason == "already_received":
            # Если уже получал - показываем его текущий промокод
            last_promo = await promo_service.get_last_received_promo(user_id)
            if last_promo:
                await send_text_message(
                    update,
                    context,
                    f"🎁 Ваш промокод:\n\n`{last_promo['code']}`\n\n"
                    f"📅 Действует до: {last_promo['expiry_date']}\n\n",
                    reply_markup,
                    edit=True,
                    photo_key="promo"
                )
            else:
                await send_text_message(
                    update,
                    context,
                    "Вы уже получили промокод на этой неделе.",
                    reply_markup,
                    edit=True,
                    photo_key="promo"
                )
        return

    # Если может получить - выдаем новый случайный промокод
    received_promo = await promo_service.get_random_active_promo()
    
    if received_promo:
        # Отмечаем что пользователь получил промокод
        await promo_service.mark_promo_received(user_id, received_promo["code"])
        
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data=str(MAIN))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await send_text_message(
            update,
            context,
            f"🎁 *Ваш промокод:*\n\n`{received_promo['code']}`\n\n"
            f"📅 *Действует до:* {received_promo['expiry_date']}\n\n"
            f"💡 *Сохраните этот промокод! Он будет доступен до конца недели*",
            reply_markup,
            edit=True,
            photo_key="promo"
        )
    else:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_text_message(
            update,
            context,
            "❌ *В данный момент нет доступных промокодов*\n\nПопробуйте позже или обратитесь к администратору",
            reply_markup,
            edit=True,
            photo_key="promo"
        )


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    # Для админа показываем админскую справку, но кнопка связи с админом есть для всех,
    # чтобы можно было тестировать функционал.
    if user_id == ADMIN_ID:
        text = HELP_ADMIN_MESSAGE
    else:
        text = HELP_USER_MESSAGE

    keyboard = [
        [InlineKeyboardButton("💬 Связаться с админом", callback_data="contact_admin")],
        [InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_menu_with_photo(update, context, "help", text, reply_markup, edit=True)


async def handle_contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включаем режим живого диалога с админом через бота."""
    query = update.callback_query
    user = update.effective_user

    # Включаем режим чата с админом и выключаем остальные режимы
    context.user_data['admin_chat_mode'] = True
    context.user_data.pop('booking_mode', None)
    context.user_data.pop('feedback_mode', None)
    context.user_data.pop('winter_drop_mode', None)

    keyboard = [[InlineKeyboardButton("Завершить диалог", callback_data="end_admin_chat")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=(
            "*Связь с администратором*\n\n"
            "Вы можете задать любой вопрос в свободной форме.\n"
            "Все ваши сообщения будут автоматически направлены администратору.\n\n"
            "Ответ администратора будет отправлен в этот диалог."
        ),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    # Уведомление администратору отправляем при первом сообщении клиента (будет кнопка "Начать чат")


async def handle_book_pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Включаем режим брони и выключаем другие режимы ввода текста
    context.user_data['booking_mode'] = True
    context.user_data.pop('feedback_mode', None)
    context.user_data.pop('winter_drop_mode', None)

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_menu_with_photo(update, context, "book_pc", BOOK_PC_MESSAGE, reply_markup, edit=True, parse_mode='Markdown')


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Выключаем другие режимы ввода текста
    context.user_data.pop('booking_mode', None)
    context.user_data.pop('winter_drop_mode', None)
    context.user_data.pop('feedback_mode', None)  # Сбрасываем режим отзыва

    keyboard = [
        [InlineKeyboardButton("💬 Оставить отзыв", callback_data="leave_feedback")],
        [InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_menu_with_photo(update, context, "feedback", FEEDBACK_MESSAGE, reply_markup, edit=True)


async def handle_leave_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса оставления отзыва - просим пользователя написать отзыв"""
    query = update.callback_query
    
    # Сохраняем состояние что пользователь оставляет отзыв,
    # и выключаем остальные режимы, если они были
    context.user_data['feedback_mode'] = True
    context.user_data.pop('booking_mode', None)
    context.user_data.pop('winter_drop_mode', None)
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=str(FEEDBACK))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="💬 *Введите ваш отзыв:*\n\nПожалуйста, напишите ваше мнение, предложение или замечание:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех текстовых сообщений"""
    user = update.effective_user
    message_text = update.message.text
    
    if update.message.chat.type != 'private':
        return

    # Если пользователь в режиме живого диалога с админом
    if context.user_data.get('admin_chat_mode'):
        try:
            username = f"@{user.username}" if user.username else "нет username"
            escaped_first_name = escape_html(user.first_name or "Не указано")
            escaped_username = escape_html(username)
            escaped_message = escape_html(message_text)

            # Если чат ещё не принят админом — шлём "запрос" с кнопкой "Начать чат"
            if not support_chat.is_active(user.id):
                if not support_chat.is_pending(user.id):
                    support_chat.set_pending(user.id)

                keyboard = [
                    [
                        InlineKeyboardButton("Начать чат", callback_data=f"support_accept:{user.id}"),
                        InlineKeyboardButton("Отклонить", callback_data=f"support_reject:{user.id}")
                    ]
                ]

                admin_message = (
                    "<b>Запрос на диалог</b>\n\n"
                    f"Идентификатор пользователя: <code>{user.id}</code>\n"
                    f"Имя: {escaped_first_name}\n"
                    f"Имя пользователя: {escaped_username}\n\n"
                    f"<b>Первичное сообщение:</b>\n{escaped_message}\n\n"
                    "Для начала переписки выберите действие ниже."
                )

                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_message,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

                await update.message.reply_text(
                    "Ваше обращение зарегистрировано.\n\n"
                    "После подключения администратора ответ будет направлен в этот диалог.",
                    parse_mode="Markdown",
                )
            else:
                # Чат активен — отправляем сообщение админу и даём кнопку завершить чат
                support_chat.set_admin_target(admin_id=ADMIN_ID, user_id=user.id)

                keyboard = [[InlineKeyboardButton("Завершить чат", callback_data=f"support_end:{user.id}")]]

                admin_message = (
                    "<b>Сообщение в активном диалоге</b>\n\n"
                    f"Идентификатор пользователя: <code>{user.id}</code>\n"
                    f"Имя: {escaped_first_name}\n"
                    f"Имя пользователя: {escaped_username}\n\n"
                    f"<b>Текст сообщения:</b>\n{escaped_message}"
                )

                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_message,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

                await update.message.reply_text(
                    "Ваше сообщение передано администратору.\n\n"
                    "Ответ будет направлен в этот диалог.",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения админу: {e}")
            await update.message.reply_text(
                "❌ Не удалось отправить сообщение администратору. Пожалуйста, попробуйте позже."
            )

        # В режиме чата с админом не переключаемся в другие режимы
        return

    # Проверяем, находится ли пользователь в режиме отзыва
    if context.user_data.get('feedback_mode'):
        # Убираем режим отзыва
        context.user_data.pop('feedback_mode', None)
        
        # Экранируем специальные символы HTML для безопасного отображения
        escaped_first_name = escape_html(user.first_name or 'Не указано')
        escaped_username = escape_html(f'@{user.username}' if user.username else 'нет username')
        escaped_feedback = escape_html(message_text)
        
        # Формируем сообщение для канала ОТЗЫВ с HTML разметкой
        admin_message = (
            f"💬 <b>НОВЫЙ ОТЗЫВ!</b>\n\n"
            f"<b>Пользователь:</b>\n"
            f"👤 {escaped_first_name}\n"
            f"📱 {escaped_username}\n"
            f"<b>Текст отзыва:</b>\n{escaped_feedback}\n\n"
        )
        
        try:
            # Отправляем отзыв в канал
            await context.bot.send_message(
                chat_id=NOTIFICATION_CHAT_ID,
                text=admin_message,
                parse_mode='HTML'
            )
            
            # Подтверждение пользователю
            await update.message.reply_text(
                "✅ *Спасибо за ваш отзыв!*\n\nВаши отзывы помогают нам становиться лучше! 🥷",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки отзыва: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при отправке отзыва. Пожалуйста, попробуйте позже."
            )
        
        # Возвращаем в главное меню
        await show_main_menu(update, context)

    else:
        # Проверяем, находится ли пользователь в режиме участия в KATANA WINTER DROP
        if context.user_data.get('winter_drop_mode'):
            # Убираем режим WINTER DROP
            context.user_data.pop('winter_drop_mode', None)

            # Экранируем специальные символы HTML для безопасного отображения
            escaped_first_name = escape_html(user.first_name or 'Не указано')
            escaped_username = escape_html(f'@{user.username}' if user.username else 'нет username')
            escaped_message = escape_html(message_text)
            
            # Формируем сообщение для канала с HTML разметкой
            admin_message = (
                f"🎯 <b>KATANA WINTER DROP!</b>\n\n"
                f"<b>Участник:</b>\n"
                f"👤 {escaped_first_name}\n"
                f"📱 {escaped_username}\n"
                f"<b>Данные участника:</b>\n<code>{escaped_message}</code>\n\n"
            )

            try:
                # Отправляем данные участника в канал
                await context.bot.send_message(
                    chat_id=NOTIFICATION_CHAT_ID,
                    text=admin_message,
                    parse_mode='HTML'
                )

                # Подтверждение пользователю
                await update.message.reply_text(
                    "✅ *Заявка на участие принята!*\n\nМы получили ваши данные и свяжемся с вами при необходимости.",
                    parse_mode='Markdown'
                )

            except Exception as e:
                logger.error(f"Ошибка отправки данных KATANA WINTER DROP: {e}")
                await update.message.reply_text(
                    "❌ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже."
                )

            # Возвращаем в главное меню
            await show_main_menu(update, context)

        # Если пользователь в режиме брони
        elif context.user_data.get('booking_mode'):
            # Убираем режим брони
            context.user_data.pop('booking_mode', None)

            # Экранируем специальные символы HTML для безопасного отображения
            escaped_first_name = escape_html(user.first_name or 'Не указано')
            escaped_username = escape_html(f'@{user.username}' if user.username else 'нет username')
            escaped_booking = escape_html(message_text)
            
            admin_message = (
                f"🎯 <b>НОВАЯ БРОНЬ!</b>\n\n"
                f"<b>Клиент:</b>\n"
                f"👤 {escaped_first_name}\n"
                f"📱 {escaped_username}\n"
                f"<b>Данные брони:</b>\n<code>{escaped_booking}</code>\n\n"
            )

            try:
                # Отправляем в канал
                await context.bot.send_message(
                    chat_id=NOTIFICATION_CHAT_ID,
                    text=admin_message,
                    parse_mode='HTML'
                )

                # Подтверждение пользователю
                await update.message.reply_text(
                    "✅ *Заявка принята!*\n\nМы получили ваши данные и скоро свяжемся с вами для подтверждения брони.",
                    parse_mode='Markdown'
                )

            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")
                await update.message.reply_text(
                    "❌ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже или свяжитесь с администратором."
                )

            # Возвращаем в главное меню
            await show_main_menu(update, context)

        else:
            # Если пользователь не в одном из специальных режимов,
            # просто показываем главное меню и ничего никуда не отправляем
            await show_main_menu(update, context)


async def handle_promotions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("❄️ KATANA WINTER DROP", callback_data="winter_drop")],
        [InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_menu_with_photo(update, context, "promotions", PROMOTIONS_MESSAGE, reply_markup, edit=True)


async def handle_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=str(MAIN))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_menu_with_photo(update, context, "tariffs", TARIFFS_MESSAGE, reply_markup, edit=True)


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
            await send_text_message(
                update,
                context,
                NOT_SUBSCRIBED_MESSAGE.format(channel=CHANNEL_USERNAME),
                reply_markup,
                edit=True,
                photo_key="promo"
            )
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise


async def handle_winter_drop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса участия в KATANA WINTER DROP — просим пользователя ввести данные"""
    query = update.callback_query

    # Сохраняем состояние, что пользователь заполняет данные для розыгрыша,
    # и выключаем остальные режимы
    context.user_data['winter_drop_mode'] = True
    context.user_data.pop('feedback_mode', None)
    context.user_data.pop('booking_mode', None)

    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data=str(PROMOTIONS))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=(
            "❄️ *KATANA WINTER DROP*\n\n"
            "Привет! Для участия в розыгрыше, пожалуйста укажи:\n"
            "• ФИО\n"
            "• Контактный номер телефона"
        ),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
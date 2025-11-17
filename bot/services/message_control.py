from typing import Optional
from telegram import Update, Bot
from telegram.ext import ContextTypes


class MessageControl:

    @staticmethod
    async def store_menu_message(context: ContextTypes.DEFAULT_TYPE, message_id: int, chat_id: int):
        context.user_data["menu_message_id"] = message_id
        context.user_data["menu_chat_id"] = chat_id

    @staticmethod
    async def get_menu_message(context: ContextTypes.DEFAULT_TYPE) -> Optional[tuple]:
        message_id = context.user_data.get("menu_message_id")
        chat_id = context.user_data.get("menu_chat_id")

        if message_id and chat_id:
            return (chat_id, message_id)
        return None

    @staticmethod
    async def delete_user_message(update: Update):
        try:
            if update.message:
                await update.message.delete()
        except Exception:
            pass

    @staticmethod
    async def safe_edit_message(
        bot: Bot,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup=None
    ):
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup
            )
            return True
        except Exception:
            return False

    @staticmethod
    async def cleanup_and_show_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        show_menu_func
    ):
        await MessageControl.delete_user_message(update)

        menu_data = await MessageControl.get_menu_message(context)
        if menu_data:
            chat_id, message_id = menu_data
            context.user_data["admin_message_id"] = message_id

        await show_menu_func(update, context, edit=True)


message_control = MessageControl()

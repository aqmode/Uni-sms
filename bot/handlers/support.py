import logging
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from config import ADMIN_ID

# In-memory store for active support chats. {user_id: admin_id}
# A proper implementation might use a database for this.
active_support_chats = {}

class SupportHandlers:
    def __init__(self):
        # Admin ID is crucial for this feature
        self.admin_id = int(ADMIN_ID)

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.initiate_support, filters.regex("^support$")),
            CallbackQueryHandler(self.close_support, filters.regex("^close_support$")),
            MessageHandler(self.user_to_admin_handler, filters.private & ~filters.command & ~filters.user(self.admin_id)),
            MessageHandler(self.admin_to_user_handler, filters.private & filters.user(self.admin_id) & filters.reply),
        ]

    async def initiate_support(self, client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        active_support_chats[user_id] = self.admin_id
        await callback_query.message.edit_text(
            "Вы вошли в чат с техподдержкой. Напишите ваше сообщение.\n"
            "Администратор ответит вам здесь, как только сможет.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Закрыть чат", callback_data="close_support")
            ]])
        )
        await callback_query.answer()

    async def close_support(self, client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        if user_id in active_support_chats:
            del active_support_chats[user_id]
        await callback_query.message.edit_text(
            "Чат с техподдержкой закрыт. Вы вернулись в главное меню.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")
            ]])
        )
        await callback_query.answer("Чат закрыт.")

    async def user_to_admin_handler(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id in active_support_chats:
            admin_id = active_support_chats[user_id]
            try:
                forwarded_message = await message.forward(admin_id)
                await client.send_message(
                    admin_id,
                    f"👆 Новое сообщение в техподдержку от пользователя ID: `{user_id}`. Ответьте на это сообщение, чтобы отправить ответ.",
                    reply_to_message_id=forwarded_message.id
                )
                await message.reply_text("Ваше сообщение было отправлено в техподдержку.")
            except Exception as e:
                logging.error(f"Не удалось переслать сообщение от {user_id} к {admin_id}: {e}")
                await message.reply_text("Извините, не удалось отправить ваше сообщение. Пожалуйста, попробуйте позже.")

    async def admin_to_user_handler(self, client: Client, message: Message):
        if message.reply_to_message and message.reply_to_message.forward_from:
            user_id = message.reply_to_message.forward_from.id
            if user_id in active_support_chats:
                try:
                    await client.send_message(user_id, f"**Ответ от техподдержки:**\n{message.text}")
                    await message.react("✅")
                except Exception as e:
                    logging.error(f"Не удалось отправить ответ администратора пользователю {user_id}: {e}")
                    await message.reply_text(f"Не удалось отправить сообщение пользователю {user_id}. Возможно, он заблокировал бота.")

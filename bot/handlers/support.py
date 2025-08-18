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
            "You are now connected to support. Please type your message.\n"
            "The admin will reply to you here as soon as possible.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Close Chat", callback_data="close_support")
            ]])
        )
        await callback_query.answer()

    async def close_support(self, client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        if user_id in active_support_chats:
            del active_support_chats[user_id]
        await callback_query.message.edit_text(
            "Support chat closed. You are now back to the main menu.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")
            ]])
        )
        await callback_query.answer("Chat closed.")

    async def user_to_admin_handler(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id in active_support_chats:
            admin_id = active_support_chats[user_id]
            try:
                # Forward the message to the admin
                forwarded_message = await message.forward(admin_id)
                # You can also send extra info
                await client.send_message(
                    admin_id,
                    f"👆 New support message from User ID: `{user_id}`. Reply to this message to respond.",
                    reply_to_message_id=forwarded_message.id
                )
                await message.reply_text("Your message has been sent to the support team.")
            except Exception as e:
                logging.error(f"Failed to forward support message from {user_id} to {admin_id}: {e}")
                await message.reply_text("Sorry, couldn't send your message. Please try again later.")

    async def admin_to_user_handler(self, client: Client, message: Message):
        # Check if the admin is replying to a message forwarded by the bot
        if message.reply_to_message and message.reply_to_message.forward_from:
            user_id = message.reply_to_message.forward_from.id
            if user_id in active_support_chats:
                try:
                    await client.send_message(user_id, f"**Support Reply:**\n{message.text}")
                    await message.react("✅")
                except Exception as e:
                    logging.error(f"Failed to send admin reply to {user_id}: {e}")
                    await message.reply_text(f"Could not send message to user {user_id}. They may have blocked the bot.")

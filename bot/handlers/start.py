from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from bot.keyboards.inline import main_menu_keyboard, account_menu_keyboard
from bot.db import Database

class StartHandlers:
    def __init__(self, db: Database):
        self.db = db

    def get_handlers(self):
        """Returns a list of handlers for registration."""
        return [
            MessageHandler(self.start_handler, filters.command("start")),
            CallbackQueryHandler(self.main_menu_callback_handler, filters.regex("^main_menu$")),
            CallbackQueryHandler(self.account_menu_callback_handler, filters.regex("^account_menu$")),
        ]

    async def start_handler(self, client: Client, message: Message):
        """Handles the /start command."""
        user = message.from_user

        referred_by = None
        if len(message.command) > 1:
            try:
                referred_by_id = int(message.command[1])
                # In a real app, you'd verify this ID exists and is valid
                referred_by = referred_by_id
            except (ValueError, IndexError):
                pass

        self.db.add_user(user.id, user.username, user.first_name, referred_by)

        welcome_text = f"Welcome to Uni SMS, {user.first_name}!\n\nYour one-stop bot for virtual numbers."
        await message.reply_text(welcome_text, reply_markup=main_menu_keyboard())

    async def main_menu_callback_handler(self, client: Client, callback_query: CallbackQuery):
        """Handles the 'Back to Main Menu' button."""
        await callback_query.answer()
        await callback_query.message.edit_text(
            "Main Menu:",
            reply_markup=main_menu_keyboard()
        )

    async def account_menu_callback_handler(self, client: Client, callback_query: CallbackQuery):
        """Handles the 'My Account' button."""
        await callback_query.answer()
        await callback_query.message.edit_text(
            "Account Menu:",
            reply_markup=account_menu_keyboard()
        )

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from bot.api import OnlineSimAPI
from bot.db import Database
from bot.keyboards.inline import account_menu_keyboard

class BalanceHandlers:
    def __init__(self, db: Database, api: OnlineSimAPI):
        self.db = db
        self.api = api

    def get_handlers(self):
        """Returns a list of handlers for registration."""
        return [
            MessageHandler(self.balance_command_handler, filters.command("balance")),
            CallbackQueryHandler(self.balance_callback_handler, filters.regex("^check_balance$")),
        ]

    async def get_balance_text(self, user_id: int):
        """Fetches and formats the user's internal balance text."""
        try:
            balance_kopecks = self.db.get_user_balance(user_id)
            # Convert from kopecks/cents to a float for display
            balance_rub = balance_kopecks / 100.0
            return f"Your current balance is: **{balance_rub:.2f} RUB**"
        except Exception as e:
            logging.error(f"Error fetching internal balance for user {user_id}: {e}")
            return "An error occurred while trying to fetch your balance."

    async def balance_command_handler(self, client: Client, message: Message):
        """Handles the /balance command."""
        balance_text = await self.get_balance_text(message.from_user.id)
        # The /balance command should probably just open the account menu
        await message.reply_text(
            "**Account Menu**\n\n" + balance_text,
            reply_markup=account_menu_keyboard()
        )

    async def balance_callback_handler(self, client: Client, callback_query: CallbackQuery):
        """Handles the 'Balance' button from the account menu."""
        await callback_query.answer("Fetching balance...", show_alert=False)
        balance_text = await self.get_balance_text(callback_query.from_user.id)
        await callback_query.message.edit_text(
            f"**Account Menu**\n\n{balance_text}",
            reply_markup=account_menu_keyboard()
        )

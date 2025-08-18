import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import CallbackQueryHandler
from bot.db import Database

class HistoryHandlers:
    def __init__(self, db: Database):
        self.db = db

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.history_menu_handler, filters.regex("^history_menu$")),
        ]

    async def history_menu_handler(self, client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        await callback_query.answer("Fetching your history...")

        try:
            purchase_history = self.db.get_purchase_history(user_id)
            rental_history = self.db.get_rental_history(user_id)

            history_text = "**Your Account History**\n\n"

            if not purchase_history and not rental_history:
                history_text += "You have no transaction history."
            else:
                if purchase_history:
                    history_text += "**Purchases (Last 5):**\n"
                    for p in purchase_history[:5]:
                        history_text += f"- Service: {p[0]}, Number: `{p[1]}` on {p[2]}\n"
                    history_text += "\n"

                if rental_history:
                    history_text += "**Rentals (Last 5):**\n"
                    for r in rental_history[:5]:
                        history_text += f"- Service: {r[0]}, Number: `{r[1]}` until {r[2]}\n"

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Account Menu", callback_data="account_menu")
            ]])

            await callback_query.message.edit_text(history_text, reply_markup=keyboard)

        except Exception as e:
            logging.error(f"Error fetching history for user {user_id}: {e}")
            await callback_query.message.edit_text("Could not retrieve your history. Please try again.")

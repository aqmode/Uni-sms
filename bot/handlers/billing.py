import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import CallbackQueryHandler

class BillingHandlers:
    def __init__(self):
        pass

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.top_up_balance_handler, filters.regex("^top_up_balance$")),
        ]

    async def top_up_balance_handler(self, client: Client, callback_query: CallbackQuery):
        await callback_query.answer()

        text = (
            "**Пополнение баланса**\n\n"
            "Для пополнения баланса, пожалуйста, свяжитесь с администратором через техподдержку.\n\n"
            "В будущем здесь будет интеграция с платежной системой."
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Назад в личный кабинет", callback_data="account_menu")
        ]])

        await callback_query.message.edit_text(text, reply_markup=keyboard)

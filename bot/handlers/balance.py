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
        """Получает и форматирует текст с внутренним балансом пользователя."""
        try:
            balance_kopecks = self.db.get_user_balance(user_id)
            balance_rub = balance_kopecks / 100.0
            return f"Ваш текущий баланс: **{balance_rub:.2f} RUB**"
        except Exception as e:
            logging.error(f"Ошибка получения внутреннего баланса для пользователя {user_id}: {e}")
            return "Произошла ошибка при получении вашего баланса."

    async def balance_command_handler(self, client: Client, message: Message):
        """Обрабатывает команду /balance."""
        balance_text = await self.get_balance_text(message.from_user.id)
        await message.reply_text(
            "**Личный кабинет**\n\n" + balance_text,
            reply_markup=account_menu_keyboard()
        )

    async def balance_callback_handler(self, client: Client, callback_query: CallbackQuery):
        """Обрабатывает кнопку 'Баланс' из меню кабинета."""
        await callback_query.answer("Загрузка баланса...", show_alert=False)
        balance_text = await self.get_balance_text(callback_query.from_user.id)
        await callback_query.message.edit_text(
            f"**Личный кабинет**\n\n{balance_text}",
            reply_markup=account_menu_keyboard()
        )

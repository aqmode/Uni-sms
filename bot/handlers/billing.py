import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from bot.keyboards.inline import account_menu_keyboard

async def top_up_balance_handler(callback_query: types.CallbackQuery):
    await callback_query.answer()

    text = (
        "**Пополнение баланса**\n\n"
        "Для пополнения баланса, пожалуйста, свяжитесь с администратором через техподдержку.\n\n"
        "В будущем здесь будет интеграция с платежной системой."
    )

    # In aiogram, we need to answer the callback query before editing
    await callback_query.message.edit_text(text, reply_markup=account_menu_keyboard())

def register_billing_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(top_up_balance_handler, Text(equals="top_up_balance"))

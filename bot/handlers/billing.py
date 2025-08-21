import logging
from aiogram import F, Router, types
from bot.keyboards.inline import account_menu_keyboard

router = Router()

@router.callback_query(F.data == "top_up_balance")
async def top_up_balance_handler(callback_query: types.CallbackQuery):
    """
    Handles the 'Top Up Balance' button.
    Currently, this is a placeholder.
    """
    await callback_query.answer()

    text = (
        "**Пополнение баланса**\n\n"
        "Для пополнения баланса, пожалуйста, свяжитесь с администратором через техподдержку.\n\n"
        "В будущем здесь будет интеграция с платежной системой."
    )

    # In aiogram, we need to answer the callback query before sending a new message or editing.
    await callback_query.message.edit_text(text, reply_markup=account_menu_keyboard())

import logging
from aiogram import F, Router, types
from aiogram.filters import Command
from bot.api import SmsActivateWrapper
from bot.db import Database
from bot.keyboards.inline import account_menu_keyboard
from .admin import AdminFilter # Import the shared admin filter

router = Router()

# --- Helper Function ---

async def get_balance_text(user_id: int, db: Database) -> str:
    """Gets and formats the user's internal balance text."""
    try:
        balance_kopecks = db.get_user_balance(user_id)
        balance_rub = balance_kopecks / 100.0
        return f"Ваш текущий баланс: **{balance_rub:.2f} RUB**"
    except Exception as e:
        logging.error(f"Ошибка получения внутреннего баланса для пользователя {user_id}: {e}")
        return "Произошла ошибка при получении вашего баланса."

# --- User Handlers ---

@router.message(Command("balance"))
async def balance_command_handler(message: types.Message, db: Database):
    """Handles the /balance command."""
    balance_text = await get_balance_text(message.from_user.id, db)
    # The original code sent a new message. Let's stick to that.
    await message.answer(
        "**Личный кабинет**\n\n" + balance_text,
        reply_markup=account_menu_keyboard()
    )

@router.callback_query(F.data == "check_balance")
async def balance_callback_handler(callback_query: types.CallbackQuery, db: Database):
    """Handles the 'Balance' button from the account menu."""
    await callback_query.answer("Загрузка баланса...", show_alert=False)
    balance_text = await get_balance_text(callback_query.from_user.id, db)
    # Using edit_text to update the existing message
    await callback_query.message.edit_text(
        f"**Личный кабинет**\n\n{balance_text}",
        reply_markup=account_menu_keyboard()
    )

# --- Admin Handler ---

@router.message(Command("service_balance"), AdminFilter())
async def service_balance_handler(message: types.Message, api: SmsActivateWrapper):
    """Handles the /service_balance command for the admin."""
    await message.answer("Запрашиваю баланс сервиса...")
    try:
        # Assuming api.get_balance() is an async function
        response = await api.get_balance()
        if isinstance(response, dict) and 'balance' in response:
            balance = response['balance']
            await message.answer(f"Баланс на sms-activate.ru: **{balance}**")
        else:
            # The original code used f-string formatting on the response directly
            await message.answer(f"Не удалось получить баланс сервиса. Ответ: `{response}`")
    except Exception as e:
        await message.answer(f"Ошибка при запросе баланса сервиса: {e}")

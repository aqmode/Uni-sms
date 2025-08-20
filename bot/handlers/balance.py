import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from bot.api import SmsActivateWrapper
from bot.db import Database
from bot.keyboards.inline import account_menu_keyboard
from config import ADMIN_ID

# Admin Filter
class AdminFilter(types.BoundFilter):
    key = 'is_admin'
    def __init__(self, is_admin: bool):
        self.is_admin = is_admin
    async def check(self, message: types.Message):
        return message.from_user.id == int(ADMIN_ID)

# --- User Handlers ---

async def get_balance_text(user_id: int, db: Database):
    """Gets and formats the user's internal balance text."""
    try:
        balance_kopecks = db.get_user_balance(user_id)
        balance_rub = balance_kopecks / 100.0
        return f"Ваш текущий баланс: **{balance_rub:.2f} RUB**"
    except Exception as e:
        logging.error(f"Ошибка получения внутреннего баланса для пользователя {user_id}: {e}")
        return "Произошла ошибка при получении вашего баланса."

async def balance_command_handler(message: types.Message, db: Database):
    """Handles the /balance command."""
    balance_text = await get_balance_text(message.from_user.id, db)
    await message.answer(
        "**Личный кабинет**\n\n" + balance_text,
        reply_markup=account_menu_keyboard()
    )

async def balance_callback_handler(callback_query: types.CallbackQuery, db: Database):
    """Handles the 'Balance' button from the account menu."""
    await callback_query.answer("Загрузка баланса...", show_alert=False)
    balance_text = await get_balance_text(callback_query.from_user.id, db)
    await callback_query.message.edit_text(
        f"**Личный кабинет**\n\n{balance_text}",
        reply_markup=account_menu_keyboard()
    )

# --- Admin Handler ---

async def service_balance_handler(message: types.Message, api: SmsActivateWrapper):
    """Handles the /service_balance command for the admin."""
    await message.answer("Запрашиваю баланс сервиса...")
    try:
        response = await api.get_balance()
        if isinstance(response, dict) and 'balance' in response:
            balance = response['balance']
            await message.answer(f"Баланс на sms-activate.ru: **{balance}**")
        else:
            await message.answer(f"Не удалось получить баланс сервиса. Ответ: `{response}`")
    except Exception as e:
        await message.answer(f"Ошибка при запросе баланса сервиса: {e}")

# --- Registration ---

def register_balance_handlers(dp: Dispatcher, db: Database, api: SmsActivateWrapper):
    dp.filters_factory.bind(AdminFilter)

    dp.register_message_handler(
        lambda msg: balance_command_handler(msg, db),
        commands=['balance']
    )
    dp.register_callback_query_handler(
        lambda cb: balance_callback_handler(cb, db),
        Text(equals="check_balance")
    )
    dp.register_message_handler(
        lambda msg: service_balance_handler(msg, api),
        commands=['service_balance'],
        is_admin=True
    )

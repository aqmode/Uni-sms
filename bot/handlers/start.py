from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from bot.keyboards.inline import main_menu_keyboard, account_menu_keyboard
from bot.db import Database
from config import IMAGE_MAIN_MENU, IMAGE_PROFILE

async def start_handler(message: types.Message, db: Database):
    """Handles the /start command."""
    user = message.from_user

    # Referral handling
    referred_by = None
    args = message.get_args()
    if args:
        try:
            referred_by_id = int(args)
            referred_by = referred_by_id
        except (ValueError, IndexError):
            pass

    db.add_user(user.id, user.username, user.first_name, referred_by)

    welcome_text = (
        f"Добро пожаловать в Uni SMS, {user.first_name}!\n\n"
        "Ваш универсальный бот для работы с виртуальными номерами. "
        "Используйте меню для навигации."
    )
    await message.answer_photo(
        photo=IMAGE_MAIN_MENU,
        caption=welcome_text,
        reply_markup=main_menu_keyboard()
    )

async def main_menu_callback_handler(callback_query: types.CallbackQuery):
    """Handles the 'Back to Main Menu' button."""
    await callback_query.answer()
    await callback_query.message.edit_media(
        media=types.InputMediaPhoto(media=IMAGE_MAIN_MENU, caption="Главное меню:"),
        reply_markup=main_menu_keyboard()
    )

async def account_menu_callback_handler(callback_query: types.CallbackQuery):
    """Handles the 'My Account' button."""
    await callback_query.answer()
    await callback_query.message.edit_media(
        media=types.InputMediaPhoto(media=IMAGE_PROFILE, caption="Личный кабинет:"),
        reply_markup=account_menu_keyboard()
    )

def register_start_handlers(dp: Dispatcher, db: Database):
    dp.register_message_handler(
        lambda msg: start_handler(msg, db),
        commands=['start']
    )
    dp.register_callback_query_handler(
        main_menu_callback_handler,
        Text(equals="main_menu")
    )
    dp.register_callback_query_handler(
        account_menu_callback_handler,
        Text(equals="account_menu")
    )

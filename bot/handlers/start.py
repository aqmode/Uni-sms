from aiogram import F, Router, types
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from bot.keyboards.inline import main_menu_keyboard, account_menu_keyboard
from bot.db import Database
from config import IMAGE_MAIN_MENU, IMAGE_PROFILE

router = Router()

@router.message(CommandStart())
async def start_handler(message: types.Message, db: Database, command: CommandObject):
    """Handles the /start command, including referral links."""
    user = message.from_user

    # Referral handling using CommandObject
    referred_by = None
    args = command.args
    if args:
        try:
            referred_by_id = int(args)
            referred_by = referred_by_id
        except (ValueError, IndexError):
            pass  # Invalid referral code

    db.add_user(user.id, user.username, user.first_name, referred_by)

    welcome_text = (
        f"Добро пожаловать в Uni SMS, {user.first_name}!\n\n"
        "Ваш универсальный бот для работы с виртуальными номерами. "
        "Используйте меню для навигации."
    )
    # Use answer_photo for sending a photo with a caption
    await message.answer_photo(
        photo=IMAGE_MAIN_MENU,
        caption=welcome_text,
        reply_markup=main_menu_keyboard()
    )

@router.callback_query(F.data == "main_menu")
async def main_menu_callback_handler(callback_query: types.CallbackQuery):
    """Handles the 'Back to Main Menu' button."""
    await callback_query.answer()
    await callback_query.message.edit_media(
        media=types.InputMediaPhoto(media=IMAGE_MAIN_MENU, caption="Главное меню:"),
        reply_markup=main_menu_keyboard()
    )

@router.callback_query(F.data == "account_menu")
async def account_menu_callback_handler(callback_query: types.CallbackQuery):
    """Handles the 'My Account' button."""
    await callback_query.answer()
    await callback_query.message.edit_media(
        media=types.InputMediaPhoto(media=IMAGE_PROFILE, caption="Личный кабинет:"),
        reply_markup=account_menu_keyboard()
    )

import logging
from aiogram import Router, types
from aiogram.filters import Command, Filter
from bot.db import Database
from config import ADMIN_ID

# Create a router for admin handlers
router = Router()

# Define a filter for the admin
class AdminFilter(Filter):
    """
    This filter checks if the message is from the admin.
    """
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == int(ADMIN_ID)

# Apply the router and filters to the handlers
@router.message(Command("credit"), AdminFilter())
async def credit_handler(message: types.Message, db: Database):
    """
    Manually credits a user's account.
    Usage: /credit <user_telegram_id> <amount_in_rub>
    """
    try:
        # In aiogram 3, command arguments are found in message.text
        args_str = message.text.split(maxsplit=2)[1] if len(message.text.split()) > 1 else ""
        args = args_str.split()

        if len(args) != 2:
            raise ValueError("Invalid number of arguments")

        user_id = int(args[0])
        amount_rub = float(args[1])
        amount_kopecks = int(amount_rub * 100)

        if amount_kopecks <= 0:
            await message.answer("Сумма должна быть положительной.")
            return

        success = db.create_transaction(
            user_telegram_id=user_id,
            amount=amount_kopecks,
            type='deposit',
            details=f"Ручное пополнение администратором {ADMIN_ID}"
        )

        if success:
            await message.answer(f"Баланс пользователя {user_id} успешно пополнен на {amount_rub:.2f} RUB.")
            try:
                await message.bot.send_message(
                    user_id,
                    f"Ваш баланс был пополнен на **{amount_rub:.2f} RUB**."
                )
            except Exception as e:
                await message.answer(f"Не удалось уведомить пользователя {user_id} (возможно, он заблокировал бота). Ошибка: {e}")
        else:
            await message.answer(f"Не удалось пополнить баланс пользователя {user_id}. Проверьте логи.")

    except (ValueError, IndexError):
        await message.answer("Неверный формат. Используйте: `/credit <user_id> <сумма>`")
    except Exception as e:
        logging.error(f"Ошибка в команде /credit: {e}")
        await message.answer(f"Произошла ошибка: {e}")


@router.message(Command("user_balance"), AdminFilter())
async def check_balance_handler(message: types.Message, db: Database):
    """
    Checks the balance of a specific user.
    Usage: /user_balance <user_telegram_id>
    """
    try:
        # In aiogram 3, command arguments are found in message.text
        args_str = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
        args = args_str.split()

        if len(args) != 1:
            raise ValueError("Invalid number of arguments")

        user_id = int(args[0])
        balance_kopecks = db.get_user_balance(user_id)
        balance_rub = balance_kopecks / 100.0

        await message.answer(f"Баланс пользователя `{user_id}`: **{balance_rub:.2f} RUB**.")

    except (ValueError, IndexError):
        await message.answer("Неверный формат. Используйте: `/user_balance <user_id>`")
    except Exception as e:
        logging.error(f"Ошибка в команде /user_balance: {e}")
        await message.answer(f"Произошла ошибка: {e}")

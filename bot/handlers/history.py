import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from bot.db import Database
from bot.keyboards.inline import account_menu_keyboard

async def history_menu_handler(callback_query: types.CallbackQuery, db: Database):
    user_id = callback_query.from_user.id
    await callback_query.answer("Загружаю историю...")

    try:
        purchase_history = db.get_purchase_history(user_id)
        # For now, I will omit the rental history since the feature is disabled
        # rental_history = db.get_rental_history(user_id)

        history_text = "**История ваших операций**\n\n"

        if not purchase_history: # and not rental_history:
            history_text += "У вас еще нет истории транзакций."
        else:
            if purchase_history:
                history_text += "**Последние 5 покупок:**\n"
                for p in purchase_history[:5]:
                    # Assuming p = (service, phone_number, created_at)
                    history_text += f"- Сервис: {p[0]}, Номер: `{p[1]}` от {p[2]}\n"
                history_text += "\n"

            # if rental_history:
            #     history_text += "**Последние 5 аренд:**\n"
            #     for r in rental_history[:5]:
            #         history_text += f"- Сервис: {r[0]}, Номер: `{r[1]}` до {r[2]}\n"

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в личный кабинет", callback_data="account_menu")
        ]])

        # In aiogram, we need to answer the callback query before editing
        await callback_query.message.edit_text(history_text, reply_markup=keyboard)

    except Exception as e:
        logging.error(f"Ошибка при получении истории для пользователя {user_id}: {e}")
        await callback_query.message.edit_text("Не удалось получить вашу историю. Попробуйте снова.")

def register_history_handlers(dp: Dispatcher, db: Database):
    # We need to pass the db instance to the handler. We can do this with a lambda.
    dp.register_callback_query_handler(
        lambda c: history_menu_handler(c, db),
        Text(equals="history_menu")
    )

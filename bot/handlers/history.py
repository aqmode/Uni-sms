import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import CallbackQueryHandler
from bot.db import Database

class HistoryHandlers:
    def __init__(self, db: Database):
        self.db = db

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.history_menu_handler, filters.regex("^history_menu$")),
        ]

    async def history_menu_handler(self, client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        await callback_query.answer("Загружаю историю...")

        try:
            purchase_history = self.db.get_purchase_history(user_id)
            rental_history = self.db.get_rental_history(user_id)

            history_text = "**История ваших операций**\n\n"

            if not purchase_history and not rental_history:
                history_text += "У вас еще нет истории транзакций."
            else:
                if purchase_history:
                    history_text += "**Последние 5 покупок:**\n"
                    for p in purchase_history[:5]:
                        history_text += f"- Сервис: {p[0]}, Номер: `{p[1]}` от {p[2]}\n"
                    history_text += "\n"

                if rental_history:
                    history_text += "**Последние 5 аренд:**\n"
                    for r in rental_history[:5]:
                        history_text += f"- Сервис: {r[0]}, Номер: `{r[1]}` до {r[2]}\n"

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад в личный кабинет", callback_data="account_menu")
            ]])

            await callback_query.message.edit_text(history_text, reply_markup=keyboard)

        except Exception as e:
            logging.error(f"Ошибка при получении истории для пользователя {user_id}: {e}")
            await callback_query.message.edit_text("Не удалось получить вашу историю. Попробуйте снова.")

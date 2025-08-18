import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import CallbackQueryHandler
from bot.api import OnlineSimAPI
from bot.utils import create_paginated_keyboard

free_numbers_cache = {}

class FreeNumbersHandlers:
    def __init__(self, api: OnlineSimAPI):
        self.api = api

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.show_free_countries, filters.regex("^free_numbers_menu$")),
            CallbackQueryHandler(self.show_free_numbers, filters.regex(r"^free_country:(\d+)$")),
            CallbackQueryHandler(self.show_free_sms, filters.regex(r"^free_number:(.+)$")),
        ]

    async def _get_free_list(self):
        if not free_numbers_cache:
            logging.info("Fetching free numbers list from API...")
            data = await self.api.get_free_list()
            if data.get("response") == "1":
                free_numbers_cache['countries'] = data['countries']
            else:
                raise Exception("Could not fetch free numbers list.")
        return free_numbers_cache

    async def show_free_countries(self, client: Client, callback_query: CallbackQuery):
        await callback_query.answer("Загружаю страны с бесплатными номерами...")
        try:
            data = await self._get_free_list()
            buttons = [(c['country_text'], f"free_country:{c['country']}") for c in data['countries']]
            keyboard = create_paginated_keyboard(buttons, 0, 15, "free_country_page")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
            await callback_query.message.edit_text("Выберите страну, чтобы увидеть бесплатные номера:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отображении бесплатных стран: {e}")
            await callback_query.message.edit_text("Не удалось загрузить бесплатные номера. Попробуйте позже.")

    async def show_free_numbers(self, client: Client, callback_query: CallbackQuery):
        country_id = int(callback_query.matches[0].group(1))
        await callback_query.answer("Загружаю номера...")
        try:
            data = await self._get_free_list()
            country_data = next((c for c in data['countries'] if c['country'] == country_id), None)
            if not country_data or not country_data.get('numbers'):
                await callback_query.message.edit_text("Не найдено бесплатных номеров для этой страны.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к странам", callback_data="free_numbers_menu")]]))
                return

            buttons = [(n['full_number'], f"free_number:{n['full_number']}") for n in country_data['numbers']]
            keyboard = create_paginated_keyboard(buttons, 0, 10, "free_number_page")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад к странам", callback_data="free_numbers_menu")])
            await callback_query.message.edit_text("Выберите номер для просмотра СМС:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отображении бесплатных номеров: {e}")
            await callback_query.message.edit_text("Произошла ошибка.")

    async def show_free_sms(self, client: Client, callback_query: CallbackQuery):
        number = callback_query.matches[0].group(1)
        await callback_query.answer("Загружаю СМС...")
        try:
            data = await self._get_free_list()
            sms_text = "Для этого номера не найдено СМС."
            for country in data['countries']:
                for num_data in country.get('numbers', []):
                    if num_data['full_number'] == number:
                        messages = num_data.get('messages', [])
                        if messages:
                            sms_text = f"**Последние 5 СМС для {number}:**\n\n" + "\n".join([
                                f"- `{msg['text']}` ({msg['in_date']})" for msg in messages[:5]
                            ])
                        break
                else:
                    continue
                break

            await callback_query.message.edit_text(sms_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к странам", callback_data="free_numbers_menu")]]))
        except Exception as e:
            logging.error(f"Ошибка при отображении бесплатных СМС: {e}")
            await callback_query.message.edit_text("Произошла ошибка.")

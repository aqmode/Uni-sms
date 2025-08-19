import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import CallbackQueryHandler
from bot.api import SmsActivateAPI
from bot.db import Database
from bot.utils import create_paginated_keyboard

# This will hold the full list of countries and services to avoid re-fetching
# during a single user session. It's a simple cache.
COUNTRY_LIST = []
SERVICE_LIST = {} # We will store services by country ID

class BuyNumberHandlers:
    def __init__(self, db: Database, api: SmsActivateAPI):
        self.db = db
        self.api = api

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.show_countries, filters.regex("^buy_menu$")),
            CallbackQueryHandler(self.show_countries_paginated, filters.regex(r"^buy_country_page:(\d+)$")),
            CallbackQueryHandler(self.show_services, filters.regex(r"^buy_country:(\d+)$")),
            CallbackQueryHandler(self.purchase_number, filters.regex(r"^buy_service:(.+):(\d+)$")),
        ]

    async def show_countries(self, client: Client, callback_query: CallbackQuery, page=0):
        await callback_query.answer("Загрузка стран...")
        try:
            # Fetch countries if the cache is empty
            if not COUNTRY_LIST:
                countries_data = await self.api._request("getCountries") # Assuming this endpoint exists as per docs
                # The provided doc has a strange format, let's assume it's a dict of dicts
                # {'0': {'id': 0, 'rus': 'Россия', ...}}
                if isinstance(countries_data, dict):
                    # Sort by the Russian name
                    COUNTRY_LIST.extend(sorted(countries_data.values(), key=lambda x: x['rus']))
                else:
                    raise Exception("Unexpected country list format")

            buttons = [(f"{c['rus']}", f"buy_country:{c['id']}") for c in COUNTRY_LIST]
            keyboard = create_paginated_keyboard(buttons, page, 15, "buy_country_page")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
            await callback_query.message.edit_text("Пожалуйста, выберите страну:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отображении стран: {e}")
            await callback_query.message.edit_text("Не удалось загрузить список стран. Попробуйте позже.")

    async def show_countries_paginated(self, client: Client, callback_query: CallbackQuery):
        page = int(callback_query.matches[0].group(1))
        await self.show_countries(client, callback_query, page=page)

    async def show_services(self, client: Client, callback_query: CallbackQuery, page=0):
        country_id = int(callback_query.matches[0].group(1))
        await callback_query.answer("Загрузка сервисов...")
        try:
            # Use getPrices to get available services and their cost for a country
            prices_data = await self.api.get_prices(country=country_id)
            country_prices = prices_data.get(str(country_id), {})

            if not country_prices:
                await callback_query.message.edit_text("Для этой страны нет доступных сервисов.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к странам", callback_data="buy_menu")]]))
                return

            buttons = [(f"{service} - {details['cost']} RUB ({details['count']} шт.)", f"buy_service:{service}:{country_id}") for service, details in country_prices.items()]
            keyboard = create_paginated_keyboard(buttons, page, 15, f"buy_service_page:{country_id}")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад к странам", callback_data="buy_menu")])
            await callback_query.message.edit_text("Пожалуйста, выберите сервис:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отображении сервисов: {e}")
            await callback_query.message.edit_text("Не удалось загрузить список сервисов.")

    async def purchase_number(self, client: Client, callback_query: CallbackQuery):
        service_code = callback_query.matches[0].group(1)
        country_id = int(callback_query.matches[0].group(2))
        user_id = callback_query.from_user.id

        await callback_query.message.edit_text("⏳ Обработка покупки...")
        try:
            prices_data = await self.api.get_prices(country=country_id, service=service_code)
            cost_rub = float(prices_data[str(country_id)][service_code]['cost'])
            cost_kopecks = int(cost_rub * 100)
        except Exception as e:
            logging.error(f"Не удалось определить стоимость: {e}")
            await callback_query.message.edit_text("Ошибка при проверке цены.")
            return

        if not self.db.create_transaction(user_id, -cost_kopecks, 'purchase', f"Покупка {service_code}"):
            await callback_query.message.edit_text("❌ Покупка не удалась! Недостаточно средств на внутреннем балансе.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 Мой кабинет", callback_data="account_menu")]]))
            return

        try:
            purchase_response = await self.api.get_number(service_code, country_id)
            # Response format is ACCESS_NUMBER:ID:NUMBER
            if "ACCESS_NUMBER" in purchase_response:
                parts = purchase_response.split(':')
                activation_id = int(parts[1])
                phone_number = parts[2]

                self.db.log_purchase(user_id, activation_id, service_code, str(country_id), phone_number)

                await callback_query.message.edit_text(f"✅ **Номер получен!**\n\n**Номер:** `{phone_number}`\n**Сервис:** {service_code}\n\nОжидаю СМС...")
                asyncio.create_task(self.poll_for_sms(callback_query, activation_id))
            else:
                logging.error(f"Ошибка API при покупке: {purchase_response}. Возврат средств.")
                self.db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат из-за ошибки: {purchase_response}")
                await callback_query.message.edit_text(f"❌ **Ошибка покупки!**\nПричина: `{purchase_response}`\n\nСредства возвращены на ваш баланс.")
        except Exception as e:
            logging.error(f"Критическая ошибка при покупке: {e}. Возврат средств.")
            self.db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат из-за непредвиденной ошибки: {e}")
            await callback_query.message.edit_text("Произошла непредвиденная ошибка. Средства возвращены.")

    async def poll_for_sms(self, callback_query: CallbackQuery, activation_id: int):
        max_wait_time = 600  # 10 minutes
        poll_interval = 10
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

            try:
                status_response = await self.api.get_status(activation_id)
                # Format: STATUS_WAIT_CODE, STATUS_OK:CODE, etc.
                if "STATUS_OK" in status_response:
                    sms_code = status_response.split(':')[1]
                    await callback_query.message.reply_text(f"✉️ **Получено СМС!**\n\nКод: `{sms_code}`")
                    await self.api.set_status(activation_id, 6) # Finish activation
                    return
                elif "STATUS_WAIT_RETRY" in status_response:
                    # You could add a button here to ask the user if they want to get another SMS
                    pass # Just continue polling for now
                elif "STATUS_CANCEL" in status_response:
                    await callback_query.message.reply_text("❌ Активация была отменена.")
                    return
            except Exception as e:
                logging.error(f"Ошибка при проверке СМС (ID: {activation_id}): {e}")

        await callback_query.message.reply_text("Ожидание СМС завершено (10 минут).")
        await self.api.set_status(activation_id, 8) # Cancel activation after timeout

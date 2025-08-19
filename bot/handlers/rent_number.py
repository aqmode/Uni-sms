import logging
import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import CallbackQueryHandler
from bot.api import SmsActivateWrapper
from bot.db import Database
from bot.utils import create_paginated_keyboard

# Simple cache for the rent tariffs
RENT_TARIFFS_CACHE = {}

class RentNumberHandlers:
    def __init__(self, db: Database, api: SmsActivateWrapper):
        self.db = db
        self.api = api

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.show_rent_countries, filters.regex("^rent_menu$")),
            CallbackQueryHandler(self.show_rent_countries_paginated, filters.regex(r"^rent_country_page:(\d+)$")),
            CallbackQueryHandler(self.show_rent_services, filters.regex(r"^rent_country:(\d+)$")),
            CallbackQueryHandler(self.rent_number, filters.regex(r"^rent_service:(\d+):(.+)$")),
            CallbackQueryHandler(self.manage_rental, filters.regex(r"^manage_rent:(\d+)$")),
            CallbackQueryHandler(self.extend_rental, filters.regex(r"^extend_rent:(\d+)$")),
            CallbackQueryHandler(self.view_rental_sms, filters.regex(r"^view_rent_sms:(\d+)$")),
            CallbackQueryHandler(self.close_rental, filters.regex(r"^close_rent:(\d+)$")),
        ]

    async def _get_rent_tariffs(self):
        if not RENT_TARIFFS_CACHE:
            logging.info("Загрузка тарифов на аренду с API...")
            tariffs = await self.api.get_rent_services_and_countries()
            if isinstance(tariffs, dict):
                RENT_TARIFFS_CACHE.update(tariffs)
            else:
                raise Exception(f"Не удалось загрузить тарифы на аренду: {tariffs}")
        return RENT_TARIFFS_CACHE

    async def show_rent_countries(self, client: Client, callback_query: CallbackQuery, page=0):
        await callback_query.answer("Загрузка стран для аренды...")
        try:
            tariffs = await self._get_rent_tariffs()
            # The API returns a dict of country IDs to country names
            countries = tariffs.get("countries", {})
            buttons = [(name, f"rent_country:{id}") for id, name in countries.items()]

            keyboard = create_paginated_keyboard(buttons, page, 15, "rent_country_page")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
            await callback_query.message.edit_text("Выберите страну для аренды:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отображении стран для аренды: {e}")
            await callback_query.message.edit_text("Произошла ошибка при загрузке стран для аренды.")

    async def show_rent_countries_paginated(self, client: Client, callback_query: CallbackQuery):
        page = int(callback_query.matches[0].group(1))
        await self.show_rent_countries(client, callback_query, page=page)

    async def show_rent_services(self, client: Client, callback_query: CallbackQuery):
        country_id = int(callback_query.matches[0].group(1))
        await callback_query.answer("Загрузка сервисов...")
        try:
            tariffs = await self._get_rent_tariffs()
            all_services = tariffs.get("services", {})
            # This API is complex. We'll show all services and assume they are available for the selected country.
            # A more robust solution would cross-reference with another endpoint if available.
            buttons = [(f"{details['search_name']} - {details['cost']} RUB/4ч", f"rent_service:{country_id}:{service_code}") for service_code, details in all_services.items()]

            keyboard = create_paginated_keyboard(buttons, 0, 10, f"rent_service_page:{country_id}")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад к странам", callback_data="rent_menu")])
            await callback_query.message.edit_text("Выберите сервис для аренды (цена за 4 часа):", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отображении сервисов для аренды: {e}")
            await callback_query.message.edit_text("Произошла ошибка при загрузке сервисов.")

    async def rent_number(self, client: Client, callback_query: CallbackQuery):
        country_id = int(callback_query.matches[0].group(1))
        service_code = callback_query.matches[0].group(2)
        user_id = callback_query.from_user.id
        rent_time = 4 # Default 4 hours

        await callback_query.message.edit_text("⏳ Обработка аренды...")
        try:
            tariffs = await self._get_rent_tariffs()
            cost_rub = float(tariffs["services"][service_code]['cost'])
            cost_kopecks = int(cost_rub * 100)
        except Exception as e:
            logging.error(f"Не удалось получить цену аренды: {e}")
            await callback_query.message.edit_text("Не удалось определить цену.")
            return

        if not self.db.create_transaction(user_id, -cost_kopecks, 'rental', f"Аренда {service_code}"):
            await callback_query.message.edit_text("❌ **Аренда не удалась!**\nНедостаточно средств.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 Мой кабинет", callback_data="account_menu")]]))
            return

        try:
            rental_data = await self.api.get_rent_number(service_code, country_id, rent_time)
            if rental_data.get("status") == "success":
                phone_info = rental_data["phone"]
                activation_id = phone_info["id"]
                self.db.log_rental(user_id, activation_id, service_code, str(country_id), phone_info["number"], phone_info["endDate"])
                await callback_query.message.edit_text(f"✅ **Аренда успешна!**\n\n**Номер:** `{phone_info['number']}`\n**Истекает:** {phone_info['endDate']}", reply_markup=self.get_rental_management_keyboard(activation_id))
            else:
                self.db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат из-за ошибки аренды: {rental_data}")
                await callback_query.message.edit_text(f"❌ **Аренда не удалась!**\nПричина: `{rental_data}`. Средства возвращены.")
        except Exception as e:
            self.db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат из-за ошибки: {e}")
            await callback_query.message.edit_text("Произошла непредвиденная ошибка. Средства возвращены.")

    def get_rental_management_keyboard(self, tzid):
        # Simplified: extend is always for 4 hours more
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("👁️ Смотреть СМС", callback_data=f"view_rent_sms:{tzid}")],
            [InlineKeyboardButton("➕ Продлить (4 часа)", callback_data=f"extend_rent:{tzid}")],
            [InlineKeyboardButton("❌ Закрыть аренду", callback_data=f"close_rent:{tzid}")],
            [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")],
        ])

    async def manage_rental(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.message.edit_text("Управление арендой:", reply_markup=self.get_rental_management_keyboard(tzid))

    async def extend_rental(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.answer("Продлеваю аренду...")
        # A full implementation would first get the price for extension and charge the user
        try:
            response = await self.api.continue_rent_number(tzid, rent_time=4)
            if response.get("status") == "success":
                await callback_query.message.edit_text(f"Аренда успешно продлена до {response['phone']['endDate']}!", reply_markup=self.get_rental_management_keyboard(tzid))
            else:
                await callback_query.answer(f"Не удалось продлить: {response}", show_alert=True)
        except Exception as e:
            await callback_query.answer("Произошла ошибка.", show_alert=True)

    async def view_rental_sms(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.answer("Загружаю СМС...", cache_time=5)
        try:
            state = await self.api.get_rent_status(tzid)
            if state.get("status") == "success" and state.get("values"):
                sms_list = "\n".join([f"- `{v['text']}` (от `{v['phoneFrom']}`)" for k, v in state["values"].items()])
                await client.send_message(callback_query.from_user.id, f"**История СМС для аренды {tzid}:**\n{sms_list}")
            else:
                await callback_query.answer("Для этого номера еще не было СМС.", show_alert=True)
        except Exception as e:
            await callback_query.answer("Произошла ошибка при загрузке СМС.", show_alert=True)

    async def close_rental(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.answer("Закрываю аренду...")
        try:
            response = await self.api.set_rent_status(tzid, 2) # 2 = cancel
            if response.get("status") == "success":
                await callback_query.message.edit_text("Аренда была закрыта.")
            else:
                await callback_query.answer(f"Не удалось закрыть: {response}", show_alert=True)
        except Exception as e:
            await callback_query.answer("Произошла ошибка.", show_alert=True)

import logging
import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import CallbackQueryHandler
from bot.api import OnlineSimAPI
from bot.db import Database
from bot.utils import create_paginated_keyboard

rent_tariffs_cache = {}

class RentNumberHandlers:
    def __init__(self, db: Database, api: OnlineSimAPI):
        self.db = db
        self.api = api

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.show_rent_countries, filters.regex("^rent_menu$")),
            CallbackQueryHandler(self.show_rent_countries_paginated, filters.regex(r"^rent_country_page:(\d+)$")),
            CallbackQueryHandler(self.show_rent_services, filters.regex(r"^rent_country:(\d+)$")),
            # Pagination for services can be added here if needed
            CallbackQueryHandler(self.confirm_rental, filters.regex(r"^rent_service:(\d+):(.+)$")),
            CallbackQueryHandler(self.manage_rental, filters.regex(r"^manage_rent:(\d+)$")),
            CallbackQueryHandler(self.extend_rental, filters.regex(r"^extend_rent:(\d+)$")),
            CallbackQueryHandler(self.view_rental_sms, filters.regex(r"^view_rent_sms:(\d+)$")),
            CallbackQueryHandler(self.close_rental, filters.regex(r"^close_rent:(\d+)$")),
        ]

    async def _get_rent_tariffs(self):
        if not rent_tariffs_cache:
            logging.info("Fetching rent tariffs from API...")
            tariffs = await self.api.get_tariffs_rent()
            if tariffs.get("response") == "1":
                rent_tariffs_cache.update(tariffs)
            else:
                raise Exception("Could not fetch rent tariffs.")
        return rent_tariffs_cache

    async def show_rent_countries(self, client: Client, callback_query: CallbackQuery, page=0):
        await callback_query.answer("Fetching countries...")
        try:
            tariffs = await self._get_rent_tariffs()
            buttons = [(f"🗓 {c['name']}", f"rent_country:{c['id']}") for c in tariffs.get("list", [])]
            keyboard = create_paginated_keyboard(buttons, page, 15, "rent_country_page")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")])
            await callback_query.message.edit_text("Select a country for rental:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Error showing rent countries: {e}")
            await callback_query.message.edit_text("Error fetching rental countries.")

    async def show_rent_countries_paginated(self, client: Client, callback_query: CallbackQuery):
        page = int(callback_query.matches[0].group(1))
        await self.show_rent_countries(client, callback_query, page=page)

    async def show_rent_services(self, client: Client, callback_query: CallbackQuery):
        """After a country is selected, show available services for rent."""
        country_id = int(callback_query.matches[0].group(1))
        await callback_query.answer("Загрузка сервисов...")
        try:
            tariffs = await self._get_rent_tariffs()
            country_info = next((c for c in tariffs.get("list", []) if c['id'] == country_id), None)

            if not country_info or not country_info.get("services"):
                await callback_query.message.edit_text("Для этой страны нет доступных сервисов для аренды.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к странам", callback_data="rent_menu")]]))
                return

            buttons = []
            for service, details in country_info["services"].items():
                # Assuming the price is for a month, let's just use this for now.
                # The API is not super clear on duration pricing.
                price = details['price']
                buttons.append((f"{service.capitalize()} - {price} RUB/мес.", f"rent_service:{country_id}:{service}"))

            keyboard = create_paginated_keyboard(buttons, 0, 15, f"rent_service_page:{country_id}")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад к странам", callback_data="rent_menu")])
            await callback_query.message.edit_text("Выберите сервис для аренды:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Error showing rent services: {e}")
            await callback_query.message.edit_text("Произошла ошибка при загрузке сервисов.")


    async def confirm_rental(self, client: Client, callback_query: CallbackQuery):
        country_id = int(callback_query.matches[0].group(1))
        service = callback_query.matches[0].group(2)
        user_id = callback_query.from_user.id

        # Simplified duration - let's assume 30 days as per the price.
        days = 30

        await callback_query.message.edit_text("⏳ Обработка аренды...")

        # Get the cost from the cached tariffs
        try:
            tariffs = await self._get_rent_tariffs()
            country_info = next((c for c in tariffs.get("list", []) if c['id'] == country_id), None)
            cost_rub = float(country_info["services"][service]['price'])
            cost_kopecks = int(cost_rub * 100)
        except Exception as e:
            logging.error(f"Could not get rental price for service {service}: {e}")
            await callback_query.message.edit_text("Не удалось определить цену. Попробуйте снова.")
            return

        # Charge internal balance
        transaction_success = self.db.create_transaction(
            user_telegram_id=user_id,
            amount=-cost_kopecks,
            type='rental',
            details=f"Attempt to rent {service} for {days} days in country {country_id}"
        )

        if not transaction_success:
            await callback_query.message.edit_text(
                "❌ **Аренда не удалась!**\n\nНа вашем внутреннем балансе недостаточно средств. Пожалуйста, пополните счет.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👤 Мой кабинет", callback_data="account_menu")
                ]])
            )
            return

        # If charge succeeds, attempt to rent from API
        transaction_success = self.db.create_transaction(
            user_telegram_id=user_id,
            amount=-cost,
            type='rental',
            details=f"Attempt to rent {service} for {days} days in country {country_id}"
        )

        if not transaction_success:
            await callback_query.message.edit_text(
                "❌ **Rental Failed!**\n\nYour internal balance is too low. Please top up.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👤 My Account", callback_data="account_menu")
                ]])
            )
            return

        # If charge succeeds, attempt to rent from API
        try:
            rental_data = await self.api.get_rent_num(service, country_id, days)
            if rental_data.get("response") == "1":
                tzid = rental_data["tzid"]
                phone = rental_data["phone"]
                expires_at = datetime.datetime.now() + datetime.timedelta(days=days)

                self.db.log_rental(user_id, tzid, service, str(country_id), phone, expires_at)

                await callback_query.message.edit_text(
                    f"**Rental Successful!**\n\nNumber: `{phone}`\nExpires: {expires_at.strftime('%Y-%m-%d %H:%M')}",
                    reply_markup=self.get_rental_management_keyboard(tzid)
                )
            else:
                # If API fails, refund the user
                error = rental_data.get('error_msg', 'Unknown error')
                logging.error(f"API rental failed for {user_id}: {error}. Refunding.")
                self.db.create_transaction(user_id, cost, 'refund', f"Refund for failed rental. Reason: {error}")
                await callback_query.message.edit_text(f"❌ **Rental Failed!**\nProvider error: `{error}`. You have been refunded.")
        except Exception as e:
            logging.error(f"Critical rental error for {user_id}: {e}. Refunding.")
            self.db.create_transaction(user_id, cost, 'refund', f"Refund due to unexpected error: {e}")
            await callback_query.message.edit_text("An unexpected error occurred during rental. You have been refunded.")

    def get_rental_management_keyboard(self, tzid):
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("View SMS", callback_data=f"view_rent_sms:{tzid}"),
                InlineKeyboardButton("Extend (7 days)", callback_data=f"extend_rent:{tzid}"),
            ],
            [InlineKeyboardButton("Close Rental", callback_data=f"close_rent:{tzid}")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")],
        ])

    async def manage_rental(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.message.edit_text("Manage your rental:", reply_markup=self.get_rental_management_keyboard(tzid))

    async def extend_rental(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        days_to_extend = 7
        await callback_query.answer("Extending rental...")
        try:
            response = await self.api.extend_rent_state(tzid, days_to_extend)
            if response.get("response") == "1":
                await callback_query.message.edit_text("Rental extended successfully!", reply_markup=self.get_rental_management_keyboard(tzid))
            else:
                await callback_query.answer(f"Failed to extend: {response.get('error_msg')}", show_alert=True)
        except Exception as e:
            logging.error(f"Error extending rental: {e}")
            await callback_query.answer("An error occurred.", show_alert=True)

    async def view_rental_sms(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.answer("Fetching SMS...")
        try:
            state = await self.api.get_rent_state(tzid)
            if state.get("response") == "1" and state.get("messages"):
                sms_list = "\n".join([f"- `{msg['msg']}` (from `{msg['from']}` at {msg['date']})" for msg in state["messages"]])
                await callback_query.answer(f"SMS History:\n{sms_list}", show_alert=True)
            else:
                await callback_query.answer("No SMS received for this number yet.", show_alert=True)
        except Exception as e:
            logging.error(f"Error fetching rental SMS: {e}")
            await callback_query.answer("An error occurred while fetching SMS.", show_alert=True)

    async def close_rental(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.answer("Closing rental...")
        try:
            response = await self.api.close_rent_num(tzid)
            if response.get("response") == "1":
                await callback_query.message.edit_text("Rental has been closed.")
            else:
                await callback_query.answer(f"Failed to close: {response.get('error_msg')}", show_alert=True)
        except Exception as e:
            logging.error(f"Error closing rental: {e}")
            await callback_query.answer("An error occurred.", show_alert=True)

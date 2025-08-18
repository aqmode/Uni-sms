import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyrogram.handlers import CallbackQueryHandler
from bot.api import OnlineSimAPI
from bot.db import Database
from bot.utils import create_paginated_keyboard

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import CallbackQueryHandler
from bot.api import OnlineSimAPI
from bot.db import Database
from bot.utils import create_paginated_keyboard

tariffs_cache = {}

class BuyNumberHandlers:
    def __init__(self, db: Database, api: OnlineSimAPI):
        self.db = db
        self.api = api

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.show_countries, filters.regex("^buy_menu$")),
            CallbackQueryHandler(self.show_countries_paginated, filters.regex(r"^buy_country_page:(\d+)$")),
            CallbackQueryHandler(self.show_services, filters.regex(r"^buy_country:(\d+)$")),
            CallbackQueryHandler(self.show_services_paginated, filters.regex(r"^buy_service_page:(\d+):(\d+)$")),
            CallbackQueryHandler(self.purchase_number, filters.regex(r"^buy_service:(.+):(\d+)$")),
        ]

    async def _get_tariffs(self):
        if "tariffs" not in tariffs_cache:
            logging.info("Fetching tariffs from API...")
            full_tariffs = await self.api.get_tariffs()
            if full_tariffs.get("response") != "1":
                raise Exception("Failed to fetch tariffs from API")
            tariffs_cache["tariffs"] = full_tariffs
            tariffs_cache["countries"] = sorted(full_tariffs.get("countries", []), key=lambda x: x['name_en'])
            tariffs_cache["services"] = full_tariffs.get("services", [])
        return tariffs_cache["tariffs"]

    async def show_countries(self, client: Client, callback_query: CallbackQuery, page=0):
        await callback_query.answer("Fetching countries...")
        try:
            await self._get_tariffs()
            buttons = [(f"🇺🇸 {c['name_en']}", f"buy_country:{c['id']}") for c in tariffs_cache["countries"]]
            keyboard = create_paginated_keyboard(buttons, page, 15, "buy_country_page")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu")])
            await callback_query.message.edit_text("Please select a country:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Error showing countries: {e}")
            await callback_query.message.edit_text("Could not fetch country list. Please try again later.")

    async def show_countries_paginated(self, client: Client, callback_query: CallbackQuery):
        page = int(callback_query.matches[0].group(1))
        await self.show_countries(client, callback_query, page=page)

    async def show_services(self, client: Client, callback_query: CallbackQuery, page=0):
        country_id = int(callback_query.matches[0].group(1))
        await callback_query.answer("Fetching services...")
        try:
            tariffs = await self._get_tariffs()
            country_services = [s for s in tariffs["services"] if s['country'] == country_id and s['count'] > 0]

            if not country_services:
                await callback_query.message.edit_text("No services available for this country.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Countries", callback_data="buy_menu")]]))
                return

            buttons = [(f"{s['service']} - {s['price']} RUB", f"buy_service:{s['id']}:{country_id}") for s in country_services]
            callback_prefix = f"buy_service_page:{country_id}"
            keyboard = create_paginated_keyboard(buttons, page, 15, callback_prefix)
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Back to Countries", callback_data="buy_menu")])
            await callback_query.message.edit_text("Please select a service:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Error showing services: {e}")
            await callback_query.message.edit_text("Could not fetch service list. Please try again later.")

    async def show_services_paginated(self, client: Client, callback_query: CallbackQuery):
        country_id = int(callback_query.matches[0].group(1))
        page = int(callback_query.matches[0].group(2))
        # We need to simulate the original callback for show_services
        callback_query.matches[0].group = lambda i: str(country_id) if i == 1 else None
        await self.show_services(client, callback_query, page=page)

    async def purchase_number(self, client: Client, callback_query: CallbackQuery):
        service_id_str = callback_query.matches[0].group(1)
        country_id = int(callback_query.matches[0].group(2))
        user_id = callback_query.from_user.id

        await callback_query.message.edit_text("⏳ Processing purchase...")

        # 1. Get the cost of the service
        try:
            tariffs = await self._get_tariffs()
            service_info = next((s for s in tariffs["services"] if s['id'] == service_id_str and s['country'] == country_id), None)
            if not service_info:
                await callback_query.message.edit_text("Error: Service not found or is no longer available.")
                return

            # Assuming price is in rubles, convert to kopecks/cents
            cost = int(float(service_info['price']) * 100)
        except Exception as e:
            logging.error(f"Could not determine service cost: {e}")
            await callback_query.message.edit_text("An error occurred while verifying the price.")
            return

        # 2. Attempt to charge the user's internal balance
        transaction_success = self.db.create_transaction(
            user_telegram_id=user_id,
            amount=-cost,
            type='purchase',
            details=f"Attempt to buy service {service_id_str} for country {country_id}"
        )

        if not transaction_success:
            await callback_query.message.edit_text(
                "❌ **Purchase Failed!**\n\nYour internal balance is too low. Please top up your account.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👤 My Account", callback_data="account_menu")
                ]])
            )
            return

        # 3. If charge is successful, attempt to buy the number from the API
        try:
            purchase_data = await self.api.get_num(service_id_str, country_id)
            if purchase_data.get("response") == "1":
                tzid = purchase_data["tzid"]
                phone_number = purchase_data["number"]

                self.db.log_purchase(user_id, tzid, service_id_str, str(country_id), phone_number)

                await callback_query.message.edit_text(
                    f"✅ **Number Purchased!**\n\n"
                    f"**Number:** `{phone_number}`\n"
                    f"**Service:** {service_info['service']}\n\n"
                    "Waiting for SMS... I will notify you when it arrives."
                )
                asyncio.create_task(self.poll_for_sms(callback_query, tzid))
            else:
                # 4. If API purchase fails, refund the user
                error = purchase_data.get("error_msg", "Unknown error")
                logging.error(f"API purchase failed for user {user_id}: {error}. Refunding internal balance.")
                self.db.create_transaction(
                    user_telegram_id=user_id,
                    amount=cost, # Positive amount for refund
                    type='refund',
                    details=f"Refund for failed purchase attempt. Reason: {error}"
                )
                await callback_query.message.edit_text(
                    f"❌ **Purchase Failed!**\n\nAn issue occurred with the provider: `{error}`\n\nYour account has been refunded.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Services", f"buy_country:{country_id}")]]))
        except Exception as e:
            logging.error(f"Critical error during number purchase for {user_id}: {e}. Refunding.")
            # Also refund on unexpected exceptions
            self.db.create_transaction(user_id, cost, 'refund', f"Refund due to unexpected error: {e}")
            await callback_query.message.edit_text("An unexpected error occurred. Your account has been refunded.")

    async def poll_for_sms(self, callback_query: CallbackQuery, tzid: int):
        max_wait_time = 300  # 5 minutes
        poll_interval = 5  # seconds
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

            try:
                state = await self.api.get_state(tzid)
                if state.get("response") == "1" and state.get("msg"):
                    sms_code = state["msg"]
                    await callback_query.message.reply_text(f"✉️ **New SMS Received!**\n\nCode: `{sms_code}`")
                    await self.api.set_operation_ok(tzid)
                    return # Stop polling
                elif state.get("response") == "ERROR_NO_OPERATIONS":
                     await callback_query.message.reply_text("Operation timed out or was cancelled.")
                     return
            except Exception as e:
                logging.error(f"Error polling for SMS (tzid: {tzid}): {e}")

        await callback_query.message.reply_text("Stopped waiting for SMS after 5 minutes.")
        await self.api.set_operation_ok(tzid) # Close the operation

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

from bot.cache import get_buy_tariffs

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

    async def show_countries(self, client: Client, callback_query: CallbackQuery, page=0):
        await callback_query.answer("Загрузка стран...")
        try:
            buy_tariffs = get_buy_tariffs()
            countries = sorted(buy_tariffs.get("countries", []), key=lambda x: x['name_en'])
            buttons = [(f"🇺🇸 {c['name_en']}", f"buy_country:{c['id']}") for c in countries]

            keyboard = create_paginated_keyboard(buttons, page, 15, "buy_country_page")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
            await callback_query.message.edit_text("Пожалуйста, выберите страну:", reply_markup=keyboard)
        except Exception as e:
            error_text = "Не удалось загрузить список стран. Убедитесь, что вы создали файл `tariffs.json`, запустив `python fetch_tariffs.py`."
            logging.error(f"Ошибка при отображении стран: {e}")
            if callback_query.message.text != error_text:
                await callback_query.message.edit_text(error_text)

    async def show_countries_paginated(self, client: Client, callback_query: CallbackQuery):
        page = int(callback_query.matches[0].group(1))
        await self.show_countries(client, callback_query, page=page)

    async def show_services(self, client: Client, callback_query: CallbackQuery, page=0):
        country_id = int(callback_query.matches[0].group(1))
        await callback_query.answer("Загрузка сервисов...")
        try:
            buy_tariffs = get_buy_tariffs()
            country_services = [s for s in buy_tariffs.get("services", []) if s['country'] == country_id and s.get('count', 0) > 0]

            if not country_services:
                await callback_query.message.edit_text("Для этой страны нет доступных сервисов.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к странам", callback_data="buy_menu")]]))
                return

            buttons = [(f"{s['service']} - {s['price']} RUB", f"buy_service:{s['id']}:{country_id}") for s in country_services]
            callback_prefix = f"buy_service_page:{country_id}"
            keyboard = create_paginated_keyboard(buttons, page, 15, callback_prefix)
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад к странам", callback_data="buy_menu")])
            await callback_query.message.edit_text("Пожалуйста, выберите сервис:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отображении сервисов: {e}")
            await callback_query.message.edit_text("Не удалось загрузить список сервисов. Убедитесь, что файл `tariffs.json` существует.")

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

        await callback_query.message.edit_text("⏳ Обработка покупки...")

        try:
            buy_tariffs = get_buy_tariffs()
            service_info = next((s for s in buy_tariffs.get("services", []) if s['id'] == service_id_str and s['country'] == country_id), None)
            if not service_info:
                await callback_query.message.edit_text("Ошибка: Сервис не найден или больше не доступен.")
                return
            cost = int(float(service_info['price']) * 100)
        except Exception as e:
            logging.error(f"Не удалось определить стоимость сервиса: {e}")
            await callback_query.message.edit_text("Произошла ошибка при проверке цены.")
            return

        transaction_success = self.db.create_transaction(
            user_telegram_id=user_id,
            amount=-cost,
            type='purchase',
            details=f"Попытка покупки сервиса {service_id_str} для страны {country_id}"
        )

        if not transaction_success:
            await callback_query.message.edit_text(
                "❌ **Покупка не удалась!**\n\nНа вашем внутреннем балансе недостаточно средств. Пожалуйста, пополните счет.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👤 Мой кабинет", callback_data="account_menu")
                ]])
            )
            return

        try:
            purchase_data = await self.api.get_num(service_id_str, country_id)
            if purchase_data.get("response") == "1":
                tzid = purchase_data["tzid"]
                phone_number = purchase_data["number"]
                self.db.log_purchase(user_id, tzid, service_id_str, str(country_id), phone_number)
                await callback_query.message.edit_text(
                    f"✅ **Номер приобретен!**\n\n"
                    f"**Номер:** `{phone_number}`\n"
                    f"**Сервис:** {service_info['service']}\n\n"
                    "Ожидаю СМС... Я сообщу, когда оно придет."
                )
                asyncio.create_task(self.poll_for_sms(callback_query, tzid))
            else:
                error = purchase_data.get("error_msg", "Unknown error")
                logging.error(f"Ошибка API при покупке для пользователя {user_id}: {error}. Возвращаю средства.")
                self.db.create_transaction(user_id, cost, 'refund', f"Возврат из-за ошибки покупки. Причина: {error}")
                await callback_query.message.edit_text(
                    f"❌ **Покупка не удалась!**\n\nПроизошла ошибка на стороне провайдера: `{error}`\n\nВаш баланс был пополнен на сумму покупки.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к сервисам", f"buy_country:{country_id}")]]))
        except Exception as e:
            logging.error(f"Критическая ошибка во время покупки номера для {user_id}: {e}. Возвращаю средства.")
            self.db.create_transaction(user_id, cost, 'refund', f"Возврат из-за непредвиденной ошибки: {e}")
            await callback_query.message.edit_text("Произошла непредвиденная ошибка. Ваш баланс был пополнен на сумму покупки.")

    async def poll_for_sms(self, callback_query: CallbackQuery, tzid: int):
        max_wait_time = 300
        poll_interval = 5
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

            try:
                state = await self.api.get_state(tzid)
                if state.get("response") == "1" and state.get("msg"):
                    sms_code = state["msg"]
                    await callback_query.message.reply_text(f"✉️ **Получено новое СМС!**\n\nКод: `{sms_code}`")
                    await self.api.set_operation_ok(tzid)
                    return
                elif state.get("response") == "ERROR_NO_OPERATIONS":
                     await callback_query.message.reply_text("Время ожидания операции истекло или она была отменена.")
                     return
            except Exception as e:
                logging.error(f"Ошибка при проверке СМС (tzid: {tzid}): {e}")

        await callback_query.message.reply_text("Ожидание СМС завершено (5 минут).")
        await self.api.set_operation_ok(tzid)

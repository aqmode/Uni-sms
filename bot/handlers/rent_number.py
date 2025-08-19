import logging
import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.handlers import CallbackQueryHandler
from bot.api import OnlineSimAPI
from bot.db import Database
from bot.utils import create_paginated_keyboard
from bot.cache import get_rent_tariffs

class RentNumberHandlers:
    def __init__(self, db: Database, api: OnlineSimAPI):
        self.db = db
        self.api = api

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.show_rent_countries, filters.regex("^rent_menu$")),
            CallbackQueryHandler(self.show_rent_countries_paginated, filters.regex(r"^rent_country_page:(\d+)$")),
            CallbackQueryHandler(self.show_rent_services, filters.regex(r"^rent_country:(\d+)$")),
            CallbackQueryHandler(self.confirm_rental, filters.regex(r"^rent_service:(\d+):(.+)$")),
            CallbackQueryHandler(self.manage_rental, filters.regex(r"^manage_rent:(\d+)$")),
            CallbackQueryHandler(self.extend_rental, filters.regex(r"^extend_rent:(\d+)$")),
            CallbackQueryHandler(self.view_rental_sms, filters.regex(r"^view_rent_sms:(\d+)$")),
            CallbackQueryHandler(self.close_rental, filters.regex(r"^close_rent:(\d+)$")),
        ]

    async def show_rent_countries(self, client: Client, callback_query: CallbackQuery, page=0):
        await callback_query.answer("Загрузка стран...")
        try:
            rent_tariffs = get_rent_tariffs()
            buttons = [(f"🗓 {c['name']}", f"rent_country:{c['id']}") for c in rent_tariffs.get("list", [])]
            keyboard = create_paginated_keyboard(buttons, page, 15, "rent_country_page")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])
            await callback_query.message.edit_text("Выберите страну для аренды:", reply_markup=keyboard)
        except Exception as e:
            error_text = "Не удалось загрузить список стран для аренды. Убедитесь, что вы создали файл `tariffs.json`, запустив `python fetch_tariffs.py`."
            logging.error(f"Ошибка при отображении стран для аренды: {e}")
            if callback_query.message.text != error_text:
                await callback_query.message.edit_text(error_text)

    async def show_rent_countries_paginated(self, client: Client, callback_query: CallbackQuery):
        page = int(callback_query.matches[0].group(1))
        await self.show_rent_countries(client, callback_query, page=page)

    async def show_rent_services(self, client: Client, callback_query: CallbackQuery):
        country_id = int(callback_query.matches[0].group(1))
        await callback_query.answer("Загрузка сервисов...")
        try:
            rent_tariffs = get_rent_tariffs()
            country_info = next((c for c in rent_tariffs.get("list", []) if c['id'] == country_id), None)
            if not country_info or not country_info.get("services"):
                await callback_query.message.edit_text("Для этой страны нет доступных сервисов для аренды.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к странам", callback_data="rent_menu")]]))
                return
            buttons = [(f"{s.capitalize()} - {d['price']} RUB/мес.", f"rent_service:{country_id}:{s}") for s, d in country_info["services"].items()]
            keyboard = create_paginated_keyboard(buttons, 0, 15, f"rent_service_page:{country_id}")
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад к странам", callback_data="rent_menu")])
            await callback_query.message.edit_text("Выберите сервис для аренды:", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Ошибка при отображении сервисов для аренды: {e}")
            await callback_query.message.edit_text("Произошла ошибка при загрузке сервисов.")

    async def confirm_rental(self, client: Client, callback_query: CallbackQuery):
        country_id = int(callback_query.matches[0].group(1))
        service = callback_query.matches[0].group(2)
        user_id = callback_query.from_user.id
        days = 30

        await callback_query.message.edit_text("⏳ Обработка аренды...")
        try:
            rent_tariffs = get_rent_tariffs()
            country_info = next((c for c in rent_tariffs.get("list", []) if c['id'] == country_id), None)
            cost_rub = float(country_info["services"][service]['price'])
            cost_kopecks = int(cost_rub * 100)
        except Exception as e:
            logging.error(f"Не удалось получить цену аренды для сервиса {service}: {e}")
            await callback_query.message.edit_text("Не удалось определить цену. Попробуйте снова.")
            return

        transaction_success = self.db.create_transaction(user_id, -cost_kopecks, 'rental', f"Попытка аренды {service} на {days} дней в стране {country_id}")
        if not transaction_success:
            await callback_query.message.edit_text("❌ **Аренда не удалась!**\n\nНа вашем внутреннем балансе недостаточно средств.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 Мой кабинет", callback_data="account_menu")]]))
            return

        try:
            rental_data = await self.api.get_rent_num(service, country_id, days)
            if rental_data.get("response") == "1":
                tzid = rental_data["tzid"]
                phone = rental_data["phone"]
                expires_at = datetime.datetime.now() + datetime.timedelta(days=days)
                self.db.log_rental(user_id, tzid, service, str(country_id), phone, expires_at)
                await callback_query.message.edit_text(f"✅ **Аренда успешна!**\n\n**Номер:** `{phone}`\n**Истекает:** {expires_at.strftime('%Y-%m-%d %H:%M')}", reply_markup=self.get_rental_management_keyboard(tzid))
            else:
                error = rental_data.get('error_msg', 'Unknown error')
                logging.error(f"Ошибка API при аренде для {user_id}: {error}. Возврат средств.")
                self.db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат средств из-за ошибки аренды. Причина: {error}")
                await callback_query.message.edit_text(f"❌ **Аренда не удалась!**\nОшибка провайдера: `{error}`. Средства возвращены на ваш баланс.")
        except Exception as e:
            logging.error(f"Критическая ошибка при аренде для {user_id}: {e}. Возврат средств.")
            self.db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат из-за непредвиденной ошибки: {e}")
            await callback_query.message.edit_text("Произошла непредвиденная ошибка. Средства возвращены на ваш баланс.")

    def get_rental_management_keyboard(self, tzid):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("👁️ Смотреть СМС", callback_data=f"view_rent_sms:{tzid}"), InlineKeyboardButton("➕ Продлить (30 дней)", callback_data=f"extend_rent:{tzid}")],
            [InlineKeyboardButton("❌ Закрыть аренду", callback_data=f"close_rent:{tzid}")],
            [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")],
        ])

    async def manage_rental(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.message.edit_text("Управление арендой:", reply_markup=self.get_rental_management_keyboard(tzid))

    async def extend_rental(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        days_to_extend = 30
        await callback_query.answer("Продлеваю аренду...")
        # Note: a real implementation would need to charge the user's internal balance here as well.
        try:
            response = await self.api.extend_rent_state(tzid, days_to_extend)
            if response.get("response") == "1":
                await callback_query.message.edit_text("Аренда успешно продлена!", reply_markup=self.get_rental_management_keyboard(tzid))
            else:
                await callback_query.answer(f"Не удалось продлить: {response.get('error_msg')}", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка при продлении аренды: {e}")
            await callback_query.answer("Произошла ошибка.", show_alert=True)

    async def view_rental_sms(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.answer("Загружаю СМС...")
        try:
            state = await self.api.get_rent_state(tzid)
            if state.get("response") == "1" and state.get("messages"):
                sms_list = "\n".join([f"- `{msg['msg']}` (от `{msg['from']}` в {msg['date']})" for msg in state["messages"]])
                await callback_query.answer(f"История СМС:\n{sms_list}", show_alert=True, cache_time=5)
            else:
                await callback_query.answer("Для этого номера еще не было СМС.", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка при загрузке СМС для аренды: {e}")
            await callback_query.answer("Произошла ошибка при загрузке СМС.", show_alert=True)

    async def close_rental(self, client: Client, callback_query: CallbackQuery):
        tzid = int(callback_query.matches[0].group(1))
        await callback_query.answer("Закрываю аренду...")
        try:
            response = await self.api.close_rent_num(tzid)
            if response.get("response") == "1":
                await callback_query.message.edit_text("Аренда была закрыта.")
            else:
                await callback_query.answer(f"Не удалось закрыть: {response.get('error_msg')}", show_alert=True)
        except Exception as e:
            logging.error(f"Ошибка при закрытии аренды: {e}")
            await callback_query.answer("Произошла ошибка.", show_alert=True)

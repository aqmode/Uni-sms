import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from pyrogram.handlers import CallbackQueryHandler
from bot.api import SmsActivateWrapper
from config import IMAGE_COUNTRIES, IMAGE_SERVICES
from bot.db import Database
from bot.utils import create_paginated_keyboard
from bot.states import set_user_state, clear_user_state

COUNTRY_LIST_CACHE = []
SERVICE_PRICE_CACHE = {} # key: country_id, value: dict of services

# Compromise: Hardcoded map for popular service names
SERVICE_NAME_MAP = {
    'tg': "Telegram", 'wa': "WhatsApp", 'vi': "Viber", 'ig': "Instagram",
    'fb': "Facebook", 'go': "Google/YouTube", 'vk': "ВКонтакте",
    'ok': "Одноклассники", 'mm': "Mail.ru", 'ya': "Яндекс",
    'ds': "Discord", 'am': "Amazon", 'tw': "Twitter", 'st': "Steam",
    'ub': "Uber", 'nf': "Netflix", 'tk': "TikTok", 'ot': "Любой другой"
}

class BuyNumberHandlers:
    def __init__(self, db: Database, api: SmsActivateWrapper):
        self.db = db
        self.api = api

    def get_handlers(self):
        return [
            CallbackQueryHandler(self.show_countries, filters.regex("^buy_menu$")),
            CallbackQueryHandler(self.show_countries_paginated, filters.regex(r"^buy_country_page:(\d+)$")),
            CallbackQueryHandler(self.search_country_handler, filters.regex("^search_country$")),
            CallbackQueryHandler(self.show_services, filters.regex(r"^buy_country:(\d+)$")),
            CallbackQueryHandler(self.search_service_handler, filters.regex(r"^search_service:(\d+)$")),
            CallbackQueryHandler(self.purchase_number, filters.regex(r"^buy_service:(.+):(\d+)$")),
        ]

    async def search_country_handler(self, client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        set_user_state(user_id, 'searching_country')
        await callback_query.message.edit_text("Пожалуйста, введите название страны для поиска:")
        await callback_query.answer()

    async def search_service_handler(self, client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        country_id = int(callback_query.matches[0].group(1))
        set_user_state(user_id, 'searching_service', context={'country_id': country_id})
        await callback_query.message.edit_text("Пожалуйста, введите название сервиса для поиска:")
        await callback_query.answer()

    async def show_countries(self, client: Client, callback_query: CallbackQuery, page=0, search_query=None):
        await callback_query.answer("Загрузка стран...")
        try:
            if not COUNTRY_LIST_CACHE:
                # SIMPLIFIED LOGIC: Just get all countries and sort alphabetically.
                countries_data = await self.api.get_countries()
                if not isinstance(countries_data, dict):
                    raise Exception("Invalid data format from API")

                all_countries = list(countries_data.values())
                all_countries.sort(key=lambda c: c['rus'])
                COUNTRY_LIST_CACHE.extend(all_countries)

            countries_to_show = COUNTRY_LIST_CACHE
            if search_query:
                countries_to_show = [c for c in COUNTRY_LIST_CACHE if search_query.lower() in c['rus'].lower()]

            buttons = [(f"{c['rus']}", f"buy_country:{c['id']}") for c in countries_to_show]
            keyboard = create_paginated_keyboard(buttons, page, 18, "buy_country_page", columns=3) # 3 columns
            keyboard.inline_keyboard.append([InlineKeyboardButton("🔎 Поиск", callback_data="search_country")])
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu")])

            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=IMAGE_COUNTRIES, caption="Пожалуйста, выберите страну (сначала популярные):"),
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Ошибка при отображении стран: {e}")
            await callback_query.message.edit_caption("Не удалось загрузить список стран.")

    async def show_countries_paginated(self, client: Client, callback_query: CallbackQuery):
        page = int(callback_query.matches[0].group(1))
        await self.show_countries(client, callback_query, page=page)

    async def show_services(self, client: Client, callback_query: CallbackQuery, page=0, search_query=None):
        country_id = int(callback_query.matches[0].group(1))
        await callback_query.answer("Загрузка сервисов...")
        logging.info(f"Запрос сервисов для страны ID: {country_id}")
        try:
            # Get prices for the selected country
            if country_id not in SERVICE_PRICE_CACHE:
                logging.info(f"Цены для страны {country_id} не в кэше, загружаю...")
                prices_data = await self.api.get_prices(country_id)
                if isinstance(prices_data, dict):
                    SERVICE_PRICE_CACHE[country_id] = prices_data.get(str(country_id), {})
                    logging.info(f"Цены для страны {country_id} загружены и кэшированы.")
                else:
                    raise Exception(f"Unexpected prices format: {prices_data}")

            country_prices = SERVICE_PRICE_CACHE[country_id]
            logging.info(f"Найдено {len(country_prices)} сервисов для страны {country_id}.")
            if not country_prices:
                await callback_query.message.edit_text("Для этой страны нет доступных сервисов.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к странам", callback_data="buy_menu")]]))
                return

            logging.info("Создание кнопок для клавиатуры...")
            buttons = []

            services_to_show = country_prices.items()
            if search_query:
                services_to_show = [
                    (sc, dt) for sc, dt in country_prices.items()
                    if search_query.lower() in SERVICE_NAME_MAP.get(sc, sc).lower()
                ]

            for service_code, details in services_to_show:
                # Use the full name from the map, or default to the code
                full_name = SERVICE_NAME_MAP.get(service_code, service_code)
                button_text = f"{full_name} - {details['cost']} RUB ({details['count']} шт.)"
                buttons.append((button_text, f"buy_service:{service_code}:{country_id}"))

            keyboard = create_paginated_keyboard(buttons, page, 12, f"buy_service_page:{country_id}", columns=2) # 2 columns
            keyboard.inline_keyboard.append([InlineKeyboardButton("🔎 Поиск", callback_data=f"search_service:{country_id}")])
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад к странам", callback_data="buy_menu")])

            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=IMAGE_SERVICES, caption="Пожалуйста, выберите сервис:"),
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Ошибка при отображении сервисов: {e}")
            await callback_query.message.edit_caption("Не удалось загрузить список сервисов.")

    async def purchase_number(self, client: Client, callback_query: CallbackQuery):
        service_code = callback_query.matches[0].group(1)
        country_id = int(callback_query.matches[0].group(2))
        user_id = callback_query.from_user.id

        await callback_query.message.edit_text("⏳ Обработка покупки...")
        try:
            cost_rub = float(SERVICE_PRICE_CACHE[country_id][service_code]['cost'])
            cost_kopecks = int(cost_rub * 100)
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"Не удалось определить стоимость: {e}")
            await callback_query.message.edit_text("Ошибка при проверке цены. Попробуйте выбрать сервис заново.")
            return

        if not self.db.create_transaction(user_id, -cost_kopecks, 'purchase', f"Покупка {service_code}"):
            await callback_query.message.edit_text("❌ Покупка не удалась! Недостаточно средств.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 Мой кабинет", callback_data="account_menu")]]))
            return

        try:
            purchase_response = await self.api.get_number(service_code, country_id)
            if isinstance(purchase_response, dict) and 'activation' in purchase_response:
                activation = purchase_response['activation']
                activation_id = int(activation['id'])
                phone_number = activation['phone']
                self.db.log_purchase(user_id, activation_id, service_code, str(country_id), phone_number)
                await callback_query.message.edit_text(f"✅ **Номер получен!**\n\n**Номер:** `{phone_number}`\n**Сервис:** {service_code}\n\nОжидаю СМС...")
                asyncio.create_task(self.poll_for_sms(callback_query, activation_id))
            else:
                logging.error(f"Ошибка API при покупке: {purchase_response}. Возврат средств.")
                self.db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат из-за ошибки: {purchase_response}")
                await callback_query.message.edit_text(f"❌ **Ошибка покупки!**\nПричина: `{purchase_response}`\n\nСредства возвращены.")
        except Exception as e:
            logging.error(f"Критическая ошибка при покупке: {e}. Возврат средств.")
            self.db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат из-за непредвиденной ошибки: {e}")
            await callback_query.message.edit_text("Произошла непредвиденная ошибка. Средства возвращены.")

    async def poll_for_sms(self, callback_query: CallbackQuery, activation_id: int):
        max_wait_time = 600
        poll_interval = 10
        for _ in range(max_wait_time // poll_interval):
            await asyncio.sleep(poll_interval)
            try:
                status_response = await self.api.get_status(activation_id)
                if isinstance(status_response, str) and "STATUS_OK" in status_response:
                    sms_code = status_response.split(':')[1]
                    await callback_query.message.reply_text(f"✉️ **Получено СМС!**\n\nКод: `{sms_code}`")
                    await self.api.set_status(activation_id, 6)
                    return
                elif isinstance(status_response, str) and "STATUS_CANCEL" in status_response:
                    await callback_query.message.reply_text("❌ Активация была отменена.")
                    return
            except Exception as e:
                logging.error(f"Ошибка при проверке СМС (ID: {activation_id}): {e}")

        await callback_query.message.reply_text("Ожидание СМС завершено (10 минут).")
        await self.api.set_status(activation_id, 8)

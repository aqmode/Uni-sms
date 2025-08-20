import asyncio
import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from bot.api import SmsActivateWrapper
from bot.db import Database
from bot.utils import create_paginated_keyboard
from bot.states import set_user_state, clear_user_state
from config import IMAGE_COUNTRIES, IMAGE_SERVICES

# Caches
COUNTRY_LIST_CACHE = []
SERVICE_PRICE_CACHE = {}
SERVICE_NAME_MAP = {
    'tg': "Telegram", 'wa': "WhatsApp", 'vi': "Viber", 'ig': "Instagram",
    'fb': "Facebook", 'go': "Google/YouTube", 'vk': "ВКонтакте",
    'ok': "Одноклассники", 'mm': "Mail.ru", 'ya': "Яндекс",
    'ds': "Discord", 'am': "Amazon", 'tw': "Twitter", 'st': "Steam",
    'ub': "Uber", 'nf': "Netflix", 'tk': "TikTok", 'ot': "Любой другой"
}

# --- Handlers ---

async def show_countries(callback_query: types.CallbackQuery, api: SmsActivateWrapper, page: int = 0):
    await callback_query.answer("Загрузка стран...")
    try:
        if not COUNTRY_LIST_CACHE:
            countries_data = await api.get_countries()
            if isinstance(countries_data, dict):
                all_countries = list(countries_data.values())
                all_countries.sort(key=lambda c: c['rus'])
                COUNTRY_LIST_CACHE.extend(all_countries)
            else:
                raise Exception(f"Invalid country data: {countries_data}")

        buttons = [(f"{c['rus']}", f"buy_country:{c['id']}") for c in COUNTRY_LIST_CACHE]
        keyboard = create_paginated_keyboard(buttons, page, 18, "buy_country_page", columns=3)
        keyboard.add(types.InlineKeyboardButton(text="🔎 Поиск", callback_data="search_country"))
        keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="main_menu"))

        await callback_query.message.edit_media(
            media=types.InputMediaPhoto(media=IMAGE_COUNTRIES, caption="Пожалуйста, выберите страну:"),
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Ошибка при отображении стран: {e}")
        await callback_query.message.edit_caption("Не удалось загрузить список стран.")

async def show_countries_paginated(callback_query: types.CallbackQuery, api: SmsActivateWrapper):
    page = int(callback_query.data.split(':')[-1])
    await show_countries(callback_query, api, page=page)

async def show_services(callback_query: types.CallbackQuery, api: SmsActivateWrapper, page: int = 0):
    country_id = int(callback_query.data.split(':')[-1])
    await callback_query.answer("Загрузка сервисов...")
    try:
        if country_id not in SERVICE_PRICE_CACHE:
            prices_data = await api.get_prices(country=country_id)
            if isinstance(prices_data, dict) and str(country_id) in prices_data:
                SERVICE_PRICE_CACHE[country_id] = prices_data[str(country_id)]
            else:
                raise Exception(f"Invalid prices data: {prices_data}")

        country_prices = SERVICE_PRICE_CACHE[country_id]
        if not country_prices:
            await callback_query.message.edit_text("Для этой страны нет доступных сервисов.")
            return

        buttons = []
        for code, details in country_prices.items():
            name = SERVICE_NAME_MAP.get(code, code)
            buttons.append((f"{name} - {details['cost']} RUB", f"buy_service:{code}:{country_id}"))

        keyboard = create_paginated_keyboard(buttons, page, 12, f"buy_service_page:{country_id}", columns=2)
        keyboard.add(types.InlineKeyboardButton(text="🔎 Поиск", callback_data=f"search_service:{country_id}"))
        keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад к странам", callback_data="buy_menu"))

        await callback_query.message.edit_media(
            media=types.InputMediaPhoto(media=IMAGE_SERVICES, caption="Пожалуйста, выберите сервис:"),
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Ошибка при отображении сервисов: {e}")
        await callback_query.message.edit_caption("Не удалось загрузить список сервисов.")

async def purchase_number(callback_query: types.CallbackQuery, db: Database, api: SmsActivateWrapper):
    _, service_code, country_id_str = callback_query.data.split(':')
    country_id = int(country_id_str)
    user_id = callback_query.from_user.id

    await callback_query.message.edit_caption("⏳ Обработка покупки...")
    try:
        cost_rub = float(SERVICE_PRICE_CACHE[country_id][service_code]['cost'])
        cost_kopecks = int(cost_rub * 100)
    except Exception as e:
        logging.error(f"Не удалось определить стоимость: {e}")
        await callback_query.message.edit_caption("Ошибка при проверке цены.")
        return

    if not db.create_transaction(user_id, -cost_kopecks, 'purchase', f"Покупка {service_code}"):
        await callback_query.message.edit_caption("❌ Покупка не удалась! Недостаточно средств.")
        return

    try:
        purchase_response = await api.get_number(service_code, country_id)
        if isinstance(purchase_response, dict) and 'activation' in purchase_response:
            act = purchase_response['activation']
            db.log_purchase(user_id, int(act['id']), service_code, str(country_id), act['phone'])
            await callback_query.message.edit_caption(f"✅ **Номер получен!**\n\n**Номер:** `{act['phone']}`\n\nОжидаю СМС...")
            asyncio.create_task(poll_for_sms(callback_query.message, int(act['id']), api))
        else:
            db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат: {purchase_response}")
            await callback_query.message.edit_caption(f"❌ **Ошибка покупки!**\nПричина: `{purchase_response}`. Средства возвращены.")
    except Exception as e:
        db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат из-за ошибки: {e}")
        await callback_query.message.edit_caption("Произошла непредвиденная ошибка. Средства возвращены.")

async def poll_for_sms(message: types.Message, activation_id: int, api: SmsActivateWrapper):
    for _ in range(60): # Poll for 10 minutes (60 * 10 seconds)
        await asyncio.sleep(10)
        try:
            status_res = await api.get_status(activation_id)
            if "STATUS_OK" in status_res:
                sms_code = status_res.split(':')[1]
                await message.answer(f"✉️ **Получено СМС!**\n\nКод: `{sms_code}`")
                await api.set_status(activation_id, 6)
                return
            elif "STATUS_CANCEL" in status_res:
                await message.answer("❌ Активация была отменена.")
                return
        except Exception as e:
            logging.error(f"Ошибка при проверке СМС (ID: {activation_id}): {e}")
    await message.answer("Ожидание СМС завершено (10 минут).")
    await api.set_status(activation_id, 8)

# --- Registration ---

def register_buy_handlers(dp: Dispatcher, db: Database, api: SmsActivateWrapper):
    dp.register_callback_query_handler(lambda c: show_countries(c, api), Text(equals="buy_menu"))
    dp.register_callback_query_handler(lambda c: show_countries_paginated(c, api), Text(startswith="buy_country_page:"))
    dp.register_callback_query_handler(lambda c: show_services(c, api), Text(startswith="buy_country:"))
    # Need handlers for service pagination and search triggers
    dp.register_callback_query_handler(lambda c: purchase_number(c, db, api), Text(startswith="buy_service:"))

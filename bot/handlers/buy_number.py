import asyncio
import logging
from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile
from bot.api import SmsActivateWrapper
from bot.db import Database
from bot.utils import create_paginated_keyboard
from config import IMAGE_COUNTRIES, IMAGE_SERVICES

router = Router()

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

@router.callback_query(F.data == "buy_menu")
async def show_countries(callback_query: types.CallbackQuery, api: SmsActivateWrapper, page: int = 0):
    await callback_query.answer("Загрузка стран...")
    try:
        if not COUNTRY_LIST_CACHE:
            countries_data = await api.get_countries()

            # Robust check for API errors and data structure
            if isinstance(countries_data, dict) and 'error' in countries_data:
                raise Exception(f"API Error getting countries: {countries_data['error']}")
            if not isinstance(countries_data, dict):
                raise Exception(f"Invalid country data type: {type(countries_data)}")

            all_countries = list(countries_data.values())
            if not all_countries or not isinstance(all_countries[0], dict):
                raise Exception(f"Unexpected country data format: {all_countries}")

            all_countries.sort(key=lambda c: c.get('rus', ''))
            COUNTRY_LIST_CACHE.extend(all_countries)

        # Use .get() for safe access
        buttons = [(f"{c.get('rus', 'N/A')}", f"buy_country:{c.get('id', 'N/A')}") for c in COUNTRY_LIST_CACHE]
        keyboard = create_paginated_keyboard(buttons, page, 18, "buy_country_page", columns=3)
        keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="🔎 Поиск", callback_data="search_country")])
        keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="main_menu")])

        try:
            await callback_query.message.edit_media(
                media=types.InputMediaPhoto(media=FSInputFile(IMAGE_COUNTRIES), caption="Пожалуйста, выберите страну:"),
                reply_markup=keyboard
            )
        except TelegramBadRequest:
            pass # Ignore "message is not modified" error
    except Exception as e:
        logging.error(f"Ошибка при отображении стран: {e}")
        try:
            # Reverted to edit_caption as the original media might not be editable to text
            await callback_query.message.edit_caption(caption="Не удалось загрузить список стран.", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]]))
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.startswith("buy_country_page:"))
async def show_countries_paginated(callback_query: types.CallbackQuery, api: SmsActivateWrapper):
    page = int(callback_query.data.split(':')[-1])
    # Re-using the show_countries logic for pagination
    # This requires show_countries to handle being called from a paginated button
    await show_countries(callback_query, api, page=page)


@router.callback_query(F.data.startswith("buy_country:"))
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
            await callback_query.message.edit_text("Для этой страны нет доступных сервисов.", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад к странам", callback_data="buy_menu")]]))
            return

        buttons = []
        for code, details in country_prices.items():
            name = SERVICE_NAME_MAP.get(code, code)
            buttons.append((f"{name} - {details['cost']} RUB", f"buy_service:{code}:{country_id}"))

        keyboard = create_paginated_keyboard(buttons, page, 12, f"buy_service_page:{country_id}", columns=2)
        keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="🔎 Поиск", callback_data=f"search_service:{country_id}")])
        keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="⬅️ Назад к странам", callback_data="buy_menu")])

        try:
            await callback_query.message.edit_media(
                media=types.InputMediaPhoto(media=FSInputFile(IMAGE_SERVICES), caption="Пожалуйста, выберите сервис:"),
                reply_markup=keyboard
            )
        except TelegramBadRequest:
            pass # Ignore "message is not modified" error
    except Exception as e:
        logging.error(f"Ошибка при отображении сервисов: {e}")
        try:
            await callback_query.message.edit_caption(caption="Не удалось загрузить список сервисов.", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад к странам", callback_data="buy_menu")]]))
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.startswith("buy_service:"))
async def purchase_number(callback_query: types.CallbackQuery, db: Database, api: SmsActivateWrapper):
    _, service_code, country_id_str = callback_query.data.split(':')
    country_id = int(country_id_str)
    user_id = callback_query.from_user.id

    # Define a simple keyboard to allow navigation back to the service list
    back_to_services_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад к сервисам", callback_data=f"buy_country:{country_id}")]
    ])

    try:
        # Edit caption but keep a simple keyboard so the user is not stuck
        await callback_query.message.edit_caption("⏳ Обработка покупки...", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[]))
    except TelegramBadRequest:
        return  # Ignore if message is not modified, but stop the handler to prevent re-purchase

    try:
        cost_rub = float(SERVICE_PRICE_CACHE[country_id][service_code]['cost'])
        cost_kopecks = int(cost_rub * 100)
    except Exception as e:
        logging.error(f"Не удалось определить стоимость: {e}")
        try:
            await callback_query.message.edit_caption("Ошибка при проверке цены.", reply_markup=back_to_services_kb)
        except TelegramBadRequest:
            pass
        return

    if not db.create_transaction(user_id, -cost_kopecks, 'purchase', f"Покупка {service_code}"):
        try:
            await callback_query.message.edit_caption("❌ Покупка не удалась! Недостаточно средств.", reply_markup=back_to_services_kb)
        except TelegramBadRequest:
            pass
        return

    try:
        purchase_response = await api.get_number(service_code, country_id)
        if isinstance(purchase_response, dict) and 'activation' in purchase_response:
            act = purchase_response['activation']
            db.log_purchase(user_id, int(act['id']), service_code, str(country_id), act['phone'])
            try:
                # On success, we remove the keyboard as the purchase is complete for this message
                await callback_query.message.edit_caption(
                    f"✅ **Номер получен!**\n\n**Номер:** `{act['phone']}`\n\nОжидаю СМС...",
                    reply_markup=None
                )
            except TelegramBadRequest:
                pass
            asyncio.create_task(poll_for_sms(callback_query.message, int(act['id']), api))
        else:
            db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат: {purchase_response}")
            try:
                await callback_query.message.edit_caption(
                    f"❌ **Ошибка покупки!**\nПричина: `{purchase_response}`. Средства возвращены.",
                    reply_markup=back_to_services_kb
                )
            except TelegramBadRequest:
                pass
    except Exception as e:
        db.create_transaction(user_id, cost_kopecks, 'refund', f"Возврат из-за ошибки: {e}")
        try:
            await callback_query.message.edit_caption(
                "Произошла непредвиденная ошибка. Средства возвращены.",
                reply_markup=back_to_services_kb
            )
        except TelegramBadRequest:
            pass


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

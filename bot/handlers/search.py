import logging
from aiogram import Dispatcher, types
from bot.states import get_user_state, clear_user_state
from bot.utils import create_paginated_keyboard
from bot.handlers.buy_number import COUNTRY_LIST_CACHE, SERVICE_PRICE_CACHE, SERVICE_NAME_MAP
from config import IMAGE_COUNTRIES, IMAGE_SERVICES

async def search_handler(message: types.Message):
    user_id = message.from_user.id
    user_state = get_user_state(user_id)

    if not user_state:
        return # Not in a search state, do nothing

    state = user_state.get('state')
    query = message.text

    # Delete the user's query message and the bot's prompt message to clean up the chat
    try:
        await message.delete()
        # The prompt message ID would need to be stored in the state to be deleted
        # For now, we'll just delete the user's message
    except Exception:
        pass # Ignore if we can't delete

    if state == 'searching_country':
        await handle_country_search(message, query)
    elif state == 'searching_service':
        country_id = user_state.get('context', {}).get('country_id')
        if country_id is not None:
            await handle_service_search(message, query, country_id)

    clear_user_state(user_id)

async def handle_country_search(message: types.Message, query: str):
    filtered_countries = [c for c in COUNTRY_LIST_CACHE if query.lower() in c['rus'].lower()]

    if not filtered_countries:
        await message.answer("По вашему запросу страны не найдены.")
        return

    buttons = [(f"{c['rus']}", f"buy_country:{c['id']}") for c in filtered_countries]
    keyboard = create_paginated_keyboard(buttons, 0, 18, "buy_country_page", columns=3)
    keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="⬅️ Назад к странам", callback_data="buy_menu")])

    await message.answer_photo(
        photo=IMAGE_COUNTRIES,
        caption=f"Результаты поиска по запросу '{query}':",
        reply_markup=keyboard
    )

async def handle_service_search(message: types.Message, query: str, country_id: int):
    country_prices = SERVICE_PRICE_CACHE.get(country_id, {})
    if not country_prices:
        await message.answer("Сначала выберите страну.")
        return

    filtered_services = [
        (sc, dt) for sc, dt in country_prices.items()
        if query.lower() in SERVICE_NAME_MAP.get(sc, sc).lower()
    ]

    if not filtered_services:
        await message.answer("По вашему запросу сервисы не найдены.")
        return

    buttons = []
    for service_code, details in filtered_services:
        full_name = SERVICE_NAME_MAP.get(service_code, service_code)
        button_text = f"{full_name} - {details['cost']} RUB ({details['count']} шт.)"
        buttons.append((button_text, f"buy_service:{service_code}:{country_id}"))

    keyboard = create_paginated_keyboard(buttons, 0, 12, f"buy_service_page:{country_id}", columns=2)
    keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="⬅️ Назад к странам", callback_data="buy_menu")])

    await message.answer_photo(
        photo=IMAGE_SERVICES,
        caption=f"Результаты поиска по запросу '{query}':",
        reply_markup=keyboard
    )

def register_search_handlers(dp: Dispatcher):
    # This handler should only work for users who are in a search state
    dp.register_message_handler(search_handler, content_types=['text'], state="*")

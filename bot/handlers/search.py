import logging
from aiogram import F, Router, types
from aiogram.filters import Filter
from aiogram.types import FSInputFile
from bot.states import get_user_state, set_user_state, clear_user_state
from bot.utils import create_paginated_keyboard
from bot.handlers.buy_number import COUNTRY_LIST_CACHE, SERVICE_PRICE_CACHE, SERVICE_NAME_MAP
from config import IMAGE_COUNTRIES, IMAGE_SERVICES

router = Router()

# --- Custom Filter for State ---
class IsInSearchState(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return get_user_state(message.from_user.id) is not None

# --- Handlers to initiate search ---

@router.callback_query(F.data == "search_country")
async def search_country_prompt(callback_query: types.CallbackQuery):
    """Prompts the user to enter a country name to search for."""
    user_id = callback_query.from_user.id
    set_user_state(user_id, 'searching_country')
    await callback_query.answer("Введите название страны для поиска", show_alert=True)

@router.callback_query(F.data.startswith("search_service:"))
async def search_service_prompt(callback_query: types.CallbackQuery):
    """Prompts the user to enter a service name to search for."""
    user_id = callback_query.from_user.id
    try:
        country_id = int(callback_query.data.split(':')[1])
        set_user_state(user_id, 'searching_service', context={'country_id': country_id})
        await callback_query.answer("Введите название сервиса для поиска", show_alert=True)
    except (ValueError, IndexError):
        await callback_query.answer("Ошибка: неверный ID страны.", show_alert=True)


# --- Main Search Handler ---

@router.message(F.text, IsInSearchState())
async def search_handler(message: types.Message):
    """Handles the user's text input when they are in a search state."""
    user_id = message.from_user.id
    user_state = get_user_state(user_id) # We know state is not None because of the filter

    state = user_state.get('state')
    query = message.text

    # Delete the user's query message to keep the chat clean
    try:
        await message.delete()
    except Exception:
        pass # Ignore if we can't delete (e.g., not enough rights)

    if state == 'searching_country':
        await handle_country_search(message, query)
    elif state == 'searching_service':
        country_id = user_state.get('context', {}).get('country_id')
        if country_id is not None:
            await handle_service_search(message, query, country_id)

    clear_user_state(user_id) # Clear state after handling the search

async def handle_country_search(message: types.Message, query: str):
    """Performs the country search and sends the results."""
    filtered_countries = [c for c in COUNTRY_LIST_CACHE if query.lower() in c['rus'].lower()]

    if not filtered_countries:
        await message.answer("По вашему запросу страны не найдены.")
        return

    buttons = [(f"{c['rus']}", f"buy_country:{c['id']}") for c in filtered_countries]
    keyboard = create_paginated_keyboard(buttons, 0, 18, "buy_country_page", columns=3)
    keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="⬅️ Назад к странам", callback_data="buy_menu")])

    await message.answer_photo(
        photo=FSInputFile(IMAGE_COUNTRIES),
        caption=f"Результаты поиска по запросу '{query}':",
        reply_markup=keyboard
    )

async def handle_service_search(message: types.Message, query: str, country_id: int):
    """Performs the service search and sends the results."""
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
        button_text = f"{full_name} - {details['cost']} RUB"
        buttons.append((button_text, f"buy_service:{service_code}:{country_id}"))

    keyboard = create_paginated_keyboard(buttons, 0, 12, f"buy_service_page:{country_id}", columns=2)
    keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="⬅️ Назад к сервисам", callback_data=f"buy_country:{country_id}")])

    await message.answer_photo(
        photo=FSInputFile(IMAGE_SERVICES),
        caption=f"Результаты поиска по запросу '{query}':",
        reply_markup=keyboard
    )

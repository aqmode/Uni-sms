import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton
from pyrogram.handlers import MessageHandler
from bot.states import get_user_state, clear_user_state
from bot.utils import create_paginated_keyboard
from bot.handlers.buy_number import COUNTRY_LIST_CACHE, SERVICE_PRICE_CACHE, SERVICE_NAME_MAP
from config import IMAGE_COUNTRIES, IMAGE_SERVICES

class SearchHandlers:
    def __init__(self):
        # This handler doesn't need db or api access, just state and caches
        pass

    def get_handlers(self):
        return [
            MessageHandler(self.search_handler, filters.text),
        ]

    async def search_handler(self, client: Client, message: Message):
        if message.command:
            return # Ignore commands
        user_id = message.from_user.id
        user_state = get_user_state(user_id)

        if not user_state:
            return # Not in a search state, do nothing

        state = user_state.get('state')
        query = message.text

        if state == 'searching_country':
            await self.handle_country_search(message, query)
        elif state == 'searching_service':
            country_id = user_state.get('context', {}).get('country_id')
            if country_id is not None:
                await self.handle_service_search(message, query, country_id)

        # Clear state after handling the search
        clear_user_state(user_id)

    async def handle_country_search(self, message: Message, query: str):
        filtered_countries = [c for c in COUNTRY_LIST_CACHE if query.lower() in c['rus'].lower()]

        if not filtered_countries:
            await message.reply_text("По вашему запросу страны не найдены.")
            return

        buttons = [(f"{c['rus']}", f"buy_country:{c['id']}") for c in filtered_countries]
        keyboard = create_paginated_keyboard(buttons, 0, 18, "buy_country_page", columns=3)
        keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад к странам", callback_data="buy_menu")])
        await message.reply_photo(
            photo=IMAGE_COUNTRIES,
            caption=f"Результаты поиска по запросу '{query}':",
            reply_markup=keyboard
        )

    async def handle_service_search(self, message: Message, query: str, country_id: int):
        country_prices = SERVICE_PRICE_CACHE.get(country_id, {})
        if not country_prices:
            await message.reply_text("Сначала выберите страну.")
            return

        filtered_services = [
            (sc, dt) for sc, dt in country_prices.items()
            if query.lower() in SERVICE_NAME_MAP.get(sc, sc).lower()
        ]

        if not filtered_services:
            await message.reply_text("По вашему запросу сервисы не найдены.")
            return

        buttons = []
        for service_code, details in filtered_services:
            full_name = SERVICE_NAME_MAP.get(service_code, service_code)
            button_text = f"{full_name} - {details['cost']} RUB ({details['count']} шт.)"
            buttons.append((button_text, f"buy_service:{service_code}:{country_id}"))

        keyboard = create_paginated_keyboard(buttons, 0, 12, f"buy_service_page:{country_id}", columns=2)
        keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад к странам", callback_data="buy_menu")])
        await message.reply_photo(
            photo=IMAGE_SERVICES,
            caption=f"Результаты поиска по запросу '{query}':",
            reply_markup=keyboard
        )

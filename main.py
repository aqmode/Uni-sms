import asyncio
import logging
import sys
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Import config and perform startup check
try:
    from config import BOT_TOKEN, ADMIN_ID
    if not all([BOT_TOKEN, ADMIN_ID]):
        raise ImportError
except ImportError:
    print("!!! ОШИБКА: НЕОБХОДИМА НАСТРОЙКА !!!")
    print("Пожалуйста, выполните следующие шаги:")
    print("1. Скопируйте файл `settings.py.example` и переименуйте его в `settings.py`.")
    print("2. Откройте `settings.py` и впишите ваши данные.")
    print("3. Сохраните файл и запустите бота снова.")
    sys.exit("Бот не может быть запущен без полной конфигурации.")

# Import other components
from bot.api import SmsActivateWrapper
from bot.db import Database
from bot.handlers import all_routers  # We will create this combined router in a later step

# Middleware for dependency injection
class DependencyMiddleware:
    def __init__(self, db: Database, api: SmsActivateWrapper):
        self.db = db
        self.api = api

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Pass db and api instances to the handler data
        data["db"] = self.db
        data["api"] = self.api
        return await handler(event, data)


async def main() -> None:
    """Initializes and starts the bot."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

    # Initialize Dispatcher
    dp = Dispatcher()

    # Initialize API and DB
    db = Database()
    api = SmsActivateWrapper()

    # Register middleware for dependency injection
    dp.update.middleware(DependencyMiddleware(db=db, api=api))

    # Include all routers from the handlers package
    dp.include_router(all_routers)

    logging.info("Все обработчики успешно зарегистрированы.")
    logging.info("Запуск бота...")
    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")

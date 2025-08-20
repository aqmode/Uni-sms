import logging
import sys
from aiogram import Bot, Dispatcher, executor, types

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
from bot.handlers.start import register_start_handlers
from bot.handlers.balance import register_balance_handlers
from bot.handlers.buy_number import register_buy_handlers
from bot.handlers.history import register_history_handlers
from bot.handlers.billing import register_billing_handlers
from bot.handlers.admin import register_admin_handlers
from bot.handlers.search import register_search_handlers

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.MARKDOWN)
dp = Dispatcher(bot)

# Initialize API and DB
db = Database()
api = SmsActivateWrapper()

def register_all_handlers(dispatcher: Dispatcher):
    """Registers all handlers for the bot."""
    register_start_handlers(dispatcher, db)
    register_balance_handlers(dispatcher, db, api)
    register_buy_handlers(dispatcher, db, api)
    register_history_handlers(dispatcher, db)
    register_billing_handlers(dispatcher)
    register_admin_handlers(dispatcher, db)
    register_search_handlers(dispatcher)

    logging.info("Все обработчики успешно зарегистрированы.")


async def on_startup(dispatcher):
    logging.info("Регистрация обработчиков...")
    register_all_handlers(dispatcher)
    logging.info("Запуск бота...")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

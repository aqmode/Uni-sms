# Этот файл является главной точкой входа для запуска Telegram-бота.
# Он инициализирует клиент бота, регистрирует все обработчики команд
# и запускает бота в режим постоянной работы.

import logging
import sys
from pyrogram import Client

# Импортируем переменные настроек и проверяем их наличие до всего остального
try:
    from config import BOT_TOKEN, ADMIN_ID, API_ID, API_HASH, SMS_ACTIVATE_API_KEY
    if not all([BOT_TOKEN, ADMIN_ID, API_ID, API_HASH, SMS_ACTIVATE_API_KEY]):
        raise ImportError
except ImportError:
    print("!!! ОШИБКА: НЕОБХОДИМА НАСТРОЙКА !!!")
    print("Пожалуйста, выполните следующие шаги:")
    print("1. Скопируйте файл `settings.py.example` и переименуйте его в `settings.py`.")
    print("2. Откройте `settings.py` и впишите ваши данные (API_ID, API_HASH, BOT_TOKEN и т.д.).")
    print("3. Сохраните файл и запустите бота снова.")
    sys.exit("Бот не может быть запущен без полной конфигурации.")

# Импортируем остальные компоненты
from bot.api import SmsActivateWrapper
from bot.db import Database
from bot.handlers.start import StartHandlers
from bot.handlers.balance import BalanceHandlers
from bot.handlers.buy_number import BuyNumberHandlers
# from bot.handlers.rent_number import RentNumberHandlers # Temporarily disabled
from bot.handlers.history import HistoryHandlers
from bot.handlers.billing import BillingHandlers
from bot.handlers.admin import AdminHandlers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class UniSMSBot(Client):
    def __init__(self):
        super().__init__(
            "uni_sms_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
        self.db = Database()
        self.api = SmsActivateWrapper() # Используем новый API

    def register_handlers(self):
        """Registers all handlers for the bot."""
        handler_classes = [
            StartHandlers(self.db),
            BalanceHandlers(self.db, self.api),
            BuyNumberHandlers(self.db, self.api),
            # RentNumberHandlers(self.db, self.api), # Temporarily disabled
            HistoryHandlers(self.db),
            BillingHandlers(),
            AdminHandlers(self.db),
        ]

        for handler_class in handler_classes:
            for handler in handler_class.get_handlers():
                self.add_handler(handler)

        logging.info("Обработчики успешно зарегистрированы.")

    def run(self):
        """Runs the bot by registering handlers and then starting the client."""
        logging.info("Регистрация обработчиков...")
        self.register_handlers()
        logging.info("Запуск бота...")
        super().run()


if __name__ == "__main__":
    bot = UniSMSBot()
    bot.run()

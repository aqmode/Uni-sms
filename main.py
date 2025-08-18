import logging
from pyrogram import Client
from bot.api import OnlineSimAPI
from bot.db import Database
from config import API_ID, API_HASH, BOT_TOKEN
from bot.handlers.start import StartHandlers
from bot.handlers.balance import BalanceHandlers
from bot.handlers.buy_number import BuyNumberHandlers
from bot.handlers.rent_number import RentNumberHandlers
from bot.handlers.free_numbers import FreeNumbersHandlers
from bot.handlers.support import SupportHandlers
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
        self.online_sim_api = OnlineSimAPI()

    def register_handlers(self):
        """Registers all handlers for the bot."""
        handler_classes = [
            StartHandlers(self.db),
            BalanceHandlers(self.db, self.online_sim_api),
            BuyNumberHandlers(self.db, self.online_sim_api),
            RentNumberHandlers(self.db, self.online_sim_api),
            FreeNumbersHandlers(self.online_sim_api),
            SupportHandlers(),
            HistoryHandlers(self.db),
            BillingHandlers(),
            AdminHandlers(self.db),
        ]

        for handler_class in handler_classes:
            for handler in handler_class.get_handlers():
                self.add_handler(handler)

        logging.info("Handlers registered successfully.")

    def run(self):
        """Runs the bot by registering handlers and then starting the client."""
        logging.info("Registering handlers...")
        self.register_handlers()
        logging.info("Starting bot...")
        super().run()


if __name__ == "__main__":
    bot = UniSMSBot()
    bot.run()

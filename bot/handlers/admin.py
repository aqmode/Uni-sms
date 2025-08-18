import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
from bot.db import Database
from config import ADMIN_ID

class AdminHandlers:
    def __init__(self, db: Database):
        self.db = db
        self.admin_id = int(ADMIN_ID)

    def get_handlers(self):
        return [
            MessageHandler(self.credit_handler, filters.command("credit") & filters.user(self.admin_id)),
            MessageHandler(self.check_balance_handler, filters.command("user_balance") & filters.user(self.admin_id)),
        ]

    async def check_balance_handler(self, client: Client, message: Message):
        """
        Checks the balance of a specific user.
        Usage: /user_balance <user_telegram_id>
        """
        try:
            _, user_id_str = message.text.split()
            user_id = int(user_id_str)

            balance_kopecks = self.db.get_user_balance(user_id)
            balance_rub = balance_kopecks / 100.0

            await message.reply_text(f"Balance for user `{user_id}` is: **{balance_rub:.2f} RUB**.")

        except ValueError:
            await message.reply_text("Invalid format. Use: `/user_balance <user_id>`")
        except Exception as e:
            logging.error(f"Error in /user_balance command: {e}")
            await message.reply_text(f"An error occurred: {e}")

    async def credit_handler(self, client: Client, message: Message):
        """
        Manually credits a user's account.
        Usage: /credit <user_telegram_id> <amount_in_rub>
        Example: /credit 123456789 500.50
        """
        try:
            _, user_id_str, amount_str = message.text.split()
            user_id = int(user_id_str)
            amount_rub = float(amount_str)
            amount_kopecks = int(amount_rub * 100)

            if amount_kopecks <= 0:
                await message.reply_text("Amount must be positive.")
                return

            success = self.db.create_transaction(
                user_telegram_id=user_id,
                amount=amount_kopecks,
                type='deposit',
                details=f"Manual credit by admin {self.admin_id}"
            )

            if success:
                await message.reply_text(f"Successfully credited {amount_rub:.2f} RUB to user {user_id}.")
                # Notify the user
                try:
                    await client.send_message(
                        user_id,
                        f"Your balance has been topped up by **{amount_rub:.2f} RUB**."
                    )
                except Exception as e:
                    await message.reply_text(f"Could not notify user {user_id} (they may have blocked the bot). Error: {e}")
            else:
                await message.reply_text(f"Failed to credit user {user_id}. Check logs.")

        except ValueError:
            await message.reply_text("Invalid command format. Use: `/credit <user_id> <amount>`")
        except Exception as e:
            logging.error(f"Error in /credit command: {e}")
            await message.reply_text(f"An error occurred: {e}")

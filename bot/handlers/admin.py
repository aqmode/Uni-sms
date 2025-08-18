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
        Проверяет баланс указанного пользователя.
        Использование: /user_balance <user_telegram_id>
        """
        try:
            _, user_id_str = message.text.split()
            user_id = int(user_id_str)

            balance_kopecks = self.db.get_user_balance(user_id)
            balance_rub = balance_kopecks / 100.0

            await message.reply_text(f"Баланс пользователя `{user_id}`: **{balance_rub:.2f} RUB**.")

        except ValueError:
            await message.reply_text("Неверный формат. Используйте: `/user_balance <user_id>`")
        except Exception as e:
            logging.error(f"Ошибка в команде /user_balance: {e}")
            await message.reply_text(f"Произошла ошибка: {e}")

    async def credit_handler(self, client: Client, message: Message):
        """
        Пополняет счет пользователя вручную.
        Использование: /credit <user_telegram_id> <сумма_в_рублях>
        Пример: /credit 123456789 500.50
        """
        try:
            _, user_id_str, amount_str = message.text.split()
            user_id = int(user_id_str)
            amount_rub = float(amount_str)
            amount_kopecks = int(amount_rub * 100)

            if amount_kopecks <= 0:
                await message.reply_text("Сумма должна быть положительной.")
                return

            success = self.db.create_transaction(
                user_telegram_id=user_id,
                amount=amount_kopecks,
                type='deposit',
                details=f"Ручное пополнение администратором {self.admin_id}"
            )

            if success:
                await message.reply_text(f"Баланс пользователя {user_id} успешно пополнен на {amount_rub:.2f} RUB.")
                try:
                    await client.send_message(
                        user_id,
                        f"Ваш баланс был пополнен на **{amount_rub:.2f} RUB**."
                    )
                except Exception as e:
                    await message.reply_text(f"Не удалось уведомить пользователя {user_id} (возможно, он заблокировал бота). Ошибка: {e}")
            else:
                await message.reply_text(f"Не удалось пополнить баланс пользователя {user_id}. Проверьте логи.")

        except ValueError:
            await message.reply_text("Неверный формат. Используйте: `/credit <user_id> <сумма>`")
        except Exception as e:
            logging.error(f"Ошибка в команде /credit: {e}")
            await message.reply_text(f"Произошла ошибка: {e}")

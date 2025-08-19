from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    """
    Возвращает клавиатуру главного меню.
    """
    keyboard = [
        [
            InlineKeyboardButton("🛒 Купить номер", callback_data="buy_menu"),
            InlineKeyboardButton("🗓 Арендовать номер", callback_data="rent_menu"),
        ],
        [
            InlineKeyboardButton("👤 Мой кабинет", callback_data="account_menu"),
        ],
        [
            InlineKeyboardButton("💬 Техподдержка", callback_data="support"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def account_menu_keyboard():
    """
    Возвращает клавиатуру личного кабинета.
    """
    keyboard = [
        [
            InlineKeyboardButton("💰 Баланс", callback_data="check_balance"),
            InlineKeyboardButton("➕ Пополнить", callback_data="top_up_balance"),
        ],
        [
            InlineKeyboardButton("📚 История операций", callback_data="history_menu"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="main_menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

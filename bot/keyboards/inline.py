from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    """
    Возвращает клавиатуру главного меню.
    """
    keyboard = [
        [
            InlineKeyboardButton(text="🛒 Купить номер", callback_data="buy_menu"),
        ],
        [
            InlineKeyboardButton(text="👤 Мой кабинет", callback_data="account_menu"),
        ],
        # Support feature is disabled for now
        # [
        #     InlineKeyboardButton(text="💬 Техподдержка", callback_data="support"),
        # ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def account_menu_keyboard():
    """
    Возвращает клавиатуру личного кабинета.
    """
    keyboard = [
        [
            InlineKeyboardButton(text="💰 Баланс", callback_data="check_balance"),
            InlineKeyboardButton(text="➕ Пополнить", callback_data="top_up_balance"),
        ],
        [
            InlineKeyboardButton(text="📚 История операций", callback_data="history_menu"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в главное меню", callback_data="main_menu"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

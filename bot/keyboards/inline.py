from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    """
    Returns the main menu keyboard.
    """
    keyboard = [
        [
            InlineKeyboardButton("🛒 Buy Number", callback_data="buy_menu"),
            InlineKeyboardButton("🗓 Rent Number", callback_data="rent_menu"),
        ],
        [
            InlineKeyboardButton("🆓 Free Numbers", callback_data="free_numbers_menu"),
            InlineKeyboardButton("👤 My Account", callback_data="account_menu"),
        ],
        [
            InlineKeyboardButton("💬 Support", callback_data="support"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def account_menu_keyboard():
    """
    Returns the account menu keyboard.
    """
    keyboard = [
        [
            InlineKeyboardButton("💰 Balance", callback_data="check_balance"),
            InlineKeyboardButton("➕ Top-up Balance", callback_data="top_up_balance"),
        ],
        [
            InlineKeyboardButton("📚 History", callback_data="history_menu"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def create_paginated_keyboard(buttons, page, page_size, callback_prefix):
    """
    Creates a paginated inline keyboard.

    :param buttons: A list of (text, callback_data) tuples.
    :param page: The current page number (0-indexed).
    :param page_size: The number of items per page.
    :param callback_prefix: A prefix for the pagination callbacks.
    :return: An InlineKeyboardMarkup.
    """
    start = page * page_size
    end = start + page_size

    keyboard = [
        [InlineKeyboardButton(text, callback_data=data)]
        for text, data in buttons[start:end]
    ]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"{callback_prefix}:{page-1}"))
    if end < len(buttons):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"{callback_prefix}:{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(keyboard)

import os

# This file manages the bot's configuration.
# It prioritizes settings from a user-friendly `settings.py` file.
# If `settings.py` is not found, it falls back to environment variables.

try:
    # User-friendly configuration from a file
    from settings import API_ID, API_HASH, BOT_TOKEN, SMS_ACTIVATE_API_KEY, ADMIN_ID

    # Simple validation to check if the user has filled out the settings
    if BOT_TOKEN == "YOUR_BOT_TOKEN" or ADMIN_ID == 0:
        # Set to None to be caught by the startup check in main.py
        BOT_TOKEN = None
        ADMIN_ID = None

    if SMS_ACTIVATE_API_KEY == "YOUR_SMS_ACTIVATE_API_KEY":
        SMS_ACTIVATE_API_KEY = None

except ImportError:
    # Fallback for server deployment using environment variables
    API_ID = os.environ.get("API_ID")
    API_HASH = os.environ.get("API_HASH")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    SMS_ACTIVATE_API_KEY = os.environ.get("SMS_ACTIVATE_API_KEY")
    ADMIN_ID = os.environ.get("ADMIN_ID")

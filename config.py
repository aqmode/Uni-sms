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

# --- Image File Paths ---
# Path to the images that will be used as headers in the bot menus.
# These files should be in the main project directory.
IMAGE_MAIN_MENU = "Без названия1_20250819065633.png"
IMAGE_PROFILE = "Без названия1_20250819065108.png"
IMAGE_COUNTRIES = "Без названия1_20250819065207.png"
IMAGE_SERVICES = "Без названия1_20250819065055.png"

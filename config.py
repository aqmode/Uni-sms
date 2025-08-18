import os

API_ID = os.environ.get("API_ID", "25534167")
API_HASH = os.environ.get("API_HASH", "a03ad3366f412b5e881b5f9ffd551f75")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8133768979:AAFPtTyzcLacDFYcej7N_y9mO9qqu6DsQrU")
ONLINE_SIM_API_KEY = os.environ.get("ONLINE_SIM_API_KEY", "93GKxXEXX2pw4fk-qqH3A26D-xSux7Y5D-mAg739n8-u1N7k1xe2LA25uw")

# For the support feature
ADMIN_ID = os.environ.get("ADMIN_ID") # Add your telegram user ID here
assert ADMIN_ID, "Please set the ADMIN_ID environment variable"

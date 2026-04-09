import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN: raise ValueError("BOT_TOKEN не задан")

ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
if not CRYPTOBOT_TOKEN: raise ValueError("CRYPTOBOT_TOKEN не задан")

CRYPTO_CURRENCY = os.getenv("CRYPTO_CURRENCY", "USDT")
ADMIN_LOG_CHAT_IDS = [int(x.strip()) for x in os.getenv("ADMIN_LOG_CHAT_IDS", "").split(",") if x.strip()]
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
PRODUCTS_PER_PAGE = 5
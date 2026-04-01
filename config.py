import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")

ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
if not CRYPTOBOT_TOKEN:
    raise ValueError("CRYPTOBOT_TOKEN не задан")

CRYPTO_CURRENCY = os.getenv("CRYPTO_CURRENCY", "USDT")
ADMIN_LOG_CHAT_IDS = [int(x.strip()) for x in os.getenv("ADMIN_LOG_CHAT_IDS", "").split(",") if x.strip()]

# Кастомные эмодзи
CUSTOM_EMOJI_IDS = {
    "catalog": "6019248093835302806",
    "my purchases": "6021650913289050282",
    "my referrals": "5298668674532538341",
    "main menu": "6039539366177541657",
    "pay": "5255933397750014894",
    "go to payment": "5195058841988914267",
    "check payment": "5197653448912293869"
}
CUSTOM_EMOJIS = {key: f'<tg-emoji emoji-id="{CUSTOM_EMOJI_IDS[key]}">😎</tg-emoji>' for key in CUSTOM_EMOJI_IDS}
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

# Ваши кастомные эмодзи
CUSTOM_EMOJI = {
    "catalog": "6019248093835302806",
    "my_purchases": "6021650913289050282",
    "my_referrals": "5298668674532538341",
    "main_menu": "6039539366177541657",
    "pay": "5255933397750014894",
    "payment": "5195058841988914267",      # для кнопки "Перейти к оплате"
    "check": "5197653448912293869",        # для кнопки "Проверить оплату"
    "back": "6039539366177541657",         # для кнопок "Назад" – можно использовать тот же ID
    # Для админ‑меню можно добавить свои ID, но если их нет – кнопки будут без иконок
}

# ID канала для проверки подписки (обязателен, если проверка включена)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
import asyncio
import logging
from aiogram import Bot
from config import BOT_TOKEN
from handlers import dp
from models import init_db

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())     
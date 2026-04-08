from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("✅ Бот работает!")
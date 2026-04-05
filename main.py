import asyncio
import logging
from aiogram import Bot
from aiohttp import web
from config import BOT_TOKEN, WEBHOOK_PORT, WEBHOOK_HOST  # добавим новые переменные
from handlers import dp
from models import SessionLocal, User, Product, Session as SessionModel, Purchase, Invoice

# ---------- Веб‑сервер для API ----------
async def handle_stats(request):
    with SessionLocal() as db:
        total_users = db.query(User).count()
        total_products = db.query(Product).count()
        total_sessions = db.query(SessionModel).count()
        sold_sessions = db.query(SessionModel).filter_by(is_sold=True).count()
        total_purchases = db.query(Purchase).count()
        total_deposits = db.query(Invoice).filter_by(is_deposit=True, status="paid").with_entities(func.sum(Invoice.amount)).scalar() or 0
        stats = {
            "total_users": total_users,
            "total_products": total_products,
            "total_sessions": total_sessions,
            "sold_sessions": sold_sessions,
            "total_purchases": total_purchases,
            "total_deposits": total_deposits,
            "bot_username": (await bot.get_me()).username,
            "status": "online"
        }
    return web.json_response(stats)

async def init_web():
    app = web.Application()
    app.router.add_get('/stats', handle_stats)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    print(f"Web server started on port {WEBHOOK_PORT}")

# ---------- Основной запуск ----------
async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    # Запускаем веб‑сервер в фоне
    asyncio.create_task(init_web())
    # Запускаем бота (поллинг)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
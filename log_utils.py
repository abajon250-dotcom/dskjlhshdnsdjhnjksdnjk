from datetime import datetime
from models import SessionLocal, User, Log
from config import ADMIN_LOG_CHAT_IDS

async def log_action(bot, tg_id: int, action: str, details: str = None):
    with SessionLocal() as db:
        user = db.query(User).filter_by(tg_id=tg_id).first()
        if not user:
            user = User(tg_id=tg_id)
            db.add(user)
            db.flush()
        log = Log(user_id=user.id, action=action, details=details)
        db.add(log)
        db.commit()

        username = user.username or f"id{user.tg_id}"
        full_name = user.full_name or ""
        text = f"🔄 <b>Действие</b>\n👤 {full_name} (@{username}) [ID {tg_id}]\n📌 {action}\n📝 {details or '—'}\n🕒 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        for chat_id in ADMIN_LOG_CHAT_IDS:
            try:
                await bot.send_message(chat_id, text, parse_mode="HTML")
            except Exception as e:
                print(f"Ошибка отправки лога в чат {chat_id}: {e}")
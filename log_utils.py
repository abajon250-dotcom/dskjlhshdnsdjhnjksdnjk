from datetime import datetime
from models import SessionLocal, User, Log
from config import ADMIN_LOG_CHAT_IDS


async def log_action(bot, tg_id: int, action: str, details: str = None, username: str = None, full_name: str = None):
    """
    Логирует действие пользователя.
    - Сохраняет в БД таблицу logs.
    - Отправляет сообщение во все ADMIN_LOG_CHAT_IDS.
    """
    with SessionLocal() as db:
        # Ищем пользователя в БД
        user = db.query(User).filter_by(tg_id=tg_id).first()
        if not user:
            # Если нет, создаём запись с переданными именем и username
            user = User(tg_id=tg_id, username=username, full_name=full_name)
            db.add(user)
            db.flush()
        else:
            # Обновляем поля, если они пустые и переданы новые значения
            if username and not user.username:
                user.username = username
            if full_name and not user.full_name:
                user.full_name = full_name
            db.commit()

        # Сохраняем лог
        log = Log(user_id=user.id, action=action, details=details)
        db.add(log)
        db.commit()

        # Формируем красивое сообщение для админов
        display_username = user.username or username or f"id{user.tg_id}"
        display_full_name = user.full_name or full_name or "Не указан"
        safe_details = details.replace("<", "&lt;").replace(">", "&gt;") if details else "—"
        text = (
            f"🔄 <b>Действие пользователя</b>\n"
            f"👤 <b>Имя:</b> {display_full_name}\n"
            f"🆔 <b>Username:</b> @{display_username}\n"
            f"🔢 <b>Telegram ID:</b> <code>{user.tg_id}</code>\n"
            f"📌 <b>Действие:</b> {action}\n"
            f"📝 <b>Подробности:</b> {safe_details}\n"
            f"🕒 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        for chat_id in ADMIN_LOG_CHAT_IDS:
            try:
                await bot.send_message(chat_id, text, parse_mode="HTML")
            except Exception as e:
                print(f"Ошибка отправки лога в чат {chat_id}: {e}")
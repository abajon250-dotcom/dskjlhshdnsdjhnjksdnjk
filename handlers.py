import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile
from sqlalchemy import func
import keyboards as kb
import models
import crypto_api
from config import ADMIN_IDS, CRYPTO_CURRENCY, CUSTOM_EMOJIS
from log_utils import log_action

dp = Dispatcher()

# ------------------ FSM ------------------
class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    currency = State()

class ToggleProductActive(StatesGroup):
    product_id = State()

class AddTdataSession(StatesGroup):
    product_id = State()
    contacts_count = State()
    waiting_file = State()

class AddTextSession(StatesGroup):
    product_id = State()
    contacts_count = State()
    text_data = State()

class Broadcast(StatesGroup):
    text = State()

# ------------------ Helper ------------------
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def emoji_tag(emoji_id: str) -> str:
    """Возвращает HTML-тег для кастомного эмодзи"""
    return f'<tg-emoji emoji-id="{emoji_id}"></tg-emoji>'

# ------------------ Основные команды ------------------
@dp.message(Command("start"))
async def start_cmd(message: types.Message, bot: Bot):
    user_id = message.from_user.id

    # Обработка реферальной ссылки
    ref_param = None
    if message.text and len(message.text.split()) > 1:
        ref_param = message.text.split()[1]
        if ref_param.startswith("ref_"):
            try:
                referrer_id = int(ref_param[4:])
                if referrer_id != user_id:
                    with models.SessionLocal() as db:
                        referrer = db.query(models.User).filter_by(tg_id=referrer_id).first()
                        if referrer:
                            user = db.query(models.User).filter_by(tg_id=user_id).first()
                            if not user:
                                user = models.User(
                                    tg_id=user_id,
                                    username=message.from_user.username,
                                    full_name=message.from_user.full_name,
                                    referred_by=referrer_id
                                )
                                db.add(user)
                                db.commit()
                            else:
                                if not user.referred_by:
                                    user.referred_by = referrer_id
                                    db.commit()
            except ValueError:
                pass

    # Регистрация пользователя (если ещё не был)
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            user = models.User(
                tg_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
            db.add(user)
            db.commit()
        # Если реферал был указан, но пользователь уже существовал без реферала
        if ref_param and ref_param.startswith("ref_") and not user.referred_by:
            try:
                referrer_id = int(ref_param[4:])
                if referrer_id != user_id:
                    referrer = db.query(models.User).filter_by(tg_id=referrer_id).first()
                    if referrer:
                        user.referred_by = referrer_id
                        db.commit()
            except:
                pass

    await log_action(bot, user_id, "/start", "Запустил бота")
    await message.answer(
        f"{CUSTOM_EMOJIS.get('main_menu', '')} Добро пожаловать! Выберите действие:",
        parse_mode="HTML",
        reply_markup=kb.main_menu_keyboard()
    )

@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery, bot: Bot):
    await log_action(bot, callback.from_user.id, "main_menu", "Главное меню")
    await callback.message.edit_text("Главное меню:", reply_markup=kb.main_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery, bot: Bot):
    await log_action(bot, callback.from_user.id, "catalog", "Открыл каталог")
    with models.SessionLocal() as db:
        products = db.query(models.Product).filter_by(is_active=True).all()
        if not products:
            await callback.message.edit_text("Товаров пока нет.")
            return
        await callback.message.edit_text("Выберите товар:", reply_markup=kb.catalog_keyboard(products))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_product(callback: types.CallbackQuery, bot: Bot):
    product_id = int(callback.data.split("_")[1])
    await log_action(bot, callback.from_user.id, "buy_product", f"Товар ID {product_id}")
    with models.SessionLocal() as db:
        product = db.query(models.Product).filter_by(id=product_id, is_active=True).first()
        if not product:
            await callback.message.edit_text("Товар не найден.")
            return
        free_sessions = db.query(models.Session).filter(
            models.Session.product_id == product_id,
            models.Session.is_sold == False
        ).all()
        if not free_sessions:
            await callback.message.edit_text("К сожалению, товар временно отсутствует.")
            return
        min_contacts = min(s.contacts_count for s in free_sessions)
        max_contacts = max(s.contacts_count for s in free_sessions)
        text = f"<b>{product.name}</b>\n\n{product.description}\n\n"
        text += f"Контактов: от {min_contacts} до {max_contacts}\n"
        text += f"Цена: {product.price} {product.currency}\n\n"
        text += "После оплаты вы получите доступ к аккаунту."
        await callback.message.edit_text(text, reply_markup=kb.product_detail_keyboard(product_id), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def create_invoice(callback: types.CallbackQuery, bot: Bot):
    product_id = int(callback.data.split("_")[1])
    await log_action(bot, callback.from_user.id, "create_invoice", f"Создание счёта для товара ID {product_id}")
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=callback.from_user.id).first()
        if not user:
            user = models.User(tg_id=callback.from_user.id, username=callback.from_user.username, full_name=callback.from_user.full_name)
            db.add(user)
            db.commit()
        product = db.query(models.Product).filter_by(id=product_id, is_active=True).first()
        if not product:
            await callback.message.edit_text("Товар не найден.")
            return
        free_session = db.query(models.Session).filter(
            models.Session.product_id == product_id,
            models.Session.is_sold == False
        ).first()
        if not free_session:
            await callback.message.edit_text("Товар закончился.")
            return
        try:
            invoice_id, pay_url = await crypto_api.create_invoice(product.price, product.currency)
        except Exception as e:
            await callback.message.edit_text(f"Ошибка при создании счёта: {e}")
            return
        invoice = models.Invoice(
            user_id=user.id,
            product_id=product_id,
            crypto_invoice_id=invoice_id,
            amount=product.price,
            currency=product.currency,
            status="active"
        )
        db.add(invoice)
        db.commit()
        await callback.message.edit_text(
            f"Счёт создан на сумму {product.price} {product.currency}\n\n"
            f"Оплатите по ссылке ниже, затем нажмите «Проверить оплату».",
            reply_markup=kb.invoice_keyboard(pay_url, invoice.id)
        )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery, bot: Bot):
    invoice_db_id = int(callback.data.split("_")[1])
    await log_action(bot, callback.from_user.id, "check_payment", f"Проверка счёта #{invoice_db_id}")
    with models.SessionLocal() as db:
        invoice = db.query(models.Invoice).filter_by(id=invoice_db_id).first()
        if not invoice:
            await callback.message.edit_text("Счёт не найден.")
            return
        if invoice.status == "paid":
            await callback.message.edit_text("Этот счёт уже оплачен.")
            return
        status = await crypto_api.check_invoice_status(invoice.crypto_invoice_id)
        if status == "paid":
            invoice.status = "paid"
            invoice.paid_at = datetime.utcnow()
            # Ищем свободную сессию
            session = db.query(models.Session).filter(
                models.Session.product_id == invoice.product_id,
                models.Session.is_sold == False
            ).first()
            if not session:
                await callback.message.edit_text("Ошибка: нет свободных сессий для этого товара. Обратитесь к администратору.")
                await log_action(bot, callback.from_user.id, "no_session", f"Нет сессии для товара ID {invoice.product_id}")
                return
            session.is_sold = True
            purchase = models.Purchase(
                user_id=invoice.user_id,
                product_id=invoice.product_id,
                session_id=session.id
            )
            db.add(purchase)

            # Начисление реферального бонуса (если это первая покупка пользователя)
            user = db.query(models.User).filter_by(id=invoice.user_id).first()
            purchases_count = db.query(models.Purchase).filter_by(user_id=user.id).count()
            if purchases_count == 0 and user.referred_by and user.referred_by != user.tg_id:
                referrer = db.query(models.User).filter_by(tg_id=user.referred_by).first()
                if referrer:
                    bonus = invoice.amount * 0.10
                    referrer.referral_balance += bonus
                    referrer.total_referral_earnings += bonus
                    referrer.referral_count += 1
                    db.commit()
                    try:
                        await bot.send_message(
                            referrer.tg_id,
                            f"🎉 Ваш реферал @{user.username or user.tg_id} совершил первую покупку на {invoice.amount} {invoice.currency}!\n"
                            f"Вы получили бонус: {bonus} {invoice.currency}.\n"
                            f"Ваш бонусный баланс: {referrer.referral_balance:.2f} {invoice.currency}"
                        )
                    except Exception as e:
                        print(f"Не удалось отправить сообщение рефереру: {e}")

            # Сохраняем покупку
            db.commit()

            # Отправка в зависимости от типа сессии
            if session.is_file and session.file_data:
                await bot.send_document(
                    callback.message.chat.id,
                    document=BufferedInputFile(session.file_data, filename=session.filename),
                    caption=f"✅ Оплата получена!\n\nВаш {invoice.product.name}\nКонтактов: {session.contacts_count}"
                )
                instruction = (
                    "📱 *Инструкция для ПК (Windows):*\n"
                    "1. Скачайте Telegram Desktop.\n"
                    "2. Замените папку tdata в %AppData%\\Telegram Desktop\\ на полученную.\n"
                    "3. Запустите Telegram Desktop, войдите автоматически.\n\n"
                    "📱 *Инструкция для Android:*\n"
                    "1. Установите Telegram.\n"
                    "2. Скопируйте папку tdata в /storage/emulated/0/Telegram/ (или в папку приложения).\n"
                    "3. Откройте Telegram, войдите.\n\n"
                    "⚠️ *Важно:* Не меняйте и не удаляйте файлы в папке tdata."
                )
                await bot.send_message(callback.message.chat.id, instruction, parse_mode="Markdown")
                await callback.message.delete()
            else:
                await callback.message.edit_text(
                    f"✅ Оплата получена!\n\n"
                    f"Ваш {invoice.product.name}:\n"
                    f"<code>{session.data}</code>\n"
                    f"Контактов: {session.contacts_count}\n\n"
                    f"Сохраните эти данные.",
                    parse_mode="HTML"
                )
        else:
            await callback.answer("Платёж ещё не получен. Попробуйте позже.", show_alert=True)

@dp.callback_query(lambda c: c.data == "my_purchases")
async def my_purchases(callback: types.CallbackQuery, bot: Bot):
    await log_action(bot, callback.from_user.id, "my_purchases", "Просмотр покупок")
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=callback.from_user.id).first()
        if not user:
            await callback.message.edit_text("У вас пока нет покупок.")
            return
        purchases = db.query(models.Purchase).filter_by(user_id=user.id).order_by(models.Purchase.purchased_at.desc()).all()
        if not purchases:
            await callback.message.edit_text("У вас пока нет покупок.")
            return
        text = "📦 <b>Ваши покупки:</b>\n\n"
        for p in purchases:
            text += f"🔹 {p.product.name} — {p.purchased_at.strftime('%d.%m.%Y %H:%M')}\n"
            if p.session.is_file:
                text += f"   📎 Файл: {p.session.filename}\n"
            else:
                text += f"   📝 Данные: {p.session.data}\n"
            text += "\n"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "my_referrals")
async def my_referrals(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            await callback.message.edit_text("Пользователь не найден.")
            return
        invited = db.query(models.User).filter_by(referred_by=user.tg_id).all()
        bot_username = (await bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.tg_id}"
        text = f"👥 <b>Ваша реферальная ссылка:</b>\n{ref_link}\n\n"
        text += f"💰 Бонусный баланс: {user.referral_balance:.2f} {CRYPTO_CURRENCY}\n"
        text += f"📊 Приглашено: {len(invited)} человек\n\n"
        if invited:
            text += "<b>Приглашённые:</b>\n"
            for u in invited:
                text += f"• {u.full_name or u.username or u.tg_id}\n"
        else:
            text += "Пригласите друзей и получайте 10% от их первых покупок!"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())
    await callback.answer()

# ------------------ Админ-панель ------------------
@dp.message(Command("admin"))
async def admin_cmd(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора.")
        return
    await log_action(bot, message.from_user.id, "admin", "Открыл админ-панель")
    await message.answer("Админ-панель:", reply_markup=kb.admin_menu_keyboard())

@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu_callback(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await log_action(bot, callback.from_user.id, "admin_menu", "Вернулся в админ-меню")
    await callback.message.edit_text("Админ-панель:", reply_markup=kb.admin_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    with models.SessionLocal() as db:
        total_users = db.query(models.User).count()
        total_products = db.query(models.Product).count()
        total_sessions = db.query(models.Session).count()
        sold_sessions = db.query(models.Session).filter_by(is_sold=True).count()
        total_purchases = db.query(models.Purchase).count()
        today = datetime.utcnow().date()
        purchases_today = db.query(models.Purchase).filter(func.date(models.Purchase.purchased_at) == today).count()
        text = (
            f"{emoji_tag(CUSTOM_EMOJI.get('stats', ''))} <b>Статистика</b>\n\n"
            f"👥 Пользователей: {total_users}\n"
            f"📦 Товаров: {total_products}\n"
            f"🔑 Всего сессий: {total_sessions}\n"
            f"✅ Продано: {sold_sessions}\n"
            f"🛒 Покупок всего: {total_purchases}\n"
            f"📅 Покупок сегодня: {purchases_today}"
        )
        await callback.message.edit_text(text, reply_markup=kb.admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_logs")
async def admin_logs(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    with models.SessionLocal() as db:
        logs = db.query(models.Log).order_by(models.Log.created_at.desc()).limit(10).all()
        if not logs:
            await callback.message.edit_text("Логов пока нет.", reply_markup=kb.admin_menu_keyboard())
            return
        text = "📜 <b>Последние логи:</b>\n\n"
        for log in logs:
            user = log.user
            username = user.username if user else "unknown"
            text += f"🕒 {log.created_at.strftime('%d.%m %H:%M')} | {username} | {log.action}\n"
            if log.details:
                text += f"   {log.details}\n"
        await callback.message.edit_text(text, reply_markup=kb.admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_referrals")
async def admin_referrals(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    with models.SessionLocal() as db:
        top = db.query(models.User).filter(models.User.referral_count > 0).order_by(models.User.referral_count.desc()).limit(10).all()
        text = "👥 <b>Топ рефералов по количеству:</b>\n\n"
        for i, u in enumerate(top, 1):
            text += f"{i}. {u.full_name or u.username or u.tg_id} — {u.referral_count} чел., бонусов: {u.referral_balance:.2f} {CRYPTO_CURRENCY}\n"
        total_referrals = db.query(models.User).filter(models.User.referred_by != None).count()
        total_bonus = db.query(models.User).with_entities(func.sum(models.User.total_referral_earnings)).scalar() or 0
        text += f"\n📊 <b>Всего:</b>\n"
        text += f"Приглашённых: {total_referrals}\n"
        text += f"Выдано бонусов: {total_bonus:.2f} {CRYPTO_CURRENCY}\n"
        await callback.message.edit_text(text, reply_markup=kb.admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

# ------------------ Добавление товара ------------------
@dp.callback_query(lambda c: c.data == "admin_add_product")
async def admin_add_product_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await log_action(bot, callback.from_user.id, "admin_add_product_start", "Начал добавление товара")
    await callback.message.edit_text("Введите название товара:")
    await state.set_state(AddProduct.name)
    await callback.answer()

@dp.message(AddProduct.name)
async def add_product_name(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(name=message.text)
    await message.answer("Введите описание товара:")
    await state.set_state(AddProduct.description)

@dp.message(AddProduct.description)
async def add_product_description(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(description=message.text)
    await message.answer("Введите цену в USDT (число):")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
async def add_product_price(message: types.Message, state: FSMContext, bot: Bot):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("Введите валюту (например, USDT, BTC):")
        await state.set_state(AddProduct.currency)
    except ValueError:
        await message.answer("Введите число.")

@dp.message(AddProduct.currency)
async def add_product_currency(message: types.Message, state: FSMContext, bot: Bot):
    currency = message.text.upper()
    await state.update_data(currency=currency)
    data = await state.get_data()
    with models.SessionLocal() as db:
        product = models.Product(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            currency=currency,
            is_active=True
        )
        db.add(product)
        db.commit()
        await log_action(bot, message.from_user.id, "admin_add_product", f"Добавлен товар ID {product.id}: {product.name}")
        await message.answer(f"Товар «{product.name}» успешно добавлен.", reply_markup=kb.admin_menu_keyboard())
    await state.clear()

# ------------------ Скрытие/показ товара ------------------
@dp.callback_query(lambda c: c.data == "admin_toggle_product")
async def admin_toggle_product_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    with models.SessionLocal() as db:
        products = db.query(models.Product).all()
        if not products:
            await callback.message.edit_text("Нет товаров.", reply_markup=kb.admin_menu_keyboard())
            return
        text = "Выберите товар для скрытия/показа:\n\n"
        for p in products:
            status = "🟢 активен" if p.is_active else "🔴 скрыт"
            text += f"ID {p.id}: {p.name} — {status}\n"
        await callback.message.edit_text(text)
        await callback.message.answer("Введите ID товара:")
        await state.set_state(ToggleProductActive.product_id)
    await callback.answer()

@dp.message(ToggleProductActive.product_id)
async def toggle_product_active(message: types.Message, state: FSMContext, bot: Bot):
    try:
        product_id = int(message.text)
        with models.SessionLocal() as db:
            product = db.query(models.Product).filter_by(id=product_id).first()
            if not product:
                await message.answer("Товар не найден.")
                return
            product.is_active = not product.is_active
            db.commit()
            new_status = "активен" if product.is_active else "скрыт"
            await log_action(bot, message.from_user.id, "admin_toggle_product", f"Товар ID {product_id} теперь {new_status}")
            await message.answer(f"Товар «{product.name}» теперь {new_status}.", reply_markup=kb.admin_menu_keyboard())
    except ValueError:
        await message.answer("Введите число.")
    await state.clear()

# ------------------ Добавление tdata (ZIP) ------------------
@dp.callback_query(lambda c: c.data == "admin_add_tdata")
async def admin_add_tdata_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    with models.SessionLocal() as db:
        products = db.query(models.Product).all()
        if not products:
            await callback.message.edit_text("Сначала добавьте товар.", reply_markup=kb.admin_menu_keyboard())
            return
        text = "Выберите товар, к которому добавить tdata (ZIP):\n\n"
        for p in products:
            text += f"ID {p.id}: {p.name}\n"
        await callback.message.edit_text(text)
        await callback.message.answer("Введите ID товара:")
        await state.set_state(AddTdataSession.product_id)
    await callback.answer()

@dp.message(AddTdataSession.product_id)
async def add_tdata_product(message: types.Message, state: FSMContext, bot: Bot):
    try:
        product_id = int(message.text)
        with models.SessionLocal() as db:
            product = db.query(models.Product).filter_by(id=product_id).first()
            if not product:
                await message.answer("Товар не найден.")
                return
            await state.update_data(product_id=product_id)
            await message.answer("Введите количество контактов (число):")
            await state.set_state(AddTdataSession.contacts_count)
    except ValueError:
        await message.answer("Введите число.")

@dp.message(AddTdataSession.contacts_count)
async def add_tdata_contacts(message: types.Message, state: FSMContext, bot: Bot):
    try:
        contacts_count = int(message.text)
        await state.update_data(contacts_count=contacts_count)
        await message.answer("Отправьте ZIP-архив с папкой tdata:")
        await state.set_state(AddTdataSession.waiting_file)
    except ValueError:
        await message.answer("Введите число.")

@dp.message(AddTdataSession.waiting_file, lambda message: message.document)
async def add_tdata_file(message: types.Message, state: FSMContext, bot: Bot):
    file = message.document
    if not file.file_name.endswith('.zip'):
        await message.answer("Пожалуйста, отправьте ZIP-архив.")
        return
    file_info = await bot.get_file(file.file_id)
    downloaded = await bot.download_file(file_info.file_path)
    file_bytes = downloaded.read()
    data = await state.get_data()
    product_id = data['product_id']
    contacts_count = data['contacts_count']
    with models.SessionLocal() as db:
        session = models.Session(
            product_id=product_id,
            file_data=file_bytes,
            filename=file.file_name,
            is_file=True,
            contacts_count=contacts_count,
            is_sold=False
        )
        db.add(session)
        db.commit()
        await log_action(bot, message.from_user.id, "admin_add_tdata", f"Добавлен tdata к товару ID {product_id}")
        await message.answer(f"ZIP-архив добавлен (контактов: {contacts_count}).", reply_markup=kb.admin_menu_keyboard())
    await state.clear()

@dp.message(AddTdataSession.waiting_file)
async def add_tdata_invalid(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте ZIP-файл.")

# ------------------ Добавление текстовой сессии (логин:пароль) ------------------
@dp.callback_query(lambda c: c.data == "admin_add_text")
async def admin_add_text_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    with models.SessionLocal() as db:
        products = db.query(models.Product).all()
        if not products:
            await callback.message.edit_text("Сначала добавьте товар.", reply_markup=kb.admin_menu_keyboard())
            return
        text = "Выберите товар, к которому добавить текстовую сессию:\n\n"
        for p in products:
            text += f"ID {p.id}: {p.name}\n"
        await callback.message.edit_text(text)
        await callback.message.answer("Введите ID товара:")
        await state.set_state(AddTextSession.product_id)
    await callback.answer()

@dp.message(AddTextSession.product_id)
async def add_text_product(message: types.Message, state: FSMContext, bot: Bot):
    try:
        product_id = int(message.text)
        with models.SessionLocal() as db:
            product = db.query(models.Product).filter_by(id=product_id).first()
            if not product:
                await message.answer("Товар не найден.")
                return
            await state.update_data(product_id=product_id)
            await message.answer("Введите количество контактов (число):")
            await state.set_state(AddTextSession.contacts_count)
    except ValueError:
        await message.answer("Введите число.")

@dp.message(AddTextSession.contacts_count)
async def add_text_contacts(message: types.Message, state: FSMContext, bot: Bot):
    try:
        contacts_count = int(message.text)
        await state.update_data(contacts_count=contacts_count)
        await message.answer("Введите текстовые данные (логин:пароль):")
        await state.set_state(AddTextSession.text_data)
    except ValueError:
        await message.answer("Введите число.")

@dp.message(AddTextSession.text_data)
async def add_text_data(message: types.Message, state: FSMContext, bot: Bot):
    text_data = message.text
    data = await state.get_data()
    product_id = data['product_id']
    contacts_count = data['contacts_count']
    with models.SessionLocal() as db:
        session = models.Session(
            product_id=product_id,
            data=text_data,
            is_file=False,
            contacts_count=contacts_count,
            is_sold=False
        )
        db.add(session)
        db.commit()
        await log_action(bot, message.from_user.id, "admin_add_text", f"Добавлена текстовая сессия к товару ID {product_id}")
        await message.answer(f"Текстовая сессия добавлена (контактов: {contacts_count}).", reply_markup=kb.admin_menu_keyboard())
    await state.clear()

# ------------------ Рассылка ------------------
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("Введите текст для рассылки (можно использовать HTML):")
    await state.set_state(Broadcast.text)
    await callback.answer()

@dp.message(Broadcast.text)
async def admin_broadcast_send(message: types.Message, state: FSMContext, bot: Bot):
    text = message.text
    await message.answer("Рассылка начата. Ожидайте...")

    with models.SessionLocal() as db:
        users = db.query(models.User).all()

    sent = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(user.tg_id, text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            print(f"Не удалось отправить {user.tg_id}: {e}")

    await message.answer(f"Рассылка завершена.\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")
    await log_action(bot, message.from_user.id, "admin_broadcast", f"Рассылка: {sent} успешно, {failed} ошибок")
    await state.clear()
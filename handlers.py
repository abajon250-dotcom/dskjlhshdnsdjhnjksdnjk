import asyncio
import json
import html
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import func
import keyboards as kb
import models
import crypto_api
from vk_api import VKClient
from config import ADMIN_IDS, CRYPTO_CURRENCY, CHANNEL_ID, PRODUCTS_PER_PAGE
from log_utils import log_action

dp = Dispatcher()

# ------------------ FSM ------------------
class AddProduct(StatesGroup): name = State(); description = State(); price = State(); currency = State()
class ToggleProductActive(StatesGroup): product_id = State()
class AddTdataSession(StatesGroup): product_id = State(); contacts_count = State(); waiting_file = State()
class AddTextSession(StatesGroup): product_id = State(); contacts_count = State(); text_data = State()
class Broadcast(StatesGroup): text = State()
class BanUser(StatesGroup): user_id = State(); action = State()
class DepositBalance(StatesGroup): amount = State()
class ActivatePromo(StatesGroup): code = State()
class CreatePromoCode(StatesGroup): amount = State(); max_activations = State(); expires_at = State()
class ManageBalance(StatesGroup): user_id = State(); amount = State(); action = State()
class ImportData(StatesGroup): file = State()
class ChangeProductPrice(StatesGroup): product_id = State(); new_price = State()
class WithdrawBalance(StatesGroup): amount = State(); wallet = State()
class VKAddAccount(StatesGroup): token = State()
class VKAddTemplate(StatesGroup): name = State(); text = State()
class VKStartSpam(StatesGroup): account_id = State(); template_id = State(); recipients_type = State(); interval = State()
class GiveVKSubscription(StatesGroup): user_id = State(); months = State()

# ------------------ Helper ------------------
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def add_transaction(db, user_id: int, amount: float, type: str, currency: str = "USDT", description: str = None):
    trans = models.Transaction(user_id=user_id, amount=amount, currency=currency, type=type, description=description)
    db.add(trans)
    db.commit()

async def is_subscribed(user_id: int, bot: Bot) -> bool:
    if not CHANNEL_ID: return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

async def check_vk_subscription(user_id: int) -> bool:
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if user and user.vk_spammer_subscription_until and user.vk_spammer_subscription_until > datetime.utcnow():
            return True
    return False

# ------------------ /start ------------------
@dp.message(Command("start"))
async def start_cmd(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    await log_action(bot, user_id, "/start", "Запустил бота", username=username, full_name=full_name)
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if user and user.is_banned:
            await message.answer("🚫 Вы забанены.")
            return
    if not await is_subscribed(user_id, bot):
        sub_kb = kb.subscription_keyboard()
        if sub_kb: await message.answer("❌ Подпишитесь на канал:", reply_markup=sub_kb)
        else: await message.answer("❌ Подпишитесь и нажмите /start")
        return
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
                                user = models.User(tg_id=user_id, username=message.from_user.username,
                                                  full_name=message.from_user.full_name, referred_by=referrer_id)
                                db.add(user); db.commit()
                            else:
                                if not user.referred_by:
                                    user.referred_by = referrer_id; db.commit()
            except: pass
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            user = models.User(tg_id=user_id, username=message.from_user.username, full_name=message.from_user.full_name, balance=0.0)
            db.add(user); db.commit()
        if ref_param and ref_param.startswith("ref_") and not user.referred_by:
            try:
                referrer_id = int(ref_param[4:])
                if referrer_id != user_id:
                    referrer = db.query(models.User).filter_by(tg_id=referrer_id).first()
                    if referrer:
                        user.referred_by = referrer_id; db.commit()
            except: pass
    await message.answer("✨ <b>Добро пожаловать в магазин!</b> ✨\n\nПополняйте баланс, используйте промокоды и покупайте аккаунты.", parse_mode="HTML", reply_markup=kb.main_menu_keyboard())

# ------------------ Главное меню ------------------
@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name
    await log_action(bot, user_id, "main_menu", "Нажал 'Главное меню'", username=username, full_name=full_name)
    await callback.message.edit_text("✨ <b>Главное меню</b> ✨\n\nВыберите действие:", parse_mode="HTML", reply_markup=kb.main_menu_keyboard())
    await callback.answer()

# ------------------ Баланс и пополнение ------------------
@dp.callback_query(lambda c: c.data == "balance_menu")
async def balance_menu(callback: types.CallbackQuery, bot: Bot):
    await log_action(bot, callback.from_user.id, "balance_menu", "Открыл меню баланса")
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=callback.from_user.id).first()
        balance = user.balance if user else 0.0
    await callback.message.edit_text(f"💰 <b>Ваш баланс:</b> <code>{balance:.2f} {CRYPTO_CURRENCY}</code>\n\nПополнить или активировать промокод:", parse_mode="HTML", reply_markup=kb.balance_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "deposit_balance")
async def deposit_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await log_action(bot, callback.from_user.id, "deposit_balance", "Начало пополнения баланса")
    await callback.message.edit_text("💸 Введите сумму пополнения в USDT (минимум 1):")
    await state.set_state(DepositBalance.amount)
    await callback.answer()

@dp.message(DepositBalance.amount)
async def deposit_amount(message: types.Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
        if amount < 1: raise ValueError
    except:
        await message.answer("❌ Введите число >=1")
        return
    user_id = message.from_user.id
    await log_action(bot, user_id, "deposit_amount", f"Сумма пополнения: {amount} {CRYPTO_CURRENCY}")
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            user = models.User(tg_id=user_id); db.add(user); db.commit()
    try:
        inv_id, pay_url = await crypto_api.create_invoice(amount, CRYPTO_CURRENCY)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")
        await state.clear(); return
    with models.SessionLocal() as db:
        inv = models.Invoice(user_id=user.id, crypto_invoice_id=inv_id, amount=amount,
                             currency=CRYPTO_CURRENCY, status="active", is_deposit=True)
        db.add(inv); db.commit()
        db_inv_id = inv.id
    await message.answer(f"💸 Счёт на <b>{amount} {CRYPTO_CURRENCY}</b> создан.\n\nОплатите и нажмите «Проверить оплату»:", reply_markup=kb.invoice_keyboard(pay_url, db_inv_id))
    await state.clear()

@dp.callback_query(lambda c: c.data == "activate_promo")
async def activate_promo_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await log_action(bot, callback.from_user.id, "activate_promo", "Начало активации промокода")
    await callback.message.edit_text("🎟 Введите код промокода:")
    await state.set_state(ActivatePromo.code)
    await callback.answer()

@dp.message(ActivatePromo.code)
async def activate_promo_code(message: types.Message, state: FSMContext, bot: Bot):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    await log_action(bot, user_id, "activate_promo_code", f"Код: {code}")
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            await message.answer("❌ Сначала /start"); await state.clear(); return
        promo = db.query(models.PromoCode).filter_by(code=code).first()
        if not promo:
            await message.answer("❌ Промокод не найден"); await state.clear(); return
        if promo.expires_at and promo.expires_at < datetime.utcnow():
            await message.answer("⏰ Срок истёк"); await state.clear(); return
        if promo.current_activations >= promo.max_activations:
            await message.answer("❌ Промокод исчерпан"); await state.clear(); return
        existing = db.query(models.PromoCodeActivation).filter_by(user_id=user.id, promo_id=promo.id).first()
        if existing:
            await message.answer("❌ Вы уже активировали"); await state.clear(); return
        user.balance += promo.amount
        promo.current_activations += 1
        activation = models.PromoCodeActivation(user_id=user.id, promo_id=promo.id)
        db.add(activation); db.commit()
        add_transaction(db, user.id, promo.amount, "bonus", description=f"Промокод {code}")
        await message.answer(f"✅ Активирован! +{promo.amount} {CRYPTO_CURRENCY}. Баланс: {user.balance:.2f} {CRYPTO_CURRENCY}")
    await state.clear()

# ------------------ История баланса ------------------
@dp.callback_query(lambda c: c.data == "balance_history")
async def balance_history(callback: types.CallbackQuery, bot: Bot):
    await log_action(bot, callback.from_user.id, "balance_history", "Просмотр истории баланса")
    user_id = callback.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            await callback.message.edit_text("❌ Пользователь не найден.")
            return
        transactions = db.query(models.Transaction).filter_by(user_id=user.id).order_by(models.Transaction.created_at.desc()).limit(20).all()
        if not transactions:
            await callback.message.edit_text("📭 История пуста.")
            return
        text = "📜 <b>История операций (последние 20):</b>\n\n"
        for t in transactions:
            sign = "+" if t.type in ["deposit", "bonus"] else "-"
            text += f"🕒 {t.created_at.strftime('%d.%m.%Y %H:%M')} – {sign} {t.amount} {t.currency} ({t.type})\n"
            if t.description:
                text += f"   📝 {t.description}\n"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())
    await callback.answer()

# ------------------ Вывод средств (из обычного баланса) ------------------
@dp.callback_query(lambda c: c.data == "withdraw_balance")
async def withdraw_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await log_action(bot, callback.from_user.id, "withdraw_balance", "Начало вывода средств")
    user_id = callback.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            await callback.message.edit_text("❌ Пользователь не найден.")
            return
        if user.balance <= 0:
            await callback.message.edit_text("❌ У вас нет средств для вывода.")
            return
        await callback.message.edit_text(f"💸 <b>Вывод средств</b>\n\n💰 Доступно: <code>{user.balance:.2f} {CRYPTO_CURRENCY}</code>\n\nВведите сумму вывода (минимум 1):", parse_mode="HTML")
        await state.set_state(WithdrawBalance.amount)
    await callback.answer()

@dp.message(WithdrawBalance.amount)
async def withdraw_amount(message: types.Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
        if amount < 1:
            await message.answer("❌ Минимальная сумма вывода – 1 USDT.")
            return
        user_id = message.from_user.id
        await log_action(bot, user_id, "withdraw_amount", f"Сумма: {amount} {CRYPTO_CURRENCY}")
        with models.SessionLocal() as db:
            user = db.query(models.User).filter_by(tg_id=user_id).first()
            if not user:
                await message.answer("❌ Пользователь не найден.")
                await state.clear()
                return
            if user.balance < amount:
                await message.answer(f"❌ Недостаточно средств. Доступно: {user.balance:.2f} {CRYPTO_CURRENCY}")
                return
            await state.update_data(amount=amount)
            await message.answer("📝 Введите адрес криптокошелька (USDT TRC20 / BEP20):")
            await state.set_state(WithdrawBalance.wallet)
    except ValueError:
        await message.answer("❌ Введите число.")

@dp.message(WithdrawBalance.wallet)
async def withdraw_wallet(message: types.Message, state: FSMContext, bot: Bot):
    wallet = message.text.strip()
    data = await state.get_data()
    amount = data['amount']
    user_id = message.from_user.id
    await log_action(bot, user_id, "withdraw_wallet", f"Сумма {amount} {CRYPTO_CURRENCY}, кошелёк {wallet}", username=message.from_user.username, full_name=message.from_user.full_name)
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return
        if user.balance < amount:
            await message.answer(f"❌ Недостаточно средств. Доступно: {user.balance:.2f} {CRYPTO_CURRENCY}")
            await state.clear()
            return
        # Создаём заявку (баланс пока не списываем)
        request = models.WithdrawalRequest(user_id=user.id, amount=amount, wallet=wallet, status='pending')
        db.add(request)
        db.commit()
        # Уведомляем администраторов
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, f"💸 <b>Новая заявка на вывод</b>\n👤 {user_id}\n💰 Сумма: {amount} {CRYPTO_CURRENCY}\n💳 Кошелёк: {wallet}\n\nИспользуйте /withdraw_approve {request.id} для одобрения\n/withdraw_reject {request.id} для отклонения")
        await message.answer(f"✅ Заявка на вывод {amount} {CRYPTO_CURRENCY} создана и отправлена администраторам. Ожидайте подтверждения.")
    await state.clear()

@dp.message(Command("withdraw_approve"))
async def withdraw_approve(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Используйте: /withdraw_approve <id_заявки>")
        return
    try:
        req_id = int(parts[1])
        with models.SessionLocal() as db:
            req = db.query(models.WithdrawalRequest).filter_by(id=req_id).first()
            if not req or req.status != 'pending':
                await message.answer("❌ Заявка не найдена или уже обработана.")
                return
            user = req.user
            if user.balance < req.amount:
                await message.answer(f"❌ Недостаточно средств на балансе пользователя. Доступно: {user.balance:.2f} {CRYPTO_CURRENCY}")
                return
            # Списание
            user.balance -= req.amount
            req.status = 'approved'
            req.processed_at = datetime.utcnow()
            db.commit()
            add_transaction(db, user.id, -req.amount, "withdrawal", description=f"Вывод на кошелёк {req.wallet} (одобрено)")
            await message.answer(f"✅ Заявка #{req_id} одобрена. Сумма {req.amount} {CRYPTO_CURRENCY} списана с баланса пользователя {user.tg_id}.")
            try:
                await bot.send_message(user.tg_id, f"✅ Ваша заявка на вывод {req.amount} {CRYPTO_CURRENCY} одобрена. Деньги будут отправлены в ближайшее время.")
            except:
                pass
    except ValueError:
        await message.answer("❌ Введите число.")

@dp.message(Command("withdraw_reject"))
async def withdraw_reject(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Используйте: /withdraw_reject <id_заявки>")
        return
    try:
        req_id = int(parts[1])
        with models.SessionLocal() as db:
            req = db.query(models.WithdrawalRequest).filter_by(id=req_id).first()
            if not req or req.status != 'pending':
                await message.answer("❌ Заявка не найдена или уже обработана.")
                return
            req.status = 'rejected'
            req.processed_at = datetime.utcnow()
            db.commit()
            await message.answer(f"❌ Заявка #{req_id} отклонена.")
            try:
                await bot.send_message(req.user.tg_id, f"❌ Ваша заявка на вывод {req.amount} {CRYPTO_CURRENCY} отклонена. Средства остались на балансе.")
            except:
                pass
    except ValueError:
        await message.answer("❌ Введите число.")
# ------------------ Каталог и пагинация ------------------
@dp.callback_query(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery, bot: Bot):
    await log_action(bot, callback.from_user.id, "catalog", "Открыл каталог")
    with models.SessionLocal() as db:
        products = db.query(models.Product).filter(
            models.Product.is_active == True,
            models.Product.sessions.any(models.Session.is_sold == False)
        ).order_by(models.Product.id).all()
        if not products:
            await callback.message.edit_text("📭 Товаров пока нет")
            return
        await callback.message.edit_text("📂 <b>Каталог</b> (страница 1)", parse_mode="HTML", reply_markup=kb.catalog_keyboard(products, page=0))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("catalog_page_"))
async def catalog_page(callback: types.CallbackQuery, bot: Bot):
    page = int(callback.data.split("_")[-1])
    await log_action(bot, callback.from_user.id, "catalog_page", f"Страница {page+1}")
    with models.SessionLocal() as db:
        products = db.query(models.Product).filter(
            models.Product.is_active == True,
            models.Product.sessions.any(models.Session.is_sold == False)
        ).order_by(models.Product.id).all()
        if not products:
            await callback.message.edit_text("📭 Товаров нет")
            return
        await callback.message.edit_text(f"📂 <b>Каталог</b> (страница {page+1})", parse_mode="HTML", reply_markup=kb.catalog_keyboard(products, page=page))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("view_product_"))
async def view_product(callback: types.CallbackQuery, bot: Bot):
    product_id = int(callback.data.split("_")[-1])
    await log_action(bot, callback.from_user.id, "view_product", f"Товар ID {product_id}")
    with models.SessionLocal() as db:
        product = db.query(models.Product).filter_by(id=product_id, is_active=True).first()
        if not product:
            await callback.message.edit_text("❌ Товар не найден")
            return
        sessions = db.query(models.Session).filter(
            models.Session.product_id == product_id,
            models.Session.is_sold == False
        ).order_by(models.Session.contacts_count).all()
        if not sessions:
            await callback.message.edit_text("❌ Нет доступных аккаунтов")
            return
        await callback.message.edit_text(f"🌟 <b>{product.name}</b>\n\nВыберите аккаунт (страница 1):", parse_mode="HTML", reply_markup=kb.sessions_keyboard(sessions, product_id, page=0))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("sessions_page_"))
async def sessions_page(callback: types.CallbackQuery, bot: Bot):
    _, _, product_id_str, page_str = callback.data.split("_")
    product_id = int(product_id_str); page = int(page_str)
    await log_action(bot, callback.from_user.id, "sessions_page", f"Товар ID {product_id}, страница {page+1}")
    with models.SessionLocal() as db:
        product = db.query(models.Product).filter_by(id=product_id).first()
        if not product:
            await callback.message.edit_text("❌ Товар не найден")
            return
        sessions = db.query(models.Session).filter(
            models.Session.product_id == product_id,
            models.Session.is_sold == False
        ).order_by(models.Session.contacts_count).all()
        await callback.message.edit_text(f"🌟 <b>{product.name}</b>\n\nВыберите аккаунт (страница {page+1}):", parse_mode="HTML", reply_markup=kb.sessions_keyboard(sessions, product_id, page=page))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_session_"))
async def buy_session(callback: types.CallbackQuery, bot: Bot):
    session_id = int(callback.data.split("_")[-1])
    await log_action(bot, callback.from_user.id, "buy_session", f"Сессия ID {session_id}")
    with models.SessionLocal() as db:
        session = db.query(models.Session).filter_by(id=session_id, is_sold=False).first()
        if not session:
            await callback.message.edit_text("❌ Аккаунт уже куплен")
            return
        product = session.product
        user = db.query(models.User).filter_by(tg_id=callback.from_user.id).first()
        if not user:
            user = models.User(tg_id=callback.from_user.id); db.add(user); db.commit()
        has_balance = user.balance >= product.price
        text = f"🌟 <b>{product.name}</b>\n👥 Контактов: {session.contacts_count}\n💵 Цена: {product.price} {product.currency}\n"
        if has_balance:
            text += f"💰 Ваш баланс: {user.balance:.2f} {CRYPTO_CURRENCY}"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.product_detail_keyboard(product.id, has_balance))
        state = dp.fsm.get_context(bot, callback.message.chat.id, callback.from_user.id)
        await state.update_data(pending_session_id=session_id)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_with_balance_"))
async def buy_with_balance(callback: types.CallbackQuery, bot: Bot):
    product_id = int(callback.data.split("_")[-1])
    await log_action(bot, callback.from_user.id, "buy_with_balance", f"Покупка товара ID {product_id} с баланса")
    state = dp.fsm.get_context(bot, callback.message.chat.id, callback.from_user.id)
    data = await state.get_data()
    session_id = data.get("pending_session_id")
    if not session_id:
        await callback.answer("⚠️ Ошибка: выберите аккаунт заново", show_alert=True)
        return
    user_id = callback.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        session = db.query(models.Session).filter_by(id=session_id, is_sold=False).first()
        if not session:
            await callback.message.edit_text("❌ Аккаунт уже куплен"); return
        product = session.product
        if user.balance < product.price:
            await callback.answer("❌ Недостаточно средств", show_alert=True); return
        user.balance -= product.price
        session.is_sold = True
        purchase = models.Purchase(user_id=user.id, product_id=product.id, session_id=session.id, paid_with_balance=True)
        db.add(purchase); db.commit()
        add_transaction(db, user.id, -product.price, "purchase", description=f"Товар {product.name}")
        # Активация подписки, если товар называется "Подписка VK Спаммер"
        if product.name == "Подписка VK Спаммер":
            expires = datetime.utcnow() + timedelta(days=30)
            user.vk_spammer_subscription_until = expires
            db.commit()
            await callback.message.edit_text(f"✅ Подписка на VK Спаммер активирована до {expires.strftime('%d.%m.%Y')}")
            await state.clear()
            return
        if session.is_file and session.file_data:
            await bot.send_document(callback.message.chat.id, BufferedInputFile(session.file_data, filename=session.filename),
                                    caption=f"✅ Оплачено с баланса!\n{product.name}\nКонтактов: {session.contacts_count}")
            await bot.send_message(callback.message.chat.id, "📱 Инструкция для Telegram...", parse_mode="HTML")
        else:
            await callback.message.edit_text(
                f"✅ Оплачено с баланса!\n\n{product.name}:\n<code>{session.data}</code>\n"
                f"Контактов: {session.contacts_count}\nОстаток: {user.balance:.2f} {CRYPTO_CURRENCY}",
                parse_mode="HTML"
            )
        await state.clear()
        await bot.send_message(callback.message.chat.id, "🔄 Обновить каталог?",
                               reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🛍 Обновить каталог", callback_data="catalog")]]))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def create_invoice_for_session(callback: types.CallbackQuery, bot: Bot):
    product_id = int(callback.data.split("_")[-1])
    await log_action(bot, callback.from_user.id, "pay_", f"Оплата криптой товара ID {product_id}")
    state = dp.fsm.get_context(bot, callback.message.chat.id, callback.from_user.id)
    data = await state.get_data()
    session_id = data.get("pending_session_id")
    if not session_id:
        await callback.answer("⚠️ Ошибка: выберите аккаунт заново", show_alert=True); return
    with models.SessionLocal() as db:
        session = db.query(models.Session).filter_by(id=session_id, is_sold=False).first()
        if not session:
            await callback.message.edit_text("❌ Аккаунт уже куплен"); return
        product = session.product
        user = db.query(models.User).filter_by(tg_id=callback.from_user.id).first()
        if not user:
            user = models.User(tg_id=callback.from_user.id); db.add(user); db.commit()
        try:
            inv_id, pay_url = await crypto_api.create_invoice(product.price, product.currency)
        except Exception as e:
            await callback.message.edit_text(f"⚠️ Ошибка: {e}"); return
        invoice = models.Invoice(user_id=user.id, product_id=product.id, crypto_invoice_id=inv_id,
                                 amount=product.price, currency=product.currency, status="active", is_deposit=False,
                                 session_id=session_id)
        db.add(invoice); db.commit()
        db_inv_id = invoice.id
        await callback.message.edit_text(
            f"💸 Счёт на <b>{product.price} {product.currency}</b> создан.\n\n"
            "Оплатите и нажмите «Проверить оплату»:",
            reply_markup=kb.invoice_keyboard(pay_url, db_inv_id)
        )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("check_"))
async def check_payment(callback: types.CallbackQuery, bot: Bot):
    invoice_db_id = int(callback.data.split("_")[1])
    await log_action(bot, callback.from_user.id, "check_payment", f"Проверка счёта #{invoice_db_id}")
    with models.SessionLocal() as db:
        invoice = db.query(models.Invoice).filter_by(id=invoice_db_id).first()
        if not invoice or invoice.status == "paid":
            await callback.message.edit_text("✅ Счёт уже оплачен"); return
        status = await crypto_api.check_invoice_status(invoice.crypto_invoice_id)
        if status != "paid":
            await callback.answer("⏳ Платёж ещё не получен", show_alert=True); return
        invoice.status = "paid"
        invoice.paid_at = datetime.utcnow()
        user = db.query(models.User).filter_by(id=invoice.user_id).first()
        if invoice.is_deposit:
            user.balance += invoice.amount
            db.commit()
            add_transaction(db, user.id, invoice.amount, "deposit")
            await log_action(bot, user.tg_id, "deposit", f"{invoice.amount} {invoice.currency}")
            await callback.message.edit_text(f"✅ Баланс пополнен на {invoice.amount} {invoice.currency}\nНовый баланс: {user.balance:.2f} {invoice.currency}")
        else:
            session = db.query(models.Session).filter_by(id=invoice.session_id, is_sold=False).first()
            if not session:
                await callback.message.edit_text("❌ Аккаунт уже куплен"); return
            session.is_sold = True
            purchase = models.Purchase(user_id=user.id, product_id=invoice.product_id, session_id=session.id, paid_with_balance=False)
            db.add(purchase); db.commit()
            add_transaction(db, user.id, -invoice.amount, "purchase", description=f"Товар {invoice.product.name}")
            # Активация подписки, если товар называется "Подписка VK Спаммер"
            if invoice.product.name == "Подписка VK Спаммер":
                expires = datetime.utcnow() + timedelta(days=30)
                user.vk_spammer_subscription_until = expires
                db.commit()
                await callback.message.edit_text(f"✅ Подписка на VK Спаммер активирована до {expires.strftime('%d.%m.%Y')}")
                await callback.message.delete()
                return
            if session.is_file and session.file_data:
                await bot.send_document(callback.message.chat.id, BufferedInputFile(session.file_data, filename=session.filename),
                                        caption=f"✅ Оплата получена!\n{invoice.product.name}\nКонтактов: {session.contacts_count}")
                await bot.send_message(callback.message.chat.id, "📱 Инструкция...", parse_mode="HTML")
            else:
                await callback.message.edit_text(
                    f"✅ Оплата получена!\n\n{invoice.product.name}:\n<code>{session.data}</code>\n"
                    f"Контактов: {session.contacts_count}",
                    parse_mode="HTML"
                )
            # Реферальный бонус
            purchases_count = db.query(models.Purchase).filter_by(user_id=user.id).count()
            if purchases_count == 1 and user.referred_by:
                referrer = db.query(models.User).filter_by(tg_id=user.referred_by).first()
                if referrer:
                    bonus = invoice.amount * 0.10
                    referrer.referral_balance += bonus
                    referrer.total_referral_earnings += bonus
                    referrer.referral_count += 1
                    db.commit()
                    add_transaction(db, referrer.id, bonus, "bonus", description=f"Реферал {user.username}")
                    try:
                        await bot.send_message(referrer.tg_id, f"🎉 Реферал @{user.username} купил! Бонус {bonus} {invoice.currency}")
                    except: pass
            await bot.send_message(callback.message.chat.id, "🔄 Обновить каталог?",
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🛍 Обновить каталог", callback_data="catalog")]]))
        await callback.message.delete()
    await callback.answer()

# ------------------ Мои покупки ------------------
@dp.callback_query(lambda c: c.data == "my_purchases")
async def my_purchases(callback: types.CallbackQuery, bot: Bot):
    await log_action(bot, callback.from_user.id, "my_purchases", "Просмотр своих покупок")
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=callback.from_user.id).first()
        if not user: await callback.message.edit_text("📭 Нет покупок"); return
        purchases = db.query(models.Purchase).filter_by(user_id=user.id).order_by(models.Purchase.purchased_at.desc()).all()
        if not purchases:
            await callback.message.edit_text("📭 Нет покупок")
            return
        text = "📦 <b>Ваши покупки</b>\n\n"
        for p in purchases:
            text += f"🔹 {p.product.name} — {p.purchased_at.strftime('%d.%m.%Y')}\n"
            if p.paid_with_balance: text += "   💳 С баланса\n"
            else: text += "   💸 Криптовалюта\n"
            if p.session.is_file: text += f"   📎 Файл: {p.session.filename}\n"
            else: text += f"   📝 Данные: {p.session.data}\n\n"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())
    await callback.answer()

# ------------------ Рефералы ------------------
@dp.callback_query(lambda c: c.data == "my_referrals")
async def my_referrals(callback: types.CallbackQuery, bot: Bot):
    await log_action(bot, callback.from_user.id, "my_referrals", "Просмотр рефералов")
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=callback.from_user.id).first()
        if not user: return
        invited = db.query(models.User).filter_by(referred_by=user.tg_id).all()
        bot_username = (await bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.tg_id}"
        text = f"👥 <b>Ваша реферальная ссылка</b>\n{ref_link}\n\n💰 Бонусный баланс: {user.referral_balance:.2f} {CRYPTO_CURRENCY}\n📊 Приглашено: {len(invited)}\n\n"
        if invited:
            text += "Приглашённые:\n" + "\n".join([f"• {u.full_name or u.username or u.tg_id}" for u in invited])
        else:
            text += "Приглашайте друзей – 10% от их первых покупок!"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())
    await callback.answer()

# ------------------ Поддержка (с экранированием HTML) ------------------
@dp.callback_query(lambda c: c.data == "support")
async def support_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name
    await log_action(bot, user_id, "support", "Открыл окно поддержки", username=username, full_name=full_name)
    await callback.message.edit_text("💬 Напишите ваше сообщение администратору.\n\nЧтобы отменить, нажмите /cancel")
    await state.set_state("support_waiting")
    await callback.answer()

@dp.message(StateFilter("support_waiting"))
async def support_send(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    text = message.text
    if text == "/cancel":
        await message.answer("❌ Отменено.")
        await state.clear()
        return
    await log_action(bot, user_id, "support_send", f"Сообщение: {text[:100]}", username=username, full_name=full_name)
    safe_text = html.escape(text)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id,
        f"📩 Новое сообщение от пользователя\n👤 {user_id}\n💬 {safe_text}\n\nЧтобы ответить, используйте:\n/reply_{user_id} <текст>")
        except Exception as e:
            print(f"Ошибка отправки админу {admin_id}: {e}")
    await message.answer("✅ Сообщение отправлено администратору. Ожидайте ответа.")
    await state.clear()

@dp.message(Command(commands=["reply"], prefix="/"))
async def admin_reply(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    # Разделяем команду и аргументы
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Используйте: /reply_<user_id> <текст>")
        return
    # Извлекаем user_id из первого аргумента (например, reply_123456789)
    try:
        user_id = int(parts[1].split('_')[1]) if '_' in parts[1] else int(parts[1])
        reply_text = parts[2]
    except (IndexError, ValueError):
        await message.answer("❌ Неверный формат. Используйте: /reply_<user_id> <текст>")
        return
    # Логируем действие
    await log_action(bot, message.from_user.id, "admin_reply", f"Ответ пользователю {user_id}: {reply_text[:100]}", username=message.from_user.username, full_name=message.from_user.full_name)
    # Экранируем текст ответа
    safe_reply = html.escape(reply_text)
    try:
        await bot.send_message(user_id, f"💬 <b>Ответ администратора:</b>\n{safe_reply}", parse_mode="HTML")
        await message.answer("✅ Ответ отправлен.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}")
# ------------------ Админ-панель ------------------
@dp.message(Command("admin"))
async def admin_cmd(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав.")
        return
    await log_action(bot, message.from_user.id, "admin", "Открыл админ-панель")
    await message.answer("🔧 <b>Админ-панель</b>", parse_mode="HTML", reply_markup=kb.admin_menu_keyboard())

@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu_back(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await log_action(bot, callback.from_user.id, "admin_menu", "Вернулся в админ-меню")
    await callback.message.edit_text("🔧 <b>Админ-панель</b>", parse_mode="HTML", reply_markup=kb.admin_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await log_action(bot, callback.from_user.id, "admin_stats", "Просмотр статистики")
    with models.SessionLocal() as db:
        total_users = db.query(models.User).count()
        total_products = db.query(models.Product).count()
        total_sessions = db.query(models.Session).count()
        sold = db.query(models.Session).filter_by(is_sold=True).count()
        total_purchases = db.query(models.Purchase).count()
        total_deposits = db.query(models.Invoice).filter_by(is_deposit=True, status="paid").with_entities(func.sum(models.Invoice.amount)).scalar() or 0
        text = f"📊 Статистика\n👥 Пользователей: {total_users}\n📦 Товаров: {total_products}\n🔑 Сессий: {total_sessions}\n✅ Продано: {sold}\n🛒 Покупок: {total_purchases}\n💰 Пополнений: {total_deposits:.2f} {CRYPTO_CURRENCY}"
        await callback.message.edit_text(text, reply_markup=kb.admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_logs")
async def admin_logs(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await log_action(bot, callback.from_user.id, "admin_logs", "Просмотр логов")
    with models.SessionLocal() as db:
        logs = db.query(models.Log).order_by(models.Log.created_at.desc()).limit(10).all()
        if not logs:
            await callback.message.edit_text("📭 Логов нет", reply_markup=kb.admin_menu_keyboard())
            return
        text = "📜 Последние логи:\n\n"
        for log in logs:
            user = log.user
            username = user.username if user else "unknown"
            text += f"🕒 {log.created_at.strftime('%d.%m %H:%M')} | {username} | {log.action}\n"
            if log.details: text += f"   {log.details}\n"
        await callback.message.edit_text(text, reply_markup=kb.admin_menu_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_withdrawals")
async def admin_withdrawals(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    with models.SessionLocal() as db:
        requests = db.query(models.WithdrawalRequest).filter_by(status='pending').order_by(models.WithdrawalRequest.created_at.desc()).all()
        if not requests:
            await callback.message.edit_text("📭 Нет активных заявок на вывод.", reply_markup=kb.admin_menu_keyboard())
            return
        text = "💸 <b>Заявки на вывод (ожидают обработки):</b>\n\n"
        for r in requests:
            user = r.user
            text += f"🆔 #{r.id} | Пользователь {user.tg_id} | Сумма {r.amount} {CRYPTO_CURRENCY} | Кошелёк: {r.wallet}\n"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.admin_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_give_vk_subscription")
async def admin_give_vk_subscription_start(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await log_action(bot, callback.from_user.id, "admin_give_vk_subscription", "Начало выдачи подписки VK")
    await callback.message.edit_text("🎟 Введите Telegram ID пользователя, которому хотите выдать подписку VK:")
    await state.set_state(GiveVKSubscription.user_id)
    await callback.answer()

@dp.message(GiveVKSubscription.user_id)
async def admin_give_vk_subscription_user_id(message: types.Message, state: FSMContext, bot: Bot):
    try:
        target_id = int(message.text.strip())
        with models.SessionLocal() as db:
            user = db.query(models.User).filter_by(tg_id=target_id).first()
            if not user:
                await message.answer("❌ Пользователь не найден.")
                await state.clear()
                return
            await state.update_data(target_user_id=user.id)
            await message.answer("Введите количество месяцев подписки (1, 3, 6):")
            await state.set_state(GiveVKSubscription.months)
    except ValueError:
        await message.answer("❌ Введите число (Telegram ID).")
        await state.clear()

@dp.message(GiveVKSubscription.months)
async def admin_give_vk_subscription_months(message: types.Message, state: FSMContext, bot: Bot):
    try:
        months = int(message.text.strip())
        if months not in [1, 3, 6]:
            await message.answer("❌ Выберите 1, 3 или 6 месяцев.")
            return
        data = await state.get_data()
        target_user_id = data['target_user_id']
        with models.SessionLocal() as db:
            user = db.query(models.User).filter_by(id=target_user_id).first()
            expires = datetime.utcnow() + timedelta(days=30*months)
            user.vk_spammer_subscription_until = expires
            db.commit()
            await log_action(bot, message.from_user.id, "admin_give_vk_subscription", f"Выдана подписка на {months} месяцев пользователю {user.tg_id}")
            await message.answer(f"✅ Пользователю {user.tg_id} выдана подписка VK на {months} месяцев (до {expires.strftime('%d.%m.%Y')}).", reply_markup=kb.admin_menu_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число.")
        await state.clear()

# ------------------ Добавление товара ------------------
@dp.callback_query(lambda c: c.data == "admin_add_product")
async def admin_add_product_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("➕ Введите название товара:")
    await state.set_state(AddProduct.name)
    await callback.answer()

@dp.message(AddProduct.name)
async def add_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📝 Введите описание:")
    await state.set_state(AddProduct.description)

@dp.message(AddProduct.description)
async def add_product_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("💵 Введите цену в USDT (число):")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
async def add_product_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("💱 Введите валюту (USDT, BTC и т.д.):")
        await state.set_state(AddProduct.currency)
    except:
        await message.answer("❌ Введите число.")

@dp.message(AddProduct.currency)
async def add_product_currency(message: types.Message, state: FSMContext, bot: Bot):
    currency = message.text.upper()
    data = await state.get_data()
    with models.SessionLocal() as db:
        product = models.Product(name=data['name'], description=data['description'], price=data['price'], currency=currency, is_active=True)
        db.add(product); db.commit()
        await log_action(bot, message.from_user.id, "admin_add_product", f"Товар ID {product.id}: {product.name}")
        await message.answer(f"✅ Товар «{product.name}» добавлен. Цена: {product.price} {product.currency}", reply_markup=kb.admin_menu_keyboard())
    await state.clear()

# ------------------ Изменение цены товара ------------------
@dp.callback_query(lambda c: c.data == "admin_change_price")
async def admin_change_price_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("💰 Введите ID товара, цену которого хотите изменить:")
    await state.set_state(ChangeProductPrice.product_id)
    await callback.answer()

@dp.message(ChangeProductPrice.product_id)
async def change_price_product_id(message: types.Message, state: FSMContext):
    try:
        product_id = int(message.text.strip())
        with models.SessionLocal() as db:
            product = db.query(models.Product).filter_by(id=product_id).first()
            if not product:
                await message.answer("❌ Товар с таким ID не найден.")
                await state.clear()
                return
            await state.update_data(product_id=product_id)
            await message.answer(
                f"📦 <b>{product.name}</b>\n"
                f"💰 Текущая цена: <code>{product.price} {product.currency}</code>\n\n"
                "Введите новую цену в USDT (число):",
                parse_mode="HTML"
            )
            await state.set_state(ChangeProductPrice.new_price)
    except ValueError:
        await message.answer("❌ Введите число (ID товара).")
        await state.clear()

@dp.message(ChangeProductPrice.new_price)
async def change_price_new_price(message: types.Message, state: FSMContext, bot: Bot):
    try:
        new_price = float(message.text.strip())
        if new_price <= 0:
            await message.answer("❌ Цена должна быть положительной.")
            return
        data = await state.get_data()
        product_id = data['product_id']
        with models.SessionLocal() as db:
            product = db.query(models.Product).filter_by(id=product_id).first()
            if not product:
                await message.answer("❌ Товар не найден.")
                await state.clear()
                return
            old_price = product.price
            product.price = new_price
            db.commit()
            await log_action(bot, message.from_user.id, "admin_change_price", f"Товар ID {product_id}: цена изменена с {old_price} на {new_price} {product.currency}")
            await message.answer(
                f"✅ Цена товара <b>{product.name}</b> изменена.\n"
                f"💰 Было: <code>{old_price} {product.currency}</code>\n"
                f"💎 Стало: <code>{new_price} {product.currency}</code>",
                parse_mode="HTML",
                reply_markup=kb.admin_menu_keyboard()
            )
    except ValueError:
        await message.answer("❌ Введите число.")
    finally:
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
        text = "🔄 <b>Выберите товар для скрытия/показа:</b>\n\n"
        for p in products:
            status = "🟢 активен" if p.is_active else "🔴 скрыт"
            text += f"ID {p.id}: {p.name} — {status}\n"
        await callback.message.edit_text(text, parse_mode="HTML")
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
async def admin_add_tdata_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    with models.SessionLocal() as db:
        products = db.query(models.Product).all()
        if not products:
            await callback.message.edit_text("❌ Сначала добавьте товар.")
            return
        text = "📦 Выберите ID товара:\n" + "\n".join([f"ID {p.id}: {p.name}" for p in products])
        await callback.message.edit_text(text)
        await callback.message.answer("Введите ID товара:")
        await state.set_state(AddTdataSession.product_id)
    await callback.answer()

@dp.message(AddTdataSession.product_id)
async def add_tdata_product(message: types.Message, state: FSMContext):
    try:
        product_id = int(message.text)
        with models.SessionLocal() as db:
            if not db.query(models.Product).filter_by(id=product_id).first():
                await message.answer("❌ Товар не найден"); return
            await state.update_data(product_id=product_id)
            await message.answer("👥 Введите количество контактов (число):")
            await state.set_state(AddTdataSession.contacts_count)
    except:
        await message.answer("❌ Введите число")

@dp.message(AddTdataSession.contacts_count)
async def add_tdata_contacts(message: types.Message, state: FSMContext):
    try:
        contacts = int(message.text)
        await state.update_data(contacts_count=contacts)
        await message.answer("📎 Отправьте ZIP-архив с папкой tdata:")
        await state.set_state(AddTdataSession.waiting_file)
    except:
        await message.answer("❌ Введите число")

@dp.message(AddTdataSession.waiting_file, lambda m: m.document)
async def add_tdata_file(message: types.Message, state: FSMContext, bot: Bot):
    file = message.document
    if not file.file_name.endswith('.zip'):
        await message.answer("❌ Отправьте ZIP-файл"); return
    file_info = await bot.get_file(file.file_id)
    downloaded = await bot.download_file(file_info.file_path)
    file_bytes = downloaded.read()
    data = await state.get_data()
    with models.SessionLocal() as db:
        session = models.Session(product_id=data['product_id'], file_data=file_bytes, filename=file.file_name,
                                 is_file=True, contacts_count=data['contacts_count'], is_sold=False)
        db.add(session); db.commit()
        await log_action(bot, message.from_user.id, "admin_add_tdata", f"Добавлен tdata к товару ID {data['product_id']}")
        await message.answer(f"✅ Сессия добавлена. Файл: {file.file_name}, контактов: {data['contacts_count']}", reply_markup=kb.admin_menu_keyboard())
    await state.clear()

@dp.message(AddTdataSession.waiting_file)
async def add_tdata_invalid(message: types.Message):
    await message.answer("❌ Отправьте ZIP-файл")

# ------------------ Добавление текстовой сессии ------------------
@dp.callback_query(lambda c: c.data == "admin_add_text")
async def admin_add_text_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    with models.SessionLocal() as db:
        products = db.query(models.Product).all()
        if not products:
            await callback.message.edit_text("❌ Сначала добавьте товар.")
            return
        text = "📝 Выберите ID товара:\n" + "\n".join([f"ID {p.id}: {p.name}" for p in products])
        await callback.message.edit_text(text)
        await callback.message.answer("Введите ID товара:")
        await state.set_state(AddTextSession.product_id)
    await callback.answer()

@dp.message(AddTextSession.product_id)
async def add_text_product(message: types.Message, state: FSMContext):
    try:
        product_id = int(message.text)
        with models.SessionLocal() as db:
            if not db.query(models.Product).filter_by(id=product_id).first():
                await message.answer("❌ Товар не найден"); return
            await state.update_data(product_id=product_id)
            await message.answer("👥 Введите количество контактов (число):")
            await state.set_state(AddTextSession.contacts_count)
    except:
        await message.answer("❌ Введите число")

@dp.message(AddTextSession.contacts_count)
async def add_text_contacts(message: types.Message, state: FSMContext):
    try:
        contacts = int(message.text)
        await state.update_data(contacts_count=contacts)
        await message.answer("🔑 Введите текст (логин:пароль):")
        await state.set_state(AddTextSession.text_data)
    except:
        await message.answer("❌ Введите число")

@dp.message(AddTextSession.text_data)
async def add_text_data(message: types.Message, state: FSMContext, bot: Bot):
    text_data = message.text
    data = await state.get_data()
    with models.SessionLocal() as db:
        session = models.Session(product_id=data['product_id'], data=text_data, is_file=False,
                                 contacts_count=data['contacts_count'], is_sold=False)
        db.add(session); db.commit()
        await log_action(bot, message.from_user.id, "admin_add_text", f"Добавлена текстовая сессия к товару ID {data['product_id']}")
        await message.answer(f"✅ Текстовая сессия добавлена. Контактов: {data['contacts_count']}", reply_markup=kb.admin_menu_keyboard())
    await state.clear()

# ------------------ Промокоды (админ) ------------------
@dp.callback_query(lambda c: c.data == "admin_promocodes")
async def admin_promocodes_menu(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("🎟 Управление промокодами:", reply_markup=kb.admin_promocodes_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_create_promo")
async def admin_create_promo_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("Введите сумму промокода в USDT (например, 5):")
    await state.set_state(CreatePromoCode.amount)
    await callback.answer()

@dp.message(CreatePromoCode.amount)
async def create_promo_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0: raise ValueError
        await state.update_data(amount=amount)
        await message.answer("Введите максимальное количество активаций (целое число):")
        await state.set_state(CreatePromoCode.max_activations)
    except:
        await message.answer("❌ Введите положительное число")

@dp.message(CreatePromoCode.max_activations)
async def create_promo_max_activations(message: types.Message, state: FSMContext):
    try:
        max_act = int(message.text.strip())
        if max_act <= 0: raise ValueError
        await state.update_data(max_activations=max_act)
        await message.answer("Введите срок действия в формате ДД.ММ.ГГГГ или 0 для бессрочного:")
        await state.set_state(CreatePromoCode.expires_at)
    except:
        await message.answer("❌ Введите целое положительное число")

@dp.message(CreatePromoCode.expires_at)
async def create_promo_expires(message: types.Message, state: FSMContext, bot: Bot):
    expires = message.text.strip()
    expires_at = None
    if expires != "0":
        try:
            expires_at = datetime.strptime(expires, "%d.%m.%Y")
        except:
            await message.answer("❌ Неверный формат. Используйте ДД.ММ.ГГГГ или 0.")
            return
    data = await state.get_data()
    code = f"PROMO{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    with models.SessionLocal() as db:
        promo = models.PromoCode(code=code, amount=data['amount'], max_activations=data['max_activations'],
                                 expires_at=expires_at, created_by=message.from_user.id)
        db.add(promo); db.commit()
        await log_action(bot, message.from_user.id, "create_promo", f"Создан промокод {code} на {data['amount']} USDT")
        await message.answer(
            f"✅ Промокод создан!\n\n🎟 Код: <code>{code}</code>\n💰 Сумма: {data['amount']} {CRYPTO_CURRENCY}\n🔢 Лимит: {data['max_activations']}\n⏳ Срок: {'бессрочный' if expires_at is None else expires_at.strftime('%d.%m.%Y')}",
            parse_mode="HTML", reply_markup=kb.admin_menu_keyboard()
        )
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_list_promos")
async def admin_list_promos(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id): return
    with models.SessionLocal() as db:
        promos = db.query(models.PromoCode).order_by(models.PromoCode.created_at.desc()).all()
        if not promos:
            await callback.message.edit_text("📭 Промокодов нет.", reply_markup=kb.admin_promocodes_keyboard())
            return
        text = "🎟 Список промокодов:\n\n"
        for p in promos:
            text += f"• <code>{p.code}</code> – {p.amount} {CRYPTO_CURRENCY}\n  Активаций: {p.current_activations}/{p.max_activations}\n"
            if p.expires_at: text += f"  Истекает: {p.expires_at.strftime('%d.%m.%Y')}\n"
            text += "\n"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.admin_promocodes_keyboard())
    await callback.answer()

# ------------------ Управление балансами (админ) ------------------
@dp.callback_query(lambda c: c.data == "admin_balance_manage")
async def admin_balance_manage_menu(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("💰 Управление балансами:", reply_markup=kb.admin_balance_manage_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_add_balance")
async def admin_add_balance_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("➕ Введите Telegram ID и сумму через пробел (например, 123456789 10.5):")
    await state.set_state(ManageBalance.user_id)
    await state.update_data(action="add")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_remove_balance")
async def admin_remove_balance_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("➖ Введите Telegram ID и сумму через пробел (например, 123456789 5):")
    await state.set_state(ManageBalance.user_id)
    await state.update_data(action="remove")
    await callback.answer()

@dp.message(ManageBalance.user_id)
async def manage_balance_user_id(message: types.Message, state: FSMContext, bot: Bot):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2: raise ValueError
        user_id = int(parts[0]); amount = float(parts[1])
        if amount <= 0: raise ValueError
        data = await state.get_data()
        action = data['action']
        with models.SessionLocal() as db:
            user = db.query(models.User).filter_by(tg_id=user_id).first()
            if not user:
                await message.answer("❌ Пользователь не найден"); await state.clear(); return
            if action == "add":
                user.balance += amount
                db.commit()
                add_transaction(db, user.id, amount, "deposit", description=f"Администратор")
                await log_action(bot, message.from_user.id, "admin_add_balance", f"+{amount} {CRYPTO_CURRENCY} пользователю {user_id}")
                await message.answer(f"✅ Добавлено {amount} {CRYPTO_CURRENCY}. Баланс: {user.balance:.2f} {CRYPTO_CURRENCY}")
            else:
                if user.balance < amount:
                    await message.answer(f"❌ Недостаточно средств. Доступно: {user.balance:.2f} {CRYPTO_CURRENCY}")
                    await state.clear(); return
                user.balance -= amount
                db.commit()
                add_transaction(db, user.id, -amount, "withdrawal", description=f"Администратор")
                await log_action(bot, message.from_user.id, "admin_remove_balance", f"-{amount} {CRYPTO_CURRENCY} у пользователя {user_id}")
                await message.answer(f"✅ Списано {amount} {CRYPTO_CURRENCY}. Баланс: {user.balance:.2f} {CRYPTO_CURRENCY}")
        await state.clear()
    except:
        await message.answer("❌ Ошибка. Введите ID и сумму через пробел, например: 123456789 10.5")
        await state.clear()

# ------------------ Бан/разбан ------------------
@dp.callback_query(lambda c: c.data == "admin_ban")
async def admin_ban_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("🔨 Введите Telegram ID пользователя:")
    await state.set_state(BanUser.user_id)
    await callback.answer()

@dp.message(BanUser.user_id)
async def admin_ban_user_id(message: types.Message, state: FSMContext, bot: Bot):
    try:
        target_id = int(message.text.strip())
        with models.SessionLocal() as db:
            user = db.query(models.User).filter_by(tg_id=target_id).first()
            if not user:
                await message.answer("❌ Пользователь не найден"); await state.clear(); return
            current = "забанен" if user.is_banned else "не забанен"
            await state.update_data(user_id=target_id, current_status=user.is_banned)
            await message.answer(f"👤 Пользователь {target_id} — {current}. Что сделать?\n/ban - забанить\n/unban - разбанить")
            await state.set_state(BanUser.action)
    except:
        await message.answer("❌ Введите число"); await state.clear()

@dp.message(BanUser.action)
async def admin_ban_action(message: types.Message, state: FSMContext, bot: Bot):
    action = message.text.lower()
    if action not in ["/ban", "/unban"]:
        await message.answer("❌ Введите /ban или /unban"); return
    data = await state.get_data()
    target_id = data['user_id']
    current = data['current_status']
    if action == "/ban":
        if current:
            await message.answer("⚠️ Уже забанен")
        else:
            with models.SessionLocal() as db:
                user = db.query(models.User).filter_by(tg_id=target_id).first()
                user.is_banned = True
                db.commit()
                await log_action(bot, message.from_user.id, "admin_ban", f"Забанен {target_id}")
                await message.answer(f"✅ Пользователь {target_id} забанен")
                try:
                    await bot.send_message(target_id, "🚫 Вы забанены")
                except: pass
    else:
        if not current:
            await message.answer("⚠️ Не забанен")
        else:
            with models.SessionLocal() as db:
                user = db.query(models.User).filter_by(tg_id=target_id).first()
                user.is_banned = False
                db.commit()
                await log_action(bot, message.from_user.id, "admin_unban", f"Разбанен {target_id}")
                await message.answer(f"✅ Пользователь {target_id} разбанен")
                try:
                    await bot.send_message(target_id, "✅ Вы разбанены")
                except: pass
    await state.clear()

# ------------------ Рассылка ------------------
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("📢 Введите текст для рассылки (можно HTML):")
    await state.set_state(Broadcast.text)
    await callback.answer()

@dp.message(Broadcast.text)
async def admin_broadcast_send(message: types.Message, state: FSMContext, bot: Bot):
    text = message.text
    await message.answer("⏳ Рассылка начата...")
    with models.SessionLocal() as db:
        users = db.query(models.User).all()
    sent = 0; failed = 0
    for user in users:
        try:
            await bot.send_message(user.tg_id, text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await message.answer(f"✅ Рассылка завершена.\n📨 Отправлено: {sent}\n❌ Ошибок: {failed}")
    await log_action(bot, message.from_user.id, "admin_broadcast", f"Рассылка: {sent} успешно, {failed} ошибок")
    await state.clear()

# ------------------ Экспорт/импорт данных ------------------
@dp.callback_query(lambda c: c.data == "admin_export_data")
async def admin_export_data(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("⏳ Экспорт данных...")
    with models.SessionLocal() as db:
        users = db.query(models.User).all()
        products = db.query(models.Product).all()
        sessions = db.query(models.Session).all()
        purchases = db.query(models.Purchase).all()
        invoices = db.query(models.Invoice).all()
        promos = db.query(models.PromoCode).all()
        promo_acts = db.query(models.PromoCodeActivation).all()
        logs = db.query(models.Log).limit(1000).all()
        data = {
            "users": [{"tg_id": u.tg_id, "username": u.username, "full_name": u.full_name, "is_admin": u.is_admin,
                       "is_banned": u.is_banned, "balance": u.balance, "referral_balance": u.referral_balance,
                       "referred_by": u.referred_by, "referral_count": u.referral_count,
                       "total_referral_earnings": u.total_referral_earnings} for u in users],
            "products": [{"name": p.name, "description": p.description, "price": p.price,
                          "currency": p.currency, "is_active": p.is_active} for p in products],
            "sessions": [{"product_id": s.product_id, "data": s.data, "file_data": s.file_data.hex() if s.file_data else None,
                          "filename": s.filename, "is_file": s.is_file, "contacts_count": s.contacts_count,
                          "is_sold": s.is_sold} for s in sessions],
            "purchases": [{"user_id": pu.user_id, "product_id": pu.product_id, "session_id": pu.session_id,
                           "paid_with_balance": pu.paid_with_balance, "purchased_at": pu.purchased_at.isoformat()} for pu in purchases],
            "invoices": [{"user_id": i.user_id, "product_id": i.product_id, "crypto_invoice_id": i.crypto_invoice_id,
                          "amount": i.amount, "currency": i.currency, "status": i.status,
                          "is_deposit": i.is_deposit, "created_at": i.created_at.isoformat()} for i in invoices],
            "promocodes": [{"code": p.code, "amount": p.amount, "max_activations": p.max_activations,
                            "current_activations": p.current_activations, "expires_at": p.expires_at.isoformat() if p.expires_at else None,
                            "created_by": p.created_by} for p in promos],
            "promo_activations": [{"user_id": a.user_id, "promo_id": a.promo_id, "activated_at": a.activated_at.isoformat()} for a in promo_acts],
            "logs": [{"user_id": l.user_id, "action": l.action, "details": l.details, "created_at": l.created_at.isoformat()} for l in logs],
        }
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        backup = models.Backup(data=json_str, note=f"Экспорт {datetime.utcnow()}")
        db.add(backup); db.commit()
        await bot.send_document(callback.message.chat.id, BufferedInputFile(json_str.encode('utf-8'), filename=f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"), caption="📦 Бэкап данных")
    await callback.answer("✅ Экспорт завершён")

@dp.callback_query(lambda c: c.data == "admin_import_data")
async def admin_import_data_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("📥 Отправьте JSON-файл с бэкапом:")
    await state.set_state(ImportData.file)
    await callback.answer()

@dp.message(ImportData.file, lambda m: m.document)
async def admin_import_data_file(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id): return
    file = message.document
    if not file.file_name.endswith('.json'):
        await message.answer("❌ Отправьте JSON файл"); return
    file_info = await bot.get_file(file.file_id)
    downloaded = await bot.download_file(file_info.file_path)
    content = downloaded.read().decode('utf-8')
    try:
        data = json.loads(content)
    except:
        await message.answer("❌ Ошибка парсинга JSON"); return
    with models.SessionLocal() as db:
        db.query(models.Purchase).delete()
        db.query(models.Session).delete()
        db.query(models.Product).delete()
        db.query(models.Invoice).delete()
        db.query(models.PromoCodeActivation).delete()
        db.query(models.PromoCode).delete()
        db.query(models.Log).delete()
        for prod_data in data.get("products", []):
            prod = models.Product(**{k:v for k,v in prod_data.items() if k in ['name','description','price','currency','is_active']})
            db.add(prod)
        db.flush()
        for sess_data in data.get("sessions", []):
            sess = models.Session(**sess_data)
            db.add(sess)
        db.commit()
        await log_action(bot, message.from_user.id, "import_data", "Импорт данных")
        await message.answer("✅ Данные импортированы", reply_markup=kb.admin_menu_keyboard())
    await state.clear()

# ------------------ VK Спаммер ------------------
@dp.callback_query(lambda c: c.data == "vk_spammer_menu")
async def vk_spammer_menu(callback: types.CallbackQuery, bot: Bot):
    await log_action(bot, callback.from_user.id, "vk_spammer_menu", "Открыл меню VK спаммера")
    if not await check_vk_subscription(callback.from_user.id):
        await callback.message.edit_text("❌ У вас нет активной подписки на VK Спаммер.\n\n💰 Выберите подписку через /buy_spammer", parse_mode="HTML")
        await callback.answer()
        return
    await callback.message.edit_text("📨 <b>VK Спаммер</b>\n\nВыберите действие:", parse_mode="HTML", reply_markup=kb.vk_spammer_menu_keyboard())
    await callback.answer()

@dp.message(Command("buy_spammer"))
async def buy_spammer(message: types.Message, bot: Bot):
    text = "Выберите срок подписки VK Спаммер:"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц – 10 USDT", callback_data="buy_spammer_1")],
        [InlineKeyboardButton(text="3 месяца – 25 USDT", callback_data="buy_spammer_3")],
        [InlineKeyboardButton(text="6 месяцев – 45 USDT", callback_data="buy_spammer_6")]
    ])
    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("buy_spammer_"))
async def buy_spammer_choose(callback: types.CallbackQuery, bot: Bot):
    months = int(callback.data.split("_")[-1])
    price = {1: 10, 3: 25, 6: 45}[months]
    user_id = callback.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            await callback.answer("❌ Сначала /start", show_alert=True)
            return
        if user.balance >= price:
            user.balance -= price
            expires = datetime.utcnow() + timedelta(days=30*months)
            user.vk_spammer_subscription_until = expires
            db.commit()
            add_transaction(db, user.id, -price, "purchase", description=f"Подписка VK Спаммер {months} мес.")
            await callback.message.edit_text(f"✅ Подписка активирована на {months} месяцев (до {expires.strftime('%d.%m.%Y')}).")
        else:
            try:
                inv_id, pay_url = await crypto_api.create_invoice(price, CRYPTO_CURRENCY)
                invoice = models.Invoice(user_id=user.id, crypto_invoice_id=inv_id, amount=price,
                                         currency=CRYPTO_CURRENCY, status="active", is_deposit=False)
                db.add(invoice); db.commit()
                await callback.message.edit_text(f"💸 Счёт на {price} {CRYPTO_CURRENCY} создан.\nОплатите и нажмите «Проверить оплату».", reply_markup=kb.invoice_keyboard(pay_url, invoice.id))
            except Exception as e:
                await callback.message.edit_text(f"Ошибка: {e}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "vk_add_account")
async def vk_add_account_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_vk_subscription(callback.from_user.id):
        await callback.answer("Нет активной подписки", show_alert=True)
        return
    await callback.message.edit_text("🔑 Введите токен доступа VK (можно получить в настройках приложения VK):")
    await state.set_state(VKAddAccount.token)
    await callback.answer()

@dp.message(VKAddAccount.token)
async def vk_add_account_token(message: types.Message, state: FSMContext, bot: Bot):
    token = message.text.strip()
    try:
        client = VKClient(token)
        user_info = await client.get_user_info()
        if not user_info:
            raise Exception("Не удалось получить данные")
        vk_user = user_info[0]
        friends = await client.get_friends_count()
        groups = await client.get_groups_count()
        followers = await client.get_followers_count()
    except Exception as e:
        await message.answer(f"❌ Ошибка авторизации: {e}\nПроверьте токен.")
        await state.clear()
        return
    user_id = message.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        db.query(models.VKAccount).filter_by(user_id=user.id).delete()
        account = models.VKAccount(
            user_id=user.id,
            access_token=token,
            vk_user_id=vk_user['id'],
            vk_username=f"{vk_user['first_name']} {vk_user['last_name']}",
            friends_count=friends,
            groups_count=groups,
            followers_count=followers,
            subscription_expires=datetime.utcnow() + timedelta(days=30)
        )
        db.add(account); db.commit()
        await log_action(bot, user_id, "vk_add_account", f"Добавлен аккаунт VK ID {vk_user['id']}")
        await message.answer(
            f"✅ Аккаунт VK добавлен!\n\n"
            f"👤 {vk_user['first_name']} {vk_user['last_name']} (ID {vk_user['id']})\n"
            f"👥 Друзей: {friends}\n"
            f"📢 Групп: {groups}\n"
            f"📸 Подписчиков: {followers}\n\n"
            f"Теперь вы можете создавать шаблоны и запускать рассылку.",
            reply_markup=kb.vk_spammer_menu_keyboard()
        )
    await state.clear()

@dp.callback_query(lambda c: c.data == "vk_my_accounts")
async def vk_my_accounts(callback: types.CallbackQuery, bot: Bot):
    if not await check_vk_subscription(callback.from_user.id):
        await callback.answer("Нет подписки", show_alert=True); return
    user_id = callback.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        accounts = db.query(models.VKAccount).filter_by(user_id=user.id).all()
        if not accounts:
            await callback.message.edit_text("У вас нет добавленных аккаунтов VK.", reply_markup=kb.vk_spammer_menu_keyboard())
            return
        await callback.message.edit_text("📊 <b>Ваши аккаунты VK</b>", parse_mode="HTML", reply_markup=kb.vk_accounts_keyboard(accounts))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "vk_templates")
async def vk_templates_menu(callback: types.CallbackQuery, bot: Bot):
    if not await check_vk_subscription(callback.from_user.id):
        await callback.answer("Нет подписки", show_alert=True); return
    user_id = callback.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        templates = db.query(models.VKMessageTemplate).filter_by(user_id=user.id).all()
        if not templates:
            await callback.message.edit_text("У вас нет шаблонов. Создайте первый.", reply_markup=kb.vk_templates_keyboard([]))
            return
        await callback.message.edit_text("📝 <b>Ваши шаблоны сообщений</b>\n\nВыберите шаблон для использования или создайте новый:", parse_mode="HTML", reply_markup=kb.vk_templates_keyboard(templates))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "vk_add_template")
async def vk_add_template_start(callback: types.CallbackQuery, state: FSMContext):
    if not await check_vk_subscription(callback.from_user.id):
        await callback.answer("Нет подписки", show_alert=True); return
    await callback.message.edit_text("📝 Введите название шаблона:")
    await state.set_state(VKAddTemplate.name)
    await callback.answer()

@dp.message(VKAddTemplate.name)
async def vk_add_template_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("✏️ Введите текст сообщения (можно использовать HTML):")
    await state.set_state(VKAddTemplate.text)

@dp.message(VKAddTemplate.text)
async def vk_add_template_text(message: types.Message, state: FSMContext, bot: Bot):
    text = message.text
    data = await state.get_data()
    name = data['name']
    user_id = message.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        template = models.VKMessageTemplate(user_id=user.id, name=name, text=text)
        db.add(template); db.commit()
        await log_action(bot, user_id, "vk_add_template", f"Шаблон '{name}'")
        await message.answer(f"✅ Шаблон «{name}» сохранён.", reply_markup=kb.vk_spammer_menu_keyboard())
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("vk_use_template_"))
async def vk_use_template(callback: types.CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        template = db.query(models.VKMessageTemplate).filter_by(id=template_id, user_id=user.id).first()
        if not template:
            await callback.answer("Шаблон не найден", show_alert=True); return
        await state.update_data(template_id=template_id)
        await callback.message.edit_text("📨 <b>Запуск рассылки</b>\n\nВыберите аккаунт VK:", parse_mode="HTML", reply_markup=kb.vk_accounts_keyboard(db.query(models.VKAccount).filter_by(user_id=user.id).all()))
        await state.set_state(VKStartSpam.account_id)
    await callback.answer()

@dp.callback_query(VKStartSpam.account_id, lambda c: c.data.startswith("vk_select_account_"))
async def vk_spam_select_account(callback: types.CallbackQuery, state: FSMContext):
    account_id = int(callback.data.split("_")[-1])
    await state.update_data(account_id=account_id)
    await callback.message.edit_text("🎯 Выберите тип получателей:\n\n/friends - все друзья\n/groups - все группы\n/followers - все подписчики\n/list - свой список ID через запятую")
    await state.set_state(VKStartSpam.recipients_type)
    await callback.answer()

@dp.message(VKStartSpam.recipients_type)
async def vk_spam_recipients_type(message: types.Message, state: FSMContext, bot: Bot):
    rt = message.text.lower()
    if rt not in ["/friends", "/groups", "/followers", "/list"]:
        await message.answer("❌ Введите /friends, /groups, /followers или /list")
        return
    await state.update_data(recipients_type=rt)
    await message.answer("⏱ Введите интервал между сообщениями в секундах (например, 30):")
    await state.set_state(VKStartSpam.interval)

@dp.message(VKStartSpam.interval)
async def vk_spam_interval(message: types.Message, state: FSMContext, bot: Bot):
    try:
        interval = int(message.text.strip())
        if interval < 5:
            await message.answer("❌ Интервал должен быть не менее 5 секунд.")
            return
        data = await state.get_data()
        account_id = data['account_id']
        template_id = data['template_id']
        recipients_type = data['recipients_type']
        user_id = message.from_user.id
        with models.SessionLocal() as db:
            user = db.query(models.User).filter_by(tg_id=user_id).first()
            account = db.query(models.VKAccount).filter_by(id=account_id, user_id=user.id).first()
            if not account:
                await message.answer("❌ Аккаунт не найден")
                await state.clear()
                return
            template = db.query(models.VKMessageTemplate).filter_by(id=template_id, user_id=user.id).first()
            if not template:
                await message.answer("❌ Шаблон не найден")
                await state.clear()
                return
            client = VKClient(account.access_token)
            if recipients_type == "/friends":
                recipients = await client.get_friends_ids()
                recipients_str = "friends"
            elif recipients_type == "/groups":
                await message.answer("❌ Рассылка по группам временно недоступна.")
                await state.clear()
                return
            elif recipients_type == "/followers":
                await message.answer("❌ Рассылка по подписчикам временно недоступна.")
                await state.clear()
                return
            else:
                await message.answer("Введите список ID получателей через запятую (например, 123,456,789):")
                await state.set_state("vk_spam_list")
                return
            task = models.VKSpamTask(
                user_id=user.id,
                vk_account_id=account_id,
                template_id=template_id,
                recipients=recipients_str,
                interval_seconds=interval,
                status="pending"
            )
            db.add(task); db.commit()
            await log_action(bot, user_id, "vk_create_spam_task", f"Задача #{task.id}")
            await message.answer(f"✅ Задача на рассылку создана (ID {task.id}).\nСтатус: {task.status}\nДля запуска используйте /vk_start_task {task.id}")
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import func
import keyboards as kb
import models
import crypto_api
from config import ADMIN_IDS, CRYPTO_CURRENCY
from log_utils import log_action

dp = Dispatcher()

# ------------------ FSM ------------------
class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    currency = State()

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

# ------------------ Основные команды ------------------
@dp.message(Command("start"))
async def start_cmd(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    # Регистрация пользователя
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=user_id).first()
        if not user:
            user = models.User(
                tg_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                balance=0.0
            )
            db.add(user)
            db.commit()
    await log_action(bot, user_id, "/start", "Запустил бота")
    await message.answer(
        "✨ Добро пожаловать в магазин! ✨\n\n"
        "Используйте кнопки ниже:",
        reply_markup=kb.main_menu_keyboard()
    )

@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery, bot: Bot):
    await callback.message.edit_text(
        "✨ Главное меню ✨",
        reply_markup=kb.main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery, bot: Bot):
    with models.SessionLocal() as db:
        products = db.query(models.Product).filter(
            models.Product.is_active == True,
            models.Product.sessions.any(models.Session.is_sold == False)
        ).all()
        if not products:
            await callback.message.edit_text("📭 Товаров пока нет.")
            return
        await callback.message.edit_text(
            "📂 Каталог:\nВыберите товар:",
            reply_markup=kb.catalog_keyboard(products)
        )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_product(callback: types.CallbackQuery, bot: Bot):
    product_id = int(callback.data.split("_")[1])
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
            await callback.message.edit_text("Товар временно отсутствует.")
            return
        # Показываем первый аккаунт (упрощённо)
        session = free_sessions[0]
        text = f"<b>{product.name}</b>\n\n{product.description}\n\nКонтактов: {session.contacts_count}\nЦена: {product.price} {product.currency}"
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=kb.product_detail_keyboard(product_id)
        )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def create_invoice(callback: types.CallbackQuery, bot: Bot):
    product_id = int(callback.data.split("_")[1])
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=callback.from_user.id).first()
        if not user:
            user = models.User(tg_id=callback.from_user.id)
            db.add(user)
            db.commit()
        product = db.query(models.Product).filter_by(id=product_id).first()
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
            await callback.message.edit_text(f"Ошибка: {e}")
            return
        invoice = models.Invoice(
            user_id=user.id,
            product_id=product_id,
            crypto_invoice_id=invoice_id,
            amount=product.price,
            currency=product.currency,
            status="active",
            is_deposit=False,
            session_id=free_session.id
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
    with models.SessionLocal() as db:
        invoice = db.query(models.Invoice).filter_by(id=invoice_db_id).first()
        if not invoice or invoice.status == "paid":
            await callback.message.edit_text("Счёт уже оплачен или не найден.")
            return
        status = await crypto_api.check_invoice_status(invoice.crypto_invoice_id)
        if status == "paid":
            invoice.status = "paid"
            invoice.paid_at = datetime.utcnow()
            session = db.query(models.Session).filter_by(id=invoice.session_id, is_sold=False).first()
            if not session:
                await callback.message.edit_text("Ошибка: аккаунт уже куплен.")
                return
            session.is_sold = True
            purchase = models.Purchase(
                user_id=invoice.user_id,
                product_id=invoice.product_id,
                session_id=session.id,
                paid_with_balance=False
            )
            db.add(purchase)
            db.commit()
            # Отправка товара
            if session.is_file and session.file_data:
                await bot.send_document(
                    callback.message.chat.id,
                    BufferedInputFile(session.file_data, filename=session.filename),
                    caption=f"✅ Оплата получена!\n{invoice.product.name}\nКонтактов: {session.contacts_count}"
                )
                await bot.send_message(callback.message.chat.id, "Инструкция по установке tdata...", parse_mode="HTML")
            else:
                await callback.message.edit_text(
                    f"✅ Оплата получена!\n\n{invoice.product.name}:\n<code>{session.data}</code>\nКонтактов: {session.contacts_count}",
                    parse_mode="HTML"
                )
            await callback.message.delete()
        else:
            await callback.answer("Платёж ещё не получен.", show_alert=True)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "my_purchases")
async def my_purchases(callback: types.CallbackQuery, bot: Bot):
    with models.SessionLocal() as db:
        user = db.query(models.User).filter_by(tg_id=callback.from_user.id).first()
        if not user:
            await callback.message.edit_text("Нет покупок.")
            return
        purchases = db.query(models.Purchase).filter_by(user_id=user.id).order_by(models.Purchase.purchased_at.desc()).all()
        if not purchases:
            await callback.message.edit_text("Нет покупок.")
            return
        text = "📦 Ваши покупки:\n\n"
        for p in purchases:
            text += f"🔹 {p.product.name} — {p.purchased_at.strftime('%d.%m.%Y %H:%M')}\n"
            if p.session.is_file:
                text += f"   📎 Файл: {p.session.filename}\n"
            else:
                text += f"   📝 Данные: {p.session.data}\n"
            text += "\n"
        await callback.message.edit_text(text, reply_markup=kb.main_menu_keyboard())
    await callback.answer()

# ------------------ Админ-панель (упрощённая) ------------------
@dp.message(Command("admin"))
async def admin_cmd(message: types.Message, bot: Bot):
    if not is_admin(message.from_user.id):
        await message.answer("Нет прав.")
        return
    await message.answer("Админ-панель:", reply_markup=kb.admin_menu_keyboard())

@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu_back(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    await callback.message.edit_text("Админ-панель:", reply_markup=kb.admin_menu_keyboard())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id): return
    with models.SessionLocal() as db:
        total_users = db.query(models.User).count()
        total_products = db.query(models.Product).count()
        total_sessions = db.query(models.Session).count()
        sold = db.query(models.Session).filter_by(is_sold=True).count()
        text = f"📊 Статистика\n👥 Пользователей: {total_users}\n📦 Товаров: {total_products}\n🔑 Сессий: {total_sessions}\n✅ Продано: {sold}"
        await callback.message.edit_text(text, reply_markup=kb.admin_menu_keyboard())
    await callback.answer()

# ------------------ Добавление товара (упрощённо) ------------------
@dp.callback_query(lambda c: c.data == "admin_add_product")
async def admin_add_product_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.edit_text("Введите название товара:")
    await state.set_state(AddProduct.name)
    await callback.answer()

@dp.message(AddProduct.name)
async def add_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите описание:")
    await state.set_state(AddProduct.description)

@dp.message(AddProduct.description)
async def add_product_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите цену в USDT (число):")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
async def add_product_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("Введите валюту (USDT, BTC):")
        await state.set_state(AddProduct.currency)
    except:
        await message.answer("Введите число.")

@dp.message(AddProduct.currency)
async def add_product_currency(message: types.Message, state: FSMContext, bot: Bot):
    currency = message.text.upper()
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
        await log_action(bot, message.from_user.id, "admin_add_product", f"Товар ID {product.id}")
        await message.answer(f"✅ Товар «{product.name}» добавлен.", reply_markup=kb.admin_menu_keyboard())
    await state.clear()

# Остальные обработчики (добавление tdata, текстовых сессий, рассылка и т.д.) можно добавить позже.
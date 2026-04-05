from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CUSTOM_EMOJI, CHANNEL_ID, PRODUCTS_PER_PAGE

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{CUSTOM_EMOJI.get('catalog','🛍')} Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text=f"{CUSTOM_EMOJI.get('my_purchases','📦')} Мои покупки", callback_data="my_purchases")],
        [InlineKeyboardButton(text=f"{CUSTOM_EMOJI.get('balance','💰')} Баланс", callback_data="balance_menu")],
        [InlineKeyboardButton(text=f"{CUSTOM_EMOJI.get('my_referrals','👥')} Мои рефералы", callback_data="my_referrals")]
    ])

def balance_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Пополнить баланс", callback_data="deposit_balance")],
        [InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="activate_promo")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])

def catalog_keyboard(products, page=0):
    start = page * PRODUCTS_PER_PAGE
    end = start + PRODUCTS_PER_PAGE
    page_products = products[start:end]
    buttons = []
    for p in page_products:
        buttons.append([InlineKeyboardButton(text=f"{p.name} — {p.price} {p.currency}", callback_data=f"view_product_{p.id}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"catalog_page_{page-1}"))
    if end < len(products):
        nav.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"catalog_page_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def sessions_keyboard(sessions, product_id, page=0):
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_sessions = sessions[start:end]
    buttons = []
    for s in page_sessions:
        buttons.append([InlineKeyboardButton(text=f"👥 {s.contacts_count} контактов", callback_data=f"buy_session_{s.id}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"sessions_page_{product_id}_{page-1}"))
    if end < len(sessions):
        nav.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"sessions_page_{product_id}_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔙 Назад к товарам", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def product_detail_keyboard(product_id, has_balance=False):
    buttons = []
    if has_balance:
        buttons.append([InlineKeyboardButton(text="💳 Купить с баланса", callback_data=f"buy_with_balance_{product_id}")])
    buttons.append([InlineKeyboardButton(text="💸 Оплатить криптовалютой", callback_data=f"pay_{product_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def invoice_keyboard(pay_url, invoice_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Перейти к оплате", url=pay_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])

def admin_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📜 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton(text="🔄 Скрыть/показать товар", callback_data="admin_toggle_product")],
        [InlineKeyboardButton(text="📎 Добавить tdata (ZIP)", callback_data="admin_add_tdata")],
        [InlineKeyboardButton(text="📝 Добавить текст (логин:пароль)", callback_data="admin_add_text")],
        [InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promocodes")],
        [InlineKeyboardButton(text="💰 Управление балансами", callback_data="admin_balance_manage")],
        [InlineKeyboardButton(text="🔨 Забанить/разбанить", callback_data="admin_ban")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💾 Экспорт данных", callback_data="admin_export_data")],
        [InlineKeyboardButton(text="📥 Импорт данных", callback_data="admin_import_data")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])

def admin_promocodes_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])

def admin_balance_manage_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить баланс", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="➖ Списать баланс", callback_data="admin_remove_balance")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])

def subscription_keyboard():
    if not CHANNEL_ID:
        return None
    if CHANNEL_ID.startswith('@'):
        url = f"https://t.me/{CHANNEL_ID[1:]}"
    else:
        url = f"https://t.me/c/{str(CHANNEL_ID)[4:]}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Подписаться", url=url)],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="verify_sub")]
    ])
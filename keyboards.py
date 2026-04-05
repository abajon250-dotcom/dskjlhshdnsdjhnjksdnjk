from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CUSTOM_EMOJI, CHANNEL_ID, PRODUCTS_PER_PAGE

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{CUSTOM_EMOJI.get('catalog','🛍')} Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text=f"{CUSTOM_EMOJI.get('my_purchases','📦')} Мои покупки", callback_data="my_purchases")],
        [InlineKeyboardButton(text=f"{CUSTOM_EMOJI.get('balance','💰')} Баланс", callback_data="balance_menu")],
        [InlineKeyboardButton(text=f"{CUSTOM_EMOJI.get('my_referrals','👥')} Мои рефералы", callback_data="my_referrals")]
    ], row_width=2)

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
    buttons = [[InlineKeyboardButton(text=f"{p.name} — {p.price} {p.currency}", callback_data=f"view_product_{p.id}")] for p in page_products]
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"catalog_page_{page-1}"))
    if end < len(products): nav.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"catalog_page_{page+1}"))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def sessions_keyboard(sessions, product_id, page=0):
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_sessions = sessions[start:end]
    buttons = [[InlineKeyboardButton(text=f"👥 {s.contacts_count} контактов", callback_data=f"buy_session_{s.id}")] for s in page_sessions]
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"sessions_page_{product_id}_{page-1}"))
    if end < len(sessions): nav.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"sessions_page_{product_id}_{page+1}"))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔙 Назад к товарам", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def product_detail_keyboard(product_id, has_balance=False):
    buttons = []
    if has_balance: buttons.append([InlineKeyboardButton("💳 Купить с баланса", callback_data=f"buy_with_balance_{product_id}")])
    buttons.append([InlineKeyboardButton("💸 Оплатить криптовалютой", callback_data=f"pay_{product_id}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def invoice_keyboard(pay_url, invoice_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("💸 Перейти к оплате", url=pay_url)],
        [InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ])

def admin_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📜 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton("🔄 Скрыть/показать товар", callback_data="admin_toggle_product")],
        [InlineKeyboardButton("📎 Добавить tdata (ZIP)", callback_data="admin_add_tdata")],
        [InlineKeyboardButton("📝 Добавить текст (логин:пароль)", callback_data="admin_add_text")],
        [InlineKeyboardButton("🎟 Промокоды", callback_data="admin_promocodes")],
        [InlineKeyboardButton("💰 Управление балансами", callback_data="admin_balance_manage")],
        [InlineKeyboardButton("🔨 Забанить/разбанить", callback_data="admin_ban")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💾 Экспорт данных", callback_data="admin_export_data")],
        [InlineKeyboardButton("📥 Импорт данных", callback_data="admin_import_data")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ], row_width=2)

def admin_promocodes_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎟 Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton("📋 Список промокодов", callback_data="admin_list_promos")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
    ])

def admin_balance_manage_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Добавить баланс", callback_data="admin_add_balance")],
        [InlineKeyboardButton("➖ Списать баланс", callback_data="admin_remove_balance")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
    ])

def subscription_keyboard():
    if not CHANNEL_ID: return None
    if CHANNEL_ID.startswith('@'): url = f"https://t.me/{CHANNEL_ID[1:]}"
    else: url = f"https://t.me/c/{str(CHANNEL_ID)[4:]}"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🔗 Подписаться", url=url)],[InlineKeyboardButton("✅ Проверить подписку", callback_data="verify_sub")]])
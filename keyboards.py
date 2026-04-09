from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_ID, PRODUCTS_PER_PAGE

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="my_purchases")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance_menu")],
        [InlineKeyboardButton(text="👥 Мои рефералы", callback_data="my_referrals")],
        [InlineKeyboardButton(text="📜 История баланса", callback_data="balance_history")],
        [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
        [InlineKeyboardButton(text="📨 VK Спаммер", callback_data="vk_spammer_menu")],
    ])

def balance_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Пополнить баланс", callback_data="deposit_balance")],
        [InlineKeyboardButton(text="🎟 Активировать промокод", callback_data="activate_promo")],
        [InlineKeyboardButton(text="💸 Вывести средства", callback_data="withdraw_balance")],
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
        [InlineKeyboardButton(text="💰 Изменить цену товара", callback_data="admin_change_price")],
        [InlineKeyboardButton(text="🔄 Скрыть/показать товар", callback_data="admin_toggle_product")],
        [InlineKeyboardButton(text="📎 Добавить tdata (ZIP)", callback_data="admin_add_tdata")],
        [InlineKeyboardButton(text="📝 Добавить текст (логин:пароль)", callback_data="admin_add_text")],
        [InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promocodes")],
        [InlineKeyboardButton(text="📩 Обращения", callback_data="admin_tickets")],
        [InlineKeyboardButton(text="💰 Управление балансами", callback_data="admin_balance_manage")],
        [InlineKeyboardButton(text="💸 Заявки на вывод", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(text="🔨 Забанить/разбанить", callback_data="admin_ban")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💾 Экспорт данных", callback_data="admin_export_data")],
        [InlineKeyboardButton(text="📥 Импорт данных", callback_data="admin_import_data")],
        [InlineKeyboardButton(text="🎟 Выдать подписку VK", callback_data="admin_give_vk_subscription")],
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

def vk_spammer_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Добавить аккаунт VK", callback_data="vk_add_account")],
        [InlineKeyboardButton(text="📊 Мои аккаунты", callback_data="vk_my_accounts")],
        [InlineKeyboardButton(text="📝 Шаблоны сообщений", callback_data="vk_templates")],
        [InlineKeyboardButton(text="🚀 Запустить рассылку", callback_data="vk_start_spam")],
        [InlineKeyboardButton(text="⏸ Мои задачи", callback_data="vk_my_tasks")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])

def vk_templates_keyboard(templates):
    buttons = []
    for t in templates:
        buttons.append([InlineKeyboardButton(text=f"📝 {t.name}", callback_data=f"vk_use_template_{t.id}")])
    buttons.append([InlineKeyboardButton(text="➕ Новый шаблон", callback_data="vk_add_template")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="vk_spammer_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def vk_accounts_keyboard(accounts):
    buttons = []
    for a in accounts:
        buttons.append([InlineKeyboardButton(text=f"👤 {a.vk_username} (ID {a.vk_user_id})", callback_data=f"vk_select_account_{a.id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="vk_spammer_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def vk_tasks_keyboard(tasks):
    buttons = []
    for t in tasks:
        status_emoji = {"pending":"⏳", "running":"▶️", "completed":"✅", "paused":"⏸", "cancelled":"❌"}
        emoji = status_emoji.get(t.status, "❓")
        buttons.append([InlineKeyboardButton(text=f"{emoji} Задача #{t.id} – {t.status}", callback_data=f"vk_task_{t.id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="vk_spammer_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
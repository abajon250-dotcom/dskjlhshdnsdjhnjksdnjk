from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="my_purchases")],
        [InlineKeyboardButton(text="👥 Мои рефералы", callback_data="my_referrals")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)

def catalog_keyboard(products):
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(text=f"{p.name} — {p.price} {p.currency}", callback_data=f"buy_{p.id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def product_detail_keyboard(product_id):
    buttons = [
        [InlineKeyboardButton(text="💰 Оплатить", callback_data=f"pay_{product_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="catalog")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def invoice_keyboard(pay_url, invoice_id):
    buttons = [
        [InlineKeyboardButton(text="💸 Перейти к оплате", url=pay_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{invoice_id}")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def admin_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📜 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton(text="🔄 Скрыть/показать товар", callback_data="admin_toggle_product")],
        [InlineKeyboardButton(text="📎 Добавить tdata (ZIP)", callback_data="admin_add_tdata")],
        [InlineKeyboardButton(text="📝 Добавить текст (логин:пароль)", callback_data="admin_add_text")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="admin_referrals")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)
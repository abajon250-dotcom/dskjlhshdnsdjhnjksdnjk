from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CUSTOM_EMOJI_IDS
from config import CHANNEL_ID

def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(
            text="Каталог",
            callback_data="catalog",
            icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("catalog")
        )],
        [InlineKeyboardButton(
            text="Мои покупки",
            callback_data="my_purchases",
            icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("my_purchases")
        )],
        [InlineKeyboardButton(
            text="Мои рефералы",
            callback_data="my_referrals",
            icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("my_referrals")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)

def catalog_keyboard(products):
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(
            text=f"{p.name} — {p.price} {p.currency}",
            callback_data=f"buy_{p.id}",
            icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("catalog")  # или отдельный ID для "купить"
        )])
    buttons.append([InlineKeyboardButton(
        text="Главное меню",
        callback_data="main_menu",
        icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("main_menu")
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def product_detail_keyboard(product_id):
    buttons = [
        [InlineKeyboardButton(
            text="Оплатить",
            callback_data=f"pay_{product_id}",
            icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("pay")
        )],
        [InlineKeyboardButton(
            text="Назад",
            callback_data="catalog",
            icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("main_menu")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def invoice_keyboard(pay_url, invoice_id):
    buttons = [
        [InlineKeyboardButton(
            text="Перейти к оплате",
            url=pay_url,
            icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("go_to_payment")
        )],
        [InlineKeyboardButton(
            text="Проверить оплату",
            callback_data=f"check_{invoice_id}",
            icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("check_payment")
        )],
        [InlineKeyboardButton(
            text="Главное меню",
            callback_data="main_menu",
            icon_custom_emoji_id=CUSTOM_EMOJI_IDS.get("main_menu")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def admin_menu_keyboard():
    # Для админ-меню вы можете добавить свои ID (их нет в вашем конфиге, поэтому оставим без иконок или добавим позже)
    buttons = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📜 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton(text="🔄 Скрыть/показать товар", callback_data="admin_toggle_product")],
        [InlineKeyboardButton(text="📎 Добавить tdata (ZIP)", callback_data="admin_add_tdata")],
        [InlineKeyboardButton(text="📝 Добавить текст (логин:пароль)", callback_data="admin_add_text")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="admin_referrals")],
        [InlineKeyboardButton(text="🔨 Забанить/разбанить", callback_data="admin_ban")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)

def subscription_keyboard():
    if CHANNEL_ID.startswith('@'):
        url = f"https://t.me/{CHANNEL_ID[1:]}"
    else:
        url = f"https://t.me/c/{str(CHANNEL_ID)[4:]}"
    buttons = [
        [InlineKeyboardButton(text="🔗 Подписаться", url=url)],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="verify_sub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
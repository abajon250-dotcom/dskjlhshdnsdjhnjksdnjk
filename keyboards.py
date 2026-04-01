from config import CUSTOM_EMOJI, CHANNEL_ID
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(
            text="🛍 Каталог",
            callback_data="catalog",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("catalog")
        )],
        [InlineKeyboardButton(
            text="📦 Мои покупки",
            callback_data="my_purchases",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("purchases")
        )],
        [InlineKeyboardButton(
            text="👥 Мои рефералы",
            callback_data="my_referrals",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("referrals")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)

def catalog_keyboard(products):
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(
            text=f"{p.name} — {p.price} {p.currency}",
            callback_data=f"buy_{p.id}",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("buy")
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="main_menu",
        icon_custom_emoji_id=CUSTOM_EMOJI.get("back")
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def product_detail_keyboard(product_id):
    buttons = [
        [InlineKeyboardButton(
            text="💰 Оплатить",
            callback_data=f"pay_{product_id}",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("pay")
        )],
        [InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="catalog",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("back")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def invoice_keyboard(pay_url, invoice_id):
    buttons = [
        [InlineKeyboardButton(
            text="💸 Перейти к оплате",
            url=pay_url,
            icon_custom_emoji_id=CUSTOM_EMOJI.get("payment")
        )],
        [InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data=f"check_{invoice_id}",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("check")
        )],
        [InlineKeyboardButton(
            text="🔙 Главное меню",
            callback_data="main_menu",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("back")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def admin_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="admin_stats",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("stats")
        )],
        [InlineKeyboardButton(
            text="📜 Логи",
            callback_data="admin_logs",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("logs")
        )],
        [InlineKeyboardButton(
            text="➕ Добавить товар",
            callback_data="admin_add_product",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("add_product")
        )],
        [InlineKeyboardButton(
            text="🔄 Скрыть/показать товар",
            callback_data="admin_toggle_product",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("toggle_product")
        )],
        [InlineKeyboardButton(
            text="📎 Добавить tdata (ZIP)",
            callback_data="admin_add_tdata",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("add_tdata")
        )],
        [InlineKeyboardButton(
            text="📝 Добавить текст (логин:пароль)",
            callback_data="admin_add_text",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("add_text")
        )],
        [InlineKeyboardButton(
            text="📢 Сделать рассылку",
            callback_data="admin_broadcast",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("broadcast")
        )],
        [InlineKeyboardButton(
            text="👥 Рефералы",
            callback_data="admin_referrals",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("referrals")
        )],
        [InlineKeyboardButton(
            text="🔨 Забанить/разбанить",
            callback_data="admin_ban",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("ban")
        )],
        [InlineKeyboardButton(
            text="🔙 В главное меню",
            callback_data="main_menu",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("back")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)

def subscription_keyboard():
    """Клавиатура для проверки подписки"""
    if not CHANNEL_ID:
        # Если CHANNEL_ID не задан, возвращаем пустую клавиатуру
        return InlineKeyboardMarkup(inline_keyboard=[])
    if CHANNEL_ID.startswith('@'):
        url = f"https://t.me/{CHANNEL_ID[1:]}"
    else:
        url = f"https://t.me/c/{str(CHANNEL_ID)[4:]}"
    buttons = [
        [InlineKeyboardButton(text="🔗 Подписаться", url=url)],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="verify_sub")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
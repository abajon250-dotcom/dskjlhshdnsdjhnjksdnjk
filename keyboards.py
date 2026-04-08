from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CUSTOM_EMOJI

def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(
            text="🛍 Каталог",
            callback_data="catalog",
            style="primary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("catalog")
        )],
        [InlineKeyboardButton(
            text="📦 Мои покупки",
            callback_data="my_purchases",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("my_purchases")
        )],
        [InlineKeyboardButton(
            text="👥 Мои рефералы",
            callback_data="my_referrals",
            style="success",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("my_referrals")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)

def catalog_keyboard(products):
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(
            text=f"{p.name} — {p.price} {p.currency}",
            callback_data=f"buy_{p.id}",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("buy")
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="main_menu",
        style="secondary",
        icon_custom_emoji_id=CUSTOM_EMOJI.get("back")
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def product_detail_keyboard(product_id):
    buttons = [
        [InlineKeyboardButton(
            text="💰 Оплатить",
            callback_data=f"pay_{product_id}",
            style="success",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("pay")
        )],
        [InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="catalog",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("back")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def invoice_keyboard(pay_url, invoice_id):
    buttons = [
        [InlineKeyboardButton(
            text="💸 Перейти к оплате",
            url=pay_url,
            style="primary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("payment")
        )],
        [InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data=f"check_{invoice_id}",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("check")
        )],
        [InlineKeyboardButton(
            text="🔙 Главное меню",
            callback_data="main_menu",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("back")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=1)

def admin_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="admin_stats",
            style="primary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("stats")
        )],
        [InlineKeyboardButton(
            text="📜 Логи",
            callback_data="admin_logs",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("logs")
        )],
        [InlineKeyboardButton(
            text="➕ Добавить товар",
            callback_data="admin_add_product",
            style="success",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("add_product")
        )],
        [InlineKeyboardButton(
            text="🔄 Скрыть/показать товар",
            callback_data="admin_toggle_product",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("toggle_product")
        )],
        [InlineKeyboardButton(
            text="📎 Добавить tdata (ZIP)",
            callback_data="admin_add_tdata",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("add_tdata")
        )],
        [InlineKeyboardButton(
            text="📝 Добавить текст (логин:пароль)",
            callback_data="admin_add_text",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("add_text")
        )],
        [InlineKeyboardButton(
            text="📢 Сделать рассылку",
            callback_data="admin_broadcast",
            style="danger",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("broadcast")
        )],
        [InlineKeyboardButton(
            text="👥 Рефералы",
            callback_data="admin_referrals",
            style="primary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("referrals")
        )],
        [InlineKeyboardButton(
            text="🔨 Забанить/разбанить",
            callback_data="admin_ban",
            style="danger",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("ban")
        )],
        [InlineKeyboardButton(
            text="🔙 В главное меню",
            callback_data="main_menu",
            style="secondary",
            icon_custom_emoji_id=CUSTOM_EMOJI.get("back")
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons, row_width=2)

def subscription_keyboard():
    if not CHANNEL_ID:
        return InlineKeyboardMarkup(inline_keyboard=[])
    if CHANNEL_ID.startswith('@'):
        url = f"https://t.me/{CHANNEL_ID[1:]}"
    else:
        url = f"https://t.me/c/{str(CHANNEL_ID)[4:]}"
    buttons = [
        [InlineKeyboardButton(text="🔗 Подписаться", url=url, style="primary")],
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="verify_sub", style="success")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
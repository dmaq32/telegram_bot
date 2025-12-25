from typing import List
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from bot.config import settings


def main_user_kb(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Мои покупки", callback_data="my_profile")
    kb.button(text="🛍 Купить подписку", callback_data="catalog")
    kb.button(text="🏠 На главную", callback_data="home")
    if user_id in settings.ADMIN_IDS:
        kb.button(text="⚙️ Админ панель", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()


def purchases_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Смотреть покупки", callback_data="purchases")
    kb.button(text="🏠 На главную", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()

def buy_user_kb(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Купить подписку", callback_data="my_profile")
    kb.adjust(1)
    return kb.as_markup()
def tariff_1m() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Купить 1 месяц", callback_data="buy_1m")
    kb.button(text="⬅ Назад", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()
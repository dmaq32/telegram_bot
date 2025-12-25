from typing import List
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_send_file_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Без файла", callback_data="without_file")
    kb.button(text="Отмена", callback_data="admin_panel")
    kb.adjust(2)
    return kb.as_markup()


def admin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Статистика", callback_data="statistic")
    kb.button(text="🏠 На главную", callback_data="home")
    kb.button(text="👥 Пользователи", callback_data="admin_users")
    kb.adjust(2)
    return kb.as_markup()


def admin_kb_back() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⚙️ Админ панель", callback_data="admin_panel")
    kb.button(text="🏠 На главную", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def cancel_kb_inline() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Отмена", callback_data="cancel")
    return kb.as_markup()


def admin_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Все верно", callback_data="confirm_add")
    kb.button(text="Отмена", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()
def admin_users_list_kb(users_with_counts) -> InlineKeyboardMarkup:
    """
    users_with_counts: список (User, purchases_count)
    """
    kb = InlineKeyboardBuilder()
    for user, count in users_with_counts:
        text = f"User #{user.id} (покупок: {count})"
        kb.button(text=text, callback_data=f"admin_user_{user.id}")
    kb.adjust(1)
    return kb.as_markup()
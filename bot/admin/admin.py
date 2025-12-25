import asyncio
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.config import settings, bot
from bot.dao.dao import UserDAO, PurchaseDao
from bot.admin.kbs import admin_kb, admin_kb_back, cancel_kb_inline, admin_send_file_kb, admin_confirm_kb, admin_users_list_kb
from bot.admin.utils import process_dell_text_msg

admin_router = Router()

class AdminSearchUser(StatesGroup):
    waiting_username = State()
    
@admin_router.callback_query(F.data == "admin_panel", F.from_user.id.in_(settings.ADMIN_IDS))
async def start_admin(call: CallbackQuery):
    await call.answer('Доступ в админ-панель разрешен!')
    await call.message.edit_text(
        text="Вам разрешен доступ в админ-панель. Выберите необходимое действие.",
        reply_markup=admin_kb()
    )
@admin_router.callback_query(F.data == 'statistic', F.from_user.id.in_(settings.ADMIN_IDS))
async def admin_statistic(call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer('Запрос на получение статистики...')
    await call.answer('📊 Собираем статистику...')

    stats = await UserDAO.get_statistics(session=session_without_commit)
    total_summ = await PurchaseDao.get_full_summ(session=session_without_commit)
    stats_message = (
        "📈 Статистика пользователей:\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🆕 Новых за сегодня: {stats['new_today']}\n"
        f"📅 Новых за неделю: {stats['new_week']}\n"
        f"📆 Новых за месяц: {stats['new_month']}\n\n"
        f"💰 Общая сумма заказов: {total_summ} руб.\n\n"
        "🕒 Данные актуальны на текущий момент."
    )
    await call.message.edit_text(
        text=stats_message,
        reply_markup=admin_kb()
    )
@admin_router.callback_query(F.data == "admin_users", F.from_user.id.in_(settings.ADMIN_IDS))
async def admin_users_list(call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer("Загружаю список пользователей")

    users_with_counts = await UserDAO.get_all_with_purchases_count(session_without_commit)

    if not users_with_counts:
        await call.message.edit_text(
            "👥 Пока нет ни одного пользователя.",
            reply_markup=admin_kb_back()
        )
        return

    await call.message.edit_text(
        "👥 <b>Список пользователей</b>",
        reply_markup=admin_users_list_kb(users_with_counts)
    )


# ================== ДЕТАЛИ КОНКРЕТНОГО ПОЛЬЗОВАТЕЛЯ ================== #

@admin_router.callback_query(F.data.startswith("admin_user_"), F.from_user.id.in_(settings.ADMIN_IDS))
async def admin_user_detail(call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer()

    _, _, user_id_str = call.data.partition("admin_user_")
    try:
        user_id = int(user_id_str)
    except ValueError:
        await call.message.answer("Некорректный ID пользователя.")
        return

    user = await UserDAO.get_user_with_purchases(session_without_commit, user_id)

    if not user:
        await call.message.edit_text(
            "Пользователь не найден.",
            reply_markup=admin_kb_back()
        )
        return

    # Расшифровываем telegram_id и username
    real_tg_id = None
    try:
        real_tg_id = decrypt_telegram_id(user.telegram_id_encrypted)
    except Exception as e:
        logger.error(f"Ошибка расшифровки telegram_id: {e}")

    username = None
    try:
        username = decrypt_username(user.username_encrypted)
    except Exception as e:
        logger.error(f"Ошибка расшифровки username: {e}")

    # Статус подписки
    now_msk = datetime.now(MSK).replace(tzinfo=None)
    if user.subscription_until and user.subscription_until > now_msk:
        sub_status = "✅ Активна"
        sub_until = user.subscription_until.strftime("%d.%m.%Y %H:%M")
    else:
        sub_status = "❌ Неактивна"
        sub_until = "—"

    purchases = user.purchases

    lines = [
        f"👤 <b>User #{user.id}</b>",
        f"🔗 Username: @{username}" if username else "🔗 Username: —",
        f"🆔 Telegram ID: <code>{real_tg_id}</code>" if real_tg_id else "🆔 Telegram ID: (недоступен)",
        "",
        f"🟢 <b>Подписка:</b> {sub_status}",
        f"⏱ <b>Действует до:</b> {sub_until}",
        "",
        f"🛒 Покупок: <b>{len(purchases)}</b>",
    ]

    if purchases:
        lines.append("")
        lines.append("📜 <b>Список покупок:</b>")
        for p in purchases:
            lines.append(f"• Покупка #{p.id}: {p.price} ₽, дата: {p.created_at}")

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_kb_back()
    )


# ================== ПОИСК ПО USERNAME (FSM) ================== #

@admin_router.callback_query(F.data == "admin_search_user", F.from_user.id.in_(settings.ADMIN_IDS))
async def admin_search_start(call: CallbackQuery, state: FSMContext):
    """
    Старт поиска пользователя по username.
    """
    await call.answer()
    await state.set_state(AdminSearchUser.waiting_username)
    await call.message.edit_text(
        "🔍 Введите username пользователя (без @):",
        reply_markup=admin_kb_back()
    )


@admin_router.message(AdminSearchUser.waiting_username, F.from_user.id.in_(settings.ADMIN_IDS))
async def admin_search_process(
    message: Message,
    state: FSMContext,
    session_without_commit: AsyncSession,
):
    """
    Обработка введённого username.
    """
    raw = (message.text or "").strip().lstrip("@")

    if not raw:
        await message.answer("❗️Username не должен быть пустым. Попробуйте ещё раз.")
        return

    username_enc = encrypt_username(raw)

    # Ищем пользователя по зашифрованному username
    user = await UserDAO.find_one_or_none(
        session=session_without_commit,
        filters={"username_encrypted": username_enc},
    )

    if not user:
        await message.answer(
            f"Пользователь с username @{raw} не найден.",
            reply_markup=admin_kb()
        )
        await state.clear()
        return

    # Расшифровываем данные для отображения админу
    try:
        username = decrypt_username(user.username_encrypted)
    except Exception as e:
        logger.error(f"Ошибка расшифровки username: {e}")
        username = None

    try:
        real_tg_id = decrypt_telegram_id(user.telegram_id_encrypted)
    except Exception as e:
        logger.error(f"Ошибка расшифровки telegram_id: {e}")
        real_tg_id = None

    text_lines = [
        f"👤 <b>Пользователь найден</b>",
        "",
        f"ID в БД: <b>{user.id}</b>",
        f"Username: @{username}" if username else "Username: —",
        f"Telegram ID: <code>{real_tg_id}</code>" if real_tg_id else "Telegram ID: (недоступен)",
    ]

    await message.answer(
        "\n".join(text_lines),
        reply_markup=admin_kb()
    )
    await state.clear()
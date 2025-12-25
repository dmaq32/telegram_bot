from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery   # вот здесь
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.enums import ContentType
from bot.config import bot, settings
from bot.dao.dao import UserDAO, PurchaseDao
from bot.user.kbs import main_user_kb, purchases_kb, tariff_1m
from bot.user.schemas import UserModel, PaymentData
from bot.dao.utils import hash_telegram_id
from datetime import datetime, timedelta, timezone
from bot.utils import hash_telegram_id
from loguru import logger

user_router = Router()

MSK = timezone(timedelta(hours=3))

@user_router.message(CommandStart())
async def cmd_start(message: Message, session_with_commit: AsyncSession):
    real_tg_id = message.from_user.id
    tg_hash = hash_telegram_id(real_tg_id)

    logger.info(f"cmd_start: real_tg_id={real_tg_id}, tg_hash={tg_hash}")

    user = await UserDAO.find_one_or_none(
        session=session_with_commit,
        filters={"telegram_hash": tg_hash}
    )

    if user:
        logger.info(f"cmd_start: user FOUND id={user.id}")
        await message.answer(
            f"👋 Привет, {message.from_user.full_name}! Выберите необходимое действие",
            reply_markup=main_user_kb(real_tg_id)
        )
        return

    values = UserModel(telegram_hash=tg_hash)
    new_user = await UserDAO.add(session=session_with_commit, values=values)

    logger.info(f"cmd_start: created user id={new_user.id}, hash={tg_hash}")

    await message.answer(
        "🎉 <b>Благодарим за регистрацию!</b>. Теперь выберите необходимое действие.",
        reply_markup=main_user_kb(real_tg_id)
    )

@user_router.callback_query(F.data == "home")
async def page_home(call: CallbackQuery):
    await call.answer("Главная страница")
    return await call.message.answer(
        f"👋 Привет, {call.from_user.full_name}! Выберите необходимое действие",
        reply_markup=main_user_kb(call.from_user.id)
    )
@user_router.callback_query(F.data == "my_profile")
async def page_about(call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer("Профиль")

    # Получаем статистику покупок пользователя
    purchases = await UserDAO.get_purchase_statistics(session=session_without_commit, telegram_id=call.from_user.id)
    total_amount = purchases.get("total_amount", 0)
    total_purchases = purchases.get("total_purchases", 0)

    # Формируем сообщение в зависимости от наличия покупок
    if total_purchases == 0:
        await call.message.answer(
            text="🔍 <b>У вас пока нет покупок.</b>\n\n"
                 "Откройте каталог и выберите что-нибудь интересное!",
            reply_markup=main_user_kb(call.from_user.id)
        )
    else:
        text = (
            f"🛍 <b>Ваш профиль:</b>\n\n"
            f"Количество покупок: <b>{total_purchases}</b>\n"
            f"Общая сумма: <b>{total_amount}₽</b>\n\n"
            "Хотите просмотреть детали ваших покупок?"
        )
        await call.message.answer(
            text=text,
            reply_markup=purchases_kb()
        )
@user_router.callback_query(F.data == "catalog")
async def open_catalog(call: CallbackQuery):
    await call.answer("Каталог подписок")
    text = (
        "📦 <b>Тариф: 1 месяц</b>\n"
        "• Доступ ко всем функциям бота\n"
        "Цена: <b>199₽</b>"
    )
    await call.message.edit_text(text, reply_markup=tariff_1m())

@user_router.callback_query(F.data == "buy_1m")
async def process_buy_1m(call: CallbackQuery, session_without_commit: AsyncSession):
    price = 199
    subscription_code = "sub_1m"

    tg_hash = hash_telegram_id(call.from_user.id)
    logger.info(f"buy_1m: real_tg_id={call.from_user.id}, tg_hash={tg_hash}")

    user_info = await UserDAO.find_one_or_none(
        session=session_without_commit,
        filters={"telegram_hash": tg_hash}
    )

    if not user_info:
        logger.warning("buy_1m: user not found in DB")
        await call.answer("Пользователь не найден в БД. Нажмите /start.", show_alert=True)
        return

    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=f'Оплата 👉 {price}₽',
        description=(
            f'Пожалуйста, завершите оплату в размере {price}₽, '
            f'чтобы открыть доступ к подписке на 1 месяц.'
        ),
        payload=f"{user_info.id}_{subscription_code}",
        provider_token=settings.PROVIDER_TOKEN,
        currency='rub',
        prices=[LabeledPrice(
            label='Подписка 1 месяц',
            amount=price * 100
        )],
    )
    await call.message.delete()

@user_router.callback_query(F.data == "purchases")
async def view_purchases(call: CallbackQuery, session_without_commit: AsyncSession):
    await call.answer("Загружаю ваши покупки")

    hashed_id = hash_telegram_id(call.from_user.id)

    # Находим пользователя по хешу
    user = await UserDAO.find_one_or_none(
        session=session_without_commit,
        filters={"telegram_hash": hashed_id}
    )

    if not user:
        await call.message.answer(
            "Вы ещё не зарегистрированы или записи о вас нет в БД. Нажмите /start.",
            reply_markup=main_user_kb(call.from_user.id)
        )
        return

    # Получаем все покупки этого пользователя
    purchases = await PurchaseDao.find_all(
        session=session_without_commit,
        filters={"user_id": user.id}
    )

    if not purchases:
        await call.message.answer(
            "У вас пока нет покупок.",
            reply_markup=main_user_kb(call.from_user.id)
        )
        return

    lines = [
        "🧾 <b>Ваши покупки:</b>",
        ""
    ]
    for p in purchases:
        lines.append(f"• Покупка #{p.id}: {p.price} ₽, дата: {p.created_at}")

    await call.message.answer(
        "\n".join(lines),
        reply_markup=main_user_kb(call.from_user.id)
    )
@user_router.pre_checkout_query(lambda query: True)
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@user_router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: Message, session_with_commit: AsyncSession):
    payment_info = message.successful_payment

    try:
        user_id_str, subscription_code = payment_info.invoice_payload.split('_', 1)
        user_id = int(user_id_str)
    except ValueError:
        logger.error(f"Неверный формат payload: {payment_info.invoice_payload}")
        await message.answer("Произошла ошибка при обработке платежа. Свяжитесь с администратором.")
        return

    price = payment_info.total_amount // 100  # целое число в рублях

    # Сохраняем покупку в БД
    try:
        payment_data = PaymentData(
            user_id=user_id,
            payment_id=payment_info.telegram_payment_charge_id,
            price=price,
        )
        await PurchaseDao.add(session=session_with_commit, values=payment_data)
    except Exception as e:
        logger.exception(f"Ошибка при сохранении покупки в БД: {e}")
        await message.answer("Произошла ошибка при сохранении покупки. Напишите администратору.")
        return
        
    user = await UserDAO.find_one_or_none(
        session=session_with_commit,
        filters={"id": user_id}
    )
    if user:
        now = datetime.now(MSK)
        # если подписка уже была активна, продлеваем от текущей даты окончания
        base_dt = user.subscription_until if user.subscription_until and user.subscription_until > now else now
        user.subscription_until = base_dt + timedelta(days=30)
        user.is_subscribed = True

    # Уведомляем админов
    for admin_id in settings.ADMIN_IDS:
        try:
            username = message.from_user.username
            user_info = f"@{username} ({message.from_user.id})" if username else f"c ID {message.from_user.id}"

            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💲 Пользователь {user_info} оплатил подписку <b>1 месяц</b> "
                    f"за <b>{price} ₽</b>."
                )
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления администраторам: {e}")

    # Сообщение пользователю
    product_text = (
        "🎉 <b>Спасибо за покупку подписки!</b>\n\n"
        "🕒 <b>Тариф:</b> 1 месяц\n"
        f"🔹 <b>Сумма:</b> <b>{price} ₽</b>\n\n"
        "✅ Доступ к функционалу бота активирован.\n\n"
        "ℹ️ Информацию о своих покупках вы можете найти в личном профиле."
    )

    await message.answer(
        text=product_text,
        reply_markup=main_user_kb(message.from_user.id)
    )
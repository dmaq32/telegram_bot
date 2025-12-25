from datetime import datetime, UTC, timedelta
from typing import Optional, List, Dict, Tuple

from loguru import logger
from sqlalchemy import select, func, case
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from bot.dao.utils import hash_telegram_id

from bot.dao.base import BaseDAO
from bot.dao.models import User, Purchase

class PurchaseDao(BaseDAO[Purchase]):
    model = Purchase

    @classmethod
    async def get_full_summ(cls, session: AsyncSession) -> int:
        """Получить общую сумму покупок."""
        query = select(func.sum(cls.model.price).label('total_price'))
        result = await session.execute(query)
        total_price = result.scalars().one_or_none()
        return total_price if total_price is not None else 0

class UserDAO(BaseDAO[User]):
    model = User

    @classmethod
    
    @classmethod
    async def get_purchase_statistics(cls, session: AsyncSession, telegram_id: int) -> Optional[Dict[str, int]]:
        try:
            """
            Статистика покупок по реальному telegram_id, но в БД храним telegram_hash.
            """
            from bot.dao.models import Purchase  # чтобы избежать циклического импорта

            hashed_id = hash_telegram_id(telegram_id)

            # Находим пользователя по хешу
            user = await cls.find_one_or_none(
                session=session,
                filters={"telegram_hash": hashed_id}
            )
            if not user:
                return {"total_purchases": 0, "total_amount": 0}

            # Считаем количество и сумму его покупок
            result = await session.execute(
                select(
                    func.count(Purchase.id).label('total_purchases'),
                    func.sum(Purchase.price).label('total_amount')
                ).where(Purchase.user_id == user.id)
            )
            stats = result.one_or_none()
            if stats is None:
                return {"total_purchases": 0, "total_amount": 0}

            total_purchases, total_amount = stats
            return {
                "total_purchases": total_purchases or 0,
                "total_amount": total_amount or 0
            }
        except SQLAlchemyError as e:
            # Обработка ошибок при работе с базой данных
            print(f"Ошибка при получении статистики покупок пользователя: {e}")
            return None

    @classmethod
    async def get_statistics(cls, session: AsyncSession):
        try:
            now = datetime.now(UTC)

            query = select(
                func.count().label('total_users'),
                func.sum(case((cls.model.created_at >= now - timedelta(days=1), 1), else_=0)).label('new_today'),
                func.sum(case((cls.model.created_at >= now - timedelta(days=7), 1), else_=0)).label('new_week'),
                func.sum(case((cls.model.created_at >= now - timedelta(days=30), 1), else_=0)).label('new_month')
            )

            result = await session.execute(query)
            stats = result.fetchone()

            statistics = {
                'total_users': stats.total_users,
                'new_today': stats.new_today,
                'new_week': stats.new_week,
                'new_month': stats.new_month
            }

            logger.info(f"Статистика успешно получена: {statistics}")
            return statistics
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            raise
    @classmethod
    async def is_subscribed(cls, session: AsyncSession, telegram_id: int) -> bool:
        from bot.dao.utils import hash_telegram_id
        hashed = hash_telegram_id(telegram_id)

        user = await cls.find_one_or_none(
            session=session,
            filters={"telegram_hash": hashed}
        )
        if not user or not user.subscription_until:
            return False

        now_msk = datetime.now(MSK).replace(tzinfo=None)
        return user.subscription_until > now_msk
    @classmethod
    async def get_all_with_purchases_count(cls, session: AsyncSession) -> List[Tuple[User, int]]:
        """
        Список пользователей + количество их покупок.
        Вернёт список кортежей: (User, purchases_count)
        """
        stmt = (
            select(User, func.count(Purchase.id).label("purchases_count"))
            .join(Purchase, Purchase.user_id == User.id, isouter=True)
            .group_by(User.id)
            .order_by(User.id)
        )
        result = await session.execute(stmt)
        return result.all()

    @classmethod
    async def get_user_with_purchases(cls, session: AsyncSession, user_id: int) -> Optional[User]:
        """
        Один пользователь + его покупки.
        """
        stmt = (
            select(User)
            .options(selectinload(User.purchases))
            .where(User.id == user_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
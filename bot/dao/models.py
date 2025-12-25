from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Text, ForeignKey, String, Boolean, DateTime
from bot.dao.database import Base
from datetime import datetime


class User(Base):
    telegram_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    purchases: Mapped[list['Purchase']] = relationship(
        "Purchase",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, telegram_hash='{self.telegram_hash[:8]}...')>"

class Purchase(Base):
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    price: Mapped[int]
    payment_id: Mapped[str] = mapped_column(unique=True)
    user: Mapped["User"] = relationship("User", back_populates="purchases")

    def __repr__(self):
        return f"<Purchase(id={self.id}, user_id={self.user_id}, date={self.created_at})>"
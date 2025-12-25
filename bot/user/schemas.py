from pydantic import BaseModel, ConfigDict, Field


class UserModel(BaseModel):
    telegram_hash: str
    model_config = ConfigDict(from_attributes=True)
    
class PaymentData(BaseModel):
    user_id: int = Field(..., description="ID пользователя Telegram")
    payment_id: str = Field(..., max_length=255, description="Уникальный ID платежа")
    price: int = Field(..., description="Сумма платежа в рублях")
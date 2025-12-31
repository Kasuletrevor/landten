from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from app.models.payment_schedule import PaymentFrequency


# Request schemas
class PaymentScheduleCreate(BaseModel):
    amount: float
    frequency: PaymentFrequency = PaymentFrequency.MONTHLY
    due_day: int = 1  # 1-28
    window_days: int = 5
    start_date: date


class PaymentScheduleUpdate(BaseModel):
    amount: Optional[float] = None
    frequency: Optional[PaymentFrequency] = None
    due_day: Optional[int] = None
    window_days: Optional[int] = None
    is_active: Optional[bool] = None


# Response schemas
class PaymentScheduleResponse(BaseModel):
    id: str
    tenant_id: str
    amount: float
    frequency: PaymentFrequency
    due_day: int
    window_days: int
    start_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from app.models.payment_schedule import PaymentFrequency


# Request schemas
class PaymentScheduleCreate(BaseModel):
    amount: float = Field(..., gt=0)
    frequency: PaymentFrequency = PaymentFrequency.BI_MONTHLY
    due_day: int = Field(default=1, ge=1, le=28)
    window_days: int = Field(default=5, ge=1, le=15)
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

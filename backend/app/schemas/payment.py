from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.models.payment import PaymentStatus


# Request schemas
class PaymentMarkPaid(BaseModel):
    payment_reference: str
    paid_date: Optional[date] = None  # Defaults to today if not provided
    notes: Optional[str] = None


class PaymentWaive(BaseModel):
    notes: Optional[str] = None


class PaymentUpdate(BaseModel):
    amount_due: Optional[float] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class ManualPaymentCreate(BaseModel):
    """For one-off charges outside the regular schedule"""

    tenant_id: str
    amount_due: float
    due_date: date
    period_start: date
    period_end: date
    notes: Optional[str] = None


# Response schemas
class PaymentResponse(BaseModel):
    id: str
    tenant_id: str
    schedule_id: Optional[str] = None
    period_start: date
    period_end: date
    amount_due: float
    due_date: date
    window_end_date: date
    status: PaymentStatus
    paid_date: Optional[date] = None
    payment_reference: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None
    is_manual: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentWithTenant(PaymentResponse):
    """Payment with tenant and property info for list views"""

    tenant_name: Optional[str] = None
    tenant_email: Optional[str] = None
    tenant_phone: Optional[str] = None
    room_name: Optional[str] = None
    property_id: Optional[str] = None
    property_name: Optional[str] = None


class PaymentListResponse(BaseModel):
    payments: List[PaymentWithTenant]
    total: int


class PaymentSummary(BaseModel):
    """Summary statistics for dashboard"""

    total_upcoming: int = 0
    total_pending: int = 0
    total_overdue: int = 0
    total_paid_this_month: int = 0
    amount_collected_this_month: float = 0.0
    amount_outstanding: float = 0.0

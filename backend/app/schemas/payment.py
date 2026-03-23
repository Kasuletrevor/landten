from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.models.payment import PaymentStatus
from app.models.payment_dispute import DisputeStatus, DisputeActorType


# Request schemas
class PaymentMarkPaid(BaseModel):
    payment_reference: str
    paid_date: Optional[date] = None  # Defaults to today if not provided
    notes: Optional[str] = None


class PaymentWaive(BaseModel):
    notes: Optional[str] = None


class PaymentRejectReceipt(BaseModel):
    reason: str


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
    rejection_reason: Optional[str] = None
    dispute_status: Optional[DisputeStatus] = None
    dispute_unread_count: int = 0
    last_dispute_message_at: Optional[datetime] = None
    is_manual: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields for UI display
    days_until_due: Optional[int] = (
        None  # Positive = days until due, Negative = days overdue
    )
    days_overdue: Optional[int] = None  # Only positive when overdue, None otherwise

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
    currency: Optional[str] = None  # Room's currency for proper formatting


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


class PaymentDisputeMessageCreate(BaseModel):
    body: str


class PaymentDisputeMessageResponse(BaseModel):
    id: str
    dispute_id: str
    payment_id: str
    author_type: DisputeActorType
    author_id: str
    body: str
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_content_type: Optional[str] = None
    attachment_size_bytes: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaymentDisputeResponse(BaseModel):
    id: str
    payment_id: str
    status: DisputeStatus
    opened_by_type: DisputeActorType
    opened_by_id: str
    opened_at: datetime
    resolved_by_type: Optional[DisputeActorType] = None
    resolved_by_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    landlord_last_read_at: Optional[datetime] = None
    tenant_last_read_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    messages: List[PaymentDisputeMessageResponse] = []

    class Config:
        from_attributes = True

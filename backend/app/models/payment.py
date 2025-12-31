from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime, date, timezone
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class PaymentStatus(str, Enum):
    """Payment status options"""

    UPCOMING = "upcoming"  # Before window starts
    PENDING = "pending"  # During payment window (due_day to due_day + window_days)
    ON_TIME = "on_time"  # Paid within window
    LATE = "late"  # Paid after window but within period
    OVERDUE = "overdue"  # Not paid after period ends
    WAIVED = "waived"  # Landlord forgave the payment


class Payment(SQLModel, table=True):
    """Payment record - tracks individual payment instances"""

    __tablename__ = "payments"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    schedule_id: Optional[str] = Field(default=None, foreign_key="payment_schedules.id")

    # Period this payment covers
    period_start: date
    period_end: date

    # Payment details
    amount_due: float
    due_date: date  # The specific due date for this payment
    window_end_date: date  # Last day to pay on time

    # Payment status
    status: PaymentStatus = Field(default=PaymentStatus.UPCOMING)
    paid_date: Optional[date] = None
    payment_reference: Optional[str] = None  # Bank receipt/transaction reference
    notes: Optional[str] = None

    # Flags
    is_manual: bool = Field(default=False)  # True for one-off charges

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant: Optional["Tenant"] = Relationship(back_populates="payments")

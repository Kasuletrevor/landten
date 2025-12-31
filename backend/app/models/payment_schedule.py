from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime, date, timezone
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class PaymentFrequency(str, Enum):
    """Payment frequency options"""

    MONTHLY = "monthly"
    BI_MONTHLY = "bi_monthly"  # Every 2 months
    QUARTERLY = "quarterly"  # Every 3 months


class PaymentSchedule(SQLModel, table=True):
    """Payment schedule for a tenant - defines when and how much they pay"""

    __tablename__ = "payment_schedules"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", unique=True, index=True)
    amount: float  # Amount due each period
    frequency: PaymentFrequency = Field(default=PaymentFrequency.MONTHLY)
    due_day: int = Field(default=1, ge=1, le=28)  # Day of month payment is due
    window_days: int = Field(
        default=5, ge=1
    )  # Days after due_day payment is accepted on time
    start_date: date  # When this schedule begins
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant: Optional["Tenant"] = Relationship(back_populates="payment_schedule")

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class DisputeStatus(str, Enum):
    """Payment dispute lifecycle state."""

    OPEN = "open"
    RESOLVED = "resolved"


class DisputeActorType(str, Enum):
    """Actor type for dispute events/messages."""

    LANDLORD = "landlord"
    TENANT = "tenant"
    SYSTEM = "system"


class PaymentDispute(SQLModel, table=True):
    """Thread container for a single payment dispute."""

    __tablename__ = "payment_disputes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    payment_id: str = Field(foreign_key="payments.id", index=True, unique=True)
    status: DisputeStatus = Field(default=DisputeStatus.OPEN)

    opened_by_type: DisputeActorType
    opened_by_id: str
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    resolved_by_type: Optional[DisputeActorType] = None
    resolved_by_id: Optional[str] = None
    resolved_at: Optional[datetime] = None

    landlord_last_read_at: Optional[datetime] = None
    tenant_last_read_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )


class PaymentDisputeMessage(SQLModel, table=True):
    """Message entry in a payment dispute thread."""

    __tablename__ = "payment_dispute_messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    dispute_id: str = Field(foreign_key="payment_disputes.id", index=True)
    payment_id: str = Field(foreign_key="payments.id", index=True)

    author_type: DisputeActorType
    author_id: str
    body: str
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_content_type: Optional[str] = None
    attachment_size_bytes: Optional[int] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


class NotificationType(str, Enum):
    """Notification types"""

    PAYMENT_DUE = "payment_due"
    PAYMENT_OVERDUE = "payment_overdue"
    PAYMENT_RECEIVED = "payment_received"
    TENANT_ADDED = "tenant_added"
    TENANT_REMOVED = "tenant_removed"
    REMINDER_SENT = "reminder_sent"


class Notification(SQLModel, table=True):
    """Notification model - for in-app notifications via SSE"""

    __tablename__ = "notifications"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    landlord_id: str = Field(foreign_key="landlords.id", index=True)
    type: NotificationType
    title: str
    message: str
    is_read: bool = Field(default=False)

    # Optional references
    tenant_id: Optional[str] = None
    payment_id: Optional[str] = None
    property_id: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

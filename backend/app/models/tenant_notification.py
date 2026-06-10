from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class TenantNotificationType(str, Enum):
    """Notification types for tenants"""

    PAYMENT_RECEIPT_REJECTED = "payment_receipt_rejected"
    PAYMENT_DISPUTE_MESSAGE = "payment_dispute_message"
    MAINTENANCE_REQUEST_UPDATED = "maintenance_request_updated"
    MAINTENANCE_COMMENT_CREATED = "maintenance_comment_created"
    PAYMENT_REMINDER = "payment_reminder"
    LEASE_SIGNED = "lease_signed"
    LEASE_REJECTED = "lease_rejected"


class TenantNotification(SQLModel, table=True):
    """Persistent notification for tenant in-app inbox"""

    __tablename__ = "tenant_notifications"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    type: TenantNotificationType
    title: str
    message: str
    is_read: bool = Field(default=False)

    # Optional references
    payment_id: Optional[str] = None
    property_id: Optional[str] = None
    maintenance_request_id: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

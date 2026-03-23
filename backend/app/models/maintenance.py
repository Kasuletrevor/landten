from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class MaintenanceCategory(str, Enum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    APPLIANCE = "appliance"
    STRUCTURAL = "structural"
    OTHER = "other"


class MaintenanceUrgency(str, Enum):
    EMERGENCY = "emergency"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MaintenanceStatus(str, Enum):
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenanceAuthorType(str, Enum):
    LANDLORD = "landlord"
    TENANT = "tenant"
    SYSTEM = "system"


class MaintenanceRequest(SQLModel, table=True):
    __tablename__ = "maintenance_requests"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True)
    property_id: str = Field(foreign_key="properties.id", index=True)
    room_id: str = Field(foreign_key="rooms.id", index=True)

    category: MaintenanceCategory
    urgency: MaintenanceUrgency = Field(default=MaintenanceUrgency.MEDIUM)
    status: MaintenanceStatus = Field(default=MaintenanceStatus.SUBMITTED)

    title: str
    description: str
    preferred_entry_time: Optional[str] = None

    assigned_to: Optional[str] = None
    scheduled_visit_at: Optional[datetime] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    landlord_notes: Optional[str] = None

    completed_at: Optional[datetime] = None
    tenant_rating: Optional[int] = None
    tenant_feedback: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )


class MaintenanceComment(SQLModel, table=True):
    __tablename__ = "maintenance_comments"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    request_id: str = Field(foreign_key="maintenance_requests.id", index=True)

    author_type: MaintenanceAuthorType
    author_id: str
    body: str
    is_internal: bool = Field(default=False)

    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_content_type: Optional[str] = None
    attachment_size_bytes: Optional[int] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

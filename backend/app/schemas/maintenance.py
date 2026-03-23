from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.maintenance import (
    MaintenanceCategory,
    MaintenanceUrgency,
    MaintenanceStatus,
    MaintenanceAuthorType,
)


class MaintenanceRequestCreate(BaseModel):
    category: MaintenanceCategory
    urgency: MaintenanceUrgency = MaintenanceUrgency.MEDIUM
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(min_length=5, max_length=5000)
    preferred_entry_time: Optional[str] = Field(default=None, max_length=280)


class MaintenanceRequestUpdate(BaseModel):
    status: Optional[MaintenanceStatus] = None
    assigned_to: Optional[str] = Field(default=None, max_length=120)
    scheduled_visit_at: Optional[datetime] = None
    estimated_cost: Optional[float] = Field(default=None, ge=0)
    actual_cost: Optional[float] = Field(default=None, ge=0)
    landlord_notes: Optional[str] = Field(default=None, max_length=4000)


class MaintenanceResolveRequest(BaseModel):
    tenant_rating: Optional[int] = Field(default=None, ge=1, le=5)
    tenant_feedback: Optional[str] = Field(default=None, max_length=2000)


class MaintenanceCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    is_internal: bool = False


class MaintenanceCommentResponse(BaseModel):
    id: str
    request_id: str
    author_type: MaintenanceAuthorType
    author_id: str
    body: str
    is_internal: bool
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_content_type: Optional[str] = None
    attachment_size_bytes: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MaintenanceRequestResponse(BaseModel):
    id: str
    tenant_id: str
    property_id: str
    room_id: str
    category: MaintenanceCategory
    urgency: MaintenanceUrgency
    status: MaintenanceStatus
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
    created_at: datetime
    updated_at: datetime

    tenant_name: Optional[str] = None
    tenant_email: Optional[str] = None
    tenant_phone: Optional[str] = None
    property_name: Optional[str] = None
    room_name: Optional[str] = None

    comments_count: int = 0
    comments: List[MaintenanceCommentResponse] = []

    class Config:
        from_attributes = True


class MaintenanceRequestListResponse(BaseModel):
    requests: List[MaintenanceRequestResponse]
    total: int

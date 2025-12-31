from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.notification import NotificationType


# Response schemas
class NotificationResponse(BaseModel):
    id: str
    landlord_id: str
    type: NotificationType
    title: str
    message: str
    is_read: bool
    tenant_id: Optional[str] = None
    payment_id: Optional[str] = None
    property_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


# SSE Event schema
class SSEEvent(BaseModel):
    event: str
    data: dict

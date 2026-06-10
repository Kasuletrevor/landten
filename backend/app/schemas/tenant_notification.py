from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.tenant_notification import TenantNotificationType


# Response schemas
class TenantNotificationResponse(BaseModel):
    id: str
    tenant_id: str
    type: TenantNotificationType
    title: str
    message: str
    is_read: bool
    payment_id: Optional[str] = None
    property_id: Optional[str] = None
    maintenance_request_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TenantNotificationListResponse(BaseModel):
    notifications: List[TenantNotificationResponse]
    total: int
    unread_count: int

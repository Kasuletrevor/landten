from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
from app.models.payment_schedule import PaymentFrequency


# Request schemas
class TenantCreate(BaseModel):
    room_id: str
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    move_in_date: date
    notes: Optional[str] = None

    # Optional: create payment schedule at the same time
    payment_amount: Optional[float] = None
    payment_frequency: Optional[PaymentFrequency] = PaymentFrequency.MONTHLY
    payment_due_day: Optional[int] = 1
    payment_window_days: Optional[int] = 5


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class TenantMoveOut(BaseModel):
    move_out_date: date


# Tenant Portal Auth schemas
class TenantLogin(BaseModel):
    email: EmailStr
    password: str


class TenantSetPassword(BaseModel):
    """Used when tenant first sets up their portal account"""

    password: str


class TenantChangePassword(BaseModel):
    current_password: str
    new_password: str


# Response schemas
class TenantResponse(BaseModel):
    id: str
    room_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    move_in_date: date
    move_out_date: Optional[date] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantPortalResponse(BaseModel):
    """Tenant info for portal (includes property/room details)"""

    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    move_in_date: date
    move_out_date: Optional[date] = None
    is_active: bool
    room_name: Optional[str] = None
    property_name: Optional[str] = None
    landlord_name: Optional[str] = None
    has_portal_access: bool = False

    class Config:
        from_attributes = True


class TenantLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant: TenantPortalResponse


class TenantWithDetails(TenantResponse):
    """Tenant with room and property info"""

    room_name: Optional[str] = None
    property_id: Optional[str] = None
    property_name: Optional[str] = None
    rent_amount: Optional[float] = None
    has_payment_schedule: bool = False
    has_portal_access: bool = False
    pending_payments: int = 0
    overdue_payments: int = 0


class TenantListResponse(BaseModel):
    tenants: List[TenantWithDetails]
    total: int

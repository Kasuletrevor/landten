from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.models.lease_agreement import LeaseStatus


# Request schemas
class LeaseAgreementCreate(BaseModel):
    """Create a new lease agreement (landlord uploads original PDF)"""

    tenant_id: str
    property_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_amount: Optional[float] = None


class LeaseAgreementUpdate(BaseModel):
    """Update lease agreement details"""

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_amount: Optional[float] = None


# Response schemas
class LeaseAgreementResponse(BaseModel):
    """Lease agreement response"""

    id: str
    tenant_id: str
    property_id: str
    original_url: str
    signed_url: Optional[str] = None
    status: LeaseStatus
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_amount: Optional[float] = None
    uploaded_by_landlord: bool
    signed_uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeaseAgreementWithTenant(LeaseAgreementResponse):
    """Lease agreement with tenant and property info"""

    tenant_name: Optional[str] = None
    tenant_email: Optional[str] = None
    tenant_phone: Optional[str] = None
    room_name: Optional[str] = None
    property_name: Optional[str] = None


class LeaseAgreementListResponse(BaseModel):
    """List of lease agreements"""

    leases: List[LeaseAgreementWithTenant]
    total: int


class LeaseStatusSummary(BaseModel):
    """Summary of lease statuses"""

    total_unsigned: int = 0
    total_signed: int = 0
    total: int = 0

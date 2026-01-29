from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# Request schemas
class PropertyCreate(BaseModel):
    name: str
    address: Optional[str] = None
    description: Optional[str] = None
    grace_period_days: int = 5  # Default 5 days grace period


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    grace_period_days: Optional[int] = None


# Response schemas
class PropertyResponse(BaseModel):
    id: str
    landlord_id: str
    name: str
    address: Optional[str] = None
    description: Optional[str] = None
    grace_period_days: int = 5
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PropertyWithStats(PropertyResponse):
    """Property with computed statistics"""

    total_rooms: int = 0
    occupied_rooms: int = 0
    vacant_rooms: int = 0
    total_tenants: int = 0
    monthly_expected_income: float = 0.0


class PropertyListResponse(BaseModel):
    properties: List[PropertyWithStats]
    total: int

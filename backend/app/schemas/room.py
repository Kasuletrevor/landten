from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# Supported currencies with display info
CURRENCIES = {
    "UGX": {"symbol": "UGX", "name": "Ugandan Shilling"},
    "USD": {"symbol": "$", "name": "US Dollar"},
    "KES": {"symbol": "KES", "name": "Kenyan Shilling"},
    "TZS": {"symbol": "TZS", "name": "Tanzanian Shilling"},
    "RWF": {"symbol": "RWF", "name": "Rwandan Franc"},
    "EUR": {"symbol": "€", "name": "Euro"},
    "GBP": {"symbol": "£", "name": "British Pound"},
}


# Request schemas
class RoomCreate(BaseModel):
    name: str
    rent_amount: float
    currency: str = "UGX"
    description: Optional[str] = None


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    rent_amount: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None


# Response schemas
class RoomResponse(BaseModel):
    id: str
    property_id: str
    name: str
    rent_amount: float
    currency: str
    is_occupied: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoomWithTenant(RoomResponse):
    """Room with current tenant info"""

    tenant_name: Optional[str] = None
    tenant_id: Optional[str] = None


class RoomListResponse(BaseModel):
    rooms: List[RoomWithTenant]
    total: int

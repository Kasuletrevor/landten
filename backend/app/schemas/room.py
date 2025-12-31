from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# Request schemas
class RoomCreate(BaseModel):
    name: str
    rent_amount: float
    description: Optional[str] = None


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    rent_amount: Optional[float] = None
    description: Optional[str] = None


# Response schemas
class RoomResponse(BaseModel):
    id: str
    property_id: str
    name: str
    rent_amount: float
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

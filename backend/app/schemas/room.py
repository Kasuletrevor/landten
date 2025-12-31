from pydantic import BaseModel, field_validator
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


# Bulk creation schemas
class PriceRange(BaseModel):
    """A price range for bulk room creation"""

    from_number: int
    to_number: int
    rent_amount: float

    @field_validator("to_number")
    @classmethod
    def to_must_be_gte_from(cls, v, info):
        if "from_number" in info.data and v < info.data["from_number"]:
            raise ValueError("to_number must be >= from_number")
        return v

    @field_validator("rent_amount")
    @classmethod
    def rent_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("rent_amount must be positive")
        return v


class BulkRoomCreate(BaseModel):
    """Request schema for bulk room creation"""

    prefix: str = ""
    from_number: int
    to_number: int
    currency: str = "UGX"
    price_ranges: List[PriceRange]
    padding: int = 0  # Number of digits for zero-padding

    @field_validator("to_number")
    @classmethod
    def to_must_be_gte_from(cls, v, info):
        if "from_number" in info.data and v < info.data["from_number"]:
            raise ValueError("to_number must be >= from_number")
        return v

    @field_validator("price_ranges")
    @classmethod
    def must_have_price_ranges(cls, v):
        if not v:
            raise ValueError("At least one price range is required")
        return v


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


class BulkRoomResponse(BaseModel):
    """Response schema for bulk room creation"""

    created: List[RoomResponse]
    total_created: int
    warnings: List[str]

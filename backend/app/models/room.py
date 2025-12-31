from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.tenant import Tenant


class Currency(str, Enum):
    """Supported currencies"""

    UGX = "UGX"  # Ugandan Shilling
    USD = "USD"  # US Dollar
    KES = "KES"  # Kenyan Shilling
    TZS = "TZS"  # Tanzanian Shilling
    RWF = "RWF"  # Rwandan Franc
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound


class Room(SQLModel, table=True):
    """Room model - a rentable unit within a property"""

    __tablename__ = "rooms"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    property_id: str = Field(foreign_key="properties.id", index=True)
    name: str  # e.g., "Room 101", "Unit A"
    rent_amount: float  # Default rent for this room
    currency: str = Field(default="UGX")  # Currency code (UGX default for Uganda)
    is_occupied: bool = Field(default=False)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    property: Optional["Property"] = Relationship(back_populates="rooms")
    tenants: List["Tenant"] = Relationship(back_populates="room")

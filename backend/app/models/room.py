from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal
import uuid

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.tenant import Tenant


class Room(SQLModel, table=True):
    """Room model - a rentable unit within a property"""

    __tablename__ = "rooms"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    property_id: str = Field(foreign_key="properties.id", index=True)
    name: str  # e.g., "Room 101", "Unit A"
    rent_amount: float  # Default rent for this room
    is_occupied: bool = Field(default=False)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    property: Optional["Property"] = Relationship(back_populates="rooms")
    tenants: List["Tenant"] = Relationship(back_populates="room")

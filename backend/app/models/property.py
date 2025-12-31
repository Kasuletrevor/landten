from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from app.models.landlord import Landlord
    from app.models.room import Room


class Property(SQLModel, table=True):
    """Property model - a rental property owned by a landlord"""

    __tablename__ = "properties"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    landlord_id: str = Field(foreign_key="landlords.id", index=True)
    name: str
    address: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    landlord: Optional["Landlord"] = Relationship(back_populates="properties")
    rooms: List["Room"] = Relationship(back_populates="property")

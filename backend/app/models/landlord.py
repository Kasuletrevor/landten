from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
import uuid

if TYPE_CHECKING:
    from app.models.property import Property


class Landlord(SQLModel, table=True):
    """Landlord model - owns properties and manages tenants"""

    __tablename__ = "landlords"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    phone: Optional[str] = None
    primary_currency: str = Field(default="UGX")  # Currency for dashboard totals
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    properties: List["Property"] = Relationship(back_populates="landlord")

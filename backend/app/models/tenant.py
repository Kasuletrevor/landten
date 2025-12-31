from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, date
import uuid

if TYPE_CHECKING:
    from app.models.room import Room
    from app.models.payment_schedule import PaymentSchedule
    from app.models.payment import Payment


class Tenant(SQLModel, table=True):
    """Tenant model - a person renting a room"""

    __tablename__ = "tenants"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    room_id: str = Field(foreign_key="rooms.id", index=True)
    name: str
    email: Optional[str] = Field(default=None, index=True)
    phone: Optional[str] = None
    move_in_date: date
    move_out_date: Optional[date] = None
    is_active: bool = Field(default=True)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    room: Optional["Room"] = Relationship(back_populates="tenants")
    payment_schedule: Optional["PaymentSchedule"] = Relationship(
        back_populates="tenant"
    )
    payments: List["Payment"] = Relationship(back_populates="tenant")

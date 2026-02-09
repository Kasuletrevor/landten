from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime, date, timezone
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.property import Property


class LeaseStatus(str, Enum):
    """Lease agreement status"""

    UNSIGNED = "unsigned"  # Original uploaded, awaiting signature
    SIGNED = "signed"  # Signed copy uploaded


class LeaseAgreement(SQLModel, table=True):
    """Lease agreement document for a tenant"""

    __tablename__ = "lease_agreements"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(foreign_key="tenants.id", index=True, unique=True)
    property_id: str = Field(foreign_key="properties.id", index=True)

    # Document URLs
    original_url: str  # Original PDF uploaded by landlord
    signed_url: Optional[str] = None  # Signed PDF uploaded by either party

    # Status tracking
    status: LeaseStatus = Field(default=LeaseStatus.UNSIGNED)

    # Key lease terms (for reference, extracted from PDF)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_amount: Optional[float] = None

    # Upload tracking
    uploaded_by_landlord: bool = Field(default=True)
    signed_uploaded_by: Optional[str] = None  # 'landlord' or 'tenant'

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant: Optional["Tenant"] = Relationship(back_populates="lease_agreement")
    property: Optional["Property"] = Relationship(back_populates="lease_agreements")

    def __repr__(self):
        return f"<LeaseAgreement(id={self.id}, tenant_id={self.tenant_id}, status={self.status})>"

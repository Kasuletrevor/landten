# Import all models for Alembic and SQLModel metadata
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment_schedule import PaymentSchedule, PaymentFrequency
from app.models.payment import Payment, PaymentStatus
from app.models.notification import Notification, NotificationType

__all__ = [
    "Landlord",
    "Property",
    "Room",
    "Tenant",
    "PaymentSchedule",
    "PaymentFrequency",
    "Payment",
    "PaymentStatus",
    "Notification",
    "NotificationType",
]

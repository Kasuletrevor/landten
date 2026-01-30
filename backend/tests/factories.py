"""
Test factories for creating model instances in tests.
Uses simple factory functions rather than external libraries for simplicity.
"""

from datetime import date, datetime, timezone
from sqlmodel import Session
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment_schedule import PaymentSchedule, PaymentFrequency
from app.models.payment import Payment, PaymentStatus
from app.models.notification import Notification
from app.core.security import get_password_hash


class LandlordFactory:
    """Factory for creating Landlord test instances"""

    @staticmethod
    def create(
        session: Session,
        name: str = "Test Landlord",
        email: str = "landlord@test.com",
        password: str = "password123",
        phone: str = "555-0000",
        primary_currency: str = "UGX",
    ) -> Landlord:
        landlord = Landlord(
            name=name,
            email=email,
            password_hash=get_password_hash(password),
            phone=phone,
            primary_currency=primary_currency,
        )
        session.add(landlord)
        session.commit()
        session.refresh(landlord)
        return landlord


class PropertyFactory:
    """Factory for creating Property test instances"""

    @staticmethod
    def create(
        session: Session,
        landlord_id: str,
        name: str = "Test Property",
        address: str = "123 Test Street",
        description: str = "A test property",
        grace_period_days: int = 5,
    ) -> Property:
        prop = Property(
            name=name,
            address=address,
            description=description,
            landlord_id=landlord_id,
            grace_period_days=grace_period_days,
        )
        session.add(prop)
        session.commit()
        session.refresh(prop)
        return prop


class RoomFactory:
    """Factory for creating Room test instances"""

    @staticmethod
    def create(
        session: Session,
        property_id: str,
        name: str = "Unit 101",
        rent_amount: float = 1000.0,
        currency: str = "UGX",
        is_occupied: bool = False,
    ) -> Room:
        room = Room(
            name=name,
            rent_amount=rent_amount,
            currency=currency,
            property_id=property_id,
            is_occupied=is_occupied,
        )
        session.add(room)
        session.commit()
        session.refresh(room)
        return room


class TenantFactory:
    """Factory for creating Tenant test instances"""

    @staticmethod
    def create(
        session: Session,
        room_id: str,
        name: str = "Test Tenant",
        email: str = "tenant@test.com",
        phone: str = "555-1234",
        move_in_date: date = None,
        move_out_date: date = None,
        is_active: bool = True,
        password_hash: str = None,
        notes: str = None,
    ) -> Tenant:
        if move_in_date is None:
            move_in_date = date(2024, 1, 1)

        tenant = Tenant(
            room_id=room_id,
            name=name,
            email=email,
            phone=phone,
            move_in_date=move_in_date,
            move_out_date=move_out_date,
            is_active=is_active,
            password_hash=password_hash,
            notes=notes,
        )
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        return tenant


class PaymentScheduleFactory:
    """Factory for creating PaymentSchedule test instances"""

    @staticmethod
    def create(
        session: Session,
        tenant_id: str,
        amount: float = 1000.0,
        frequency: PaymentFrequency = PaymentFrequency.MONTHLY,
        due_day: int = 1,
        window_days: int = 5,
        start_date: date = None,
        is_active: bool = True,
    ) -> PaymentSchedule:
        if start_date is None:
            start_date = date(2024, 1, 1)

        schedule = PaymentSchedule(
            tenant_id=tenant_id,
            amount=amount,
            frequency=frequency,
            due_day=due_day,
            window_days=window_days,
            start_date=start_date,
            is_active=is_active,
        )
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        return schedule


class PaymentFactory:
    """Factory for creating Payment test instances"""

    @staticmethod
    def create(
        session: Session,
        tenant_id: str,
        schedule_id: str = None,
        period_start: date = None,
        period_end: date = None,
        amount_due: float = 1000.0,
        due_date: date = None,
        window_end_date: date = None,
        status: PaymentStatus = PaymentStatus.PENDING,
        paid_date: date = None,
        payment_reference: str = None,
        receipt_url: str = None,
        notes: str = None,
        is_manual: bool = False,
    ) -> Payment:
        if period_start is None:
            period_start = date(2024, 1, 1)
        if period_end is None:
            period_end = date(2024, 1, 31)
        if due_date is None:
            due_date = date(2024, 1, 1)
        if window_end_date is None:
            window_end_date = date(2024, 1, 6)

        payment = Payment(
            tenant_id=tenant_id,
            schedule_id=schedule_id,
            period_start=period_start,
            period_end=period_end,
            amount_due=amount_due,
            due_date=due_date,
            window_end_date=window_end_date,
            status=status,
            paid_date=paid_date,
            payment_reference=payment_reference,
            receipt_url=receipt_url,
            notes=notes,
            is_manual=is_manual,
        )
        session.add(payment)
        session.commit()
        session.refresh(payment)
        return payment


class NotificationFactory:
    """Factory for creating Notification test instances"""

    @staticmethod
    def create(
        session: Session,
        landlord_id: str,
        type: str = "payment",
        title: str = "Test Notification",
        message: str = "This is a test notification",
        is_read: bool = False,
        payment_id: str = None,
        tenant_id: str = None,
    ) -> Notification:
        notification = Notification(
            landlord_id=landlord_id,
            type=type,
            title=title,
            message=message,
            is_read=is_read,
            payment_id=payment_id,
            tenant_id=tenant_id,
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)
        return notification


# Convenience function for creating full test scenarios
def create_full_test_scenario(
    session: Session, landlord_password: str = "password123"
) -> dict:
    """
    Creates a complete test scenario with landlord, property, room, and tenant.
    Returns dict with all created objects.
    """
    landlord = LandlordFactory.create(session=session, password=landlord_password)

    property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)

    room = RoomFactory.create(session=session, property_id=property_obj.id)

    tenant = TenantFactory.create(session=session, room_id=room.id)

    return {
        "landlord": landlord,
        "property": property_obj,
        "room": room,
        "tenant": tenant,
    }

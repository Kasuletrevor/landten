"""
Tests for Payment model.

Tests CRUD operations, all payment statuses, and calculations.
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from sqlmodel import select
from app.models.payment import Payment, PaymentStatus
from app.models.tenant import Tenant
from app.models.room import Room
from app.models.property import Property
from app.models.landlord import Landlord
from app.models.payment_schedule import PaymentSchedule


# =============================================================================
# CRUD Operations Tests
# =============================================================================


def test_payment_creation(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test creating a payment with valid data."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id, amount_due=1500.00, due_date=date(2024, 1, 1)
    )

    assert payment.amount_due == 1500.00
    assert payment.tenant_id == tenant.id
    assert payment.id is not None


def test_payment_creation_with_all_fields(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
    payment_factory,
):
    """Test creating a payment with all fields."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id)

    payment = payment_factory(
        tenant_id=tenant.id,
        schedule_id=schedule.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        amount_due=2000.00,
        due_date=date(2024, 1, 1),
        window_end_date=date(2024, 1, 6),
        status=PaymentStatus.PENDING,
        notes="January rent payment",
    )

    assert payment.tenant_id == tenant.id
    assert payment.schedule_id == schedule.id
    assert payment.period_start == date(2024, 1, 1)
    assert payment.period_end == date(2024, 1, 31)
    assert payment.amount_due == 2000.00
    assert payment.notes == "January rent payment"


def test_payment_read_by_id(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test reading a payment by ID."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    payment = payment_factory(tenant_id=tenant.id, amount_due=1000.00)

    statement = select(Payment).where(Payment.id == payment.id)
    result = session.exec(statement).first()

    assert result is not None
    assert result.id == payment.id
    assert result.amount_due == 1000.00


def test_payment_update(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test updating payment fields."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    payment = payment_factory(tenant_id=tenant.id, amount_due=1000.00, notes="Old note")

    payment.amount_due = 1200.00
    payment.notes = "Updated note"
    session.add(payment)
    session.commit()
    session.refresh(payment)

    assert payment.amount_due == 1200.00
    assert payment.notes == "Updated note"


def test_payment_delete(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test deleting a payment."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    payment = payment_factory(tenant_id=tenant.id)
    payment_id = payment.id

    session.delete(payment)
    session.commit()

    statement = select(Payment).where(Payment.id == payment_id)
    result = session.exec(statement).first()

    assert result is None


def test_multiple_payments_per_tenant(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test creating multiple payments for one tenant."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment1 = payment_factory(tenant_id=tenant.id, amount_due=1000.00)
    payment2 = payment_factory(tenant_id=tenant.id, amount_due=1000.00)
    payment3 = payment_factory(tenant_id=tenant.id, amount_due=1000.00)

    statement = select(Payment).where(Payment.tenant_id == tenant.id)
    results = session.exec(statement).all()

    assert len(results) == 3


def test_payments_for_different_tenants(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payments for different tenants."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room1 = room_factory(property_id=prop.id)
    room2 = room_factory(property_id=prop.id)
    tenant1 = tenant_factory(room_id=room1.id)
    tenant2 = tenant_factory(room_id=room2.id)

    payment1 = payment_factory(tenant_id=tenant1.id, amount_due=1000.00)
    payment2 = payment_factory(tenant_id=tenant2.id, amount_due=1500.00)

    # Query payments for tenant1
    statement = select(Payment).where(Payment.tenant_id == tenant1.id)
    results = session.exec(statement).all()

    assert len(results) == 1
    assert results[0].amount_due == 1000.00


# =============================================================================
# Payment Status Tests
# =============================================================================


def test_payment_status_upcoming(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment with UPCOMING status."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, status=PaymentStatus.UPCOMING)

    assert payment.status == PaymentStatus.UPCOMING
    assert payment.status.value == "upcoming"


def test_payment_status_pending(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment with PENDING status."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, status=PaymentStatus.PENDING)

    assert payment.status == PaymentStatus.PENDING
    assert payment.status.value == "pending"


def test_payment_status_on_time(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment with ON_TIME status."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id,
        status=PaymentStatus.ON_TIME,
        paid_date=date(2024, 1, 5),
        payment_reference="REF123",
    )

    assert payment.status == PaymentStatus.ON_TIME
    assert payment.paid_date == date(2024, 1, 5)
    assert payment.payment_reference == "REF123"


def test_payment_status_late(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment with LATE status."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id, status=PaymentStatus.LATE, paid_date=date(2024, 1, 20)
    )

    assert payment.status == PaymentStatus.LATE
    assert payment.paid_date == date(2024, 1, 20)


def test_payment_status_overdue(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment with OVERDUE status."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, status=PaymentStatus.OVERDUE)

    assert payment.status == PaymentStatus.OVERDUE


def test_payment_status_waived(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment with WAIVED status."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id,
        status=PaymentStatus.WAIVED,
        notes="Waived due to maintenance issues",
    )

    assert payment.status == PaymentStatus.WAIVED


def test_payment_status_verifying(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment with VERIFYING status."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id,
        status=PaymentStatus.VERIFYING,
        paid_date=date(2024, 1, 3),
        receipt_url="/uploads/receipts/test_receipt.pdf",
        payment_reference="BANK12345",
    )

    assert payment.status == PaymentStatus.VERIFYING
    assert payment.receipt_url == "/uploads/receipts/test_receipt.pdf"


def test_payment_status_transitions(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test transitioning payment between statuses."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    # Start as UPCOMING
    payment = payment_factory(tenant_id=tenant.id, status=PaymentStatus.UPCOMING)

    # Transition to PENDING
    payment.status = PaymentStatus.PENDING
    session.add(payment)
    session.commit()
    session.refresh(payment)
    assert payment.status == PaymentStatus.PENDING

    # Transition to VERIFYING (tenant uploads receipt)
    payment.status = PaymentStatus.VERIFYING
    payment.paid_date = date(2024, 1, 5)
    session.add(payment)
    session.commit()
    session.refresh(payment)
    assert payment.status == PaymentStatus.VERIFYING

    # Transition to ON_TIME (landlord approves)
    payment.status = PaymentStatus.ON_TIME
    session.add(payment)
    session.commit()
    session.refresh(payment)
    assert payment.status == PaymentStatus.ON_TIME


def test_payment_all_status_values():
    """Test all payment status enum values."""
    statuses = [
        (PaymentStatus.UPCOMING, "upcoming"),
        (PaymentStatus.PENDING, "pending"),
        (PaymentStatus.ON_TIME, "on_time"),
        (PaymentStatus.LATE, "late"),
        (PaymentStatus.OVERDUE, "overdue"),
        (PaymentStatus.WAIVED, "waived"),
        (PaymentStatus.VERIFYING, "verifying"),
    ]

    for status, expected_value in statuses:
        assert status.value == expected_value


# =============================================================================
# Period and Date Tests
# =============================================================================


def test_payment_period_dates(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment period start and end dates."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id, period_start=date(2024, 1, 1), period_end=date(2024, 1, 31)
    )

    assert payment.period_start == date(2024, 1, 1)
    assert payment.period_end == date(2024, 1, 31)
    assert payment.period_start < payment.period_end


def test_payment_due_date(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment due date."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, due_date=date(2024, 1, 1))

    assert payment.due_date == date(2024, 1, 1)


def test_payment_window_end_date(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment window end date."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id, due_date=date(2024, 1, 1), window_end_date=date(2024, 1, 6)
    )

    assert payment.window_end_date == date(2024, 1, 6)
    assert payment.due_date < payment.window_end_date


def test_payment_period_calculation(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test calculating payment period duration."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id, period_start=date(2024, 1, 1), period_end=date(2024, 1, 31)
    )

    period_duration = payment.period_end - payment.period_start
    assert period_duration.days == 30


# =============================================================================
# Amount Tests
# =============================================================================


def test_payment_amount_due(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment amount due."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, amount_due=2500.50)

    assert payment.amount_due == 2500.50


def test_payment_amount_zero(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment with zero amount (waived or free period)."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id, amount_due=0.00, status=PaymentStatus.WAIVED
    )

    assert payment.amount_due == 0.00


def test_payment_amount_large(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment with large amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, amount_due=999999.99)

    assert payment.amount_due == 999999.99


def test_payment_amount_update(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test updating payment amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    payment = payment_factory(tenant_id=tenant.id, amount_due=1000.00)

    payment.amount_due = 1200.00
    session.add(payment)
    session.commit()
    session.refresh(payment)

    assert payment.amount_due == 1200.00


# =============================================================================
# Manual Payment Tests
# =============================================================================


def test_payment_default_not_manual(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test default is_manual is False."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    payment = payment_factory(tenant_id=tenant.id)

    assert payment.is_manual is False


def test_payment_manual_creation(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test creating a manual payment."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id, is_manual=True, notes="One-time charge for repairs"
    )

    assert payment.is_manual is True


# =============================================================================
# Relationship Tests
# =============================================================================


def test_payment_tenant_relationship(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment's tenant relationship."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, name="Rent Payer")
    payment = payment_factory(tenant_id=tenant.id)

    session.refresh(payment)

    assert payment.tenant is not None
    assert payment.tenant.id == tenant.id
    assert payment.tenant.name == "Rent Payer"


def test_payment_schedule_relationship(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
    payment_factory,
):
    """Test payment's schedule relationship."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id, amount=1500.00)

    payment = payment_factory(tenant_id=tenant.id, schedule_id=schedule.id)

    assert payment.schedule_id == schedule.id


def test_payment_without_schedule(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test payment without schedule (manual payment)."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, schedule_id=None, is_manual=True)

    assert payment.schedule_id is None


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================


def test_payment_optional_schedule_id(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test that schedule_id is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, schedule_id=None)

    assert payment.schedule_id is None


def test_payment_optional_paid_date(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test that paid_date is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(
        tenant_id=tenant.id, status=PaymentStatus.PENDING, paid_date=None
    )

    assert payment.paid_date is None


def test_payment_optional_reference(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test that payment_reference is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, payment_reference=None)

    assert payment.payment_reference is None


def test_payment_optional_receipt_url(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test that receipt_url is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, receipt_url=None)

    assert payment.receipt_url is None


def test_payment_optional_notes(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test that notes is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = payment_factory(tenant_id=tenant.id, notes=None)

    assert payment.notes is None


def test_payment_tenant_id_required(session, landlord_factory):
    """Test that tenant_id is required."""
    from sqlalchemy.exc import IntegrityError

    payment = Payment(
        tenant_id=None,
        period_start=date.today(),
        period_end=date.today(),
        amount_due=1000.00,
        due_date=date.today(),
        window_end_date=date.today(),
    )

    with pytest.raises(IntegrityError):
        session.add(payment)
        session.commit()


def test_payment_tenant_id_index(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test that tenant_id is indexed for fast lookups."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    # Create multiple payments
    for i in range(5):
        payment_factory(tenant_id=tenant.id)

    statement = select(Payment).where(Payment.tenant_id == tenant.id)
    results = session.exec(statement).all()

    assert len(results) == 5


def test_payment_timestamps(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test that created_at and updated_at are automatically set."""
    before_creation = datetime.now(timezone.utc)
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    payment = payment_factory(tenant_id=tenant.id)
    after_creation = datetime.now(timezone.utc)

    assert before_creation <= payment.created_at <= after_creation
    assert before_creation <= payment.updated_at <= after_creation


def test_payment_update_timestamp(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test that updated_at is refreshed on update."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    payment = payment_factory(tenant_id=tenant.id)
    original_updated_at = payment.updated_at

    # Wait and update
    import time

    time.sleep(0.01)

    payment.notes = "Updated notes"
    session.add(payment)
    session.commit()
    session.refresh(payment)

    assert payment.updated_at > original_updated_at


def test_payment_foreign_key_constraint(session, payment_factory):
    """Test that tenant_id must reference a valid tenant."""
    from sqlalchemy.exc import IntegrityError

    payment = Payment(
        tenant_id="non-existent-tenant-id",
        period_start=date.today(),
        period_end=date.today(),
        amount_due=1000.00,
        due_date=date.today(),
        window_end_date=date.today(),
    )

    with pytest.raises(IntegrityError):
        session.add(payment)
        session.commit()


def test_payment_schedule_foreign_key_constraint(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test that schedule_id must reference a valid schedule if provided."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment = Payment(
        tenant_id=tenant.id,
        schedule_id="non-existent-schedule-id",
        period_start=date.today(),
        period_end=date.today(),
        amount_due=1000.00,
        due_date=date.today(),
        window_end_date=date.today(),
    )

    with pytest.raises(IntegrityError):
        session.add(payment)
        session.commit()

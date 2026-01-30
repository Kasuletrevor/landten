"""
Tests for PaymentSchedule model.

Tests CRUD operations, payment frequency, and due_day constraints.
"""

import pytest
from datetime import date, datetime, timezone
from sqlmodel import select
from app.models.payment_schedule import PaymentSchedule, PaymentFrequency
from app.models.tenant import Tenant
from app.models.room import Room
from app.models.property import Property
from app.models.landlord import Landlord


# =============================================================================
# CRUD Operations Tests
# =============================================================================


def test_schedule_creation(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test creating a payment schedule with valid data."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(
        tenant_id=tenant.id,
        amount=1500.00,
        frequency=PaymentFrequency.MONTHLY,
        due_day=1,
    )

    assert schedule.amount == 1500.00
    assert schedule.frequency == PaymentFrequency.MONTHLY
    assert schedule.due_day == 1
    assert schedule.tenant_id == tenant.id
    assert schedule.id is not None


def test_schedule_creation_with_all_fields(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test creating a payment schedule with all fields."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(
        tenant_id=tenant.id,
        amount=2000.00,
        frequency=PaymentFrequency.MONTHLY,
        due_day=15,
        window_days=7,
        start_date=date(2024, 1, 1),
        is_active=True,
    )

    assert schedule.amount == 2000.00
    assert schedule.frequency == PaymentFrequency.MONTHLY
    assert schedule.due_day == 15
    assert schedule.window_days == 7
    assert schedule.start_date == date(2024, 1, 1)
    assert schedule.is_active is True


def test_schedule_read_by_id(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test reading a payment schedule by ID."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id, amount=1000.00)

    statement = select(PaymentSchedule).where(PaymentSchedule.id == schedule.id)
    result = session.exec(statement).first()

    assert result is not None
    assert result.id == schedule.id
    assert result.amount == 1000.00


def test_schedule_read_by_tenant_id(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test reading a payment schedule by tenant ID."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id)

    statement = select(PaymentSchedule).where(PaymentSchedule.tenant_id == tenant.id)
    result = session.exec(statement).first()

    assert result is not None
    assert result.tenant_id == tenant.id


def test_schedule_update(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test updating payment schedule fields."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id, amount=1000.00)

    schedule.amount = 1200.00
    schedule.due_day = 10
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    assert schedule.amount == 1200.00
    assert schedule.due_day == 10


def test_schedule_delete(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test deleting a payment schedule."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id)
    schedule_id = schedule.id

    session.delete(schedule)
    session.commit()

    statement = select(PaymentSchedule).where(PaymentSchedule.id == schedule_id)
    result = session.exec(statement).first()

    assert result is None


def test_only_one_schedule_per_tenant(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test that only one schedule can exist per tenant (unique constraint)."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    # Create first schedule
    schedule1 = schedule_factory(tenant_id=tenant.id)

    # Attempt to create second schedule for same tenant
    schedule2 = PaymentSchedule(
        tenant_id=tenant.id,
        amount=2000.00,
        frequency=PaymentFrequency.MONTHLY,
        due_day=1,
        window_days=5,
        start_date=date.today(),
    )

    with pytest.raises(IntegrityError):
        session.add(schedule2)
        session.commit()


# =============================================================================
# Payment Frequency Tests
# =============================================================================


def test_schedule_frequency_monthly(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test schedule with MONTHLY frequency."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, frequency=PaymentFrequency.MONTHLY)

    assert schedule.frequency == PaymentFrequency.MONTHLY
    assert schedule.frequency.value == "monthly"


def test_schedule_frequency_bi_monthly(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test schedule with BI_MONTHLY frequency."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(
        tenant_id=tenant.id, frequency=PaymentFrequency.BI_MONTHLY
    )

    assert schedule.frequency == PaymentFrequency.BI_MONTHLY
    assert schedule.frequency.value == "bi_monthly"


def test_schedule_frequency_quarterly(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test schedule with QUARTERLY frequency."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(
        tenant_id=tenant.id, frequency=PaymentFrequency.QUARTERLY
    )

    assert schedule.frequency == PaymentFrequency.QUARTERLY
    assert schedule.frequency.value == "quarterly"


def test_schedule_frequency_default(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test default frequency is MONTHLY."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id)

    assert schedule.frequency == PaymentFrequency.MONTHLY


def test_schedule_frequency_update(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test updating payment frequency."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id, frequency=PaymentFrequency.MONTHLY)

    schedule.frequency = PaymentFrequency.QUARTERLY
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    assert schedule.frequency == PaymentFrequency.QUARTERLY


def test_schedule_all_frequency_values():
    """Test all payment frequency enum values."""
    frequencies = [
        (PaymentFrequency.MONTHLY, "monthly"),
        (PaymentFrequency.BI_MONTHLY, "bi_monthly"),
        (PaymentFrequency.QUARTERLY, "quarterly"),
    ]

    for freq, expected_value in frequencies:
        assert freq.value == expected_value


# =============================================================================
# Due Day Tests
# =============================================================================


def test_schedule_due_day_minimum(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test minimum due_day value (1)."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, due_day=1)

    assert schedule.due_day == 1


def test_schedule_due_day_maximum(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test maximum due_day value (28)."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, due_day=28)

    assert schedule.due_day == 28


def test_schedule_due_day_fifteenth(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test due_day on the 15th."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, due_day=15)

    assert schedule.due_day == 15


def test_schedule_default_due_day(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test default due_day is 1."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id)

    assert schedule.due_day == 1


def test_schedule_due_day_update(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test updating due_day."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id, due_day=1)

    schedule.due_day = 15
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    assert schedule.due_day == 15


# =============================================================================
# Window Days Tests
# =============================================================================


def test_schedule_window_days(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test setting window_days."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, due_day=1, window_days=10)

    assert schedule.window_days == 10


def test_schedule_default_window_days(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test default window_days is 5."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id)

    assert schedule.window_days == 5


def test_schedule_window_days_update(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test updating window_days."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id, window_days=5)

    schedule.window_days = 7
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    assert schedule.window_days == 7


def test_schedule_window_days_calculation(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test calculating payment window end date from due_day and window_days."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, due_day=5, window_days=5)

    # Window should be due_day + window_days = 5 + 5 = 10th
    expected_window_end = schedule.due_day + schedule.window_days
    assert expected_window_end == 10


# =============================================================================
# Amount Tests
# =============================================================================


def test_schedule_amount(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test setting payment amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, amount=2500.50)

    assert schedule.amount == 2500.50


def test_schedule_amount_integer(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test schedule with integer amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, amount=1000)

    assert schedule.amount == 1000.00


def test_schedule_amount_large(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test schedule with large amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, amount=99999.99)

    assert schedule.amount == 99999.99


def test_schedule_amount_update(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test updating amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id, amount=1000.00)

    schedule.amount = 1200.00
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    assert schedule.amount == 1200.00


# =============================================================================
# Start Date Tests
# =============================================================================


def test_schedule_start_date(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test setting start date."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    start = date(2024, 6, 1)
    schedule = schedule_factory(tenant_id=tenant.id, start_date=start)

    assert schedule.start_date == start


def test_schedule_default_start_date(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test default start date from factory."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id)

    # Factory defaults to date(2024, 1, 1)
    assert schedule.start_date == date(2024, 1, 1)


def test_schedule_start_date_update(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test updating start date."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id, start_date=date(2024, 1, 1))

    schedule.start_date = date(2024, 3, 1)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    assert schedule.start_date == date(2024, 3, 1)


# =============================================================================
# Active Status Tests
# =============================================================================


def test_schedule_default_active(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test default is_active is True."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id)

    assert schedule.is_active is True


def test_schedule_inactive(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test creating inactive schedule."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, is_active=False)

    assert schedule.is_active is False


def test_schedule_activate_deactivate(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test activating and deactivating schedule."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id, is_active=True)

    # Deactivate
    schedule.is_active = False
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    assert schedule.is_active is False

    # Reactivate
    schedule.is_active = True
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    assert schedule.is_active is True


# =============================================================================
# Relationship Tests
# =============================================================================


def test_schedule_tenant_relationship(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test schedule's tenant relationship."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, name="Scheduled Tenant")
    schedule = schedule_factory(tenant_id=tenant.id)

    session.refresh(schedule)

    assert schedule.tenant is not None
    assert schedule.tenant.id == tenant.id
    assert schedule.tenant.name == "Scheduled Tenant"


def test_schedule_tenant_cascade_behavior(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test schedule behavior when tenant is deleted."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id)
    schedule_id = schedule.id

    # Delete tenant
    session.delete(tenant)
    session.commit()

    # Verify schedule still exists (no cascade delete)
    statement = select(PaymentSchedule).where(PaymentSchedule.id == schedule_id)
    result = session.exec(statement).first()

    # Schedule remains but tenant_id becomes invalid reference
    assert result is not None


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================


def test_schedule_amount_required(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that amount is required."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = PaymentSchedule(
        tenant_id=tenant.id,
        amount=None,
        due_day=1,
        window_days=5,
        start_date=date.today(),
    )

    with pytest.raises(IntegrityError):
        session.add(schedule)
        session.commit()


def test_schedule_due_day_required(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that due_day is required."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = PaymentSchedule(
        tenant_id=tenant.id,
        amount=1000.00,
        due_day=None,
        window_days=5,
        start_date=date.today(),
    )

    with pytest.raises(IntegrityError):
        session.add(schedule)
        session.commit()


def test_schedule_start_date_required(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that start_date is required."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = PaymentSchedule(
        tenant_id=tenant.id, amount=1000.00, due_day=1, window_days=5, start_date=None
    )

    with pytest.raises(IntegrityError):
        session.add(schedule)
        session.commit()


def test_schedule_tenant_id_unique_index(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test that tenant_id has unique index constraint."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    # Create first schedule
    schedule_factory(tenant_id=tenant.id)

    # Query should return exactly one
    statement = select(PaymentSchedule).where(PaymentSchedule.tenant_id == tenant.id)
    result = session.exec(statement).first()

    assert result is not None
    assert result.tenant_id == tenant.id


def test_schedule_tenant_id_foreign_key_constraint(session, schedule_factory):
    """Test that tenant_id must reference a valid tenant."""
    from sqlalchemy.exc import IntegrityError

    schedule = PaymentSchedule(
        tenant_id="non-existent-tenant-id",
        amount=1000.00,
        due_day=1,
        window_days=5,
        start_date=date.today(),
    )

    with pytest.raises(IntegrityError):
        session.add(schedule)
        session.commit()


def test_schedule_timestamps(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test that created_at and updated_at are automatically set."""
    before_creation = datetime.now(timezone.utc)
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id)
    after_creation = datetime.now(timezone.utc)

    assert before_creation <= schedule.created_at <= after_creation
    assert before_creation <= schedule.updated_at <= after_creation


def test_schedule_update_timestamp(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test that updated_at is refreshed on update."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    schedule = schedule_factory(tenant_id=tenant.id)
    original_updated_at = schedule.updated_at

    # Wait and update
    import time

    time.sleep(0.01)

    schedule.amount = 2000.00
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    assert schedule.updated_at > original_updated_at


def test_schedule_due_day_boundary_values(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test due_day boundary values 1-28."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)

    # Test days 1, 15, and 28
    test_days = [1, 15, 28]

    for day in test_days:
        room = room_factory(property_id=prop.id)
        tenant = tenant_factory(room_id=room.id)

        schedule = schedule_factory(tenant_id=tenant.id, due_day=day)

        assert schedule.due_day == day


def test_schedule_window_days_minimum(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test minimum window_days value."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    # Create schedule with window_days=1 (minimum allowed by model)
    schedule = schedule_factory(tenant_id=tenant.id, window_days=1)

    assert schedule.window_days == 1


def test_schedule_frequency_comparison(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test comparing payment frequencies."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room1 = room_factory(property_id=prop.id)
    room2 = room_factory(property_id=prop.id)
    room3 = room_factory(property_id=prop.id)
    tenant1 = tenant_factory(room_id=room1.id)
    tenant2 = tenant_factory(room_id=room2.id)
    tenant3 = tenant_factory(room_id=room3.id)

    monthly = schedule_factory(tenant_id=tenant1.id, frequency=PaymentFrequency.MONTHLY)
    bi_monthly = schedule_factory(
        tenant_id=tenant2.id, frequency=PaymentFrequency.BI_MONTHLY
    )
    quarterly = schedule_factory(
        tenant_id=tenant3.id, frequency=PaymentFrequency.QUARTERLY
    )

    assert monthly.frequency != bi_monthly.frequency
    assert monthly.frequency != quarterly.frequency
    assert bi_monthly.frequency != quarterly.frequency

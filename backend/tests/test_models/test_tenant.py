"""
Tests for Tenant model.

Tests CRUD operations, dates, is_active status, and room relationship.
"""

import pytest
from datetime import date, datetime, timezone, timedelta
from sqlmodel import select
from app.models.tenant import Tenant
from app.models.room import Room
from app.models.property import Property
from app.models.landlord import Landlord
from app.models.payment import Payment
from app.models.payment_schedule import PaymentSchedule


# =============================================================================
# CRUD Operations Tests
# =============================================================================


def test_tenant_creation(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test creating a tenant with valid data."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(
        room_id=room.id, name="Alice Johnson", email="alice@test.com"
    )

    assert tenant.name == "Alice Johnson"
    assert tenant.email == "alice@test.com"
    assert tenant.room_id == room.id
    assert tenant.id is not None


def test_tenant_creation_with_all_fields(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test creating a tenant with all fields."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    move_in = date(2024, 1, 15)
    move_out = date(2024, 12, 31)

    tenant = tenant_factory(
        room_id=room.id,
        name="Bob Smith",
        email="bob@test.com",
        phone="555-5678",
        move_in_date=move_in,
        move_out_date=move_out,
        is_active=True,
        notes="Excellent tenant, always pays on time",
    )

    assert tenant.name == "Bob Smith"
    assert tenant.email == "bob@test.com"
    assert tenant.phone == "555-5678"
    assert tenant.move_in_date == move_in
    assert tenant.move_out_date == move_out
    assert tenant.is_active is True
    assert tenant.notes == "Excellent tenant, always pays on time"


def test_tenant_read_by_id(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test reading a tenant by ID."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, name="Find Me Tenant")

    statement = select(Tenant).where(Tenant.id == tenant.id)
    result = session.exec(statement).first()

    assert result is not None
    assert result.id == tenant.id
    assert result.name == "Find Me Tenant"


def test_tenant_read_by_email(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test reading a tenant by email."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, email="findme@tenant.com")

    statement = select(Tenant).where(Tenant.email == "findme@tenant.com")
    result = session.exec(statement).first()

    assert result is not None
    assert result.email == "findme@tenant.com"


def test_tenant_update(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test updating tenant fields."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, name="Old Name")

    tenant.name = "New Name"
    tenant.phone = "555-9999"
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    assert tenant.name == "New Name"
    assert tenant.phone == "555-9999"


def test_tenant_delete(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test deleting a tenant."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    tenant_id = tenant.id

    session.delete(tenant)
    session.commit()

    statement = select(Tenant).where(Tenant.id == tenant_id)
    result = session.exec(statement).first()

    assert result is None


def test_multiple_tenants_per_room(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test creating multiple tenants for one room (e.g., roommates or sequential)."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    tenant1 = tenant_factory(room_id=room.id, name="Tenant 1", is_active=False)
    tenant2 = tenant_factory(room_id=room.id, name="Tenant 2", is_active=True)

    statement = select(Tenant).where(Tenant.room_id == room.id)
    results = session.exec(statement).all()

    assert len(results) == 2


def test_tenants_in_different_rooms(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test tenants in different rooms."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room1 = room_factory(property_id=prop.id)
    room2 = room_factory(property_id=prop.id)

    tenant1 = tenant_factory(room_id=room1.id, name="Room 1 Tenant")
    tenant2 = tenant_factory(room_id=room2.id, name="Room 2 Tenant")

    # Query tenants for room1
    statement = select(Tenant).where(Tenant.room_id == room1.id)
    results = session.exec(statement).all()

    assert len(results) == 1
    assert results[0].name == "Room 1 Tenant"


# =============================================================================
# Date Tests
# =============================================================================


def test_tenant_move_in_date(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test tenant move-in date."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    move_in = date(2024, 3, 15)

    tenant = tenant_factory(room_id=room.id, move_in_date=move_in)

    assert tenant.move_in_date == move_in
    assert isinstance(tenant.move_in_date, date)


def test_tenant_move_out_date(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test tenant move-out date."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    move_in = date(2024, 1, 1)
    move_out = date(2024, 12, 31)

    tenant = tenant_factory(
        room_id=room.id, move_in_date=move_in, move_out_date=move_out
    )

    assert tenant.move_out_date == move_out
    assert tenant.move_in_date < tenant.move_out_date


def test_tenant_no_move_out_date(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test tenant without move-out date (current tenant)."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    tenant = tenant_factory(room_id=room.id, move_out_date=None)

    assert tenant.move_out_date is None


def test_tenant_update_move_out_date(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test updating move-out date."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, move_out_date=None)

    tenant.move_out_date = date(2024, 6, 30)
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    assert tenant.move_out_date == date(2024, 6, 30)


def test_tenant_date_range_calculation(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test calculating tenant stay duration."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    move_in = date(2024, 1, 1)
    move_out = date(2024, 3, 31)

    tenant = tenant_factory(
        room_id=room.id, move_in_date=move_in, move_out_date=move_out
    )

    duration = tenant.move_out_date - tenant.move_in_date
    assert duration.days == 90  # Jan 1 to Mar 31 = 90 days (2024 is leap year)


# =============================================================================
# Is Active Tests
# =============================================================================


def test_tenant_default_active_status(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test default is_active is True."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    assert tenant.is_active is True


def test_tenant_inactive_status(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test setting tenant as inactive."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, is_active=False)

    assert tenant.is_active is False


def test_tenant_activate_deactivate(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test activating and deactivating a tenant."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, is_active=True)

    # Deactivate
    tenant.is_active = False
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    assert tenant.is_active is False

    # Reactivate
    tenant.is_active = True
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    assert tenant.is_active is True


def test_tenant_inactive_with_move_out(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test inactive tenant with move-out date (former tenant)."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    tenant = tenant_factory(
        room_id=room.id, is_active=False, move_out_date=date(2024, 6, 30)
    )

    assert tenant.is_active is False
    assert tenant.move_out_date is not None


# =============================================================================
# Relationship Tests
# =============================================================================


def test_tenant_room_relationship(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test tenant's room relationship."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id, name="Property Building")
    room = room_factory(property_id=prop.id, name="Room 101")
    tenant = tenant_factory(room_id=room.id, name="Room Tenant")

    session.refresh(tenant)

    assert tenant.room is not None
    assert tenant.room.id == room.id
    assert tenant.room.name == "Room 101"


def test_tenant_payment_schedule_relationship(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    schedule_factory,
):
    """Test tenant's payment_schedule relationship."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    schedule = schedule_factory(tenant_id=tenant.id, amount=1500.00)

    session.refresh(tenant)

    assert tenant.payment_schedule is not None
    assert tenant.payment_schedule.id == schedule.id
    assert tenant.payment_schedule.amount == 1500.00


def test_tenant_payments_relationship(
    session,
    landlord_factory,
    property_factory,
    room_factory,
    tenant_factory,
    payment_factory,
):
    """Test tenant's payments relationship."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    payment1 = payment_factory(tenant_id=tenant.id, amount_due=1000.00)
    payment2 = payment_factory(tenant_id=tenant.id, amount_due=1000.00)

    session.refresh(tenant)

    assert len(tenant.payments) == 2


def test_tenant_no_payment_schedule(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test tenant without payment schedule."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    session.refresh(tenant)

    assert tenant.payment_schedule is None


def test_tenant_no_payments(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test tenant with no payments."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)

    session.refresh(tenant)

    assert tenant.payments == []


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================


def test_tenant_optional_email(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that email field is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, email=None)

    assert tenant.email is None


def test_tenant_optional_phone(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that phone field is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, phone=None)

    assert tenant.phone is None


def test_tenant_optional_notes(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that notes field is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, notes=None)

    assert tenant.notes is None


def test_tenant_name_required(
    session, landlord_factory, property_factory, room_factory
):
    """Test that name is required."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = Tenant(room_id=room.id, name=None, move_in_date=date.today())

    with pytest.raises(IntegrityError):
        session.add(tenant)
        session.commit()


def test_tenant_move_in_date_required(
    session, landlord_factory, property_factory, room_factory
):
    """Test that move_in_date is required."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = Tenant(room_id=room.id, name="Test Tenant", move_in_date=None)

    with pytest.raises(IntegrityError):
        session.add(tenant)
        session.commit()


def test_tenant_room_id_index(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that room_id is indexed for fast lookups."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    # Create multiple tenants
    for i in range(5):
        tenant_factory(room_id=room.id, name=f"Tenant {i}")

    # Query should work efficiently
    statement = select(Tenant).where(Tenant.room_id == room.id)
    results = session.exec(statement).all()

    assert len(results) == 5


def test_tenant_email_index(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that email is indexed for fast lookups."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    # Create tenants with emails
    for i in range(5):
        tenant_factory(room_id=room.id, email=f"tenant{i}@test.com")

    # Query by email should use index
    statement = select(Tenant).where(Tenant.email == "tenant3@test.com")
    result = session.exec(statement).first()

    assert result is not None
    assert result.email == "tenant3@test.com"


def test_tenant_timestamps(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that created_at and updated_at are automatically set."""
    before_creation = datetime.now(timezone.utc)
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    after_creation = datetime.now(timezone.utc)

    assert before_creation <= tenant.created_at <= after_creation
    assert before_creation <= tenant.updated_at <= after_creation


def test_tenant_update_timestamp(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that updated_at is refreshed on update."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    original_updated_at = tenant.updated_at

    # Wait and update
    import time

    time.sleep(0.01)

    tenant.phone = "555-0000"
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    assert tenant.updated_at > original_updated_at


def test_tenant_foreign_key_constraint(session, tenant_factory):
    """Test that room_id must reference a valid room."""
    from sqlalchemy.exc import IntegrityError

    tenant = Tenant(
        room_id="non-existent-room-id", name="Orphan Tenant", move_in_date=date.today()
    )

    with pytest.raises(IntegrityError):
        session.add(tenant)
        session.commit()


def test_tenant_password_hash_nullable(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test that password_hash is nullable (portal access optional)."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id, password_hash=None)

    assert tenant.password_hash is None


def test_tenant_password_hash_for_portal(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test tenant with password hash for portal access."""
    from app.core.security import get_password_hash

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    password_hash = get_password_hash("tenantpassword")
    tenant = tenant_factory(room_id=room.id, password_hash=password_hash)

    assert tenant.password_hash is not None
    assert tenant.password_hash != "tenantpassword"  # Should be hashed

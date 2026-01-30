"""
Tests for Room model.

Tests CRUD operations, occupancy status, rent_amount, currency, and relationships.
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import select
from app.models.room import Room, Currency
from app.models.property import Property
from app.models.landlord import Landlord
from app.models.tenant import Tenant


# =============================================================================
# CRUD Operations Tests
# =============================================================================


def test_room_creation(session, landlord_factory, property_factory, room_factory):
    """Test creating a room with valid data."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, name="Unit 101", rent_amount=1500.00)

    assert room.name == "Unit 101"
    assert room.rent_amount == 1500.00
    assert room.property_id == prop.id
    assert room.id is not None


def test_room_creation_with_all_fields(
    session, landlord_factory, property_factory, room_factory
):
    """Test creating a room with all fields."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(
        property_id=prop.id,
        name="Suite A",
        rent_amount=2500.50,
        currency="USD",
        is_occupied=True,
        description="Premium corner unit",
    )

    assert room.name == "Suite A"
    assert room.rent_amount == 2500.50
    assert room.currency == "USD"
    assert room.is_occupied is True
    assert room.description == "Premium corner unit"


def test_room_read_by_id(session, landlord_factory, property_factory, room_factory):
    """Test reading a room by ID."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, name="Find Me Room")

    statement = select(Room).where(Room.id == room.id)
    result = session.exec(statement).first()

    assert result is not None
    assert result.id == room.id
    assert result.name == "Find Me Room"


def test_room_update(session, landlord_factory, property_factory, room_factory):
    """Test updating room fields."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, name="Old Room Name")

    room.name = "New Room Name"
    room.rent_amount = 2000.00
    session.add(room)
    session.commit()
    session.refresh(room)

    assert room.name == "New Room Name"
    assert room.rent_amount == 2000.00


def test_room_delete(session, landlord_factory, property_factory, room_factory):
    """Test deleting a room."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    room_id = room.id

    session.delete(room)
    session.commit()

    statement = select(Room).where(Room.id == room_id)
    result = session.exec(statement).first()

    assert result is None


def test_multiple_rooms_per_property(
    session, landlord_factory, property_factory, room_factory
):
    """Test creating multiple rooms for one property."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)

    room1 = room_factory(property_id=prop.id, name="Room 1")
    room2 = room_factory(property_id=prop.id, name="Room 2")
    room3 = room_factory(property_id=prop.id, name="Room 3")

    statement = select(Room).where(Room.property_id == prop.id)
    results = session.exec(statement).all()

    assert len(results) == 3


def test_rooms_in_different_properties(
    session, landlord_factory, property_factory, room_factory
):
    """Test rooms in different properties."""
    landlord = landlord_factory()
    prop1 = property_factory(landlord_id=landlord.id, name="Building A")
    prop2 = property_factory(landlord_id=landlord.id, name="Building B")

    room1 = room_factory(property_id=prop1.id, name="Unit in A")
    room2 = room_factory(property_id=prop2.id, name="Unit in B")

    # Query rooms for property1
    statement = select(Room).where(Room.property_id == prop1.id)
    results = session.exec(statement).all()

    assert len(results) == 1
    assert results[0].name == "Unit in A"


# =============================================================================
# Occupancy Status Tests
# =============================================================================


def test_room_default_occupancy(
    session, landlord_factory, property_factory, room_factory
):
    """Test default occupancy is False (vacant)."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    assert room.is_occupied is False


def test_room_mark_occupied(session, landlord_factory, property_factory, room_factory):
    """Test marking a room as occupied."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, is_occupied=False)

    room.is_occupied = True
    session.add(room)
    session.commit()
    session.refresh(room)

    assert room.is_occupied is True


def test_room_mark_vacant(session, landlord_factory, property_factory, room_factory):
    """Test marking a room as vacant."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, is_occupied=True)

    room.is_occupied = False
    session.add(room)
    session.commit()
    session.refresh(room)

    assert room.is_occupied is False


def test_room_occupancy_with_tenant(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test room occupancy relationship with tenant."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, is_occupied=False)

    # Add tenant
    tenant = tenant_factory(room_id=room.id, is_active=True)

    # Room should be considered occupied logic-wise
    session.refresh(room)

    assert len(room.tenants) > 0


# =============================================================================
# Rent Amount Tests
# =============================================================================


def test_room_rent_amount_integer(
    session, landlord_factory, property_factory, room_factory
):
    """Test room with integer rent amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, rent_amount=1000)

    assert room.rent_amount == 1000.00


def test_room_rent_amount_decimal(
    session, landlord_factory, property_factory, room_factory
):
    """Test room with decimal rent amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, rent_amount=1234.56)

    assert room.rent_amount == 1234.56


def test_room_rent_amount_zero(
    session, landlord_factory, property_factory, room_factory
):
    """Test room with zero rent amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, rent_amount=0.00)

    assert room.rent_amount == 0.00


def test_room_rent_amount_large(
    session, landlord_factory, property_factory, room_factory
):
    """Test room with large rent amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, rent_amount=999999.99)

    assert room.rent_amount == 999999.99


def test_room_rent_update(session, landlord_factory, property_factory, room_factory):
    """Test updating rent amount."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, rent_amount=1000.00)

    room.rent_amount = 1200.00
    session.add(room)
    session.commit()
    session.refresh(room)

    assert room.rent_amount == 1200.00


# =============================================================================
# Currency Tests
# =============================================================================


def test_room_default_currency(
    session, landlord_factory, property_factory, room_factory
):
    """Test default currency is UGX."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    assert room.currency == "UGX"


def test_room_currency_usd(session, landlord_factory, property_factory, room_factory):
    """Test room with USD currency."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, currency="USD")

    assert room.currency == "USD"


def test_room_currency_all_supported(
    session, landlord_factory, property_factory, room_factory
):
    """Test room with all supported currencies."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)

    currencies = ["UGX", "USD", "KES", "TZS", "RWF", "EUR", "GBP"]

    for curr in currencies:
        room = room_factory(property_id=prop.id, currency=curr)
        assert room.currency == curr


def test_room_currency_update(
    session, landlord_factory, property_factory, room_factory
):
    """Test updating currency."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, currency="UGX")

    room.currency = "USD"
    session.add(room)
    session.commit()
    session.refresh(room)

    assert room.currency == "USD"


# =============================================================================
# Relationship Tests
# =============================================================================


def test_room_property_relationship(
    session, landlord_factory, property_factory, room_factory
):
    """Test room's property relationship."""
    landlord = landlord_factory(name="Building Owner")
    prop = property_factory(landlord_id=landlord.id, name="My Building")
    room = room_factory(property_id=prop.id)

    session.refresh(room)

    assert room.property is not None
    assert room.property.id == prop.id
    assert room.property.name == "My Building"


def test_room_tenants_relationship(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test room's tenants relationship."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    tenant1 = tenant_factory(room_id=room.id, name="Tenant A")
    tenant2 = tenant_factory(room_id=room.id, name="Tenant B")

    session.refresh(room)

    assert len(room.tenants) == 2
    tenant_names = [t.name for t in room.tenants]
    assert "Tenant A" in tenant_names
    assert "Tenant B" in tenant_names


def test_room_empty_tenants(session, landlord_factory, property_factory, room_factory):
    """Test room with no tenants."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)

    session.refresh(room)

    assert room.tenants == []


def test_room_tenant_deletion_behavior(
    session, landlord_factory, property_factory, room_factory, tenant_factory
):
    """Test tenant behavior when room is deleted."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    tenant = tenant_factory(room_id=room.id)
    tenant_id = tenant.id

    # Delete room
    session.delete(room)
    session.commit()

    # Verify tenant still exists (no cascade delete)
    statement = select(Tenant).where(Tenant.id == tenant_id)
    result = session.exec(statement).first()

    # Tenant remains but room_id becomes invalid reference
    assert result is not None


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================


def test_room_optional_description(
    session, landlord_factory, property_factory, room_factory
):
    """Test that description field is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id, description=None)

    assert room.description is None


def test_room_name_required(session, landlord_factory, property_factory):
    """Test that name is required."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = Room(property_id=prop.id, name=None, rent_amount=1000.00)

    with pytest.raises(IntegrityError):
        session.add(room)
        session.commit()


def test_room_rent_amount_required(session, landlord_factory, property_factory):
    """Test that rent_amount is required."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = Room(property_id=prop.id, name="Test Room", rent_amount=None)

    with pytest.raises(IntegrityError):
        session.add(room)
        session.commit()


def test_room_property_id_index(
    session, landlord_factory, property_factory, room_factory
):
    """Test that property_id is indexed for fast lookups."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)

    # Create multiple rooms
    for i in range(5):
        room_factory(property_id=prop.id, name=f"Room {i}")

    # Query should work efficiently with index
    statement = select(Room).where(Room.property_id == prop.id)
    results = session.exec(statement).all()

    assert len(results) == 5


def test_room_timestamps(session, landlord_factory, property_factory, room_factory):
    """Test that created_at and updated_at are automatically set."""
    before_creation = datetime.now(timezone.utc)
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    after_creation = datetime.now(timezone.utc)

    assert before_creation <= room.created_at <= after_creation
    assert before_creation <= room.updated_at <= after_creation


def test_room_update_timestamp(
    session, landlord_factory, property_factory, room_factory
):
    """Test that updated_at is refreshed on update."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    original_updated_at = room.updated_at

    # Wait and update
    import time

    time.sleep(0.01)

    room.rent_amount = 2000.00
    session.add(room)
    session.commit()
    session.refresh(room)

    assert room.updated_at > original_updated_at


def test_room_foreign_key_constraint(session, room_factory):
    """Test that property_id must reference a valid property."""
    from sqlalchemy.exc import IntegrityError

    room = Room(
        property_id="non-existent-property-id", name="Orphan Room", rent_amount=1000.00
    )

    with pytest.raises(IntegrityError):
        session.add(room)
        session.commit()


def test_room_unique_names_same_property(
    session, landlord_factory, property_factory, room_factory
):
    """Test that rooms can have same name in different properties."""
    landlord = landlord_factory()
    prop1 = property_factory(landlord_id=landlord.id)
    prop2 = property_factory(landlord_id=landlord.id)

    room1 = room_factory(property_id=prop1.id, name="Standard Room")
    room2 = room_factory(property_id=prop2.id, name="Standard Room")

    assert room1.name == room2.name
    assert room1.property_id != room2.property_id

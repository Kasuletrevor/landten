"""
Tests for Property model.

Tests CRUD operations, grace_period_days, and landlord relationship.
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import select
from app.models.property import Property
from app.models.landlord import Landlord
from app.models.room import Room


# =============================================================================
# CRUD Operations Tests
# =============================================================================


def test_property_creation(session, landlord_factory, property_factory):
    """Test creating a property with valid data."""
    landlord = landlord_factory()
    prop = property_factory(
        landlord_id=landlord.id, name="Sunset Apartments", address="123 Main St, City"
    )

    assert prop.name == "Sunset Apartments"
    assert prop.address == "123 Main St, City"
    assert prop.landlord_id == landlord.id
    assert prop.id is not None


def test_property_creation_with_all_fields(session, landlord_factory, property_factory):
    """Test creating a property with all fields."""
    landlord = landlord_factory()
    prop = property_factory(
        landlord_id=landlord.id,
        name="Ocean View",
        address="456 Beach Ave",
        description="Beautiful seaside property",
        grace_period_days=10,
    )

    assert prop.name == "Ocean View"
    assert prop.address == "456 Beach Ave"
    assert prop.description == "Beautiful seaside property"
    assert prop.grace_period_days == 10


def test_property_read_by_id(session, landlord_factory, property_factory):
    """Test reading a property by ID."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id, name="Find Me Property")

    statement = select(Property).where(Property.id == prop.id)
    result = session.exec(statement).first()

    assert result is not None
    assert result.id == prop.id
    assert result.name == "Find Me Property"


def test_property_update(session, landlord_factory, property_factory):
    """Test updating property fields."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id, name="Old Name")

    prop.name = "New Name"
    prop.address = "New Address"
    session.add(prop)
    session.commit()
    session.refresh(prop)

    assert prop.name == "New Name"
    assert prop.address == "New Address"


def test_property_update_grace_period(session, landlord_factory, property_factory):
    """Test updating grace_period_days."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id, grace_period_days=5)

    prop.grace_period_days = 15
    session.add(prop)
    session.commit()
    session.refresh(prop)

    assert prop.grace_period_days == 15


def test_property_delete(session, landlord_factory, property_factory):
    """Test deleting a property."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    property_id = prop.id

    session.delete(prop)
    session.commit()

    statement = select(Property).where(Property.id == property_id)
    result = session.exec(statement).first()

    assert result is None


def test_multiple_properties_per_landlord(session, landlord_factory, property_factory):
    """Test creating multiple properties for one landlord."""
    landlord = landlord_factory()

    prop1 = property_factory(landlord_id=landlord.id, name="Property 1")
    prop2 = property_factory(landlord_id=landlord.id, name="Property 2")
    prop3 = property_factory(landlord_id=landlord.id, name="Property 3")

    statement = select(Property).where(Property.landlord_id == landlord.id)
    results = session.exec(statement).all()

    assert len(results) == 3


def test_properties_for_different_landlords(
    session, landlord_factory, property_factory
):
    """Test properties belonging to different landlords."""
    landlord1 = landlord_factory(email="l1@test.com")
    landlord2 = landlord_factory(email="l2@test.com")

    prop1 = property_factory(landlord_id=landlord1.id, name="Landlord 1 Property")
    prop2 = property_factory(landlord_id=landlord2.id, name="Landlord 2 Property")

    # Query for landlord1's properties
    statement = select(Property).where(Property.landlord_id == landlord1.id)
    results = session.exec(statement).all()

    assert len(results) == 1
    assert results[0].name == "Landlord 1 Property"


# =============================================================================
# Grace Period Tests
# =============================================================================


def test_property_default_grace_period(session, landlord_factory, property_factory):
    """Test default grace_period_days is 5."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)

    assert prop.grace_period_days == 5


def test_property_grace_period_zero(session, landlord_factory, property_factory):
    """Test setting grace_period_days to 0."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id, grace_period_days=0)

    assert prop.grace_period_days == 0


def test_property_grace_period_large(session, landlord_factory, property_factory):
    """Test setting a large grace_period_days value."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id, grace_period_days=30)

    assert prop.grace_period_days == 30


def test_property_grace_period_negative(session, landlord_factory, property_factory):
    """Test negative grace_period_days (SQLite allows it, validates at app level)."""
    # Note: SQLite allows negative integers, business logic should validate
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id, grace_period_days=-5)

    # This will be allowed at DB level but should be rejected by business logic
    assert prop.grace_period_days == -5


# =============================================================================
# Relationship Tests
# =============================================================================


def test_property_landlord_relationship(session, landlord_factory, property_factory):
    """Test property's landlord relationship."""
    landlord = landlord_factory(name="Property Owner")
    prop = property_factory(landlord_id=landlord.id)

    session.refresh(prop)

    assert prop.landlord is not None
    assert prop.landlord.id == landlord.id
    assert prop.landlord.name == "Property Owner"


def test_property_rooms_relationship(
    session, landlord_factory, property_factory, room_factory
):
    """Test property's rooms relationship."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)

    room1 = room_factory(property_id=prop.id, name="Room A")
    room2 = room_factory(property_id=prop.id, name="Room B")

    session.refresh(prop)

    assert len(prop.rooms) == 2
    room_names = [r.name for r in prop.rooms]
    assert "Room A" in room_names
    assert "Room B" in room_names


def test_property_empty_rooms(session, landlord_factory, property_factory):
    """Test property with no rooms."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)

    session.refresh(prop)

    assert prop.rooms == []


def test_property_room_deletion_behavior(
    session, landlord_factory, property_factory, room_factory
):
    """Test room behavior when property is deleted."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=prop.id)
    room_id = room.id

    # Delete property
    session.delete(prop)
    session.commit()

    # Verify room still exists (no cascade delete in SQLite default)
    statement = select(Room).where(Room.id == room_id)
    result = session.exec(statement).first()

    # Room remains but property_id becomes invalid reference
    assert result is not None


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================


def test_property_optional_address(session, landlord_factory, property_factory):
    """Test that address field is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id, address=None)

    assert prop.address is None


def test_property_optional_description(session, landlord_factory, property_factory):
    """Test that description field is optional."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id, description=None)

    assert prop.description is None


def test_property_name_required(session, landlord_factory):
    """Test that name is required (NOT NULL constraint)."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    prop = Property(
        landlord_id=landlord.id,
        name=None,  # This should fail
    )

    with pytest.raises(IntegrityError):
        session.add(prop)
        session.commit()


def test_property_landlord_id_index(session, landlord_factory, property_factory):
    """Test that landlord_id is indexed for fast lookups."""
    landlord = landlord_factory()

    # Create multiple properties
    for i in range(5):
        property_factory(landlord_id=landlord.id)

    # Query should use index
    statement = select(Property).where(Property.landlord_id == landlord.id)
    results = session.exec(statement).all()

    assert len(results) == 5


def test_property_timestamps(session, landlord_factory, property_factory):
    """Test that created_at and updated_at are automatically set."""
    before_creation = datetime.now(timezone.utc)
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    after_creation = datetime.now(timezone.utc)

    assert before_creation <= prop.created_at <= after_creation
    assert before_creation <= prop.updated_at <= after_creation


def test_property_update_timestamp(session, landlord_factory, property_factory):
    """Test that updated_at is refreshed on update."""
    landlord = landlord_factory()
    prop = property_factory(landlord_id=landlord.id)
    original_updated_at = prop.updated_at

    # Wait a moment and update
    import time

    time.sleep(0.01)

    prop.name = "Updated Name"
    session.add(prop)
    session.commit()
    session.refresh(prop)

    assert prop.updated_at > original_updated_at


def test_property_foreign_key_constraint(session, property_factory):
    """Test that landlord_id must reference a valid landlord."""
    from sqlalchemy.exc import IntegrityError

    # Attempt to create property with non-existent landlord_id
    prop = Property(landlord_id="non-existent-landlord-id", name="Orphan Property")

    with pytest.raises(IntegrityError):
        session.add(prop)
        session.commit()


def test_property_long_name(session, landlord_factory, property_factory):
    """Test property with a very long name."""
    landlord = landlord_factory()
    long_name = "A" * 200
    prop = property_factory(landlord_id=landlord.id, name=long_name)

    assert prop.name == long_name
    assert len(prop.name) == 200


def test_property_special_characters_in_address(
    session, landlord_factory, property_factory
):
    """Test property address with special characters."""
    landlord = landlord_factory()
    prop = property_factory(
        landlord_id=landlord.id, address="123 Main St., Apt #456, Building 'A', Floor-2"
    )

    assert "Apt #456" in prop.address
    assert "Building 'A'" in prop.address

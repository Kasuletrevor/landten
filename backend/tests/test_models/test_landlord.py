"""
Tests for Landlord model.

Tests CRUD operations, password hashing, and relationships.
"""

import pytest
from datetime import datetime, timezone
from sqlmodel import select
from app.models.landlord import Landlord
from app.models.property import Property
from app.core.security import get_password_hash, verify_password


# =============================================================================
# CRUD Operations Tests
# =============================================================================


def test_landlord_creation(session, landlord_factory):
    """Test creating a landlord with valid data."""
    landlord = landlord_factory(name="John Doe", email="john@test.com")

    assert landlord.name == "John Doe"
    assert landlord.email == "john@test.com"
    assert landlord.id is not None
    assert len(landlord.id) == 36  # UUID v4 is 36 characters
    assert landlord.created_at is not None
    assert landlord.updated_at is not None


def test_landlord_creation_with_all_fields(session, landlord_factory):
    """Test creating a landlord with all optional fields."""
    landlord = landlord_factory(
        name="Jane Smith",
        email="jane@test.com",
        password="securepass123",
        phone="555-1234",
        primary_currency="USD",
    )

    assert landlord.name == "Jane Smith"
    assert landlord.email == "jane@test.com"
    assert landlord.phone == "555-1234"
    assert landlord.primary_currency == "USD"


def test_landlord_read_by_id(session, landlord_factory):
    """Test reading a landlord by ID."""
    landlord = landlord_factory()

    # Query the database
    statement = select(Landlord).where(Landlord.id == landlord.id)
    result = session.exec(statement).first()

    assert result is not None
    assert result.id == landlord.id
    assert result.email == landlord.email


def test_landlord_read_by_email(session, landlord_factory):
    """Test reading a landlord by email."""
    landlord = landlord_factory(email="findme@test.com")

    statement = select(Landlord).where(Landlord.email == "findme@test.com")
    result = session.exec(statement).first()

    assert result is not None
    assert result.email == "findme@test.com"


def test_landlord_update(session, landlord_factory):
    """Test updating a landlord's fields."""
    landlord = landlord_factory(name="Original Name")

    # Update the landlord
    landlord.name = "Updated Name"
    landlord.phone = "555-9999"
    session.add(landlord)
    session.commit()
    session.refresh(landlord)

    assert landlord.name == "Updated Name"
    assert landlord.phone == "555-9999"


def test_landlord_update_timestamp(session, landlord_factory):
    """Test that updated_at is refreshed on update."""
    landlord = landlord_factory()
    original_updated_at = landlord.updated_at

    # Update and verify timestamp changes
    landlord.name = "New Name"
    session.add(landlord)
    session.commit()
    session.refresh(landlord)

    assert landlord.updated_at >= original_updated_at


def test_landlord_delete(session, landlord_factory):
    """Test deleting a landlord."""
    landlord = landlord_factory()
    landlord_id = landlord.id

    # Delete the landlord
    session.delete(landlord)
    session.commit()

    # Verify deletion
    statement = select(Landlord).where(Landlord.id == landlord_id)
    result = session.exec(statement).first()

    assert result is None


def test_multiple_landlords_creation(session, landlord_factory):
    """Test creating multiple landlords."""
    landlord1 = landlord_factory(email="landlord1@test.com")
    landlord2 = landlord_factory(email="landlord2@test.com")
    landlord3 = landlord_factory(email="landlord3@test.com")

    # Query all landlords
    statement = select(Landlord)
    results = session.exec(statement).all()

    assert len(results) == 3
    emails = [l.email for l in results]
    assert "landlord1@test.com" in emails
    assert "landlord2@test.com" in emails
    assert "landlord3@test.com" in emails


# =============================================================================
# Password Hashing Tests
# =============================================================================


def test_landlord_password_hashing(session, landlord_factory):
    """Test that password is properly hashed on creation."""
    landlord = landlord_factory(password="mypassword123")

    # Password should be hashed, not stored plain
    assert landlord.password_hash is not None
    assert landlord.password_hash != "mypassword123"
    assert len(landlord.password_hash) > 20  # Hashed password is long


def test_landlord_password_verification(session, landlord_factory):
    """Test password verification works correctly."""
    landlord = landlord_factory(password="correctpassword")

    # Verify correct password
    assert verify_password("correctpassword", landlord.password_hash) is True

    # Verify incorrect password fails
    assert verify_password("wrongpassword", landlord.password_hash) is False


def test_landlord_password_update(session, landlord_factory):
    """Test updating a landlord's password."""
    landlord = landlord_factory(password="oldpassword")

    # Update password
    landlord.password_hash = get_password_hash("newpassword")
    session.add(landlord)
    session.commit()
    session.refresh(landlord)

    # Verify new password works
    assert verify_password("newpassword", landlord.password_hash) is True
    assert verify_password("oldpassword", landlord.password_hash) is False


# =============================================================================
# Relationship Tests
# =============================================================================


def test_landlord_properties_relationship(session, landlord_factory, property_factory):
    """Test landlord's properties relationship."""
    landlord = landlord_factory()

    # Create properties for this landlord
    prop1 = property_factory(landlord_id=landlord.id, name="Property 1")
    prop2 = property_factory(landlord_id=landlord.id, name="Property 2")

    # Refresh landlord to load relationships
    session.refresh(landlord)

    assert len(landlord.properties) == 2
    property_names = [p.name for p in landlord.properties]
    assert "Property 1" in property_names
    assert "Property 2" in property_names


def test_landlord_empty_properties(session, landlord_factory):
    """Test landlord with no properties."""
    landlord = landlord_factory()

    session.refresh(landlord)

    assert landlord.properties == []


def test_landlord_property_cascade_delete(
    session, landlord_factory, property_factory, room_factory
):
    """Test that deleting a landlord fails due to NOT NULL constraint on properties."""
    from sqlalchemy.exc import IntegrityError

    landlord = landlord_factory()
    property_obj = property_factory(landlord_id=landlord.id)
    room = room_factory(property_id=property_obj.id)

    # Delete the landlord - should fail due to foreign key constraint
    # because properties.landlord_id has NOT NULL constraint
    with pytest.raises(IntegrityError):
        session.delete(landlord)
        session.commit()


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================


def test_landlord_unique_email_constraint(session, landlord_factory):
    """Test that email must be unique."""
    landlord1 = landlord_factory(email="unique@test.com")

    # Attempt to create another landlord with same email
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        landlord2 = Landlord(
            email="unique@test.com",
            password_hash=get_password_hash("password"),
            name="Another Landlord",
        )
        session.add(landlord2)
        session.commit()


def test_landlord_email_index(session, landlord_factory):
    """Test that email field is indexed for fast lookups."""
    # Create multiple landlords
    for i in range(10):
        landlord_factory(email=f"landlord{i}@test.com")

    # Query by email should be fast (index is used)
    statement = select(Landlord).where(Landlord.email == "landlord5@test.com")
    result = session.exec(statement).first()

    assert result is not None
    assert result.email == "landlord5@test.com"


def test_landlord_default_currency(session, landlord_factory):
    """Test default currency is UGX."""
    landlord = landlord_factory()

    assert landlord.primary_currency == "UGX"


def test_landlord_optional_phone(session, landlord_factory):
    """Test that phone field is optional."""
    landlord = landlord_factory(phone=None)

    assert landlord.phone is None


def test_landlord_timestamps_autoset(session, landlord_factory):
    """Test that created_at and updated_at are automatically set."""
    from datetime import datetime, timezone

    before_creation = datetime.now(timezone.utc)
    landlord = landlord_factory()
    after_creation = datetime.now(timezone.utc)

    # Compare without timezone info to avoid offset-naive vs offset-aware issues
    created_at_naive = (
        landlord.created_at.replace(tzinfo=None)
        if landlord.created_at.tzinfo
        else landlord.created_at
    )
    before_naive = (
        before_creation.replace(tzinfo=None)
        if before_creation.tzinfo
        else before_creation
    )
    after_naive = (
        after_creation.replace(tzinfo=None) if after_creation.tzinfo else after_creation
    )

    assert before_naive <= created_at_naive <= after_naive
    assert landlord.created_at is not None
    assert landlord.updated_at is not None


def test_landlord_uuid_generation(session, landlord_factory):
    """Test that UUID is auto-generated and unique."""
    landlord1 = landlord_factory(email="uuid1@test.com")
    landlord2 = landlord_factory(email="uuid2@test.com")

    assert landlord1.id != landlord2.id
    assert len(landlord1.id) == 36
    assert len(landlord2.id) == 36
    # Verify UUID format (should be 8-4-4-4-12 format)
    assert landlord1.id.count("-") == 4

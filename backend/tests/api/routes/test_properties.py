"""
Tests for property API routes.
Tests all CRUD operations, authentication, and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.core.security import create_access_token


# =============================================================================
# List Properties Tests
# =============================================================================


def test_list_properties_success(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test listing properties returns landlord's properties with stats."""
    # Create properties for the authenticated landlord
    from tests.factories import PropertyFactory, RoomFactory, TenantFactory

    prop1 = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="Property One"
    )
    prop2 = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="Property Two"
    )

    # Create rooms for stats
    room1 = RoomFactory.create(
        session=session, property_id=prop1.id, rent_amount=500000, is_occupied=True
    )
    room2 = RoomFactory.create(
        session=session, property_id=prop1.id, rent_amount=600000, is_occupied=False
    )
    RoomFactory.create(
        session=session, property_id=prop2.id, rent_amount=700000, is_occupied=True
    )

    # Create tenant for occupied room
    TenantFactory.create(session=session, room_id=room1.id, is_active=True)

    # Make request
    response = client.get("/api/properties", headers=auth_headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "properties" in data
    assert "total" in data
    assert data["total"] == 2

    # Check property with stats
    prop_with_stats = data["properties"][0]
    assert "total_rooms" in prop_with_stats
    assert "occupied_rooms" in prop_with_stats
    assert "vacant_rooms" in prop_with_stats
    assert "total_tenants" in prop_with_stats
    assert "monthly_expected_income" in prop_with_stats


def test_list_properties_empty(client: TestClient, auth_headers: dict):
    """Test listing properties returns empty list when landlord has no properties."""
    response = client.get("/api/properties", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["properties"] == []
    assert data["total"] == 0


def test_list_properties_unauthorized(client: TestClient):
    """Test listing properties without authentication fails."""
    response = client.get("/api/properties")

    assert response.status_code in [401, 403]


def test_list_properties_only_own_properties(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test that landlord only sees their own properties."""
    from tests.factories import LandlordFactory, PropertyFactory

    # Create another landlord with properties
    other_landlord = LandlordFactory.create(session=session, email="other@test.com")
    PropertyFactory.create(
        session=session, landlord_id=other_landlord.id, name="Other Property"
    )

    # Create property for auth landlord
    PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="My Property"
    )

    response = client.get("/api/properties", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["properties"][0]["name"] == "My Property"


def test_list_properties_stats_calculation(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test that property stats are calculated correctly."""
    from tests.factories import PropertyFactory, RoomFactory, TenantFactory

    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)

    # Create 3 rooms: 2 occupied, 1 vacant
    room1 = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=500000, is_occupied=True
    )
    room2 = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=600000, is_occupied=True
    )
    RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=700000, is_occupied=False
    )

    # Create tenants for occupied rooms
    TenantFactory.create(session=session, room_id=room1.id, is_active=True)
    TenantFactory.create(session=session, room_id=room2.id, is_active=True)

    response = client.get("/api/properties", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    prop_stats = data["properties"][0]

    assert prop_stats["total_rooms"] == 3
    assert prop_stats["occupied_rooms"] == 2
    assert prop_stats["vacant_rooms"] == 1
    assert prop_stats["total_tenants"] == 2
    assert prop_stats["monthly_expected_income"] == 1100000  # 500000 + 600000


# =============================================================================
# Create Property Tests
# =============================================================================


def test_create_property_success(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test creating a new property."""
    property_data = {
        "name": "New Test Property",
        "address": "123 Test Street",
        "description": "A beautiful test property",
    }

    response = client.post("/api/properties", headers=auth_headers, json=property_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == property_data["name"]
    assert data["address"] == property_data["address"]
    assert data["description"] == property_data["description"]
    assert data["landlord_id"] == auth_landlord.id
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_property_minimal(
    client: TestClient, auth_landlord: Landlord, auth_headers: dict
):
    """Test creating a property with only required fields."""
    property_data = {"name": "Minimal Property"}

    response = client.post("/api/properties", headers=auth_headers, json=property_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Property"
    assert data["address"] is None
    assert data["description"] is None


def test_create_property_unauthorized(client: TestClient):
    """Test creating a property without authentication fails."""
    property_data = {"name": "Test Property"}

    response = client.post("/api/properties", json=property_data)

    assert response.status_code in [401, 403]


def test_create_property_invalid_data(client: TestClient, auth_headers: dict):
    """Test creating a property with missing required fields fails."""
    property_data = {}  # Missing required 'name' field

    response = client.post("/api/properties", headers=auth_headers, json=property_data)

    assert response.status_code == 422


def test_create_property_with_grace_period(
    client: TestClient, auth_landlord: Landlord, auth_headers: dict
):
    """Test creating a property with custom grace period."""
    # Note: grace_period_days is in schema but not implemented in router
    property_data = {"name": "Property with Grace", "grace_period_days": 10}

    response = client.post("/api/properties", headers=auth_headers, json=property_data)

    assert response.status_code == 201
    # grace_period_days not currently handled by router - field exists in schema for future use


# =============================================================================
# Get Property Tests
# =============================================================================


def test_get_property_success(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test getting a specific property by ID with stats."""
    from tests.factories import PropertyFactory, RoomFactory, TenantFactory

    prop = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="Test Property"
    )
    room = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=500000, is_occupied=True
    )
    TenantFactory.create(session=session, room_id=room.id, is_active=True)

    response = client.get(f"/api/properties/{prop.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == prop.id
    assert data["name"] == "Test Property"
    assert "total_rooms" in data
    assert "occupied_rooms" in data
    assert "monthly_expected_income" in data


def test_get_property_not_found(client: TestClient, auth_headers: dict):
    """Test getting a non-existent property returns 404."""
    response = client.get("/api/properties/non-existent-id", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_property_unauthorized(
    client: TestClient, session: Session, auth_landlord: Landlord
):
    """Test getting a property without authentication fails."""
    from tests.factories import PropertyFactory

    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)

    response = client.get(f"/api/properties/{prop.id}")

    assert response.status_code in [401, 403]


def test_get_property_wrong_landlord(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test that landlord cannot access another landlord's property."""
    from tests.factories import LandlordFactory, PropertyFactory

    other_landlord = LandlordFactory.create(session=session, email="other2@test.com")
    other_prop = PropertyFactory.create(session=session, landlord_id=other_landlord.id)

    response = client.get(f"/api/properties/{other_prop.id}", headers=auth_headers)

    assert response.status_code == 404


def test_get_property_stats_with_no_rooms(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test getting property stats when property has no rooms."""
    from tests.factories import PropertyFactory

    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)

    response = client.get(f"/api/properties/{prop.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_rooms"] == 0
    assert data["occupied_rooms"] == 0
    assert data["vacant_rooms"] == 0
    assert data["total_tenants"] == 0
    assert data["monthly_expected_income"] == 0.0


# =============================================================================
# Update Property Tests
# =============================================================================


def test_update_property_success(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test updating a property."""
    from tests.factories import PropertyFactory

    prop = PropertyFactory.create(
        session=session,
        landlord_id=auth_landlord.id,
        name="Original Name",
        address="Original Address",
    )

    update_data = {
        "name": "Updated Name",
        "address": "Updated Address",
        "description": "Updated Description",
    }

    response = client.put(
        f"/api/properties/{prop.id}", headers=auth_headers, json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["address"] == "Updated Address"
    assert data["description"] == "Updated Description"


def test_update_property_partial(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test partially updating a property (only some fields)."""
    from tests.factories import PropertyFactory

    prop = PropertyFactory.create(
        session=session,
        landlord_id=auth_landlord.id,
        name="Original Name",
        address="Original Address",
        description="Original Description",
    )

    # Only update name
    update_data = {"name": "New Name Only"}

    response = client.put(
        f"/api/properties/{prop.id}", headers=auth_headers, json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name Only"
    assert data["address"] == "Original Address"  # Unchanged
    assert data["description"] == "Original Description"  # Unchanged


def test_update_property_not_found(client: TestClient, auth_headers: dict):
    """Test updating a non-existent property returns 404."""
    update_data = {"name": "New Name"}

    response = client.put(
        "/api/properties/non-existent-id", headers=auth_headers, json=update_data
    )

    assert response.status_code == 404


def test_update_property_unauthorized(
    client: TestClient, session: Session, auth_landlord: Landlord
):
    """Test updating a property without authentication fails."""
    from tests.factories import PropertyFactory

    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)

    response = client.put(f"/api/properties/{prop.id}", json={"name": "New Name"})

    assert response.status_code in [401, 403]


def test_update_property_wrong_landlord(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test that landlord cannot update another landlord's property."""
    from tests.factories import LandlordFactory, PropertyFactory

    other_landlord = LandlordFactory.create(session=session, email="other3@test.com")
    other_prop = PropertyFactory.create(session=session, landlord_id=other_landlord.id)

    response = client.put(
        f"/api/properties/{other_prop.id}",
        headers=auth_headers,
        json={"name": "Hacked Name"},
    )

    assert response.status_code == 404


def test_update_property_grace_period(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test updating property grace period days."""
    # Note: grace_period_days is in schema but not implemented in router
    from tests.factories import PropertyFactory

    prop = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, grace_period_days=5
    )

    update_data = {"grace_period_days": 15}

    response = client.put(
        f"/api/properties/{prop.id}", headers=auth_headers, json=update_data
    )

    assert response.status_code == 200
    # grace_period_days not currently handled by router - field exists in schema for future use


def test_update_property_all_fields(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test updating all implemented property fields at once."""
    # Note: grace_period_days is in schema but not implemented in router
    from tests.factories import PropertyFactory

    prop = PropertyFactory.create(
        session=session,
        landlord_id=auth_landlord.id,
        name="Old Name",
        address="Old Address",
        description="Old Description",
        grace_period_days=5,
    )

    update_data = {
        "name": "Completely New Name",
        "address": "Completely New Address",
        "description": "Completely New Description",
        "grace_period_days": 20,  # In schema but not implemented in router
    }

    response = client.put(
        f"/api/properties/{prop.id}", headers=auth_headers, json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Completely New Name"
    assert data["address"] == "Completely New Address"
    assert data["description"] == "Completely New Description"
    # grace_period_days not currently handled by router - field exists in schema for future use


# =============================================================================
# Delete Property Tests
# =============================================================================


def test_delete_property_success(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test deleting a property without rooms."""
    from tests.factories import PropertyFactory

    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)
    prop_id = prop.id

    response = client.delete(f"/api/properties/{prop.id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify property is deleted
    from sqlmodel import select

    result = session.exec(select(Property).where(Property.id == prop_id)).first()
    assert result is None


def test_delete_property_with_rooms_fails(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test that deleting a property with rooms fails."""
    from tests.factories import PropertyFactory, RoomFactory

    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)
    RoomFactory.create(session=session, property_id=prop.id)

    response = client.delete(f"/api/properties/{prop.id}", headers=auth_headers)

    assert response.status_code == 400
    assert "rooms" in response.json()["detail"].lower()


def test_delete_property_not_found(client: TestClient, auth_headers: dict):
    """Test deleting a non-existent property returns 404."""
    response = client.delete("/api/properties/non-existent-id", headers=auth_headers)

    assert response.status_code == 404


def test_delete_property_unauthorized(
    client: TestClient, session: Session, auth_landlord: Landlord
):
    """Test deleting a property without authentication fails."""
    from tests.factories import PropertyFactory

    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)

    response = client.delete(f"/api/properties/{prop.id}")

    assert response.status_code in [401, 403]


def test_delete_property_wrong_landlord(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test that landlord cannot delete another landlord's property."""
    from tests.factories import LandlordFactory, PropertyFactory

    other_landlord = LandlordFactory.create(session=session, email="other4@test.com")
    other_prop = PropertyFactory.create(session=session, landlord_id=other_landlord.id)

    response = client.delete(f"/api/properties/{other_prop.id}", headers=auth_headers)

    assert response.status_code == 404


def test_delete_property_preserves_other_properties(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test that deleting one property doesn't affect other properties."""
    from tests.factories import PropertyFactory
    from sqlmodel import select

    prop1 = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="To Delete"
    )
    prop2 = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="To Keep"
    )

    response = client.delete(f"/api/properties/{prop1.id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify prop2 still exists
    result = session.exec(select(Property).where(Property.id == prop2.id)).first()
    assert result is not None
    assert result.name == "To Keep"

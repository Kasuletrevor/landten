"""
Tests for room API routes.
Tests all CRUD operations, bulk creation, authentication, and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.core.security import create_access_token


# =============================================================================
# Helper Fixtures
# =============================================================================


@pytest.fixture
def test_property(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Create a test property for room tests."""
    from tests.factories import PropertyFactory

    return PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="Test Property"
    )


@pytest.fixture
def test_room(client: TestClient, session: Session, test_property: Property):
    """Create a test room."""
    from tests.factories import RoomFactory

    return RoomFactory.create(
        session=session, property_id=test_property.id, name="Room 101"
    )


# =============================================================================
# List Rooms Tests
# =============================================================================


def test_list_rooms_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test listing rooms in a property with tenant info."""
    from tests.factories import RoomFactory, TenantFactory

    # Create rooms
    room1 = RoomFactory.create(
        session=session, property_id=test_property.id, name="Room A", rent_amount=500000
    )
    room2 = RoomFactory.create(
        session=session, property_id=test_property.id, name="Room B", rent_amount=600000
    )

    # Create tenant for room1
    tenant = TenantFactory.create(
        session=session, room_id=room1.id, name="John Doe", is_active=True
    )

    response = client.get(
        f"/api/properties/{test_property.id}/rooms", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "rooms" in data
    assert "total" in data
    assert data["total"] == 2

    # Check room with tenant info
    room_with_tenant = data["rooms"][0]
    assert "tenant_name" in room_with_tenant
    assert "tenant_id" in room_with_tenant


def test_list_rooms_empty(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test listing rooms returns empty list when property has no rooms."""
    response = client.get(
        f"/api/properties/{test_property.id}/rooms", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["rooms"] == []
    assert data["total"] == 0


def test_list_rooms_unauthorized(client: TestClient, test_property: Property):
    """Test listing rooms without authentication fails."""
    response = client.get(f"/api/properties/{test_property.id}/rooms")

    assert response.status_code in [401, 403]


def test_list_rooms_wrong_property(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test listing rooms for non-existent property returns 404."""
    response = client.get("/api/properties/non-existent-id/rooms", headers=auth_headers)

    assert response.status_code == 404


def test_list_rooms_other_landlord_property(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test that landlord cannot list rooms of another landlord's property."""
    from tests.factories import LandlordFactory, PropertyFactory

    other_landlord = LandlordFactory.create(session=session, email="other1@test.com")
    other_property = PropertyFactory.create(
        session=session, landlord_id=other_landlord.id
    )

    response = client.get(
        f"/api/properties/{other_property.id}/rooms", headers=auth_headers
    )

    assert response.status_code == 404


def test_list_rooms_with_tenant_info(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test that room list includes correct tenant information."""
    from tests.factories import RoomFactory, TenantFactory

    room = RoomFactory.create(
        session=session,
        property_id=test_property.id,
        name="Occupied Room",
        is_occupied=True,
    )
    tenant = TenantFactory.create(
        session=session, room_id=room.id, name="Jane Smith", is_active=True
    )

    response = client.get(
        f"/api/properties/{test_property.id}/rooms", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    room_data = data["rooms"][0]

    assert room_data["tenant_name"] == "Jane Smith"
    assert room_data["tenant_id"] == tenant.id


def test_list_rooms_vacant_room(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test that vacant rooms have null tenant info."""
    from tests.factories import RoomFactory

    RoomFactory.create(
        session=session,
        property_id=test_property.id,
        name="Vacant Room",
        is_occupied=False,
    )

    response = client.get(
        f"/api/properties/{test_property.id}/rooms", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    room_data = data["rooms"][0]

    assert room_data["tenant_name"] is None
    assert room_data["tenant_id"] is None


# =============================================================================
# Create Room Tests
# =============================================================================


def test_create_room_success(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test creating a new room."""
    room_data = {
        "name": "New Room 101",
        "rent_amount": 750000,
        "currency": "UGX",
        "description": "A nice room",
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms",
        headers=auth_headers,
        json=room_data,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == room_data["name"]
    assert data["rent_amount"] == room_data["rent_amount"]
    assert data["currency"] == room_data["currency"]
    assert data["description"] == room_data["description"]
    assert data["property_id"] == test_property.id
    assert data["is_occupied"] is False
    assert "id" in data


def test_create_room_minimal(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test creating a room with only required fields."""
    room_data = {"name": "Basic Room", "rent_amount": 500000}

    response = client.post(
        f"/api/properties/{test_property.id}/rooms",
        headers=auth_headers,
        json=room_data,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Basic Room"
    assert data["rent_amount"] == 500000
    assert data["currency"] == "UGX"  # Default
    assert data["is_occupied"] is False


def test_create_room_unauthorized(client: TestClient, test_property: Property):
    """Test creating a room without authentication fails."""
    room_data = {"name": "Test Room", "rent_amount": 500000}

    response = client.post(f"/api/properties/{test_property.id}/rooms", json=room_data)

    assert response.status_code in [401, 403]


def test_create_room_wrong_property(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test creating a room in another landlord's property fails."""
    from tests.factories import LandlordFactory, PropertyFactory

    other_landlord = LandlordFactory.create(session=session, email="other2@test.com")
    other_property = PropertyFactory.create(
        session=session, landlord_id=other_landlord.id
    )

    room_data = {"name": "Hacked Room", "rent_amount": 500000}

    response = client.post(
        f"/api/properties/{other_property.id}/rooms",
        headers=auth_headers,
        json=room_data,
    )

    assert response.status_code == 404


def test_create_room_invalid_data(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test creating a room with missing required fields fails."""
    room_data = {"name": "No Price Room"}  # Missing rent_amount

    response = client.post(
        f"/api/properties/{test_property.id}/rooms",
        headers=auth_headers,
        json=room_data,
    )

    assert response.status_code == 422


def test_create_room_different_currency(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test creating a room with different currency."""
    room_data = {"name": "USD Room", "rent_amount": 500, "currency": "USD"}

    response = client.post(
        f"/api/properties/{test_property.id}/rooms",
        headers=auth_headers,
        json=room_data,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["currency"] == "USD"


# =============================================================================
# Get Room Tests
# =============================================================================


def test_get_room_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test getting a specific room by ID."""
    from tests.factories import TenantFactory

    # Create tenant for the room
    tenant = TenantFactory.create(
        session=session, room_id=test_room.id, name="Room Tenant", is_active=True
    )

    response = client.get(
        f"/api/properties/{test_property.id}/rooms/{test_room.id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_room.id
    assert data["name"] == test_room.name
    assert data["tenant_name"] == "Room Tenant"
    assert data["tenant_id"] == tenant.id


def test_get_room_not_found(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test getting a non-existent room returns 404."""
    response = client.get(
        f"/api/properties/{test_property.id}/rooms/non-existent-id",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_get_room_unauthorized(
    client: TestClient, test_property: Property, test_room: Room
):
    """Test getting a room without authentication fails."""
    response = client.get(f"/api/properties/{test_property.id}/rooms/{test_room.id}")

    assert response.status_code in [401, 403]


def test_get_room_wrong_property(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test getting a room from wrong property returns 404."""
    from tests.factories import PropertyFactory, RoomFactory

    other_property = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id
    )
    other_room = RoomFactory.create(session=session, property_id=other_property.id)

    # Try to get room from different property
    response = client.get(
        f"/api/properties/{test_property.id}/rooms/{other_room.id}",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_get_room_vacant(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test getting a vacant room returns null tenant info."""
    from tests.factories import RoomFactory

    vacant_room = RoomFactory.create(
        session=session, property_id=test_property.id, name="Vacant", is_occupied=False
    )

    response = client.get(
        f"/api/properties/{test_property.id}/rooms/{vacant_room.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_name"] is None
    assert data["tenant_id"] is None


# =============================================================================
# Update Room Tests
# =============================================================================


def test_update_room_success(
    client: TestClient, auth_headers: dict, test_property: Property, test_room: Room
):
    """Test updating a room."""
    update_data = {
        "name": "Updated Room Name",
        "rent_amount": 800000,
        "description": "Updated description",
    }

    response = client.put(
        f"/api/properties/{test_property.id}/rooms/{test_room.id}",
        headers=auth_headers,
        json=update_data,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Room Name"
    assert data["rent_amount"] == 800000
    assert data["description"] == "Updated description"


def test_update_room_partial(
    client: TestClient, auth_headers: dict, test_property: Property, test_room: Room
):
    """Test partially updating a room."""
    original_name = test_room.name

    update_data = {"rent_amount": 900000}

    response = client.put(
        f"/api/properties/{test_property.id}/rooms/{test_room.id}",
        headers=auth_headers,
        json=update_data,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == original_name  # Unchanged
    assert data["rent_amount"] == 900000


def test_update_room_not_found(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test updating a non-existent room returns 404."""
    update_data = {"name": "New Name"}

    response = client.put(
        f"/api/properties/{test_property.id}/rooms/non-existent-id",
        headers=auth_headers,
        json=update_data,
    )

    assert response.status_code == 404


def test_update_room_unauthorized(
    client: TestClient, test_property: Property, test_room: Room
):
    """Test updating a room without authentication fails."""
    response = client.put(
        f"/api/properties/{test_property.id}/rooms/{test_room.id}",
        json={"name": "New Name"},
    )

    assert response.status_code in [401, 403]


def test_update_room_wrong_property(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test updating a room in wrong property returns 404."""
    from tests.factories import PropertyFactory, RoomFactory

    other_property = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id
    )
    other_room = RoomFactory.create(session=session, property_id=other_property.id)

    response = client.put(
        f"/api/properties/{test_property.id}/rooms/{other_room.id}",
        headers=auth_headers,
        json={"name": "Hacked"},
    )

    assert response.status_code == 404


def test_update_room_currency(
    client: TestClient, auth_headers: dict, test_property: Property, test_room: Room
):
    """Test updating room currency."""
    update_data = {"currency": "USD"}

    response = client.put(
        f"/api/properties/{test_property.id}/rooms/{test_room.id}",
        headers=auth_headers,
        json=update_data,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "USD"


# =============================================================================
# Delete Room Tests
# =============================================================================


def test_delete_room_success(
    client: TestClient, session: Session, auth_headers: dict, test_property: Property
):
    """Test deleting a vacant room."""
    from tests.factories import RoomFactory
    from sqlmodel import select

    room = RoomFactory.create(
        session=session, property_id=test_property.id, is_occupied=False
    )
    room_id = room.id

    response = client.delete(
        f"/api/properties/{test_property.id}/rooms/{room.id}", headers=auth_headers
    )

    assert response.status_code == 204

    # Verify room is deleted
    result = session.exec(select(Room).where(Room.id == room_id)).first()
    assert result is None


def test_delete_room_occupied_fails(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test that deleting an occupied room fails."""
    from tests.factories import RoomFactory, TenantFactory

    room = RoomFactory.create(
        session=session, property_id=test_property.id, is_occupied=True
    )
    TenantFactory.create(session=session, room_id=room.id, is_active=True)

    response = client.delete(
        f"/api/properties/{test_property.id}/rooms/{room.id}", headers=auth_headers
    )

    assert response.status_code == 400
    assert "active tenant" in response.json()["detail"].lower()


def test_delete_room_not_found(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test deleting a non-existent room returns 404."""
    response = client.delete(
        f"/api/properties/{test_property.id}/rooms/non-existent-id",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_delete_room_unauthorized(
    client: TestClient, test_property: Property, test_room: Room
):
    """Test deleting a room without authentication fails."""
    response = client.delete(f"/api/properties/{test_property.id}/rooms/{test_room.id}")

    assert response.status_code in [401, 403]


def test_delete_room_wrong_property(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test deleting a room from wrong property returns 404."""
    from tests.factories import PropertyFactory, RoomFactory

    other_property = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id
    )
    other_room = RoomFactory.create(
        session=session, property_id=other_property.id, is_occupied=False
    )

    response = client.delete(
        f"/api/properties/{test_property.id}/rooms/{other_room.id}",
        headers=auth_headers,
    )

    assert response.status_code == 404


# =============================================================================
# Bulk Create Rooms Tests
# =============================================================================


def test_bulk_create_rooms_success(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test bulk creating rooms with price ranges."""
    bulk_data = {
        "prefix": "Room ",
        "from_number": 1,
        "to_number": 5,
        "currency": "UGX",
        "price_ranges": [
            {"from_number": 1, "to_number": 3, "rent_amount": 500000},
            {"from_number": 4, "to_number": 5, "rent_amount": 600000},
        ],
        "padding": 3,
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms/bulk",
        headers=auth_headers,
        json=bulk_data,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["total_created"] == 5
    assert len(data["created"]) == 5
    assert "warnings" in data

    # Check room names with padding
    room_names = [r["name"] for r in data["created"]]
    assert "Room 001" in room_names
    assert "Room 005" in room_names


def test_bulk_create_rooms_single_price(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test bulk creating rooms with single price range."""
    bulk_data = {
        "from_number": 1,
        "to_number": 3,
        "currency": "USD",
        "price_ranges": [{"from_number": 1, "to_number": 3, "rent_amount": 1000}],
        "padding": 0,
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms/bulk",
        headers=auth_headers,
        json=bulk_data,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["total_created"] == 3


def test_bulk_create_rooms_with_gaps(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test bulk creating rooms with price gaps generates warnings."""
    bulk_data = {
        "from_number": 1,
        "to_number": 5,
        "currency": "UGX",
        "price_ranges": [
            {"from_number": 1, "to_number": 2, "rent_amount": 500000},
            {"from_number": 4, "to_number": 5, "rent_amount": 600000},
        ],
        "padding": 0,
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms/bulk",
        headers=auth_headers,
        json=bulk_data,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["total_created"] == 4  # Room 3 skipped
    assert len(data["warnings"]) == 1
    assert "3" in data["warnings"][0]  # Warning about room 3


def test_bulk_create_rooms_too_many(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test bulk creating more than 500 rooms fails."""
    bulk_data = {
        "from_number": 1,
        "to_number": 501,
        "currency": "UGX",
        "price_ranges": [{"from_number": 1, "to_number": 501, "rent_amount": 500000}],
        "padding": 0,
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms/bulk",
        headers=auth_headers,
        json=bulk_data,
    )

    assert response.status_code == 400
    assert "500" in response.json()["detail"]


def test_bulk_create_rooms_invalid_range(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test bulk creating with invalid range (to < from) fails."""
    bulk_data = {
        "from_number": 10,
        "to_number": 1,
        "currency": "UGX",
        "price_ranges": [{"from_number": 10, "to_number": 1, "rent_amount": 500000}],
        "padding": 0,
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms/bulk",
        headers=auth_headers,
        json=bulk_data,
    )

    assert response.status_code == 422  # Validation error


def test_bulk_create_rooms_price_range_outside(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test bulk creating with price range outside overall range fails."""
    bulk_data = {
        "from_number": 1,
        "to_number": 5,
        "currency": "UGX",
        "price_ranges": [
            {"from_number": 1, "to_number": 10, "rent_amount": 500000}  # 10 > 5
        ],
        "padding": 0,
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms/bulk",
        headers=auth_headers,
        json=bulk_data,
    )

    assert response.status_code == 400
    assert "outside" in response.json()["detail"].lower()


def test_bulk_create_rooms_no_price_ranges(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test bulk creating without price ranges fails."""
    bulk_data = {
        "from_number": 1,
        "to_number": 3,
        "currency": "UGX",
        "price_ranges": [],
        "padding": 0,
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms/bulk",
        headers=auth_headers,
        json=bulk_data,
    )

    assert response.status_code == 422  # Validation error


def test_bulk_create_rooms_unauthorized(client: TestClient, test_property: Property):
    """Test bulk creating without authentication fails."""
    bulk_data = {
        "from_number": 1,
        "to_number": 2,
        "currency": "UGX",
        "price_ranges": [{"from_number": 1, "to_number": 2, "rent_amount": 500000}],
        "padding": 0,
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms/bulk", json=bulk_data
    )

    assert response.status_code in [401, 403]


def test_bulk_create_rooms_wrong_property(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test bulk creating in another landlord's property fails."""
    from tests.factories import LandlordFactory, PropertyFactory

    other_landlord = LandlordFactory.create(session=session, email="other3@test.com")
    other_property = PropertyFactory.create(
        session=session, landlord_id=other_landlord.id
    )

    bulk_data = {
        "from_number": 1,
        "to_number": 2,
        "currency": "UGX",
        "price_ranges": [{"from_number": 1, "to_number": 2, "rent_amount": 500000}],
        "padding": 0,
    }

    response = client.post(
        f"/api/properties/{other_property.id}/rooms/bulk",
        headers=auth_headers,
        json=bulk_data,
    )

    assert response.status_code == 404


def test_bulk_create_rooms_prices_assigned_correctly(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test that prices are assigned correctly based on ranges."""
    bulk_data = {
        "prefix": "Apt",
        "from_number": 1,
        "to_number": 4,
        "currency": "UGX",
        "price_ranges": [
            {"from_number": 1, "to_number": 2, "rent_amount": 400000},
            {"from_number": 3, "to_number": 4, "rent_amount": 600000},
        ],
        "padding": 0,
    }

    response = client.post(
        f"/api/properties/{test_property.id}/rooms/bulk",
        headers=auth_headers,
        json=bulk_data,
    )

    assert response.status_code == 201
    data = response.json()

    # Check prices
    prices = {r["name"]: r["rent_amount"] for r in data["created"]}
    assert prices["Apt1"] == 400000
    assert prices["Apt2"] == 400000
    assert prices["Apt3"] == 600000
    assert prices["Apt4"] == 600000

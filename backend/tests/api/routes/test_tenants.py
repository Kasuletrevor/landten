"""
Tests for tenant API routes.
Tests all CRUD operations, payment schedules, portal access, and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment_schedule import PaymentSchedule, PaymentFrequency
from app.models.payment import Payment, PaymentStatus
from app.core.security import create_access_token, get_password_hash


# =============================================================================
# Helper Fixtures
# =============================================================================


@pytest.fixture
def test_property(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Create a test property for tenant tests."""
    from tests.factories import PropertyFactory

    return PropertyFactory.create(
        session=session,
        landlord_id=auth_landlord.id,
        name="Test Property",
        grace_period_days=5,
    )


@pytest.fixture
def test_room(client: TestClient, session: Session, test_property: Property):
    """Create a test room."""
    from tests.factories import RoomFactory

    return RoomFactory.create(
        session=session,
        property_id=test_property.id,
        name="Room 101",
        rent_amount=1000000,
        is_occupied=False,
    )


@pytest.fixture
def test_tenant(client: TestClient, session: Session, test_room: Room):
    """Create a test tenant."""
    from tests.factories import TenantFactory

    return TenantFactory.create(
        session=session, room_id=test_room.id, name="Test Tenant", is_active=True
    )


# =============================================================================
# List Tenants Tests
# =============================================================================


def test_list_tenants_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test listing all tenants for landlord."""
    from tests.factories import RoomFactory, TenantFactory

    # Create rooms and tenants
    room1 = RoomFactory.create(
        session=session, property_id=test_property.id, name="Room A"
    )
    room2 = RoomFactory.create(
        session=session, property_id=test_property.id, name="Room B"
    )

    tenant1 = TenantFactory.create(
        session=session, room_id=room1.id, name="John Doe", is_active=True
    )
    tenant2 = TenantFactory.create(
        session=session, room_id=room2.id, name="Jane Smith", is_active=True
    )

    response = client.get("/api/tenants", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "tenants" in data
    assert "total" in data
    assert data["total"] == 2

    # Check tenant details are included
    tenant_names = [t["name"] for t in data["tenants"]]
    assert "John Doe" in tenant_names
    assert "Jane Smith" in tenant_names


def test_list_tenants_with_property_filter(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test listing tenants filtered by property."""
    from tests.factories import PropertyFactory, RoomFactory, TenantFactory

    # Create two properties
    property1 = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="Property 1"
    )
    property2 = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="Property 2"
    )

    # Create rooms and tenants in each property
    room1 = RoomFactory.create(session=session, property_id=property1.id, name="Room 1")
    room2 = RoomFactory.create(session=session, property_id=property2.id, name="Room 2")

    TenantFactory.create(session=session, room_id=room1.id, name="Tenant in Prop 1")
    TenantFactory.create(session=session, room_id=room2.id, name="Tenant in Prop 2")

    # Filter by property1
    response = client.get(
        f"/api/tenants?property_id={property1.id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tenants"][0]["name"] == "Tenant in Prop 1"


def test_list_tenants_active_only_filter(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test listing tenants with active_only filter."""
    from tests.factories import RoomFactory, TenantFactory

    room1 = RoomFactory.create(
        session=session, property_id=test_property.id, name="Room 1"
    )
    room2 = RoomFactory.create(
        session=session, property_id=test_property.id, name="Room 2"
    )

    # Active tenant
    TenantFactory.create(
        session=session, room_id=room1.id, name="Active Tenant", is_active=True
    )
    # Inactive tenant
    TenantFactory.create(
        session=session, room_id=room2.id, name="Inactive Tenant", is_active=False
    )

    # Get only active tenants (default)
    response = client.get("/api/tenants?active_only=true", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["tenants"][0]["name"] == "Active Tenant"

    # Get all tenants including inactive
    response = client.get("/api/tenants?active_only=false", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


def test_list_tenants_empty(
    client: TestClient, auth_headers: dict, test_property: Property
):
    """Test listing tenants returns empty list when no tenants exist."""
    response = client.get("/api/tenants", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tenants"] == []
    assert data["total"] == 0


def test_list_tenants_unauthorized(client: TestClient):
    """Test listing tenants without authentication fails."""
    response = client.get("/api/tenants")
    assert response.status_code in [401, 403]


def test_list_tenants_includes_details(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test that tenant list includes room and property details."""
    from tests.factories import (
        RoomFactory,
        TenantFactory,
        PaymentScheduleFactory,
        PaymentFactory,
    )

    room = RoomFactory.create(
        session=session,
        property_id=test_property.id,
        name="Master Suite",
        rent_amount=1500000,
    )
    tenant = TenantFactory.create(
        session=session, room_id=room.id, name="Detailed Tenant"
    )

    # Add payment schedule
    schedule = PaymentScheduleFactory.create(session=session, tenant_id=tenant.id)
    # Add pending payment
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        schedule_id=schedule.id,
        status=PaymentStatus.PENDING,
    )

    response = client.get("/api/tenants", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    tenant_data = data["tenants"][0]

    assert tenant_data["room_name"] == "Master Suite"
    assert tenant_data["property_id"] == test_property.id
    assert tenant_data["property_name"] == "Test Property"
    assert tenant_data["rent_amount"] == 1500000
    assert tenant_data["has_payment_schedule"] is True
    assert tenant_data["pending_payments"] == 1


def test_list_tenants_other_landlord(
    client: TestClient, session: Session, auth_landlord: Landlord, auth_headers: dict
):
    """Test that landlord only sees their own tenants."""
    from tests.factories import (
        LandlordFactory,
        PropertyFactory,
        RoomFactory,
        TenantFactory,
    )

    # Create another landlord with property and tenant
    other_landlord = LandlordFactory.create(session=session, email="other@example.com")
    other_property = PropertyFactory.create(
        session=session, landlord_id=other_landlord.id
    )
    other_room = RoomFactory.create(session=session, property_id=other_property.id)
    TenantFactory.create(session=session, room_id=other_room.id, name="Other's Tenant")

    # First landlord should see no tenants
    response = client.get("/api/tenants", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


# =============================================================================
# Create Tenant Tests
# =============================================================================


def test_create_tenant_with_auto_schedule(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test creating tenant automatically creates payment schedule and first payment."""
    from app.models.payment_schedule import PaymentSchedule
    from app.models.payment import Payment

    move_in_date = date(2024, 1, 1)  # 1st of month - no proration

    tenant_data = {
        "room_id": test_room.id,
        "name": "New Tenant",
        "email": "newtenant@example.com",
        "phone": "555-1234",
        "move_in_date": move_in_date.isoformat(),
        "auto_create_schedule": True,
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Tenant"
    assert data["email"] == "newtenant@example.com"
    assert data["room_id"] == test_room.id
    assert data["has_payment_schedule"] is True
    assert data["rent_amount"] == test_room.rent_amount  # Uses room rent

    # Verify room is now occupied
    session.refresh(test_room)
    assert test_room.is_occupied is True

    # Verify payment schedule was created
    schedule = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.tenant_id == data["id"])
    ).first()
    assert schedule is not None
    assert schedule.amount == test_room.rent_amount
    assert schedule.frequency == PaymentFrequency.MONTHLY

    # Verify first payment was generated
    payment = session.exec(
        select(Payment).where(Payment.tenant_id == data["id"])
    ).first()
    assert payment is not None
    assert payment.amount_due == test_room.rent_amount


def test_create_tenant_without_auto_schedule(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test creating tenant without auto schedule skips payment schedule creation."""
    from app.models.payment_schedule import PaymentSchedule

    tenant_data = {
        "room_id": test_room.id,
        "name": "No Schedule Tenant",
        "email": "noschedule@example.com",
        "move_in_date": date(2024, 1, 1).isoformat(),
        "auto_create_schedule": False,
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)

    assert response.status_code == 201
    data = response.json()
    assert data["has_payment_schedule"] is False

    # Verify no payment schedule was created
    schedule = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.tenant_id == data["id"])
    ).first()
    assert schedule is None

    # Verify room is still occupied
    session.refresh(test_room)
    assert test_room.is_occupied is True


def test_create_tenant_with_custom_payment_amount(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test creating tenant with custom payment amount overrides room rent."""
    from app.models.payment_schedule import PaymentSchedule

    custom_amount = 800000  # Less than room rent of 1000000

    tenant_data = {
        "room_id": test_room.id,
        "name": "Custom Rent Tenant",
        "email": "custom@example.com",
        "move_in_date": date(2024, 1, 1).isoformat(),
        "payment_amount": custom_amount,
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)

    assert response.status_code == 201
    data = response.json()

    # Verify payment schedule uses custom amount
    schedule = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.tenant_id == data["id"])
    ).first()
    assert schedule is not None
    assert schedule.amount == custom_amount


def test_create_tenant_prorated_payment_after_5th(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test creating tenant with move-in after 5th creates prorated payment."""
    from app.models.payment import Payment

    move_in_date = date(2024, 1, 15)  # After 5th - should create prorated payment

    tenant_data = {
        "room_id": test_room.id,
        "name": "Mid-month Tenant",
        "email": "midmonth@example.com",
        "move_in_date": move_in_date.isoformat(),
        "auto_create_schedule": True,
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)

    assert response.status_code == 201
    data = response.json()
    assert data["pending_payments"] == 1  # Prorated payment counts as pending

    # Verify prorated payment was created
    payments = session.exec(
        select(Payment).where(Payment.tenant_id == data["id"])
    ).all()

    # Should have prorated payment (manual) and first scheduled payment
    prorated = [p for p in payments if p.is_manual]
    scheduled = [p for p in payments if not p.is_manual]

    assert len(prorated) == 1
    assert prorated[0].period_start == move_in_date
    assert "prorated" in prorated[0].notes.lower()

    # First scheduled payment should start from Feb 1st (next month)
    assert len(scheduled) == 1
    assert scheduled[0].period_start == date(2024, 2, 1)


def test_create_tenant_no_proration_before_5th(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test creating tenant with move-in on or before 5th has no prorated payment."""
    from app.models.payment import Payment

    move_in_date = date(2024, 1, 3)  # Before 5th - no proration

    tenant_data = {
        "room_id": test_room.id,
        "name": "Early Month Tenant",
        "email": "early@example.com",
        "move_in_date": move_in_date.isoformat(),
        "auto_create_schedule": True,
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)

    assert response.status_code == 201
    data = response.json()

    # Verify only one payment (scheduled, no prorated)
    payments = session.exec(
        select(Payment).where(Payment.tenant_id == data["id"])
    ).all()

    assert len(payments) == 1
    assert payments[0].is_manual is False  # Not a manual prorated payment


def test_create_tenant_occupied_room_fails(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test that creating tenant in occupied room fails."""
    from tests.factories import TenantFactory

    # First tenant occupies the room
    TenantFactory.create(session=session, room_id=test_room.id, is_active=True)
    test_room.is_occupied = True
    session.add(test_room)
    session.commit()

    # Try to add second tenant
    tenant_data = {
        "room_id": test_room.id,
        "name": "Second Tenant",
        "email": "second@example.com",
        "move_in_date": date(2024, 1, 1).isoformat(),
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)

    assert response.status_code == 400
    assert "already has an active tenant" in response.json()["detail"].lower()


def test_create_tenant_invalid_room(client: TestClient, auth_headers: dict):
    """Test creating tenant with non-existent room fails."""
    tenant_data = {
        "room_id": "non-existent-room-id",
        "name": "Orphan Tenant",
        "email": "orphan@example.com",
        "move_in_date": date(2024, 1, 1).isoformat(),
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)

    assert response.status_code == 404
    assert "room not found" in response.json()["detail"].lower()


def test_create_tenant_other_landlord_room(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test creating tenant in another landlord's room fails."""
    from tests.factories import LandlordFactory, PropertyFactory, RoomFactory

    other_landlord = LandlordFactory.create(session=session, email="other@example.com")
    other_property = PropertyFactory.create(
        session=session, landlord_id=other_landlord.id
    )
    other_room = RoomFactory.create(session=session, property_id=other_property.id)

    tenant_data = {
        "room_id": other_room.id,
        "name": "Hacker Tenant",
        "email": "hacker@example.com",
        "move_in_date": date(2024, 1, 1).isoformat(),
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)

    assert response.status_code == 404  # Should not reveal room exists


def test_create_tenant_unauthorized(client: TestClient, test_room: Room):
    """Test creating tenant without authentication fails."""
    tenant_data = {
        "room_id": test_room.id,
        "name": "Unauthorized Tenant",
        "email": "unauthorized@example.com",
        "move_in_date": date(2024, 1, 1).isoformat(),
    }

    response = client.post("/api/tenants", json=tenant_data)
    assert response.status_code in [401, 403]


def test_create_tenant_missing_required_fields(
    client: TestClient, auth_headers: dict, test_room: Room
):
    """Test creating tenant without required fields fails."""
    tenant_data = {
        "room_id": test_room.id,
        # Missing name and move_in_date
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)
    assert response.status_code == 422


def test_create_tenant_uses_property_grace_period(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test that payment schedule uses property's grace_period_days."""
    from tests.factories import PropertyFactory, RoomFactory
    from app.models.payment_schedule import PaymentSchedule

    # Create property with custom grace period
    custom_property = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, grace_period_days=10
    )
    custom_room = RoomFactory.create(
        session=session, property_id=custom_property.id, is_occupied=False
    )

    tenant_data = {
        "room_id": custom_room.id,
        "name": "Grace Period Tenant",
        "email": "grace@example.com",
        "move_in_date": date(2024, 1, 1).isoformat(),
        "auto_create_schedule": True,
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)
    assert response.status_code == 201
    data = response.json()

    # Verify schedule uses property's grace period
    schedule = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.tenant_id == data["id"])
    ).first()
    assert schedule is not None
    assert schedule.window_days == 10


# =============================================================================
# Get Tenant Tests
# =============================================================================


def test_get_tenant_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test getting a specific tenant by ID."""
    from tests.factories import TenantFactory, PaymentScheduleFactory, PaymentFactory

    tenant = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        name="Specific Tenant",
        email="specific@example.com",
    )

    # Add schedule and payments
    schedule = PaymentScheduleFactory.create(session=session, tenant_id=tenant.id)
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        schedule_id=schedule.id,
        status=PaymentStatus.PENDING,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        schedule_id=schedule.id,
        status=PaymentStatus.OVERDUE,
    )

    response = client.get(f"/api/tenants/{tenant.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tenant.id
    assert data["name"] == "Specific Tenant"
    assert data["email"] == "specific@example.com"
    assert data["room_name"] == test_room.name
    assert data["property_id"] == test_property.id
    assert data["property_name"] == test_property.name
    assert data["rent_amount"] == test_room.rent_amount
    assert data["has_payment_schedule"] is True
    assert data["pending_payments"] == 1
    assert data["overdue_payments"] == 1


def test_get_tenant_not_found(client: TestClient, auth_headers: dict):
    """Test getting non-existent tenant returns 404."""
    response = client.get("/api/tenants/non-existent-id", headers=auth_headers)
    assert response.status_code == 404


def test_get_tenant_unauthorized(client: TestClient, test_tenant: Tenant):
    """Test getting tenant without authentication fails."""
    response = client.get(f"/api/tenants/{test_tenant.id}")
    assert response.status_code in [401, 403]


def test_get_tenant_other_landlord(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test getting another landlord's tenant fails."""
    from tests.factories import (
        LandlordFactory,
        PropertyFactory,
        RoomFactory,
        TenantFactory,
    )

    other_landlord = LandlordFactory.create(session=session, email="other@example.com")
    other_property = PropertyFactory.create(
        session=session, landlord_id=other_landlord.id
    )
    other_room = RoomFactory.create(session=session, property_id=other_property.id)
    other_tenant = TenantFactory.create(session=session, room_id=other_room.id)

    response = client.get(f"/api/tenants/{other_tenant.id}", headers=auth_headers)
    assert response.status_code == 404


# =============================================================================
# Update Tenant Tests
# =============================================================================


def test_update_tenant_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test updating tenant information."""
    from tests.factories import TenantFactory

    tenant = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        name="Original Name",
        email="original@example.com",
    )

    update_data = {
        "name": "Updated Name",
        "email": "updated@example.com",
        "phone": "555-9999",
        "notes": "Updated notes",
    }

    response = client.put(
        f"/api/tenants/{tenant.id}", headers=auth_headers, json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["email"] == "updated@example.com"
    assert data["phone"] == "555-9999"
    assert data["notes"] == "Updated notes"


def test_update_tenant_partial(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test partially updating tenant (only some fields)."""
    from tests.factories import TenantFactory

    tenant = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        name="Partial Tenant",
        email="partial@example.com",
        phone="555-0000",
    )

    update_data = {"phone": "555-1111"}  # Only update phone

    response = client.put(
        f"/api/tenants/{tenant.id}", headers=auth_headers, json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Partial Tenant"  # Unchanged
    assert data["email"] == "partial@example.com"  # Unchanged
    assert data["phone"] == "555-1111"  # Updated


def test_update_tenant_not_found(client: TestClient, auth_headers: dict):
    """Test updating non-existent tenant returns 404."""
    update_data = {"name": "New Name"}
    response = client.put(
        "/api/tenants/non-existent-id", headers=auth_headers, json=update_data
    )
    assert response.status_code == 404


def test_update_tenant_unauthorized(client: TestClient, test_tenant: Tenant):
    """Test updating tenant without authentication fails."""
    update_data = {"name": "New Name"}
    response = client.put(f"/api/tenants/{test_tenant.id}", json=update_data)
    assert response.status_code in [401, 403]


def test_update_tenant_other_landlord(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test updating another landlord's tenant fails."""
    from tests.factories import (
        LandlordFactory,
        PropertyFactory,
        RoomFactory,
        TenantFactory,
    )

    other_landlord = LandlordFactory.create(session=session, email="other@example.com")
    other_property = PropertyFactory.create(
        session=session, landlord_id=other_landlord.id
    )
    other_room = RoomFactory.create(session=session, property_id=other_property.id)
    other_tenant = TenantFactory.create(session=session, room_id=other_room.id)

    update_data = {"name": "Hacked Name"}
    response = client.put(
        f"/api/tenants/{other_tenant.id}", headers=auth_headers, json=update_data
    )
    assert response.status_code == 404


# =============================================================================
# Move Out Tenant Tests
# =============================================================================


def test_move_out_tenant_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test moving out a tenant."""
    from tests.factories import TenantFactory, PaymentScheduleFactory

    tenant = TenantFactory.create(
        session=session, room_id=test_room.id, name="Moving Out Tenant", is_active=True
    )
    test_room.is_occupied = True
    session.add(test_room)

    # Add active payment schedule
    schedule = PaymentScheduleFactory.create(
        session=session, tenant_id=tenant.id, is_active=True
    )
    session.commit()

    move_out_date = date(2024, 12, 31)
    move_out_data = {"move_out_date": move_out_date.isoformat()}

    response = client.post(
        f"/api/tenants/{tenant.id}/move-out", headers=auth_headers, json=move_out_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False
    assert data["move_out_date"] == move_out_date.isoformat()

    # Verify room is now vacant
    session.refresh(test_room)
    assert test_room.is_occupied is False

    # Verify payment schedule is deactivated
    session.refresh(schedule)
    assert schedule.is_active is False


def test_move_out_already_inactive_tenant(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test moving out already inactive tenant fails."""
    from tests.factories import TenantFactory

    tenant = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        is_active=False,
        move_out_date=date(2024, 6, 1),
    )

    move_out_data = {"move_out_date": date(2024, 12, 31).isoformat()}

    response = client.post(
        f"/api/tenants/{tenant.id}/move-out", headers=auth_headers, json=move_out_data
    )

    assert response.status_code == 400
    assert "already moved out" in response.json()["detail"].lower()


def test_move_out_tenant_not_found(client: TestClient, auth_headers: dict):
    """Test moving out non-existent tenant returns 404."""
    move_out_data = {"move_out_date": date(2024, 12, 31).isoformat()}
    response = client.post(
        "/api/tenants/non-existent-id/move-out",
        headers=auth_headers,
        json=move_out_data,
    )
    assert response.status_code == 404


def test_move_out_tenant_unauthorized(client: TestClient, test_tenant: Tenant):
    """Test moving out tenant without authentication fails."""
    move_out_data = {"move_out_date": date(2024, 12, 31).isoformat()}
    response = client.post(
        f"/api/tenants/{test_tenant.id}/move-out", json=move_out_data
    )
    assert response.status_code in [401, 403]


def test_move_out_other_landlord_tenant(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test moving out another landlord's tenant fails."""
    from tests.factories import (
        LandlordFactory,
        PropertyFactory,
        RoomFactory,
        TenantFactory,
    )

    other_landlord = LandlordFactory.create(session=session, email="other@example.com")
    other_property = PropertyFactory.create(
        session=session, landlord_id=other_landlord.id
    )
    other_room = RoomFactory.create(session=session, property_id=other_property.id)
    other_tenant = TenantFactory.create(
        session=session, room_id=other_room.id, is_active=True
    )

    move_out_data = {"move_out_date": date(2024, 12, 31).isoformat()}
    response = client.post(
        f"/api/tenants/{other_tenant.id}/move-out",
        headers=auth_headers,
        json=move_out_data,
    )
    assert response.status_code == 404


# =============================================================================
# Payment Schedule Tests
# =============================================================================


def test_get_tenant_schedule_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test getting tenant's payment schedule."""
    from tests.factories import TenantFactory, PaymentScheduleFactory

    tenant = TenantFactory.create(session=session, room_id=test_room.id)
    schedule = PaymentScheduleFactory.create(
        session=session, tenant_id=tenant.id, amount=1200000, due_day=5, window_days=7
    )

    response = client.get(f"/api/tenants/{tenant.id}/schedule", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == tenant.id
    assert data["amount"] == 1200000
    assert data["due_day"] == 5
    assert data["window_days"] == 7


def test_get_tenant_schedule_not_found(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test getting schedule for tenant without schedule returns 404."""
    from tests.factories import TenantFactory

    tenant = TenantFactory.create(session=session, room_id=test_room.id)

    response = client.get(f"/api/tenants/{tenant.id}/schedule", headers=auth_headers)
    assert response.status_code == 404


def test_create_tenant_schedule_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test creating payment schedule for tenant."""
    from tests.factories import TenantFactory
    from app.models.payment_schedule import PaymentSchedule

    tenant = TenantFactory.create(session=session, room_id=test_room.id)

    schedule_data = {
        "amount": 1500000,
        "frequency": "monthly",
        "due_day": 1,
        "window_days": 5,
        "start_date": date(2024, 1, 1).isoformat(),
    }

    response = client.post(
        f"/api/tenants/{tenant.id}/schedule", headers=auth_headers, json=schedule_data
    )

    assert response.status_code == 201
    data = response.json()
    assert data["tenant_id"] == tenant.id
    assert data["amount"] == 1500000
    assert data["frequency"] == "monthly"
    assert data["due_day"] == 1

    # Verify schedule was created in database
    schedule = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.tenant_id == tenant.id)
    ).first()
    assert schedule is not None


def test_create_tenant_schedule_already_exists(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test creating schedule when one already exists fails."""
    from tests.factories import TenantFactory, PaymentScheduleFactory

    tenant = TenantFactory.create(session=session, room_id=test_room.id)
    PaymentScheduleFactory.create(session=session, tenant_id=tenant.id, is_active=True)

    schedule_data = {
        "amount": 1500000,
        "frequency": "monthly",
        "due_day": 1,
        "window_days": 5,
        "start_date": date(2024, 1, 1).isoformat(),
    }

    response = client.post(
        f"/api/tenants/{tenant.id}/schedule", headers=auth_headers, json=schedule_data
    )

    assert response.status_code == 400
    assert "already has an active payment schedule" in response.json()["detail"].lower()


def test_create_tenant_schedule_not_found(client: TestClient, auth_headers: dict):
    """Test creating schedule for non-existent tenant returns 404."""
    schedule_data = {
        "amount": 1500000,
        "frequency": "monthly",
        "due_day": 1,
        "window_days": 5,
        "start_date": date(2024, 1, 1).isoformat(),
    }

    response = client.post(
        "/api/tenants/non-existent-id/schedule",
        headers=auth_headers,
        json=schedule_data,
    )
    assert response.status_code == 404


def test_update_tenant_schedule_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test updating tenant's payment schedule."""
    from tests.factories import TenantFactory, PaymentScheduleFactory

    tenant = TenantFactory.create(session=session, room_id=test_room.id)
    schedule = PaymentScheduleFactory.create(
        session=session, tenant_id=tenant.id, amount=1000000, due_day=1
    )

    update_data = {
        "amount": 1200000,
        "due_day": 5,
        "window_days": 10,
    }

    response = client.put(
        f"/api/tenants/{tenant.id}/schedule", headers=auth_headers, json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 1200000
    assert data["due_day"] == 5
    assert data["window_days"] == 10

    # Verify changes persisted
    session.refresh(schedule)
    assert schedule.amount == 1200000
    assert schedule.due_day == 5


def test_update_tenant_schedule_partial(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test partially updating payment schedule."""
    from tests.factories import TenantFactory, PaymentScheduleFactory

    tenant = TenantFactory.create(session=session, room_id=test_room.id)
    schedule = PaymentScheduleFactory.create(
        session=session, tenant_id=tenant.id, amount=1000000, due_day=1, window_days=5
    )

    update_data = {"amount": 1300000}  # Only update amount

    response = client.put(
        f"/api/tenants/{tenant.id}/schedule", headers=auth_headers, json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 1300000
    assert data["due_day"] == 1  # Unchanged
    assert data["window_days"] == 5  # Unchanged


def test_update_tenant_schedule_deactivate(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test deactivating payment schedule."""
    from tests.factories import TenantFactory, PaymentScheduleFactory

    tenant = TenantFactory.create(session=session, room_id=test_room.id)
    schedule = PaymentScheduleFactory.create(
        session=session, tenant_id=tenant.id, is_active=True
    )

    update_data = {"is_active": False}

    response = client.put(
        f"/api/tenants/{tenant.id}/schedule", headers=auth_headers, json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False

    session.refresh(schedule)
    assert schedule.is_active is False


def test_update_tenant_schedule_not_found(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test updating schedule for tenant without schedule returns 404."""
    from tests.factories import TenantFactory

    tenant = TenantFactory.create(session=session, room_id=test_room.id)

    update_data = {"amount": 1500000}
    response = client.put(
        f"/api/tenants/{tenant.id}/schedule", headers=auth_headers, json=update_data
    )
    assert response.status_code == 404


def test_schedule_routes_unauthorized(client: TestClient, test_tenant: Tenant):
    """Test schedule routes without authentication fail."""
    # Get schedule
    response = client.get(f"/api/tenants/{test_tenant.id}/schedule")
    assert response.status_code in [401, 403]

    # Create schedule
    schedule_data = {
        "amount": 1000000,
        "frequency": "monthly",
        "due_day": 1,
        "window_days": 5,
        "start_date": date(2024, 1, 1).isoformat(),
    }
    response = client.post(
        f"/api/tenants/{test_tenant.id}/schedule", json=schedule_data
    )
    assert response.status_code in [401, 403]

    # Update schedule
    response = client.put(
        f"/api/tenants/{test_tenant.id}/schedule", json={"amount": 1200000}
    )
    assert response.status_code in [401, 403]


# =============================================================================
# Portal Access Tests
# =============================================================================


def test_enable_tenant_portal_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test enabling portal access for tenant."""
    from tests.factories import TenantFactory

    tenant = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        name="Portal Tenant",
        email="portal@example.com",
        is_active=True,
    )

    response = client.post(
        f"/api/tenants/{tenant.id}/enable-portal", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "invite_token" in data
    assert data["tenant_id"] == tenant.id
    assert data["tenant_name"] == "Portal Tenant"
    assert data["tenant_email"] == "portal@example.com"
    assert data["property_name"] == test_property.name
    assert data["expires_in_days"] == 7
    assert data["has_existing_access"] is False


def test_enable_tenant_portal_no_email(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test enabling portal for tenant without email fails."""
    from tests.factories import TenantFactory

    tenant = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        name="No Email Tenant",
        email=None,  # No email
        is_active=True,
    )

    response = client.post(
        f"/api/tenants/{tenant.id}/enable-portal", headers=auth_headers
    )

    assert response.status_code == 400
    assert "email address" in response.json()["detail"].lower()


def test_enable_tenant_portal_inactive_tenant(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test enabling portal for inactive tenant fails."""
    from tests.factories import TenantFactory

    tenant = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        name="Inactive Tenant",
        email="inactive@example.com",
        is_active=False,
    )

    response = client.post(
        f"/api/tenants/{tenant.id}/enable-portal", headers=auth_headers
    )

    assert response.status_code == 400
    assert "inactive tenant" in response.json()["detail"].lower()


def test_enable_tenant_portal_not_found(client: TestClient, auth_headers: dict):
    """Test enabling portal for non-existent tenant returns 404."""
    response = client.post(
        "/api/tenants/non-existent-id/enable-portal", headers=auth_headers
    )
    assert response.status_code == 404


def test_disable_tenant_portal_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test disabling portal access for tenant."""
    from tests.factories import TenantFactory
    from app.core.security import get_password_hash

    tenant = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        name="Portal Disable Tenant",
        email="disable@example.com",
        password_hash=get_password_hash("password123"),  # Has portal access
    )

    response = client.delete(
        f"/api/tenants/{tenant.id}/disable-portal", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Portal access disabled"
    assert data["tenant_id"] == tenant.id

    # Verify password was removed
    session.refresh(tenant)
    assert tenant.password_hash is None


def test_disable_tenant_portal_no_access(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_room: Room,
):
    """Test disabling portal for tenant without access fails."""
    from tests.factories import TenantFactory

    tenant = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        name="No Portal Tenant",
        email="noportal@example.com",
        password_hash=None,  # No portal access
    )

    response = client.delete(
        f"/api/tenants/{tenant.id}/disable-portal", headers=auth_headers
    )

    assert response.status_code == 400
    assert "does not have portal access" in response.json()["detail"].lower()


def test_disable_tenant_portal_not_found(client: TestClient, auth_headers: dict):
    """Test disabling portal for non-existent tenant returns 404."""
    response = client.delete(
        "/api/tenants/non-existent-id/disable-portal", headers=auth_headers
    )
    assert response.status_code == 404


def test_portal_routes_unauthorized(client: TestClient, test_tenant: Tenant):
    """Test portal routes without authentication fail."""
    # Enable portal
    response = client.post(f"/api/tenants/{test_tenant.id}/enable-portal")
    assert response.status_code in [401, 403]

    # Disable portal
    response = client.delete(f"/api/tenants/{test_tenant.id}/disable-portal")
    assert response.status_code in [401, 403]


# =============================================================================
# Additional Edge Case Tests
# =============================================================================


def test_create_tenant_different_frequencies(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test creating tenant with different payment frequencies."""
    from app.models.payment_schedule import PaymentSchedule

    frequencies = ["monthly", "bi_monthly", "quarterly"]

    for freq in frequencies:
        # Create a new room for each frequency test
        from tests.factories import RoomFactory

        room = RoomFactory.create(
            session=session,
            property_id=test_property.id,
            name=f"Room {freq}",
            is_occupied=False,
        )

        tenant_data = {
            "room_id": room.id,
            "name": f"{freq} Tenant",
            "email": f"{freq}@example.com",
            "move_in_date": date(2024, 1, 1).isoformat(),
            "payment_frequency": freq,
        }

        response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)
        assert response.status_code == 201
        data = response.json()

        # Verify frequency was set correctly
        schedule = session.exec(
            select(PaymentSchedule).where(PaymentSchedule.tenant_id == data["id"])
        ).first()
        assert schedule is not None
        assert schedule.frequency.value == freq


def test_tenant_portal_response_includes_has_access(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test that tenant details include portal access status."""
    from tests.factories import TenantFactory
    from app.core.security import get_password_hash

    # Tenant with portal access
    tenant_with_access = TenantFactory.create(
        session=session,
        room_id=test_room.id,
        name="With Access",
        password_hash=get_password_hash("password123"),
    )

    response = client.get(f"/api/tenants/{tenant_with_access.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["has_portal_access"] is True

    # Tenant without portal access
    from tests.factories import RoomFactory

    room2 = RoomFactory.create(
        session=session, property_id=test_property.id, name="Room 2"
    )
    tenant_without_access = TenantFactory.create(
        session=session, room_id=room2.id, name="Without Access", password_hash=None
    )

    response = client.get(
        f"/api/tenants/{tenant_without_access.id}", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_portal_access"] is False


def test_list_tenants_pagination_not_implemented(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
):
    """Test that tenant list returns all tenants (pagination not implemented)."""
    from tests.factories import RoomFactory, TenantFactory

    # Create multiple tenants
    for i in range(5):
        room = RoomFactory.create(
            session=session,
            property_id=test_property.id,
            name=f"Room {i}",
            is_occupied=False,
        )
        TenantFactory.create(session=session, room_id=room.id, name=f"Tenant {i}")

    response = client.get("/api/tenants", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["tenants"]) == 5


def test_create_tenant_custom_due_day(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test creating tenant with custom payment due day."""
    from app.models.payment_schedule import PaymentSchedule

    tenant_data = {
        "room_id": test_room.id,
        "name": "Custom Due Day Tenant",
        "email": "customdue@example.com",
        "move_in_date": date(2024, 1, 1).isoformat(),
        "payment_due_day": 15,  # 15th of month
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)
    assert response.status_code == 201
    data = response.json()

    # Verify due day was set correctly
    schedule = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.tenant_id == data["id"])
    ).first()
    assert schedule is not None
    assert schedule.due_day == 15


def test_create_tenant_custom_window_days(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
    test_property: Property,
    test_room: Room,
):
    """Test creating tenant with custom payment window days."""
    from app.models.payment_schedule import PaymentSchedule

    tenant_data = {
        "room_id": test_room.id,
        "name": "Custom Window Tenant",
        "email": "customwindow@example.com",
        "move_in_date": date(2024, 1, 1).isoformat(),
        "payment_window_days": 10,  # 10 day window
    }

    response = client.post("/api/tenants", headers=auth_headers, json=tenant_data)
    assert response.status_code == 201
    data = response.json()

    # Verify window days was set correctly
    schedule = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.tenant_id == data["id"])
    ).first()
    assert schedule is not None
    assert schedule.window_days == 10

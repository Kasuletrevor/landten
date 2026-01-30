"""
Tests for analytics API routes.
Tests all dashboard analytics endpoints and helper functions.
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session
from dateutil.relativedelta import relativedelta

from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment import Payment, PaymentStatus
from app.core.security import create_access_token
from app.routers.analytics import (
    get_landlord_data,
    get_room_currency,
    get_tenant_room_id,
    calculate_month_stats,
    calculate_vacancy_stats,
    calculate_overdue_summary,
    calculate_trend_comparison,
)
from tests.factories import (
    LandlordFactory,
    PropertyFactory,
    RoomFactory,
    TenantFactory,
    PaymentFactory,
)


# =============================================================================
# GET /analytics/dashboard Tests
# =============================================================================


def test_get_dashboard_analytics_success(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test that dashboard analytics returns successfully with valid data."""
    # Setup: Create a complete scenario with properties, rooms, tenants, and payments
    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)
    room = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=500000,
        currency="UGX",
        is_occupied=True,
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    # Create a payment for current month (ON_TIME)
    today = date.today()
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=500000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
        paid_date=date(today.year, today.month, 1),
    )

    # Make request
    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Check all expected fields are present
    assert "current_month" in data
    assert "trend" in data
    assert "vacancy" in data
    assert "overdue_summary" in data
    assert "income_trend" in data
    assert "collection_trend" in data
    assert "vacancy_trend" in data
    assert "primary_currency" in data
    assert "currency_note" in data


def test_dashboard_includes_current_month_stats(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test that dashboard includes accurate current month statistics."""
    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)
    room = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=1000000,
        currency="UGX",
        is_occupied=True,
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()
    # Create expected payment
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.PENDING,
    )

    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    current_month = data["current_month"]
    assert current_month["expected"] == 1000000.0
    assert current_month["received"] == 0.0
    assert current_month["outstanding"] == 1000000.0
    assert current_month["collection_rate"] == 0.0


def test_dashboard_includes_three_month_trend(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test that dashboard includes 3-month trend data."""
    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)
    room = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=500000,
        is_occupied=True,
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()

    # Create payments for 3 months
    for i in range(3):
        month_date = today - relativedelta(months=i)
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount_due=500000,
            due_date=date(month_date.year, month_date.month, 1),
            status=PaymentStatus.ON_TIME if i == 0 else PaymentStatus.LATE,
        )

    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Should have exactly 3 months of trend data
    assert len(data["trend"]) == 3

    # Trend should be ordered oldest to newest
    months = [t["month"] for t in data["trend"]]
    assert months == sorted(months)


def test_dashboard_includes_vacancy_stats(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test that dashboard includes vacancy statistics."""
    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)

    # Create 3 rooms: 2 occupied, 1 vacant
    room1 = RoomFactory.create(
        session=session,
        property_id=prop.id,
        is_occupied=True,
    )
    room2 = RoomFactory.create(
        session=session,
        property_id=prop.id,
        is_occupied=True,
    )
    RoomFactory.create(
        session=session,
        property_id=prop.id,
        is_occupied=False,
    )

    # Assign tenants to occupied rooms
    TenantFactory.create(session=session, room_id=room1.id)
    TenantFactory.create(session=session, room_id=room2.id)

    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    vacancy = data["vacancy"]
    assert vacancy["total_rooms"] == 3
    assert vacancy["occupied"] == 2
    assert vacancy["vacant"] == 1
    assert vacancy["vacancy_rate"] == pytest.approx(33.3, abs=0.1)


def test_dashboard_includes_overdue_summary(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test that dashboard includes overdue payment summary."""
    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)
    room = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=1000000,
        is_occupied=True,
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()

    # Create overdue payments
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=today - timedelta(days=15),
        status=PaymentStatus.OVERDUE,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=500000,
        due_date=today - timedelta(days=30),
        status=PaymentStatus.OVERDUE,
    )

    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    overdue = data["overdue_summary"]
    assert overdue["count"] == 2
    assert overdue["total_amount"] == 1500000.0
    assert overdue["oldest_days"] == 30


def test_dashboard_includes_income_trend_comparison(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test that dashboard includes income trend comparison."""
    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)
    room = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=1000000,
        is_occupied=True,
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()

    # Previous month: partial payment
    prev_month = today - relativedelta(months=1)
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=date(prev_month.year, prev_month.month, 1),
        status=PaymentStatus.LATE,
    )

    # Current month: full payment
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )

    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    income_trend = data["income_trend"]
    assert income_trend["current_value"] == 1000000.0
    assert income_trend["previous_value"] == 1000000.0
    assert "change_percent" in income_trend
    assert "is_improvement" in income_trend


def test_dashboard_includes_collection_rate_trend(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test that dashboard includes collection rate trend."""
    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)
    room = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=1000000,
        is_occupied=True,
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()

    # Previous month: 50% collection rate
    prev_month = today - relativedelta(months=1)
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=date(prev_month.year, prev_month.month, 1),
        status=PaymentStatus.PENDING,
    )

    # Current month: 100% collection rate
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )

    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    collection_trend = data["collection_trend"]
    assert collection_trend["current_value"] == 100.0
    assert collection_trend["previous_value"] == 0.0
    assert collection_trend["is_improvement"] is True


def test_dashboard_uses_landlord_primary_currency(
    client: TestClient,
    session: Session,
    auth_headers: dict,
):
    """Test that dashboard uses landlord's primary currency for all amounts."""
    # Create landlord with USD as primary currency
    landlord = LandlordFactory.create(
        session=session,
        email="usd_landlord@test.com",
        primary_currency="USD",
    )
    token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
    headers = {"Authorization": f"Bearer {token}"}

    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=3750000,  # UGX amount
        currency="UGX",
        is_occupied=True,
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=3750000,  # UGX
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )

    response = client.get("/api/analytics/dashboard", headers=headers)

    assert response.status_code == 200
    data = response.json()

    # Should be in USD (3750000 UGX = 1000 USD at 1 USD = 3750 UGX)
    assert data["primary_currency"] == "USD"
    assert "USD" in data["currency_note"]
    # Expected should be ~1000 USD (converted from 3750000 UGX)
    assert data["current_month"]["expected"] == pytest.approx(1000.0, abs=1.0)


def test_dashboard_empty_landlord_returns_zeros(
    client: TestClient,
    session: Session,
):
    """Test that empty landlord (no properties) returns zero values."""
    # Create landlord with no properties
    landlord = LandlordFactory.create(session=session, email="empty@test.com")
    token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/analytics/dashboard", headers=headers)

    assert response.status_code == 200
    data = response.json()

    # All values should be zero
    assert data["current_month"]["expected"] == 0.0
    assert data["current_month"]["received"] == 0.0
    assert data["current_month"]["outstanding"] == 0.0
    assert data["current_month"]["collection_rate"] == 0.0
    assert data["vacancy"]["total_rooms"] == 0
    assert data["vacancy"]["occupied"] == 0
    assert data["vacancy"]["vacant"] == 0
    assert data["vacancy"]["vacancy_rate"] == 0.0
    assert data["overdue_summary"]["count"] == 0
    assert data["overdue_summary"]["total_amount"] == 0.0
    assert data["overdue_summary"]["oldest_days"] == 0


def test_dashboard_unauthorized_access_fails(client: TestClient):
    """Test that accessing dashboard without authentication fails."""
    response = client.get("/api/analytics/dashboard")

    assert response.status_code in [401, 403]


# =============================================================================
# Helper Function Tests - get_landlord_data
# =============================================================================


def test_get_landlord_data_returns_all_entities(session: Session):
    """Test that get_landlord_data returns all related entities."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(session=session, property_id=prop.id)
    tenant = TenantFactory.create(session=session, room_id=room.id)

    # Create payment
    payment = PaymentFactory.create(session=session, tenant_id=tenant.id)

    data = get_landlord_data(landlord.id, session)

    assert len(data["properties"]) == 1
    assert len(data["rooms"]) == 1
    assert len(data["tenants"]) == 1
    assert len(data["payments"]) == 1
    assert data["properties"][0].id == prop.id
    assert data["rooms"][0].id == room.id
    assert data["tenants"][0].id == tenant.id
    assert data["payments"][0].id == payment.id


def test_get_landlord_data_empty_landlord(session: Session):
    """Test get_landlord_data returns empty lists for landlord with no data."""
    landlord = LandlordFactory.create(session=session, email="empty2@test.com")

    data = get_landlord_data(landlord.id, session)

    assert data["properties"] == []
    assert data["rooms"] == []
    assert data["tenants"] == []
    assert data["payments"] == []


def test_get_landlord_data_multiple_properties(session: Session):
    """Test get_landlord_data with multiple properties."""
    landlord = LandlordFactory.create(session=session)

    # Create 2 properties with rooms
    prop1 = PropertyFactory.create(session=session, landlord_id=landlord.id)
    prop2 = PropertyFactory.create(session=session, landlord_id=landlord.id)

    room1 = RoomFactory.create(session=session, property_id=prop1.id)
    room2 = RoomFactory.create(session=session, property_id=prop2.id)

    tenant1 = TenantFactory.create(session=session, room_id=room1.id)
    tenant2 = TenantFactory.create(session=session, room_id=room2.id)

    PaymentFactory.create(session=session, tenant_id=tenant1.id)
    PaymentFactory.create(session=session, tenant_id=tenant2.id)

    data = get_landlord_data(landlord.id, session)

    assert len(data["properties"]) == 2
    assert len(data["rooms"]) == 2
    assert len(data["tenants"]) == 2
    assert len(data["payments"]) == 2


def test_get_landlord_data_ignores_other_landlords(session: Session):
    """Test that get_landlord_data only returns data for the specified landlord."""
    landlord1 = LandlordFactory.create(session=session, email="l1@test.com")
    landlord2 = LandlordFactory.create(session=session, email="l2@test.com")

    # Create data for landlord1
    prop1 = PropertyFactory.create(session=session, landlord_id=landlord1.id)
    room1 = RoomFactory.create(session=session, property_id=prop1.id)
    tenant1 = TenantFactory.create(session=session, room_id=room1.id)
    PaymentFactory.create(session=session, tenant_id=tenant1.id)

    # Create data for landlord2
    prop2 = PropertyFactory.create(session=session, landlord_id=landlord2.id)
    room2 = RoomFactory.create(session=session, property_id=prop2.id)
    tenant2 = TenantFactory.create(session=session, room_id=room2.id)
    PaymentFactory.create(session=session, tenant_id=tenant2.id)

    # Query for landlord1
    data = get_landlord_data(landlord1.id, session)

    assert len(data["properties"]) == 1
    assert data["properties"][0].id == prop1.id
    assert data["rooms"][0].id == room1.id


# =============================================================================
# Helper Function Tests - get_room_currency
# =============================================================================


def test_get_room_currency_returns_correct_currency(session: Session):
    """Test that get_room_currency returns the correct currency for a room."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(session=session, property_id=prop.id, currency="USD")

    rooms = [room]
    currency = get_room_currency(room.id, rooms)

    assert currency == "USD"


def test_get_room_currency_defaults_to_ugx_for_unknown_room():
    """Test that get_room_currency defaults to UGX for unknown room."""
    rooms = []
    currency = get_room_currency("non-existent-id", rooms)

    assert currency == "UGX"


def test_get_room_currency_multiple_rooms(session: Session):
    """Test get_room_currency with multiple rooms."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)

    room1 = RoomFactory.create(session=session, property_id=prop.id, currency="USD")
    room2 = RoomFactory.create(session=session, property_id=prop.id, currency="KES")

    rooms = [room1, room2]

    assert get_room_currency(room1.id, rooms) == "USD"
    assert get_room_currency(room2.id, rooms) == "KES"


# =============================================================================
# Helper Function Tests - get_tenant_room_id
# =============================================================================


def test_get_tenant_room_id_returns_correct_id(session: Session):
    """Test that get_tenant_room_id returns the correct room ID."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(session=session, property_id=prop.id)
    tenant = TenantFactory.create(session=session, room_id=room.id)

    tenants = [tenant]
    room_id = get_tenant_room_id(tenant.id, tenants)

    assert room_id == room.id


def test_get_tenant_room_id_returns_none_for_unknown_tenant():
    """Test that get_tenant_room_id returns None for unknown tenant."""
    tenants = []
    room_id = get_tenant_room_id("non-existent-id", tenants)

    assert room_id is None


def test_get_tenant_room_id_multiple_tenants(session: Session):
    """Test get_tenant_room_id with multiple tenants."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)

    room1 = RoomFactory.create(session=session, property_id=prop.id)
    room2 = RoomFactory.create(session=session, property_id=prop.id)

    tenant1 = TenantFactory.create(session=session, room_id=room1.id)
    tenant2 = TenantFactory.create(session=session, room_id=room2.id)

    tenants = [tenant1, tenant2]

    assert get_tenant_room_id(tenant1.id, tenants) == room1.id
    assert get_tenant_room_id(tenant2.id, tenants) == room2.id


# =============================================================================
# Helper Function Tests - calculate_month_stats
# =============================================================================


def test_calculate_month_stats_basic(session: Session):
    """Test basic month stats calculation."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=1000000, currency="UGX"
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()

    # Create payment
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )

    # Refresh data
    data = get_landlord_data(landlord.id, session)

    stats = calculate_month_stats(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
        today.year,
        today.month,
    )

    assert stats.expected == 1000000.0
    assert stats.received == 1000000.0
    assert stats.collection_rate == 100.0


def test_calculate_month_stats_partial_payments(session: Session):
    """Test month stats with partial payments."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room1 = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=1000000, currency="UGX"
    )
    room2 = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=500000, currency="UGX"
    )

    tenant1 = TenantFactory.create(session=session, room_id=room1.id)
    tenant2 = TenantFactory.create(session=session, room_id=room2.id)

    today = date.today()

    # One paid, one pending
    PaymentFactory.create(
        session=session,
        tenant_id=tenant1.id,
        amount_due=1000000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant2.id,
        amount_due=500000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.PENDING,
    )

    data = get_landlord_data(landlord.id, session)

    stats = calculate_month_stats(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
        today.year,
        today.month,
    )

    assert stats.expected == 1500000.0
    assert stats.received == 1000000.0
    assert stats.collection_rate == pytest.approx(66.7, abs=0.1)


def test_calculate_month_stats_currency_conversion(session: Session):
    """Test month stats with currency conversion."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)

    # Room in USD
    room = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=1000, currency="USD"
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()

    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )

    data = get_landlord_data(landlord.id, session)

    # Convert to UGX (1 USD = 3750 UGX)
    stats = calculate_month_stats(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",  # Target currency
        today.year,
        today.month,
    )

    # 1000 USD should convert to 3,750,000 UGX
    assert stats.expected == 3750000.0
    assert stats.received == 3750000.0


def test_calculate_month_stats_no_payments(session: Session):
    """Test month stats with no payments."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    RoomFactory.create(session=session, property_id=prop.id)

    data = get_landlord_data(landlord.id, session)

    stats = calculate_month_stats(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
        2024,
        1,
    )

    assert stats.expected == 0.0
    assert stats.received == 0.0
    assert stats.collection_rate == 0.0


def test_calculate_month_stats_different_statuses(session: Session):
    """Test month stats with different payment statuses."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)

    room = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=1000000, currency="UGX"
    )

    # Create tenants with different payment statuses
    statuses = [
        PaymentStatus.ON_TIME,
        PaymentStatus.LATE,
        PaymentStatus.PENDING,
        PaymentStatus.OVERDUE,
    ]

    today = date.today()

    for i, status in enumerate(statuses):
        room_i = RoomFactory.create(
            session=session,
            property_id=prop.id,
            rent_amount=1000000,
            currency="UGX",
        )
        tenant = TenantFactory.create(session=session, room_id=room_i.id)
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount_due=1000000,
            due_date=date(today.year, today.month, 1),
            status=status,
        )

    data = get_landlord_data(landlord.id, session)

    stats = calculate_month_stats(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
        today.year,
        today.month,
    )

    # ON_TIME and LATE count as received
    assert stats.expected == 4000000.0
    assert stats.received == 2000000.0
    assert stats.collection_rate == 50.0


def test_calculate_month_stats_date_boundaries(session: Session):
    """Test month stats with date boundaries."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=1000000, currency="UGX"
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    # Create payments for different months
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=date(2024, 1, 15),
        status=PaymentStatus.ON_TIME,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=date(2024, 2, 15),
        status=PaymentStatus.ON_TIME,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=date(2024, 3, 15),
        status=PaymentStatus.ON_TIME,
    )

    data = get_landlord_data(landlord.id, session)

    # Test January
    jan_stats = calculate_month_stats(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
        2024,
        1,
    )
    assert jan_stats.expected == 1000000.0

    # Test February
    feb_stats = calculate_month_stats(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
        2024,
        2,
    )
    assert feb_stats.expected == 1000000.0

    # Test March
    mar_stats = calculate_month_stats(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
        2024,
        3,
    )
    assert mar_stats.expected == 1000000.0


# =============================================================================
# Helper Function Tests - calculate_vacancy_stats
# =============================================================================


def test_calculate_vacancy_stats_all_occupied(session: Session):
    """Test vacancy stats when all rooms are occupied."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)

    for i in range(3):
        RoomFactory.create(session=session, property_id=prop.id, is_occupied=True)

    data = get_landlord_data(landlord.id, session)
    stats = calculate_vacancy_stats(data["rooms"])

    assert stats.total_rooms == 3
    assert stats.occupied == 3
    assert stats.vacant == 0
    assert stats.vacancy_rate == 0.0


def test_calculate_vacancy_stats_all_vacant(session: Session):
    """Test vacancy stats when all rooms are vacant."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)

    for i in range(5):
        RoomFactory.create(session=session, property_id=prop.id, is_occupied=False)

    data = get_landlord_data(landlord.id, session)
    stats = calculate_vacancy_stats(data["rooms"])

    assert stats.total_rooms == 5
    assert stats.occupied == 0
    assert stats.vacant == 5
    assert stats.vacancy_rate == 100.0


def test_calculate_vacancy_stats_mixed(session: Session):
    """Test vacancy stats with mix of occupied and vacant rooms."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)

    # 3 occupied, 2 vacant
    for i in range(3):
        RoomFactory.create(session=session, property_id=prop.id, is_occupied=True)
    for i in range(2):
        RoomFactory.create(session=session, property_id=prop.id, is_occupied=False)

    data = get_landlord_data(landlord.id, session)
    stats = calculate_vacancy_stats(data["rooms"])

    assert stats.total_rooms == 5
    assert stats.occupied == 3
    assert stats.vacant == 2
    assert stats.vacancy_rate == 40.0


def test_calculate_vacancy_stats_no_rooms():
    """Test vacancy stats with no rooms."""
    stats = calculate_vacancy_stats([])

    assert stats.total_rooms == 0
    assert stats.occupied == 0
    assert stats.vacant == 0
    assert stats.vacancy_rate == 0.0


def test_calculate_vacancy_stats_multiple_properties(session: Session):
    """Test vacancy stats across multiple properties."""
    landlord = LandlordFactory.create(session=session)

    prop1 = PropertyFactory.create(session=session, landlord_id=landlord.id)
    prop2 = PropertyFactory.create(session=session, landlord_id=landlord.id)

    # Property 1: 2 occupied, 1 vacant
    for i in range(2):
        RoomFactory.create(session=session, property_id=prop1.id, is_occupied=True)
    RoomFactory.create(session=session, property_id=prop1.id, is_occupied=False)

    # Property 2: 1 occupied, 2 vacant
    RoomFactory.create(session=session, property_id=prop2.id, is_occupied=True)
    for i in range(2):
        RoomFactory.create(session=session, property_id=prop2.id, is_occupied=False)

    data = get_landlord_data(landlord.id, session)
    stats = calculate_vacancy_stats(data["rooms"])

    assert stats.total_rooms == 6
    assert stats.occupied == 3
    assert stats.vacant == 3
    assert stats.vacancy_rate == 50.0


# =============================================================================
# Helper Function Tests - calculate_overdue_summary
# =============================================================================


def test_calculate_overdue_summary_basic(session: Session):
    """Test basic overdue summary calculation."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=1000000, currency="UGX"
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()

    # Create overdue payment
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        due_date=today - timedelta(days=10),
        status=PaymentStatus.OVERDUE,
    )

    data = get_landlord_data(landlord.id, session)
    summary = calculate_overdue_summary(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
    )

    assert summary.count == 1
    assert summary.total_amount == 1000000.0
    assert summary.oldest_days == 10


def test_calculate_overdue_summary_multiple_overdue(session: Session):
    """Test overdue summary with multiple overdue payments."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)

    today = date.today()

    # Create multiple tenants with overdue payments
    amounts_and_days = [
        (500000, 5),
        (1000000, 15),
        (750000, 30),
    ]

    for amount, days in amounts_and_days:
        room = RoomFactory.create(
            session=session,
            property_id=prop.id,
            rent_amount=amount,
            currency="UGX",
        )
        tenant = TenantFactory.create(session=session, room_id=room.id)
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount_due=amount,
            due_date=today - timedelta(days=days),
            status=PaymentStatus.OVERDUE,
        )

    data = get_landlord_data(landlord.id, session)
    summary = calculate_overdue_summary(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
    )

    assert summary.count == 3
    assert summary.total_amount == 2250000.0
    assert summary.oldest_days == 30


def test_calculate_overdue_summary_no_overdue(session: Session):
    """Test overdue summary with no overdue payments."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(session=session, property_id=prop.id)
    tenant = TenantFactory.create(session=session, room_id=room.id)

    # Create non-overdue payments
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        status=PaymentStatus.ON_TIME,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000000,
        status=PaymentStatus.PENDING,
    )

    data = get_landlord_data(landlord.id, session)
    summary = calculate_overdue_summary(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
    )

    assert summary.count == 0
    assert summary.total_amount == 0.0
    assert summary.oldest_days == 0


def test_calculate_overdue_summary_currency_conversion(session: Session):
    """Test overdue summary with currency conversion."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(
        session=session, property_id=prop.id, rent_amount=1000, currency="USD"
    )
    tenant = TenantFactory.create(session=session, room_id=room.id)

    today = date.today()

    PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        amount_due=1000,
        due_date=today - timedelta(days=20),
        status=PaymentStatus.OVERDUE,
    )

    data = get_landlord_data(landlord.id, session)

    # Convert to UGX
    summary = calculate_overdue_summary(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
    )

    # 1000 USD = 3,750,000 UGX
    assert summary.count == 1
    assert summary.total_amount == 3750000.0
    assert summary.oldest_days == 20


def test_calculate_overdue_summary_mixed_statuses(session: Session):
    """Test overdue summary ignores non-overdue payments."""
    landlord = LandlordFactory.create(session=session)
    prop = PropertyFactory.create(session=session, landlord_id=landlord.id)

    # Create payments with different statuses
    statuses = [
        PaymentStatus.OVERDUE,
        PaymentStatus.ON_TIME,
        PaymentStatus.LATE,
        PaymentStatus.PENDING,
        PaymentStatus.OVERDUE,
    ]

    today = date.today()

    for i, status in enumerate(statuses):
        room = RoomFactory.create(
            session=session,
            property_id=prop.id,
            rent_amount=1000000,
            currency="UGX",
        )
        tenant = TenantFactory.create(session=session, room_id=room.id)
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount_due=1000000,
            due_date=today - timedelta(days=(i + 1) * 5)
            if status == PaymentStatus.OVERDUE
            else today,
            status=status,
        )

    data = get_landlord_data(landlord.id, session)
    summary = calculate_overdue_summary(
        data["payments"],
        data["tenants"],
        data["rooms"],
        "UGX",
    )

    # Only 2 overdue payments
    assert summary.count == 2
    assert summary.total_amount == 2000000.0


# =============================================================================
# Helper Function Tests - calculate_trend_comparison
# =============================================================================


def test_calculate_trend_comparison_improvement():
    """Test trend comparison when metric improves."""
    trend = calculate_trend_comparison(
        current_value=100.0,
        previous_value=80.0,
        higher_is_better=True,
    )

    assert trend.current_value == 100.0
    assert trend.previous_value == 80.0
    assert trend.change_percent == 25.0
    assert trend.is_improvement is True


def test_calculate_trend_comparison_decline():
    """Test trend comparison when metric declines."""
    trend = calculate_trend_comparison(
        current_value=80.0,
        previous_value=100.0,
        higher_is_better=True,
    )

    assert trend.change_percent == -20.0
    assert trend.is_improvement is False


def test_calculate_trend_comparison_lower_is_better_improvement():
    """Test trend comparison when lower is better and metric improves."""
    # For vacancy rate, lower is better
    trend = calculate_trend_comparison(
        current_value=10.0,
        previous_value=20.0,
        higher_is_better=False,  # Lower is better
    )

    assert trend.change_percent == -50.0
    assert trend.is_improvement is True  # Decreased vacancy is good


def test_calculate_trend_comparison_lower_is_better_decline():
    """Test trend comparison when lower is better and metric declines."""
    trend = calculate_trend_comparison(
        current_value=20.0,
        previous_value=10.0,
        higher_is_better=False,
    )

    assert trend.change_percent == 100.0
    assert trend.is_improvement is False  # Increased vacancy is bad


def test_calculate_trend_comparison_no_change():
    """Test trend comparison when no change."""
    trend = calculate_trend_comparison(
        current_value=100.0,
        previous_value=100.0,
        higher_is_better=True,
    )

    assert trend.change_percent == 0.0
    assert trend.is_improvement is False  # No change is not an improvement


def test_calculate_trend_comparison_zero_previous():
    """Test trend comparison when previous value is zero."""
    trend = calculate_trend_comparison(
        current_value=100.0,
        previous_value=0.0,
        higher_is_better=True,
    )

    assert trend.change_percent == 100.0
    assert trend.is_improvement is True


def test_calculate_trend_comparison_zero_current():
    """Test trend comparison when current value is zero."""
    trend = calculate_trend_comparison(
        current_value=0.0,
        previous_value=100.0,
        higher_is_better=True,
    )

    assert trend.change_percent == -100.0
    assert trend.is_improvement is False


def test_calculate_trend_comparison_both_zero():
    """Test trend comparison when both values are zero."""
    trend = calculate_trend_comparison(
        current_value=0.0,
        previous_value=0.0,
        higher_is_better=True,
    )

    assert trend.change_percent == 0.0
    assert trend.is_improvement is False


# =============================================================================
# Integration Tests - Complex Scenarios
# =============================================================================


def test_dashboard_multiple_properties_with_rooms(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test dashboard with landlord having multiple properties with rooms."""
    # Create 2 properties
    prop1 = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="Property One"
    )
    prop2 = PropertyFactory.create(
        session=session, landlord_id=auth_landlord.id, name="Property Two"
    )

    # Property 1: 3 rooms (2 occupied, 1 vacant)
    room1 = RoomFactory.create(
        session=session,
        property_id=prop1.id,
        rent_amount=500000,
        is_occupied=True,
    )
    room2 = RoomFactory.create(
        session=session,
        property_id=prop1.id,
        rent_amount=600000,
        is_occupied=True,
    )
    RoomFactory.create(
        session=session,
        property_id=prop1.id,
        rent_amount=700000,
        is_occupied=False,
    )

    # Property 2: 2 rooms (1 occupied, 1 vacant)
    room4 = RoomFactory.create(
        session=session,
        property_id=prop2.id,
        rent_amount=800000,
        is_occupied=True,
    )
    RoomFactory.create(
        session=session,
        property_id=prop2.id,
        rent_amount=900000,
        is_occupied=False,
    )

    # Create tenants
    tenant1 = TenantFactory.create(session=session, room_id=room1.id)
    tenant2 = TenantFactory.create(session=session, room_id=room2.id)
    tenant4 = TenantFactory.create(session=session, room_id=room4.id)

    today = date.today()

    # Create payments for current month
    PaymentFactory.create(
        session=session,
        tenant_id=tenant1.id,
        amount_due=500000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant2.id,
        amount_due=600000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.PENDING,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant4.id,
        amount_due=800000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )

    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Verify totals across all properties
    assert data["current_month"]["expected"] == 1900000.0  # 500k + 600k + 800k
    assert data["current_month"]["received"] == 1300000.0  # 500k + 800k
    assert data["vacancy"]["total_rooms"] == 5
    assert data["vacancy"]["occupied"] == 3
    assert data["vacancy"]["vacant"] == 2


def test_dashboard_multiple_currencies(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test dashboard with payments in different currencies."""
    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)

    # Room in USD
    room1 = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=1000,
        currency="USD",
        is_occupied=True,
    )

    # Room in KES
    room2 = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=100000,
        currency="KES",
        is_occupied=True,
    )

    # Room in UGX
    room3 = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=1000000,
        currency="UGX",
        is_occupied=True,
    )

    tenant1 = TenantFactory.create(session=session, room_id=room1.id)
    tenant2 = TenantFactory.create(session=session, room_id=room2.id)
    tenant3 = TenantFactory.create(session=session, room_id=room3.id)

    today = date.today()

    PaymentFactory.create(
        session=session,
        tenant_id=tenant1.id,
        amount_due=1000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant2.id,
        amount_due=100000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant3.id,
        amount_due=1000000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )

    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # All amounts should be converted to UGX (landlord's primary currency)
    # 1000 USD = 3,750,000 UGX
    # 100,000 KES = 2,900,000 UGX
    # 1,000,000 UGX = 1,000,000 UGX
    # Total = 7,650,000 UGX
    expected_total = 3750000.0 + 2900000.0 + 1000000.0
    assert data["current_month"]["expected"] == pytest.approx(expected_total, abs=100.0)
    assert data["current_month"]["collection_rate"] == 100.0


def test_dashboard_complete_with_overdue_and_vacancy(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    """Test dashboard with complete scenario including overdue and vacancies."""
    prop = PropertyFactory.create(session=session, landlord_id=auth_landlord.id)

    # 4 rooms: 2 occupied, 2 vacant
    room1 = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=1000000,
        is_occupied=True,
    )
    room2 = RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=800000,
        is_occupied=True,
    )
    RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=750000,
        is_occupied=False,
    )
    RoomFactory.create(
        session=session,
        property_id=prop.id,
        rent_amount=900000,
        is_occupied=False,
    )

    tenant1 = TenantFactory.create(session=session, room_id=room1.id)
    tenant2 = TenantFactory.create(session=session, room_id=room2.id)

    today = date.today()

    # Current month payments
    PaymentFactory.create(
        session=session,
        tenant_id=tenant1.id,
        amount_due=1000000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.ON_TIME,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant2.id,
        amount_due=800000,
        due_date=date(today.year, today.month, 1),
        status=PaymentStatus.PENDING,
    )

    # Overdue payments from previous month
    PaymentFactory.create(
        session=session,
        tenant_id=tenant1.id,
        amount_due=1000000,
        due_date=today - timedelta(days=45),
        status=PaymentStatus.OVERDUE,
    )
    PaymentFactory.create(
        session=session,
        tenant_id=tenant2.id,
        amount_due=800000,
        due_date=today - timedelta(days=30),
        status=PaymentStatus.OVERDUE,
    )

    response = client.get("/api/analytics/dashboard", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Current month: 1.8M expected, 1M received
    assert data["current_month"]["expected"] == 1800000.0
    assert data["current_month"]["received"] == 1000000.0
    assert data["current_month"]["outstanding"] == 800000.0

    # Vacancy: 4 rooms, 2 occupied, 2 vacant = 50% vacancy
    assert data["vacancy"]["total_rooms"] == 4
    assert data["vacancy"]["vacant"] == 2
    assert data["vacancy"]["vacancy_rate"] == 50.0

    # Overdue: 2 payments totaling 1.8M, oldest is 45 days
    assert data["overdue_summary"]["count"] == 2
    assert data["overdue_summary"]["total_amount"] == 1800000.0
    assert data["overdue_summary"]["oldest_days"] == 45

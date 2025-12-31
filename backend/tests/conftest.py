import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.core.database import get_session
from app.models.tenant import Tenant
from app.models.property import Property
from app.models.room import Room
from app.models.landlord import Landlord
from app.core.security import get_password_hash


# Use in-memory SQLite database for tests
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="tenant_data")
def tenant_data_fixture(session: Session):
    # Create landlord
    landlord = Landlord(
        name="Test Landlord",
        email="landlord@test.com",
        password_hash=get_password_hash("password123"),
        phone="555-0000",
    )
    session.add(landlord)
    session.commit()
    session.refresh(landlord)

    # Create property
    prop = Property(
        name="Test Property", address="123 Test St", landlord_id=landlord.id
    )
    session.add(prop)
    session.commit()
    session.refresh(prop)

    # Create room
    room = Room(name="Unit 101", rent_amount=1000, property_id=prop.id)
    session.add(room)
    session.commit()
    session.refresh(room)

    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        email="tenant@test.com",
        phone="555-1234",
        room_id=room.id,
        is_active=True,
        move_in_date=date(2024, 1, 1),
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    return {"landlord": landlord, "property": prop, "room": room, "tenant": tenant}

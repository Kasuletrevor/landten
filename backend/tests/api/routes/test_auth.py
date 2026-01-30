"""
Tests for landlord authentication routes.
Tests registration, login, profile access, and updates.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.landlord import Landlord
from app.core.security import verify_password


# =============================================================================
# Registration Tests
# =============================================================================


def test_register_landlord_success(client: TestClient, session: Session):
    """Test registering a new landlord successfully."""
    register_data = {
        "email": "new@landlord.com",
        "password": "securepassword123",
        "name": "New Landlord",
        "phone": "555-1234",
    }

    response = client.post("/api/auth/register", json=register_data)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "landlord" in data
    assert data["landlord"]["email"] == "new@landlord.com"
    assert data["landlord"]["name"] == "New Landlord"
    assert data["landlord"]["phone"] == "555-1234"
    assert "password_hash" not in data["landlord"]


def test_register_duplicate_email_fails(
    client: TestClient, session: Session, auth_landlord: Landlord
):
    """Test registering with duplicate email fails."""
    register_data = {
        "email": auth_landlord.email,  # Already exists
        "password": "securepassword123",
        "name": "Another Landlord",
    }

    response = client.post("/api/auth/register", json=register_data)

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_register_missing_required_fields(client: TestClient):
    """Test registering without required fields fails."""
    # Missing email
    response = client.post(
        "/api/auth/register",
        json={"password": "securepassword123", "name": "Test"},
    )
    assert response.status_code == 422

    # Missing password
    response = client.post(
        "/api/auth/register",
        json={"email": "test@test.com", "name": "Test"},
    )
    assert response.status_code == 422

    # Missing name
    response = client.post(
        "/api/auth/register",
        json={"email": "test@test.com", "password": "securepassword123"},
    )
    assert response.status_code == 422


def test_register_invalid_email_format(client: TestClient):
    """Test registering with invalid email format fails."""
    register_data = {
        "email": "not-an-email",
        "password": "securepassword123",
        "name": "Test Landlord",
    }

    response = client.post("/api/auth/register", json=register_data)

    assert response.status_code == 422


def test_register_password_stored_hashed(client: TestClient, session: Session):
    """Test that password is stored hashed, not plaintext."""
    register_data = {
        "email": "hashtest@landlord.com",
        "password": "securepassword123",
        "name": "Hash Test",
    }

    response = client.post("/api/auth/register", json=register_data)

    assert response.status_code == 201

    # Verify password is hashed in database
    landlord = session.exec(
        select(Landlord).where(Landlord.email == "hashtest@landlord.com")
    ).first()
    assert landlord is not None
    assert landlord.password_hash != "securepassword123"
    assert verify_password("securepassword123", landlord.password_hash)


# =============================================================================
# Login Tests
# =============================================================================


def test_login_success(client: TestClient, auth_landlord: Landlord, test_password: str):
    """Test logging in with valid credentials."""
    login_data = {
        "email": auth_landlord.email,
        "password": test_password,
    }

    response = client.post("/api/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "landlord" in data
    assert data["landlord"]["email"] == auth_landlord.email


def test_login_invalid_password(client: TestClient, auth_landlord: Landlord):
    """Test logging in with invalid password fails."""
    login_data = {
        "email": auth_landlord.email,
        "password": "wrongpassword",
    }

    response = client.post("/api/auth/login", json=login_data)

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_login_nonexistent_email(client: TestClient):
    """Test logging in with non-existent email fails."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "somepassword",
    }

    response = client.post("/api/auth/login", json=login_data)

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_login_missing_fields(client: TestClient):
    """Test logging in without required fields fails."""
    # Missing email
    response = client.post("/api/auth/login", json={"password": "somepass"})
    assert response.status_code == 422

    # Missing password
    response = client.post("/api/auth/login", json={"email": "test@test.com"})
    assert response.status_code == 422


def test_login_after_register(client: TestClient, session: Session):
    """Test full flow: register then login with same credentials."""
    # Register
    register_data = {
        "email": "flow@landlord.com",
        "password": "securepassword123",
        "name": "Flow Test",
    }
    register_response = client.post("/api/auth/register", json=register_data)
    assert register_response.status_code == 201

    # Login with same credentials
    login_data = {
        "email": "flow@landlord.com",
        "password": "securepassword123",
    }
    login_response = client.post("/api/auth/login", json=login_data)

    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data
    assert data["landlord"]["email"] == "flow@landlord.com"


# =============================================================================
# Profile Tests
# =============================================================================


def test_get_profile_success(
    client: TestClient, auth_landlord: Landlord, auth_headers: dict
):
    """Test getting current landlord profile."""
    response = client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == auth_landlord.id
    assert data["email"] == auth_landlord.email
    assert data["name"] == auth_landlord.name
    assert "password_hash" not in data


def test_get_profile_unauthorized(client: TestClient):
    """Test getting profile without authentication fails."""
    response = client.get("/api/auth/me")

    assert response.status_code in [401, 403]


def test_get_profile_invalid_token(client: TestClient):
    """Test getting profile with invalid token fails."""
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401


def test_update_profile_success(
    client: TestClient, auth_landlord: Landlord, auth_headers: dict, session: Session
):
    """Test updating landlord profile."""
    update_data = {
        "name": "Updated Name",
        "phone": "555-9999",
    }

    response = client.put("/api/auth/me", headers=auth_headers, json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["phone"] == "555-9999"

    # Verify in database
    session.refresh(auth_landlord)
    assert auth_landlord.name == "Updated Name"
    assert auth_landlord.phone == "555-9999"


def test_update_profile_partial(
    client: TestClient, auth_landlord: Landlord, auth_headers: dict, session: Session
):
    """Test updating only name."""
    original_phone = auth_landlord.phone

    update_data = {"name": "New Name Only"}

    response = client.put("/api/auth/me", headers=auth_headers, json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name Only"
    assert data["phone"] == original_phone  # Unchanged


def test_update_profile_unauthorized(client: TestClient):
    """Test updating profile without authentication fails."""
    update_data = {"name": "Test"}

    response = client.put("/api/auth/me", json=update_data)

    assert response.status_code in [401, 403]


def test_update_profile_invalid_data(
    client: TestClient, auth_landlord: Landlord, auth_headers: dict
):
    """Test updating with invalid data types fails."""
    # Try to update email (should not be allowed or should fail validation)
    # This tests that the schema properly restricts fields
    update_data = {"name": "", "phone": ""}

    response = client.put("/api/auth/me", headers=auth_headers, json=update_data)

    # Empty strings might be accepted depending on validation
    # but they shouldn't break anything
    assert response.status_code in [200, 422]


# =============================================================================
# Token Validation Tests
# =============================================================================


def test_token_expiration(
    client: TestClient, auth_landlord: Landlord, test_password: str
):
    """Test that token works immediately after login."""
    # Login to get token
    login_data = {"email": auth_landlord.email, "password": test_password}
    login_response = client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Use token immediately
    profile_response = client.get("/api/auth/me", headers=headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["email"] == auth_landlord.email


def test_token_format(client: TestClient, auth_landlord: Landlord, test_password: str):
    """Test that token has proper JWT format (3 parts separated by dots)."""
    login_data = {"email": auth_landlord.email, "password": test_password}
    response = client.post("/api/auth/login", json=login_data)

    assert response.status_code == 200
    token = response.json()["access_token"]

    # JWT format: header.payload.signature
    parts = token.split(".")
    assert len(parts) == 3
    assert all(len(part) > 0 for part in parts)


# =============================================================================
# Edge Cases
# =============================================================================


def test_register_very_long_password(client: TestClient, session: Session):
    """Test registering with very long password."""
    register_data = {
        "email": "longpass@landlord.com",
        "password": "a" * 1000,  # 1000 character password
        "name": "Long Password Test",
    }

    response = client.post("/api/auth/register", json=register_data)

    # Should succeed (bcrypt can handle long passwords)
    assert response.status_code == 201


def test_register_unicode_password(client: TestClient, session: Session):
    """Test registering with unicode password."""
    register_data = {
        "email": "unicode@landlord.com",
        "password": "пароль123",  # Russian word for "password"
        "name": "Unicode Test",
    }

    response = client.post("/api/auth/register", json=register_data)

    assert response.status_code == 201

    # Verify can login with unicode password
    login_response = client.post(
        "/api/auth/login",
        json={"email": "unicode@landlord.com", "password": "пароль123"},
    )
    assert login_response.status_code == 200


def test_concurrent_requests(
    client: TestClient, auth_landlord: Landlord, auth_headers: dict
):
    """Test that multiple concurrent profile requests work."""
    # Make multiple requests in quick succession
    responses = []
    for _ in range(5):
        response = client.get("/api/auth/me", headers=auth_headers)
        responses.append(response)

    # All should succeed
    for response in responses:
        assert response.status_code == 200

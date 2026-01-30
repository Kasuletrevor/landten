"""
Tests for security module - password hashing, JWT tokens, and authentication dependencies.
"""

import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    get_current_landlord,
    get_current_tenant,
)
from app.core.config import settings
from app.models.landlord import Landlord
from app.models.tenant import Tenant


# =============================================================================
# Password Hashing Tests
# =============================================================================


class TestPasswordHashing:
    """Test password hashing and verification functions."""

    def test_get_password_hash_returns_string(self):
        """Test that password hashing returns a string."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_get_password_hash_different_each_time(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct_password(self):
        """Test verifying correct password against hash."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self):
        """Test verifying incorrect password against hash."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self):
        """Test verifying empty password."""
        password = ""
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_verify_password_unicode_characters(self):
        """Test password with unicode characters."""
        password = "пароль123"  # Russian word for password
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False


# =============================================================================
# JWT Token Tests
# =============================================================================


class TestJWTToken:
    """Test JWT token creation, decoding, and validation."""

    def test_create_access_token_returns_string(self):
        """Test token creation returns a string."""
        data = {"sub": "test-id", "type": "landlord"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_data(self):
        """Test token contains the original data."""
        data = {"sub": "test-id", "type": "landlord", "custom": "value"}
        token = create_access_token(data)
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert decoded["sub"] == "test-id"
        assert decoded["type"] == "landlord"
        assert decoded["custom"] == "value"

    def test_create_access_token_has_expiration(self):
        """Test token includes expiration time."""
        data = {"sub": "test-id", "type": "landlord"}
        token = create_access_token(data)
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert "exp" in decoded
        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

        # Should be roughly ACCESS_TOKEN_EXPIRE_MINUTES in the future
        expected_exp = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        time_diff = abs((exp_datetime - expected_exp).total_seconds())
        assert time_diff < 5  # Within 5 seconds

    def test_create_access_token_custom_expiry(self):
        """Test token with custom expiration time."""
        data = {"sub": "test-id", "type": "landlord"}
        custom_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta=custom_delta)
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + custom_delta
        time_diff = abs((exp_datetime - expected_exp).total_seconds())
        assert time_diff < 5

    def test_decode_token_valid(self):
        """Test decoding a valid token."""
        data = {"sub": "test-id", "type": "landlord"}
        token = create_access_token(data)
        decoded = decode_token(token)

        assert decoded is not None
        assert decoded["sub"] == "test-id"
        assert decoded["type"] == "landlord"

    def test_decode_token_invalid(self):
        """Test decoding an invalid token."""
        invalid_token = "invalid.token.here"
        decoded = decode_token(invalid_token)

        assert decoded is None

    def test_decode_token_expired(self):
        """Test decoding an expired token."""
        data = {"sub": "test-id", "type": "landlord"}
        # Create token that expires in -1 second (already expired)
        expired_token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        decoded = decode_token(expired_token)

        assert decoded is None

    def test_decode_token_wrong_secret(self):
        """Test decoding with wrong secret key."""
        data = {"sub": "test-id", "type": "landlord"}
        token = create_access_token(data)

        # Try to decode with wrong secret
        try:
            jwt.decode(token, "wrong-secret", algorithms=[settings.ALGORITHM])
            assert False, "Should have raised JWTError"
        except JWTError:
            pass  # Expected

    def test_decode_token_tampered(self):
        """Test decoding a tampered token."""
        data = {"sub": "test-id", "type": "landlord"}
        token = create_access_token(data)

        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        decoded = decode_token(tampered)

        assert decoded is None


# =============================================================================
# Authentication Dependency Tests
# =============================================================================


class TestCurrentLandlordDependency:
    """Test get_current_landlord dependency."""

    @pytest.mark.asyncio
    async def test_get_current_landlord_valid(self, session, auth_landlord):
        """Test getting current landlord with valid token."""
        # Create valid landlord token
        token = create_access_token(data={"sub": auth_landlord.id, "type": "landlord"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        landlord = await get_current_landlord(credentials=credentials, session=session)

        assert landlord.id == auth_landlord.id
        assert landlord.email == auth_landlord.email

    @pytest.mark.asyncio
    async def test_get_current_landlord_invalid_token(self, session):
        """Test getting landlord with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.token.here"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_landlord(credentials=credentials, session=session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_landlord_wrong_type(self, session, auth_landlord):
        """Test getting landlord with tenant type token."""
        token = create_access_token(data={"sub": auth_landlord.id, "type": "tenant"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_landlord(credentials=credentials, session=session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_landlord_no_sub(self, session):
        """Test getting landlord with token missing sub claim."""
        token = create_access_token(data={"type": "landlord"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_landlord(credentials=credentials, session=session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_landlord_nonexistent(self, session):
        """Test getting landlord with token for non-existent user."""
        token = create_access_token(data={"sub": "nonexistent-id", "type": "landlord"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_landlord(credentials=credentials, session=session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_landlord_backwards_compat(self, session, auth_landlord):
        """Test getting landlord with token without type (backwards compatibility)."""
        token = create_access_token(data={"sub": auth_landlord.id})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        landlord = await get_current_landlord(credentials=credentials, session=session)

        assert landlord.id == auth_landlord.id


class TestCurrentTenantDependency:
    """Test get_current_tenant dependency."""

    @pytest.mark.asyncio
    async def test_get_current_tenant_valid(self, session, auth_tenant):
        """Test getting current tenant with valid token."""
        token = create_access_token(data={"sub": auth_tenant.id, "type": "tenant"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        tenant = await get_current_tenant(credentials=credentials, session=session)

        assert tenant.id == auth_tenant.id
        assert tenant.email == auth_tenant.email

    @pytest.mark.asyncio
    async def test_get_current_tenant_invalid_token(self, session):
        """Test getting tenant with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.token.here"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_tenant(credentials=credentials, session=session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_tenant_wrong_type(self, session, auth_landlord):
        """Test getting tenant with landlord type token."""
        token = create_access_token(data={"sub": auth_landlord.id, "type": "landlord"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_tenant(credentials=credentials, session=session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_tenant_inactive(
        self, session, tenant_factory, room_factory, property_factory, auth_landlord
    ):
        """Test getting inactive tenant returns 403."""
        # Create inactive tenant
        prop = property_factory(landlord_id=auth_landlord.id)
        room = room_factory(property_id=prop.id)
        tenant = tenant_factory(
            room_id=room.id,
            is_active=False,
            password_hash=get_password_hash("testpass"),
        )

        token = create_access_token(data={"sub": tenant.id, "type": "tenant"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_tenant(credentials=credentials, session=session)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_current_tenant_no_type(self, session, auth_tenant):
        """Test getting tenant with token missing type (should fail)."""
        # Unlike landlord, tenant REQUIRES type="tenant"
        token = create_access_token(data={"sub": auth_tenant.id})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_tenant(credentials=credentials, session=session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Integration Tests
# =============================================================================


class TestAuthIntegration:
    """Integration tests for authentication flow."""

    def test_full_landlord_auth_flow(self):
        """Test complete landlord authentication flow."""
        # 1. Register (hash password)
        password = "securepassword123"
        hashed = get_password_hash(password)

        # 2. Login (verify password)
        assert verify_password(password, hashed) is True

        # 3. Create token
        landlord_id = "test-landlord-id"
        token = create_access_token(data={"sub": landlord_id, "type": "landlord"})

        # 4. Decode and verify
        decoded = decode_token(token)
        assert decoded["sub"] == landlord_id
        assert decoded["type"] == "landlord"

    def test_full_tenant_auth_flow(self):
        """Test complete tenant authentication flow."""
        # 1. Setup password
        password = "tenantpass123"
        hashed = get_password_hash(password)

        # 2. Verify password
        assert verify_password(password, hashed) is True

        # 3. Create tenant token
        tenant_id = "test-tenant-id"
        token = create_access_token(data={"sub": tenant_id, "type": "tenant"})

        # 4. Decode
        decoded = decode_token(token)
        assert decoded["sub"] == tenant_id
        assert decoded["type"] == "tenant"

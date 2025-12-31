from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models.landlord import Landlord
from app.models.tenant import Tenant

# JWT Bearer token security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


async def get_current_landlord(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> Landlord:
    """
    Dependency to get the current authenticated landlord.
    Validates the JWT token and returns the landlord.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    # Check token type - must be landlord or unspecified (for backwards compatibility)
    token_type = payload.get("type", "landlord")
    if token_type != "landlord":
        raise credentials_exception

    landlord_id: str = payload.get("sub")
    if landlord_id is None:
        raise credentials_exception

    # Get landlord from database
    landlord = session.get(Landlord, landlord_id)
    if landlord is None:
        raise credentials_exception

    return landlord


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> Tenant:
    """
    Dependency to get the current authenticated tenant.
    Validates the JWT token and returns the tenant.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    # Check token type - must be tenant
    token_type = payload.get("type")
    if token_type != "tenant":
        raise credentials_exception

    tenant_id: str = payload.get("sub")
    if tenant_id is None:
        raise credentials_exception

    # Get tenant from database
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise credentials_exception

    # Check if tenant is active
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive",
        )

    return tenant

"""
Tenant Portal Authentication Router.
Handles tenant login, password setup, and profile access.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import timedelta, datetime, timezone

from app.core.database import get_session
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_tenant,
)
from app.core.config import settings
from app.models.tenant import Tenant
from app.models.room import Room
from app.models.property import Property
from app.models.landlord import Landlord
from app.models.payment import Payment, PaymentStatus
from app.schemas.tenant import (
    TenantLogin,
    TenantSetPassword,
    TenantChangePassword,
    TenantLoginResponse,
    TenantPortalResponse,
)

router = APIRouter(prefix="/tenant-auth", tags=["Tenant Authentication"])


def get_tenant_portal_response(
    tenant: Tenant, session: Session
) -> TenantPortalResponse:
    """Build tenant portal response with property details"""
    room = session.get(Room, tenant.room_id)
    property_obj = session.get(Property, room.property_id) if room else None
    landlord = session.get(Landlord, property_obj.landlord_id) if property_obj else None

    return TenantPortalResponse(
        id=tenant.id,
        name=tenant.name,
        email=tenant.email,
        phone=tenant.phone,
        move_in_date=tenant.move_in_date,
        move_out_date=tenant.move_out_date,
        is_active=tenant.is_active,
        room_name=room.name if room else None,
        property_name=property_obj.name if property_obj else None,
        landlord_name=landlord.name if landlord else None,
        has_portal_access=tenant.password_hash is not None,
    )


@router.post("/login", response_model=TenantLoginResponse)
async def tenant_login(
    credentials: TenantLogin, session: Session = Depends(get_session)
):
    """
    Login to tenant portal with email and password.
    """
    # Find tenant by email
    statement = select(Tenant).where(Tenant.email == credentials.email)
    tenant = session.exec(statement).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if tenant has portal access set up
    if not tenant.password_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portal access not set up. Please contact your landlord.",
        )

    # Verify password
    if not verify_password(credentials.password, tenant.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if tenant is active
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your tenancy is no longer active",
        )

    # Create access token with tenant type
    access_token = create_access_token(
        data={"sub": tenant.id, "type": "tenant"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TenantLoginResponse(
        access_token=access_token,
        token_type="bearer",
        tenant=get_tenant_portal_response(tenant, session),
    )


@router.get("/me", response_model=TenantPortalResponse)
async def get_tenant_me(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Get current authenticated tenant's profile.
    """
    return get_tenant_portal_response(current_tenant, session)


@router.post("/setup-password", response_model=TenantPortalResponse)
async def setup_tenant_password(
    password_data: TenantSetPassword,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Set up password for tenant portal (first time setup).
    Note: Tenant must already have a token (from invite link).
    """
    if current_tenant.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password already set. Please use change password instead.",
        )

    if len(password_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    current_tenant.password_hash = get_password_hash(password_data.password)
    current_tenant.updated_at = datetime.now(timezone.utc)
    session.add(current_tenant)
    session.commit()
    session.refresh(current_tenant)

    return get_tenant_portal_response(current_tenant, session)


@router.put("/change-password", response_model=TenantPortalResponse)
async def change_tenant_password(
    password_data: TenantChangePassword,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Change tenant's password.
    """
    # Verify current password
    if not current_tenant.password_hash or not verify_password(
        password_data.current_password, current_tenant.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters",
        )

    current_tenant.password_hash = get_password_hash(password_data.new_password)
    current_tenant.updated_at = datetime.now(timezone.utc)
    session.add(current_tenant)
    session.commit()
    session.refresh(current_tenant)

    return get_tenant_portal_response(current_tenant, session)


@router.get("/payments")
async def get_tenant_payments(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Get current tenant's payment history.
    """
    payments = session.exec(
        select(Payment)
        .where(Payment.tenant_id == current_tenant.id)
        .order_by(Payment.due_date.desc())
    ).all()

    return {
        "payments": [
            {
                "id": p.id,
                "period_start": p.period_start,
                "period_end": p.period_end,
                "amount_due": p.amount_due,
                "due_date": p.due_date,
                "status": p.status.value,
                "paid_date": p.paid_date,
                "is_manual": p.is_manual,
            }
            for p in payments
        ],
        "summary": {
            "total_payments": len(payments),
            "pending": sum(1 for p in payments if p.status == PaymentStatus.PENDING),
            "overdue": sum(1 for p in payments if p.status == PaymentStatus.OVERDUE),
            "paid_on_time": sum(
                1 for p in payments if p.status == PaymentStatus.ON_TIME
            ),
            "paid_late": sum(1 for p in payments if p.status == PaymentStatus.LATE),
        },
    }

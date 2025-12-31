from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime, date

from app.core.database import get_session
from app.core.security import get_current_landlord
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment_schedule import PaymentSchedule, PaymentFrequency
from app.models.payment import Payment, PaymentStatus
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantMoveOut,
    TenantResponse,
    TenantWithDetails,
    TenantListResponse,
)
from app.schemas.payment_schedule import (
    PaymentScheduleCreate,
    PaymentScheduleUpdate,
    PaymentScheduleResponse,
)

router = APIRouter(prefix="/tenants", tags=["Tenants"])


def verify_room_access(
    room_id: str, landlord_id: str, session: Session
) -> tuple[Room, Property]:
    """Verify the room exists and belongs to a property owned by the landlord."""
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )

    property = session.get(Property, room.property_id)
    if not property or property.landlord_id != landlord_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )

    return room, property


@router.get("", response_model=TenantListResponse)
async def list_tenants(
    property_id: Optional[str] = None,
    active_only: bool = True,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    List all tenants for the landlord with optional filters.
    """
    # Get all properties for the landlord
    properties_query = select(Property).where(
        Property.landlord_id == current_landlord.id
    )
    if property_id:
        properties_query = properties_query.where(Property.id == property_id)
    properties = session.exec(properties_query).all()
    property_ids = [p.id for p in properties]

    if not property_ids:
        return TenantListResponse(tenants=[], total=0)

    # Get all rooms in those properties
    rooms = session.exec(select(Room).where(Room.property_id.in_(property_ids))).all()
    room_ids = [r.id for r in rooms]
    room_map = {r.id: r for r in rooms}
    property_map = {p.id: p for p in properties}

    if not room_ids:
        return TenantListResponse(tenants=[], total=0)

    # Get tenants
    tenants_query = select(Tenant).where(Tenant.room_id.in_(room_ids))
    if active_only:
        tenants_query = tenants_query.where(Tenant.is_active == True)
    tenants = session.exec(tenants_query).all()

    tenants_with_details = []
    for tenant in tenants:
        room = room_map.get(tenant.room_id)
        property = property_map.get(room.property_id) if room else None

        # Check for payment schedule
        schedule = session.exec(
            select(PaymentSchedule).where(
                PaymentSchedule.tenant_id == tenant.id,
                PaymentSchedule.is_active == True,
            )
        ).first()

        # Count pending/overdue payments
        pending_count = session.exec(
            select(Payment).where(
                Payment.tenant_id == tenant.id, Payment.status == PaymentStatus.PENDING
            )
        ).all()
        overdue_count = session.exec(
            select(Payment).where(
                Payment.tenant_id == tenant.id, Payment.status == PaymentStatus.OVERDUE
            )
        ).all()

        tenants_with_details.append(
            TenantWithDetails(
                **tenant.model_dump(),
                room_name=room.name if room else None,
                property_id=property.id if property else None,
                property_name=property.name if property else None,
                rent_amount=room.rent_amount if room else None,
                has_payment_schedule=schedule is not None,
                pending_payments=len(pending_count),
                overdue_payments=len(overdue_count),
            )
        )

    return TenantListResponse(
        tenants=tenants_with_details, total=len(tenants_with_details)
    )


@router.post("", response_model=TenantWithDetails, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Create a new tenant and assign to a room.
    Optionally create a payment schedule at the same time.
    """
    room, property = verify_room_access(
        tenant_data.room_id, current_landlord.id, session
    )

    # Check if room already has an active tenant
    existing_tenant = session.exec(
        select(Tenant).where(Tenant.room_id == room.id, Tenant.is_active == True)
    ).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room already has an active tenant",
        )

    # Create tenant
    tenant = Tenant(
        room_id=room.id,
        name=tenant_data.name,
        email=tenant_data.email,
        phone=tenant_data.phone,
        move_in_date=tenant_data.move_in_date,
        notes=tenant_data.notes,
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    # Mark room as occupied
    room.is_occupied = True
    session.add(room)

    # Create payment schedule if provided
    schedule = None
    if tenant_data.payment_amount:
        schedule = PaymentSchedule(
            tenant_id=tenant.id,
            amount=tenant_data.payment_amount,
            frequency=tenant_data.payment_frequency or PaymentFrequency.MONTHLY,
            due_day=tenant_data.payment_due_day or 1,
            window_days=tenant_data.payment_window_days or 5,
            start_date=tenant_data.move_in_date,
        )
        session.add(schedule)

    session.commit()
    session.refresh(tenant)

    return TenantWithDetails(
        **tenant.model_dump(),
        room_name=room.name,
        property_id=property.id,
        property_name=property.name,
        rent_amount=room.rent_amount,
        has_payment_schedule=schedule is not None,
        pending_payments=0,
        overdue_payments=0,
    )


@router.get("/{tenant_id}", response_model=TenantWithDetails)
async def get_tenant(
    tenant_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get a specific tenant by ID with details.
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    room, property = verify_room_access(tenant.room_id, current_landlord.id, session)

    # Check for payment schedule
    schedule = session.exec(
        select(PaymentSchedule).where(
            PaymentSchedule.tenant_id == tenant.id, PaymentSchedule.is_active == True
        )
    ).first()

    # Count pending/overdue payments
    pending_count = len(
        session.exec(
            select(Payment).where(
                Payment.tenant_id == tenant.id, Payment.status == PaymentStatus.PENDING
            )
        ).all()
    )
    overdue_count = len(
        session.exec(
            select(Payment).where(
                Payment.tenant_id == tenant.id, Payment.status == PaymentStatus.OVERDUE
            )
        ).all()
    )

    return TenantWithDetails(
        **tenant.model_dump(),
        room_name=room.name,
        property_id=property.id,
        property_name=property.name,
        rent_amount=room.rent_amount,
        has_payment_schedule=schedule is not None,
        pending_payments=pending_count,
        overdue_payments=overdue_count,
    )


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    update_data: TenantUpdate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Update tenant information.
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    verify_room_access(tenant.room_id, current_landlord.id, session)

    if update_data.name is not None:
        tenant.name = update_data.name
    if update_data.email is not None:
        tenant.email = update_data.email
    if update_data.phone is not None:
        tenant.phone = update_data.phone
    if update_data.notes is not None:
        tenant.notes = update_data.notes

    tenant.updated_at = datetime.utcnow()
    session.add(tenant)
    session.commit()
    session.refresh(tenant)

    return TenantResponse.model_validate(tenant)


@router.post("/{tenant_id}/move-out", response_model=TenantResponse)
async def move_out_tenant(
    tenant_id: str,
    move_out_data: TenantMoveOut,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Move out a tenant from their room.
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    room, _ = verify_room_access(tenant.room_id, current_landlord.id, session)

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant is already moved out",
        )

    # Update tenant
    tenant.is_active = False
    tenant.move_out_date = move_out_data.move_out_date
    tenant.updated_at = datetime.utcnow()

    # Deactivate payment schedule
    schedule = session.exec(
        select(PaymentSchedule).where(
            PaymentSchedule.tenant_id == tenant.id, PaymentSchedule.is_active == True
        )
    ).first()
    if schedule:
        schedule.is_active = False
        session.add(schedule)

    # Mark room as vacant
    room.is_occupied = False

    session.add(tenant)
    session.add(room)
    session.commit()
    session.refresh(tenant)

    return TenantResponse.model_validate(tenant)


# Payment Schedule sub-routes
@router.get("/{tenant_id}/schedule", response_model=PaymentScheduleResponse)
async def get_tenant_schedule(
    tenant_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get the payment schedule for a tenant.
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    verify_room_access(tenant.room_id, current_landlord.id, session)

    schedule = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.tenant_id == tenant_id)
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment schedule not found"
        )

    return PaymentScheduleResponse.model_validate(schedule)


@router.post(
    "/{tenant_id}/schedule",
    response_model=PaymentScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant_schedule(
    tenant_id: str,
    schedule_data: PaymentScheduleCreate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Create a payment schedule for a tenant.
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    verify_room_access(tenant.room_id, current_landlord.id, session)

    # Check if tenant already has an active schedule
    existing = session.exec(
        select(PaymentSchedule).where(
            PaymentSchedule.tenant_id == tenant_id, PaymentSchedule.is_active == True
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant already has an active payment schedule",
        )

    schedule = PaymentSchedule(
        tenant_id=tenant_id,
        amount=schedule_data.amount,
        frequency=schedule_data.frequency,
        due_day=schedule_data.due_day,
        window_days=schedule_data.window_days,
        start_date=schedule_data.start_date,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    return PaymentScheduleResponse.model_validate(schedule)


@router.put("/{tenant_id}/schedule", response_model=PaymentScheduleResponse)
async def update_tenant_schedule(
    tenant_id: str,
    update_data: PaymentScheduleUpdate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Update the payment schedule for a tenant.
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    verify_room_access(tenant.room_id, current_landlord.id, session)

    schedule = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.tenant_id == tenant_id)
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment schedule not found"
        )

    if update_data.amount is not None:
        schedule.amount = update_data.amount
    if update_data.frequency is not None:
        schedule.frequency = update_data.frequency
    if update_data.due_day is not None:
        schedule.due_day = update_data.due_day
    if update_data.window_days is not None:
        schedule.window_days = update_data.window_days
    if update_data.is_active is not None:
        schedule.is_active = update_data.is_active

    schedule.updated_at = datetime.utcnow()
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    return PaymentScheduleResponse.model_validate(schedule)

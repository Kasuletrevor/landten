from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime

from app.core.database import get_session
from app.core.security import get_current_landlord
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.schemas.room import (
    RoomCreate,
    RoomUpdate,
    RoomResponse,
    RoomWithTenant,
    RoomListResponse,
)

router = APIRouter(prefix="/properties/{property_id}/rooms", tags=["Rooms"])


def verify_property_ownership(
    property_id: str, landlord_id: str, session: Session
) -> Property:
    """Verify the property exists and belongs to the landlord."""
    property = session.get(Property, property_id)
    if not property or property.landlord_id != landlord_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
        )
    return property


@router.get("", response_model=RoomListResponse)
async def list_rooms(
    property_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    List all rooms in a property with tenant info.
    """
    verify_property_ownership(property_id, current_landlord.id, session)

    rooms = session.exec(select(Room).where(Room.property_id == property_id)).all()

    rooms_with_tenant = []
    for room in rooms:
        # Get active tenant if any
        tenant = session.exec(
            select(Tenant).where(Tenant.room_id == room.id, Tenant.is_active == True)
        ).first()

        rooms_with_tenant.append(
            RoomWithTenant(
                **room.model_dump(),
                tenant_name=tenant.name if tenant else None,
                tenant_id=tenant.id if tenant else None,
            )
        )

    return RoomListResponse(rooms=rooms_with_tenant, total=len(rooms_with_tenant))


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    property_id: str,
    room_data: RoomCreate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Create a new room in a property.
    """
    verify_property_ownership(property_id, current_landlord.id, session)

    room = Room(
        property_id=property_id,
        name=room_data.name,
        rent_amount=room_data.rent_amount,
        description=room_data.description,
    )
    session.add(room)
    session.commit()
    session.refresh(room)

    return RoomResponse.model_validate(room)


@router.get("/{room_id}", response_model=RoomWithTenant)
async def get_room(
    property_id: str,
    room_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get a specific room by ID with tenant info.
    """
    verify_property_ownership(property_id, current_landlord.id, session)

    room = session.get(Room, room_id)
    if not room or room.property_id != property_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )

    # Get active tenant if any
    tenant = session.exec(
        select(Tenant).where(Tenant.room_id == room.id, Tenant.is_active == True)
    ).first()

    return RoomWithTenant(
        **room.model_dump(),
        tenant_name=tenant.name if tenant else None,
        tenant_id=tenant.id if tenant else None,
    )


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(
    property_id: str,
    room_id: str,
    update_data: RoomUpdate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Update a room.
    """
    verify_property_ownership(property_id, current_landlord.id, session)

    room = session.get(Room, room_id)
    if not room or room.property_id != property_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )

    if update_data.name is not None:
        room.name = update_data.name
    if update_data.rent_amount is not None:
        room.rent_amount = update_data.rent_amount
    if update_data.description is not None:
        room.description = update_data.description

    room.updated_at = datetime.utcnow()
    session.add(room)
    session.commit()
    session.refresh(room)

    return RoomResponse.model_validate(room)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    property_id: str,
    room_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Delete a room. Will fail if room has active tenants.
    """
    verify_property_ownership(property_id, current_landlord.id, session)

    room = session.get(Room, room_id)
    if not room or room.property_id != property_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
        )

    # Check if room has active tenant
    tenant = session.exec(
        select(Tenant).where(Tenant.room_id == room_id, Tenant.is_active == True)
    ).first()
    if tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete room with active tenant. Move out tenant first.",
        )

    session.delete(room)
    session.commit()

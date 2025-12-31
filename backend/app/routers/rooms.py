from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime, timezone

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
    BulkRoomCreate,
    BulkRoomResponse,
    PriceRange,
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
        currency=room_data.currency,
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
    if update_data.currency is not None:
        room.currency = update_data.currency
    if update_data.description is not None:
        room.description = update_data.description

    room.updated_at = datetime.now(timezone.utc)
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


# Maximum rooms per bulk creation
MAX_BULK_ROOMS = 500


def find_price_for_room_number(
    room_number: int, price_ranges: List[PriceRange]
) -> Optional[float]:
    """Find the price for a given room number from the price ranges."""
    for pr in price_ranges:
        if pr.from_number <= room_number <= pr.to_number:
            return pr.rent_amount
    return None


def find_coverage_gaps(
    from_number: int, to_number: int, price_ranges: List[PriceRange]
) -> List[tuple]:
    """Find gaps in price range coverage."""
    covered = set()
    for pr in price_ranges:
        for num in range(pr.from_number, pr.to_number + 1):
            if from_number <= num <= to_number:
                covered.add(num)

    all_numbers = set(range(from_number, to_number + 1))
    uncovered = sorted(all_numbers - covered)

    if not uncovered:
        return []

    # Group consecutive numbers into ranges
    gaps = []
    gap_start = uncovered[0]
    gap_end = uncovered[0]

    for num in uncovered[1:]:
        if num == gap_end + 1:
            gap_end = num
        else:
            gaps.append((gap_start, gap_end))
            gap_start = num
            gap_end = num

    gaps.append((gap_start, gap_end))
    return gaps


@router.post(
    "/bulk", response_model=BulkRoomResponse, status_code=status.HTTP_201_CREATED
)
async def create_rooms_bulk(
    property_id: str,
    bulk_data: BulkRoomCreate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Create multiple rooms at once with optional price ranges.

    - Maximum 500 rooms per operation
    - Supports prefix and zero-padding for room names
    - Allows different prices for different room number ranges
    """
    verify_property_ownership(property_id, current_landlord.id, session)

    # Validate total rooms
    total_rooms = bulk_data.to_number - bulk_data.from_number + 1
    if total_rooms > MAX_BULK_ROOMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_BULK_ROOMS} rooms per bulk creation. You requested {total_rooms}.",
        )

    if total_rooms < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room range.",
        )

    # Validate price ranges are within overall range
    for pr in bulk_data.price_ranges:
        if pr.from_number < bulk_data.from_number or pr.to_number > bulk_data.to_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Price range {pr.from_number}-{pr.to_number} is outside overall range {bulk_data.from_number}-{bulk_data.to_number}.",
            )

    # Find gaps in coverage
    warnings = []
    gaps = find_coverage_gaps(
        bulk_data.from_number, bulk_data.to_number, bulk_data.price_ranges
    )
    for gap_start, gap_end in gaps:
        if gap_start == gap_end:
            warnings.append(f"Room {gap_start} has no price assigned.")
        else:
            warnings.append(f"Rooms {gap_start}-{gap_end} have no price assigned.")

    # Create rooms
    created_rooms = []
    for num in range(bulk_data.from_number, bulk_data.to_number + 1):
        price = find_price_for_room_number(num, bulk_data.price_ranges)

        # Skip rooms without a price (gap rooms)
        if price is None:
            continue

        # Generate room name with optional padding
        if bulk_data.padding > 0:
            num_str = str(num).zfill(bulk_data.padding)
        else:
            num_str = str(num)

        room_name = f"{bulk_data.prefix}{num_str}"

        room = Room(
            property_id=property_id,
            name=room_name,
            rent_amount=price,
            currency=bulk_data.currency,
        )
        session.add(room)
        created_rooms.append(room)

    session.commit()

    # Refresh all rooms to get their IDs
    for room in created_rooms:
        session.refresh(room)

    return BulkRoomResponse(
        created=[RoomResponse.model_validate(room) for room in created_rooms],
        total_created=len(created_rooms),
        warnings=warnings,
    )

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
from typing import Optional
from datetime import datetime

from app.core.database import get_session
from app.core.security import get_current_landlord
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyWithStats,
    PropertyListResponse,
)

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("", response_model=PropertyListResponse)
async def list_properties(
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    List all properties for the current landlord with statistics.
    """
    statement = select(Property).where(Property.landlord_id == current_landlord.id)
    properties = session.exec(statement).all()

    properties_with_stats = []
    for prop in properties:
        # Get room stats
        rooms = session.exec(select(Room).where(Room.property_id == prop.id)).all()

        total_rooms = len(rooms)
        occupied_rooms = sum(1 for r in rooms if r.is_occupied)
        vacant_rooms = total_rooms - occupied_rooms
        monthly_expected_income = sum(r.rent_amount for r in rooms if r.is_occupied)

        # Get tenant count
        total_tenants = sum(1 for r in rooms if r.is_occupied)

        properties_with_stats.append(
            PropertyWithStats(
                **prop.model_dump(),
                total_rooms=total_rooms,
                occupied_rooms=occupied_rooms,
                vacant_rooms=vacant_rooms,
                total_tenants=total_tenants,
                monthly_expected_income=monthly_expected_income,
            )
        )

    return PropertyListResponse(
        properties=properties_with_stats, total=len(properties_with_stats)
    )


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
async def create_property(
    property_data: PropertyCreate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Create a new property for the current landlord.
    """
    property = Property(
        landlord_id=current_landlord.id,
        name=property_data.name,
        address=property_data.address,
        description=property_data.description,
    )
    session.add(property)
    session.commit()
    session.refresh(property)

    return PropertyResponse.model_validate(property)


@router.get("/{property_id}", response_model=PropertyWithStats)
async def get_property(
    property_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get a specific property by ID with statistics.
    """
    property = session.get(Property, property_id)
    if not property or property.landlord_id != current_landlord.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
        )

    # Get room stats
    rooms = session.exec(select(Room).where(Room.property_id == property.id)).all()

    total_rooms = len(rooms)
    occupied_rooms = sum(1 for r in rooms if r.is_occupied)
    vacant_rooms = total_rooms - occupied_rooms
    monthly_expected_income = sum(r.rent_amount for r in rooms if r.is_occupied)
    total_tenants = sum(1 for r in rooms if r.is_occupied)

    return PropertyWithStats(
        **property.model_dump(),
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        vacant_rooms=vacant_rooms,
        total_tenants=total_tenants,
        monthly_expected_income=monthly_expected_income,
    )


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: str,
    update_data: PropertyUpdate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Update a property.
    """
    property = session.get(Property, property_id)
    if not property or property.landlord_id != current_landlord.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
        )

    if update_data.name is not None:
        property.name = update_data.name
    if update_data.address is not None:
        property.address = update_data.address
    if update_data.description is not None:
        property.description = update_data.description

    property.updated_at = datetime.utcnow()
    session.add(property)
    session.commit()
    session.refresh(property)

    return PropertyResponse.model_validate(property)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Delete a property. Will fail if property has rooms.
    """
    property = session.get(Property, property_id)
    if not property or property.landlord_id != current_landlord.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
        )

    # Check if property has rooms
    rooms = session.exec(select(Room).where(Room.property_id == property_id)).first()
    if rooms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete property with rooms. Delete rooms first.",
        )

    session.delete(property)
    session.commit()

from datetime import datetime, timezone
from typing import Literal, Optional
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.models.landlord import Landlord
from app.models.maintenance import (
    MaintenanceAuthorType,
    MaintenanceComment,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.schemas.maintenance import MaintenanceCommentResponse, MaintenanceRequestResponse

MaintenanceViewerType = Literal["landlord", "tenant"]

_ALLOWED_ATTACHMENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
_MAINTENANCE_UPLOADS_DIR = os.path.normpath(os.path.join("uploads", "maintenance"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_request_for_landlord(
    session: Session, request_id: str, landlord_id: str
) -> tuple[MaintenanceRequest, Tenant, Room, Property]:
    maintenance_request = session.get(MaintenanceRequest, request_id)
    if not maintenance_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found",
        )

    tenant = session.get(Tenant, maintenance_request.tenant_id)
    room = session.get(Room, maintenance_request.room_id)
    property_obj = session.get(Property, maintenance_request.property_id)
    if (
        tenant is None
        or room is None
        or property_obj is None
        or property_obj.landlord_id != landlord_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found",
        )
    return maintenance_request, tenant, room, property_obj


def get_request_for_tenant(
    session: Session, request_id: str, tenant_id: str
) -> tuple[MaintenanceRequest, Tenant, Room, Property, Landlord]:
    maintenance_request = session.get(MaintenanceRequest, request_id)
    if not maintenance_request or maintenance_request.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found",
        )

    tenant = session.get(Tenant, maintenance_request.tenant_id)
    room = session.get(Room, maintenance_request.room_id)
    property_obj = session.get(Property, maintenance_request.property_id)
    landlord = session.get(Landlord, property_obj.landlord_id) if property_obj else None
    if tenant is None or room is None or property_obj is None or landlord is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance request not found",
        )
    return maintenance_request, tenant, room, property_obj, landlord


def get_request_comments(
    session: Session,
    request_id: str,
    viewer_type: MaintenanceViewerType,
) -> list[MaintenanceComment]:
    query = (
        select(MaintenanceComment)
        .where(MaintenanceComment.request_id == request_id)
        .order_by(MaintenanceComment.created_at.asc())
    )
    if viewer_type == "tenant":
        query = query.where(MaintenanceComment.is_internal == False)
    return session.exec(query).all()


def create_maintenance_comment(
    session: Session,
    maintenance_request: MaintenanceRequest,
    author_type: MaintenanceAuthorType,
    author_id: str,
    body: str,
    is_internal: bool = False,
    attachment_name: Optional[str] = None,
    attachment_url: Optional[str] = None,
    attachment_content_type: Optional[str] = None,
    attachment_size_bytes: Optional[int] = None,
) -> MaintenanceComment:
    timestamp = now_utc()
    comment = MaintenanceComment(
        request_id=maintenance_request.id,
        author_type=author_type,
        author_id=author_id,
        body=body,
        is_internal=is_internal,
        attachment_name=attachment_name,
        attachment_url=attachment_url,
        attachment_content_type=attachment_content_type,
        attachment_size_bytes=attachment_size_bytes,
        created_at=timestamp,
    )
    session.add(comment)
    maintenance_request.updated_at = timestamp
    session.add(maintenance_request)
    session.commit()
    session.refresh(comment)
    return comment


def build_maintenance_response(
    session: Session,
    maintenance_request: MaintenanceRequest,
    viewer_type: MaintenanceViewerType,
    include_comments: bool = True,
) -> MaintenanceRequestResponse:
    tenant = session.get(Tenant, maintenance_request.tenant_id)
    room = session.get(Room, maintenance_request.room_id)
    property_obj = session.get(Property, maintenance_request.property_id)
    comments = (
        get_request_comments(session, maintenance_request.id, viewer_type)
        if include_comments
        else []
    )
    comments_count = len(comments)

    return MaintenanceRequestResponse(
        id=maintenance_request.id,
        tenant_id=maintenance_request.tenant_id,
        property_id=maintenance_request.property_id,
        room_id=maintenance_request.room_id,
        category=maintenance_request.category,
        urgency=maintenance_request.urgency,
        status=maintenance_request.status,
        title=maintenance_request.title,
        description=maintenance_request.description,
        preferred_entry_time=maintenance_request.preferred_entry_time,
        assigned_to=maintenance_request.assigned_to,
        scheduled_visit_at=maintenance_request.scheduled_visit_at,
        estimated_cost=maintenance_request.estimated_cost,
        actual_cost=maintenance_request.actual_cost,
        landlord_notes=maintenance_request.landlord_notes,
        completed_at=maintenance_request.completed_at,
        tenant_rating=maintenance_request.tenant_rating,
        tenant_feedback=maintenance_request.tenant_feedback,
        created_at=maintenance_request.created_at,
        updated_at=maintenance_request.updated_at,
        tenant_name=tenant.name if tenant else None,
        tenant_email=tenant.email if tenant else None,
        tenant_phone=tenant.phone if tenant else None,
        property_name=property_obj.name if property_obj else None,
        room_name=room.name if room else None,
        comments_count=comments_count,
        comments=[MaintenanceCommentResponse.model_validate(c) for c in comments],
    )


async def save_maintenance_attachment(
    file: UploadFile, request_id: str
) -> tuple[str, str, str, int]:
    content_type = file.content_type or "application/octet-stream"
    if content_type not in _ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, and PDF are allowed.",
        )

    content = await file.read()
    size_bytes = len(content)
    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty"
        )
    if size_bytes > _MAX_ATTACHMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attachment too large. Maximum size is 10MB.",
        )

    extension = os.path.splitext(file.filename or "")[1]
    safe_name = f"{request_id}_{uuid.uuid4()}{extension}"
    os.makedirs(_MAINTENANCE_UPLOADS_DIR, exist_ok=True)
    file_path = os.path.join(_MAINTENANCE_UPLOADS_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    return (
        file.filename or safe_name,
        f"/uploads/maintenance/{safe_name}",
        content_type,
        size_bytes,
    )


def assert_valid_status_transition(
    current_status: MaintenanceStatus, new_status: MaintenanceStatus
) -> None:
    valid_transitions = {
        MaintenanceStatus.SUBMITTED: {
            MaintenanceStatus.ACKNOWLEDGED,
            MaintenanceStatus.CANCELLED,
            MaintenanceStatus.IN_PROGRESS,
        },
        MaintenanceStatus.ACKNOWLEDGED: {
            MaintenanceStatus.IN_PROGRESS,
            MaintenanceStatus.COMPLETED,
            MaintenanceStatus.CANCELLED,
        },
        MaintenanceStatus.IN_PROGRESS: {
            MaintenanceStatus.COMPLETED,
            MaintenanceStatus.CANCELLED,
            MaintenanceStatus.ACKNOWLEDGED,
        },
        MaintenanceStatus.COMPLETED: {
            MaintenanceStatus.ACKNOWLEDGED,
            MaintenanceStatus.IN_PROGRESS,
        },
        MaintenanceStatus.CANCELLED: {MaintenanceStatus.ACKNOWLEDGED},
    }

    allowed = valid_transitions.get(current_status, set())
    if new_status != current_status and new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Invalid status transition from {current_status.value} "
                f"to {new_status.value}"
            ),
        )

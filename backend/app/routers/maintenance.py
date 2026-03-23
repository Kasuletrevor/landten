from datetime import datetime, timezone
from typing import Optional, Awaitable
import logging
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, status, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from sqlalchemy import or_

from app.core.database import get_session
from app.core.security import (
    decode_token,
    get_current_landlord,
    get_token_from_request,
)
from app.models.landlord import Landlord
from app.models.maintenance import (
    MaintenanceAuthorType,
    MaintenanceComment,
    MaintenanceRequest,
    MaintenanceStatus,
    MaintenanceUrgency,
)
from app.models.property import Property
from app.models.tenant import Tenant
from app.schemas.maintenance import (
    MaintenanceCommentCreate,
    MaintenanceRequestListResponse,
    MaintenanceRequestResponse,
    MaintenanceRequestUpdate,
)
from app.services import email_service, notification_service
from app.services.maintenance_service import (
    assert_valid_status_transition,
    build_maintenance_response,
    build_maintenance_attachment_url,
    create_maintenance_comment,
    get_request_for_landlord,
    get_request_for_tenant,
    resolve_maintenance_attachment_file_path,
    save_maintenance_attachment,
)

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])
logger = logging.getLogger(__name__)


async def _run_post_commit_task(
    task_name: str,
    coroutine: Awaitable[object],
    **context: object,
) -> None:
    try:
        await coroutine
    except Exception:
        logger.exception(
            "Post-commit maintenance task failed",
            extra={"task_name": task_name, **context},
        )


def _get_landlord_property_ids(session: Session, landlord_id: str) -> list[str]:
    properties = session.exec(
        select(Property).where(Property.landlord_id == landlord_id)
    ).all()
    return [p.id for p in properties]


async def _get_current_maintenance_viewer(
    request: Request,
    session: Session = Depends(get_session),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    bearer_token = get_token_from_request(request)
    if not bearer_token:
        raise credentials_exception

    payload = decode_token(bearer_token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    token_type = payload.get("type", "landlord")
    if not user_id:
        raise credentials_exception

    if token_type == "tenant":
        tenant = session.get(Tenant, user_id)
        if tenant is None or not tenant.is_active:
            raise credentials_exception
        return ("tenant", tenant)

    landlord = session.get(Landlord, user_id)
    if landlord is None:
        raise credentials_exception
    return ("landlord", landlord)


@router.get("", response_model=MaintenanceRequestListResponse)
async def list_maintenance_requests(
    status_filter: Optional[MaintenanceStatus] = Query(default=None, alias="status"),
    urgency: Optional[MaintenanceUrgency] = None,
    property_id: Optional[str] = None,
    search: Optional[str] = None,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    property_ids = _get_landlord_property_ids(session, current_landlord.id)
    if not property_ids:
        return MaintenanceRequestListResponse(requests=[], total=0)

    query = select(MaintenanceRequest).where(
        MaintenanceRequest.property_id.in_(property_ids)
    )
    if property_id:
        query = query.where(MaintenanceRequest.property_id == property_id)
    if status_filter:
        query = query.where(MaintenanceRequest.status == status_filter)
    if urgency:
        query = query.where(MaintenanceRequest.urgency == urgency)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                MaintenanceRequest.title.ilike(pattern),
                MaintenanceRequest.description.ilike(pattern),
            )
        )

    requests = session.exec(query.order_by(MaintenanceRequest.created_at.desc())).all()
    response_requests = [
        build_maintenance_response(
            session,
            maintenance_request,
            viewer_type="landlord",
            include_comments=False,
        )
        for maintenance_request in requests
    ]
    return MaintenanceRequestListResponse(requests=response_requests, total=len(requests))


@router.get("/{request_id}", response_model=MaintenanceRequestResponse)
async def get_maintenance_request(
    request_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    maintenance_request, _, _, _ = get_request_for_landlord(
        session, request_id, current_landlord.id
    )
    return build_maintenance_response(
        session, maintenance_request, viewer_type="landlord", include_comments=True
    )


@router.get("/{request_id}/comments/{comment_id}/attachment")
async def get_maintenance_comment_attachment(
    request_id: str,
    comment_id: str,
    viewer=Depends(_get_current_maintenance_viewer),
    session: Session = Depends(get_session),
):
    viewer_type, viewer_user = viewer

    if viewer_type == "landlord":
        get_request_for_landlord(session, request_id, viewer_user.id)
    else:
        get_request_for_tenant(session, request_id, viewer_user.id)

    comment = session.exec(
        select(MaintenanceComment).where(
            MaintenanceComment.id == comment_id,
            MaintenanceComment.request_id == request_id,
        )
    ).first()

    if not comment or not comment.attachment_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    if viewer_type == "tenant" and comment.is_internal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    file_path = resolve_maintenance_attachment_file_path(comment.attachment_url)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )

    return FileResponse(
        file_path,
        media_type=comment.attachment_content_type or "application/octet-stream",
        filename=comment.attachment_name or os.path.basename(file_path),
    )


@router.put("/{request_id}", response_model=MaintenanceRequestResponse)
async def update_maintenance_request(
    request_id: str,
    payload: MaintenanceRequestUpdate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    maintenance_request, tenant, room, property_obj = get_request_for_landlord(
        session, request_id, current_landlord.id
    )

    updates = payload.model_dump(exclude_unset=True)
    new_status = updates.get("status")
    if new_status is not None:
        assert_valid_status_transition(maintenance_request.status, new_status)
        maintenance_request.status = new_status
        if new_status == MaintenanceStatus.COMPLETED:
            maintenance_request.completed_at = datetime.now(timezone.utc)
        elif maintenance_request.status != MaintenanceStatus.COMPLETED:
            maintenance_request.completed_at = None

    for field_name in [
        "assigned_to",
        "scheduled_visit_at",
        "estimated_cost",
        "actual_cost",
        "landlord_notes",
    ]:
        if field_name in updates:
            setattr(maintenance_request, field_name, updates[field_name])

    maintenance_request.updated_at = datetime.now(timezone.utc)
    session.add(maintenance_request)
    session.commit()
    session.refresh(maintenance_request)

    await _run_post_commit_task(
        "broadcast_maintenance_update_to_tenant",
        notification_service.broadcast_to_tenant(
            tenant.id,
            "maintenance_request_updated",
            {
                "request_id": maintenance_request.id,
                "title": "Maintenance request updated",
                "message": (
                    f"{maintenance_request.title} is now {maintenance_request.status.value.replace('_', ' ')}."
                ),
                "request_title": maintenance_request.title,
                "status": maintenance_request.status.value,
                "updated_at": maintenance_request.updated_at.isoformat(),
            },
        ),
        request_id=maintenance_request.id,
        tenant_id=tenant.id,
        landlord_id=current_landlord.id,
    )
    if tenant.email:
        await _run_post_commit_task(
            "send_maintenance_update_email_to_tenant",
            email_service.send_maintenance_update(
                recipient_name=tenant.name,
                recipient_email=tenant.email,
                actor_name=current_landlord.name,
                property_name=property_obj.name,
                room_name=room.name,
                request_title=maintenance_request.title,
                update_summary="Maintenance request updated",
                message=(
                    f"Status changed to {maintenance_request.status.value.replace('_', ' ')}."
                ),
            ),
            request_id=maintenance_request.id,
            tenant_id=tenant.id,
            landlord_id=current_landlord.id,
            recipient_email=tenant.email,
        )

    return build_maintenance_response(
        session, maintenance_request, viewer_type="landlord", include_comments=True
    )


@router.post(
    "/{request_id}/comments",
    response_model=MaintenanceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_maintenance_comment(
    request_id: str,
    payload: MaintenanceCommentCreate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    maintenance_request, tenant, room, property_obj = get_request_for_landlord(
        session, request_id, current_landlord.id
    )
    body = payload.body.strip()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Comment body is required"
        )

    _ = create_maintenance_comment(
        session,
        maintenance_request=maintenance_request,
        author_type=MaintenanceAuthorType.LANDLORD,
        author_id=current_landlord.id,
        body=body,
        is_internal=payload.is_internal,
    )

    if not payload.is_internal:
        await _run_post_commit_task(
            "broadcast_maintenance_comment_to_tenant",
            notification_service.broadcast_to_tenant(
                tenant.id,
                "maintenance_comment_created",
                {
                    "request_id": maintenance_request.id,
                    "title": "Landlord commented on your maintenance request",
                    "author_type": "landlord",
                    "message": body,
                    "request_title": maintenance_request.title,
                },
            ),
            request_id=maintenance_request.id,
            tenant_id=tenant.id,
            landlord_id=current_landlord.id,
        )
        if tenant.email:
            await _run_post_commit_task(
                "send_maintenance_comment_email_to_tenant",
                email_service.send_maintenance_update(
                    recipient_name=tenant.name,
                    recipient_email=tenant.email,
                    actor_name=current_landlord.name,
                    property_name=property_obj.name,
                    room_name=room.name,
                    request_title=maintenance_request.title,
                    update_summary="Landlord added a comment",
                    message=body,
                ),
                request_id=maintenance_request.id,
                tenant_id=tenant.id,
                landlord_id=current_landlord.id,
                recipient_email=tenant.email,
            )

    updated = session.get(MaintenanceRequest, maintenance_request.id)
    return build_maintenance_response(
        session, updated, viewer_type="landlord", include_comments=True
    )


@router.post(
    "/{request_id}/comments/attachments",
    response_model=MaintenanceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_maintenance_attachment_comment(
    request_id: str,
    file: UploadFile = File(...),
    body: Optional[str] = Form(default=None),
    is_internal: bool = Form(default=False),
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    maintenance_request, tenant, room, property_obj = get_request_for_landlord(
        session, request_id, current_landlord.id
    )
    attachment_name, attachment_url, content_type, size_bytes = (
        await save_maintenance_attachment(file, maintenance_request.id)
    )
    message_body = (body or "").strip() or f"Attachment shared: {attachment_name}"
    comment = create_maintenance_comment(
        session,
        maintenance_request=maintenance_request,
        author_type=MaintenanceAuthorType.LANDLORD,
        author_id=current_landlord.id,
        body=message_body,
        is_internal=is_internal,
        attachment_name=attachment_name,
        attachment_url=attachment_url,
        attachment_content_type=content_type,
        attachment_size_bytes=size_bytes,
    )
    secure_attachment_url = build_maintenance_attachment_url(
        maintenance_request.id,
        comment.id,
        attachment_url,
    )
    if not is_internal:
        await _run_post_commit_task(
            "broadcast_maintenance_attachment_to_tenant",
            notification_service.broadcast_to_tenant(
                tenant.id,
                "maintenance_comment_created",
                {
                    "request_id": maintenance_request.id,
                    "title": "Landlord shared a maintenance attachment",
                    "author_type": "landlord",
                    "message": message_body,
                    "request_title": maintenance_request.title,
                    "attachment_url": secure_attachment_url,
                },
            ),
            request_id=maintenance_request.id,
            tenant_id=tenant.id,
            landlord_id=current_landlord.id,
        )
        if tenant.email:
            await _run_post_commit_task(
                "send_maintenance_attachment_email_to_tenant",
                email_service.send_maintenance_update(
                    recipient_name=tenant.name,
                    recipient_email=tenant.email,
                    actor_name=current_landlord.name,
                    property_name=property_obj.name,
                    room_name=room.name,
                    request_title=maintenance_request.title,
                    update_summary="Landlord shared an attachment",
                    message=message_body,
                ),
                request_id=maintenance_request.id,
                tenant_id=tenant.id,
                landlord_id=current_landlord.id,
                recipient_email=tenant.email,
            )

    updated = session.get(MaintenanceRequest, maintenance_request.id)
    return build_maintenance_response(
        session, updated, viewer_type="landlord", include_comments=True
    )

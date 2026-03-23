"""
Tenant Portal Authentication Router.
Handles tenant login, password setup, and profile access.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Response,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from typing import Awaitable
from datetime import timedelta, datetime, timezone
import logging

from app.core.database import get_session
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_tenant,
    decode_token,
    AUTH_COOKIE_NAME,
    get_token_from_request,
)
from app.core.config import settings
from app.core.rate_limit import limiter, AUTH_RATE_LIMIT, SETUP_RATE_LIMIT
from app.models.tenant import Tenant
from app.models.room import Room
from app.models.property import Property
from app.models.landlord import Landlord
from app.models.notification import Notification, NotificationType
from app.models.payment_dispute import DisputeActorType
from app.models.maintenance import (
    MaintenanceAuthorType,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.services import email_service, notification_service
from app.services.payment_dispute_service import (
    get_payment_for_tenant,
    get_dispute_for_payment,
    mark_dispute_read,
    build_dispute_response,
    create_dispute_message,
    save_dispute_attachment,
)
from app.services.maintenance_service import (
    assert_valid_status_transition,
    build_maintenance_response,
    build_maintenance_attachment_url,
    create_maintenance_comment,
    get_request_for_tenant,
    save_maintenance_attachment,
)
from app.models.payment import Payment, PaymentStatus
from app.schemas.tenant import (
    TenantLogin,
    TenantSetPassword,
    TenantChangePassword,
    TenantLoginResponse,
    TenantPortalResponse,
)
from app.schemas.payment import PaymentDisputeMessageCreate, PaymentDisputeResponse
from app.schemas.maintenance import (
    MaintenanceCommentCreate,
    MaintenanceRequestCreate,
    MaintenanceRequestListResponse,
    MaintenanceRequestResponse,
    MaintenanceResolveRequest,
)

router = APIRouter(prefix="/tenant-auth", tags=["Tenant Authentication"])
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
            "Post-commit tenant-auth task failed",
            extra={"task_name": task_name, **context},
        )


def _set_auth_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.FRONTEND_URL.startswith("https://"),
        samesite="lax",
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        secure=settings.FRONTEND_URL.startswith("https://"),
        httponly=True,
        samesite="lax",
    )


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
        room_currency=room.currency if room else None,
        rent_amount=room.rent_amount if room else None,
        property_name=property_obj.name if property_obj else None,
        landlord_name=landlord.name if landlord else None,
        has_portal_access=tenant.password_hash is not None,
    )


@router.post("/login", response_model=TenantLoginResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def tenant_login(
    request: Request,
    credentials: TenantLogin,
    response: Response,
    session: Session = Depends(get_session),
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
    _set_auth_cookie(response, access_token)

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


@router.get("/stream")
async def tenant_notification_stream(
    request: Request,
    session: Session = Depends(get_session),
):
    """
    Server-Sent Events endpoint for tenant real-time notifications.
    """
    bearer_token = get_token_from_request(request)
    if not bearer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(bearer_token)
    if payload is None or payload.get("type") != "tenant":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tenant_id = payload.get("sub")
    tenant = session.get(Tenant, tenant_id) if tenant_id else None
    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return StreamingResponse(
        notification_service.subscribe_tenant(tenant.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/setup-password", response_model=TenantPortalResponse)
@limiter.limit(SETUP_RATE_LIMIT)
async def setup_tenant_password(
    request: Request,
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


@router.post("/logout")
async def tenant_logout(
    response: Response,
    current_tenant: Tenant = Depends(get_current_tenant),
):
    """
    Logout current tenant by clearing auth cookie.
    """
    _ = current_tenant
    _clear_auth_cookie(response)
    return {"message": "Logged out"}


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
                "window_end_date": p.window_end_date,
                "status": p.status.value,
                "paid_date": p.paid_date,
                "payment_reference": p.payment_reference,
                "receipt_url": p.receipt_url,
                "notes": p.notes,
                "rejection_reason": p.rejection_reason,
                "is_manual": p.is_manual,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
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


def _get_tenant_landlord(session: Session, tenant: Tenant) -> Landlord | None:
    room = session.get(Room, tenant.room_id)
    property_obj = session.get(Property, room.property_id) if room else None
    return session.get(Landlord, property_obj.landlord_id) if property_obj else None


@router.get("/payments/{payment_id}/dispute", response_model=PaymentDisputeResponse)
async def get_tenant_payment_dispute(
    payment_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    _ = get_payment_for_tenant(session, payment_id, current_tenant.id)
    dispute = get_dispute_for_payment(session, payment_id)
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found"
        )

    mark_dispute_read(dispute, "tenant")
    session.add(dispute)
    session.commit()
    session.refresh(dispute)
    return build_dispute_response(session, dispute, "tenant")


@router.post(
    "/payments/{payment_id}/dispute/messages",
    response_model=PaymentDisputeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_tenant_payment_dispute_message(
    payment_id: str,
    payload: PaymentDisputeMessageCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    payment = get_payment_for_tenant(session, payment_id, current_tenant.id)
    body = payload.body.strip()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message body is required"
        )

    dispute = create_dispute_message(
        session,
        payment_id=payment.id,
        author_type=DisputeActorType.TENANT,
        author_id=current_tenant.id,
        body=body,
    )

    landlord = _get_tenant_landlord(session, current_tenant)
    room = session.get(Room, current_tenant.room_id)
    property_obj = session.get(Property, room.property_id) if room else None
    if landlord:
        notification = Notification(
            landlord_id=landlord.id,
            type=NotificationType.PAYMENT_DISPUTE_MESSAGE,
            title="Tenant replied on payment discussion",
            message=body,
            payment_id=payment.id,
            tenant_id=current_tenant.id,
        )
        session.add(notification)
        session.commit()

        await _run_post_commit_task(
            "broadcast_dispute_message_to_landlord",
            notification_service.broadcast_to_landlord(
                landlord.id,
                "payment_dispute_message",
                {
                    "id": notification.id,
                    "title": notification.title,
                    "message": body,
                    "payment_id": payment.id,
                    "tenant_id": current_tenant.id,
                    "tenant_name": current_tenant.name,
                    "author_type": "tenant",
                    "created_at": notification.created_at.isoformat(),
                },
            ),
            payment_id=payment.id,
            landlord_id=landlord.id,
            tenant_id=current_tenant.id,
        )
        if landlord.email and property_obj:
            await _run_post_commit_task(
                "send_dispute_email_to_landlord",
                email_service.send_payment_dispute_update(
                    recipient_name=landlord.name,
                    recipient_email=landlord.email,
                    actor_name=current_tenant.name,
                    property_name=property_obj.name,
                    room_name=room.name if room else None,
                    amount=payment.amount_due,
                    currency=room.currency if room else None,
                    message=body,
                ),
                payment_id=payment.id,
                landlord_id=landlord.id,
                tenant_id=current_tenant.id,
                recipient_email=landlord.email,
            )

    return build_dispute_response(session, dispute, "tenant")


@router.post(
    "/payments/{payment_id}/dispute/messages/attachments",
    response_model=PaymentDisputeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_tenant_payment_dispute_attachment(
    payment_id: str,
    file: UploadFile = File(...),
    body: str | None = Form(None),
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    payment = get_payment_for_tenant(session, payment_id, current_tenant.id)
    attachment_name, attachment_url, content_type, size_bytes = (
        await save_dispute_attachment(file, payment.id)
    )
    message_body = (body or "").strip() or f"Attachment shared: {attachment_name}"

    dispute = create_dispute_message(
        session,
        payment_id=payment.id,
        author_type=DisputeActorType.TENANT,
        author_id=current_tenant.id,
        body=message_body,
        attachment_name=attachment_name,
        attachment_url=attachment_url,
        attachment_content_type=content_type,
        attachment_size_bytes=size_bytes,
    )

    landlord = _get_tenant_landlord(session, current_tenant)
    room = session.get(Room, current_tenant.room_id)
    property_obj = session.get(Property, room.property_id) if room else None
    if landlord:
        notification = Notification(
            landlord_id=landlord.id,
            type=NotificationType.PAYMENT_DISPUTE_MESSAGE,
            title="Tenant shared dispute attachment",
            message=message_body,
            payment_id=payment.id,
            tenant_id=current_tenant.id,
        )
        session.add(notification)
        session.commit()

        await _run_post_commit_task(
            "broadcast_dispute_attachment_to_landlord",
            notification_service.broadcast_to_landlord(
                landlord.id,
                "payment_dispute_message",
                {
                    "id": notification.id,
                    "title": notification.title,
                    "message": message_body,
                    "payment_id": payment.id,
                    "tenant_id": current_tenant.id,
                    "tenant_name": current_tenant.name,
                    "author_type": "tenant",
                    "attachment_name": attachment_name,
                    "has_attachment": True,
                    "created_at": notification.created_at.isoformat(),
                },
            ),
            payment_id=payment.id,
            landlord_id=landlord.id,
            tenant_id=current_tenant.id,
        )
        if landlord.email and property_obj:
            await _run_post_commit_task(
                "send_dispute_attachment_email_to_landlord",
                email_service.send_payment_dispute_update(
                    recipient_name=landlord.name,
                    recipient_email=landlord.email,
                    actor_name=current_tenant.name,
                    property_name=property_obj.name,
                    room_name=room.name if room else None,
                    amount=payment.amount_due,
                    currency=room.currency if room else None,
                    message=message_body,
                    has_attachment=True,
                ),
                payment_id=payment.id,
                landlord_id=landlord.id,
                tenant_id=current_tenant.id,
                recipient_email=landlord.email,
            )

    return build_dispute_response(session, dispute, "tenant")


@router.get("/maintenance", response_model=MaintenanceRequestListResponse)
async def list_tenant_maintenance_requests(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    requests = session.exec(
        select(MaintenanceRequest)
        .where(MaintenanceRequest.tenant_id == current_tenant.id)
        .order_by(MaintenanceRequest.created_at.desc())
    ).all()
    response_items = [
        build_maintenance_response(
            session,
            maintenance_request,
            viewer_type="tenant",
            include_comments=False,
        )
        for maintenance_request in requests
    ]
    return MaintenanceRequestListResponse(requests=response_items, total=len(requests))


@router.post(
    "/maintenance",
    response_model=MaintenanceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant_maintenance_request(
    payload: MaintenanceRequestCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    room = session.get(Room, current_tenant.room_id)
    property_obj = session.get(Property, room.property_id) if room else None
    if room is None or property_obj is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant room/property context is invalid",
        )

    maintenance_request = MaintenanceRequest(
        tenant_id=current_tenant.id,
        property_id=property_obj.id,
        room_id=room.id,
        category=payload.category,
        urgency=payload.urgency,
        status=MaintenanceStatus.SUBMITTED,
        title=payload.title.strip(),
        description=payload.description.strip(),
        preferred_entry_time=(
            payload.preferred_entry_time.strip()
            if payload.preferred_entry_time
            else None
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(maintenance_request)
    session.commit()
    session.refresh(maintenance_request)

    landlord = session.get(Landlord, property_obj.landlord_id)
    if landlord:
        await _run_post_commit_task(
            "broadcast_maintenance_request_created",
            notification_service.broadcast_to_landlord(
                landlord.id,
                "maintenance_request_created",
                {
                    "request_id": maintenance_request.id,
                    "title": maintenance_request.title,
                    "message": (
                        f"{current_tenant.name} submitted a {maintenance_request.urgency.value} "
                        "maintenance request."
                    ),
                    "urgency": maintenance_request.urgency.value,
                    "tenant_id": current_tenant.id,
                    "tenant_name": current_tenant.name,
                    "property_name": property_obj.name,
                    "created_at": maintenance_request.created_at.isoformat(),
                },
            ),
            request_id=maintenance_request.id,
            landlord_id=landlord.id,
            tenant_id=current_tenant.id,
        )
        if landlord.email:
            await _run_post_commit_task(
                "send_maintenance_request_created_email",
                email_service.send_maintenance_update(
                    recipient_name=landlord.name,
                    recipient_email=landlord.email,
                    actor_name=current_tenant.name,
                    property_name=property_obj.name,
                    room_name=room.name,
                    request_title=maintenance_request.title,
                    update_summary="New maintenance request submitted",
                    message=maintenance_request.description,
                ),
                request_id=maintenance_request.id,
                landlord_id=landlord.id,
                tenant_id=current_tenant.id,
                recipient_email=landlord.email,
            )

    return build_maintenance_response(
        session, maintenance_request, viewer_type="tenant", include_comments=True
    )


@router.get("/maintenance/{request_id}", response_model=MaintenanceRequestResponse)
async def get_tenant_maintenance_request(
    request_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    maintenance_request, _, _, _, _ = get_request_for_tenant(
        session, request_id, current_tenant.id
    )
    return build_maintenance_response(
        session, maintenance_request, viewer_type="tenant", include_comments=True
    )


@router.post(
    "/maintenance/{request_id}/comments",
    response_model=MaintenanceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_tenant_maintenance_comment(
    request_id: str,
    payload: MaintenanceCommentCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    maintenance_request, _, room, property_obj, landlord = get_request_for_tenant(
        session, request_id, current_tenant.id
    )
    body = payload.body.strip()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Comment body is required"
        )

    comment = create_maintenance_comment(
        session,
        maintenance_request=maintenance_request,
        author_type=MaintenanceAuthorType.TENANT,
        author_id=current_tenant.id,
        body=body,
        is_internal=False,
    )

    await _run_post_commit_task(
        "broadcast_maintenance_comment_to_landlord",
        notification_service.broadcast_to_landlord(
            landlord.id,
            "maintenance_comment_created",
            {
                "request_id": maintenance_request.id,
                "title": "Tenant commented on a maintenance request",
                "author_type": "tenant",
                "message": body,
                "request_title": maintenance_request.title,
                "tenant_name": current_tenant.name,
                "property_name": property_obj.name,
            },
        ),
        request_id=maintenance_request.id,
        landlord_id=landlord.id,
        tenant_id=current_tenant.id,
    )
    if landlord.email:
        await _run_post_commit_task(
            "send_maintenance_comment_email_to_landlord",
            email_service.send_maintenance_update(
                recipient_name=landlord.name,
                recipient_email=landlord.email,
                actor_name=current_tenant.name,
                property_name=property_obj.name,
                room_name=room.name,
                request_title=maintenance_request.title,
                update_summary="Tenant added a comment",
                message=body,
            ),
            request_id=maintenance_request.id,
            landlord_id=landlord.id,
            tenant_id=current_tenant.id,
            recipient_email=landlord.email,
        )

    updated = session.get(MaintenanceRequest, maintenance_request.id)
    return build_maintenance_response(
        session, updated, viewer_type="tenant", include_comments=True
    )


@router.post(
    "/maintenance/{request_id}/comments/attachments",
    response_model=MaintenanceRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_tenant_maintenance_attachment_comment(
    request_id: str,
    file: UploadFile = File(...),
    body: str | None = Form(None),
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    maintenance_request, _, room, property_obj, landlord = get_request_for_tenant(
        session, request_id, current_tenant.id
    )
    attachment_name, attachment_url, content_type, size_bytes = (
        await save_maintenance_attachment(file, maintenance_request.id)
    )
    message_body = (body or "").strip() or f"Attachment shared: {attachment_name}"

    comment = create_maintenance_comment(
        session,
        maintenance_request=maintenance_request,
        author_type=MaintenanceAuthorType.TENANT,
        author_id=current_tenant.id,
        body=message_body,
        is_internal=False,
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

    await _run_post_commit_task(
        "broadcast_maintenance_attachment_to_landlord",
        notification_service.broadcast_to_landlord(
            landlord.id,
            "maintenance_comment_created",
            {
                "request_id": maintenance_request.id,
                "title": "Tenant shared a maintenance attachment",
                "author_type": "tenant",
                "message": message_body,
                "request_title": maintenance_request.title,
                "tenant_name": current_tenant.name,
                "property_name": property_obj.name,
                "attachment_url": secure_attachment_url,
            },
        ),
        request_id=maintenance_request.id,
        landlord_id=landlord.id,
        tenant_id=current_tenant.id,
    )
    if landlord.email:
        await _run_post_commit_task(
            "send_maintenance_attachment_email_to_landlord",
            email_service.send_maintenance_update(
                recipient_name=landlord.name,
                recipient_email=landlord.email,
                actor_name=current_tenant.name,
                property_name=property_obj.name,
                room_name=room.name,
                request_title=maintenance_request.title,
                update_summary="Tenant shared an attachment",
                message=message_body,
            ),
            request_id=maintenance_request.id,
            landlord_id=landlord.id,
            tenant_id=current_tenant.id,
            recipient_email=landlord.email,
        )

    updated = session.get(MaintenanceRequest, maintenance_request.id)
    return build_maintenance_response(
        session, updated, viewer_type="tenant", include_comments=True
    )


@router.put("/maintenance/{request_id}/resolve", response_model=MaintenanceRequestResponse)
async def resolve_tenant_maintenance_request(
    request_id: str,
    payload: MaintenanceResolveRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    maintenance_request, _, room, property_obj, landlord = get_request_for_tenant(
        session, request_id, current_tenant.id
    )
    assert_valid_status_transition(maintenance_request.status, MaintenanceStatus.COMPLETED)

    maintenance_request.status = MaintenanceStatus.COMPLETED
    maintenance_request.completed_at = datetime.now(timezone.utc)
    if payload.tenant_rating is not None:
        maintenance_request.tenant_rating = payload.tenant_rating
    if payload.tenant_feedback is not None:
        maintenance_request.tenant_feedback = payload.tenant_feedback.strip()
    maintenance_request.updated_at = datetime.now(timezone.utc)
    session.add(maintenance_request)
    session.commit()
    session.refresh(maintenance_request)

    await _run_post_commit_task(
        "broadcast_maintenance_completed_to_landlord",
        notification_service.broadcast_to_landlord(
            landlord.id,
            "maintenance_request_updated",
            {
                "request_id": maintenance_request.id,
                "title": "Tenant marked maintenance as completed",
                "message": payload.tenant_feedback.strip()
                if payload.tenant_feedback
                else "Tenant marked the request as completed.",
                "request_title": maintenance_request.title,
                "status": maintenance_request.status.value,
                "tenant_rating": maintenance_request.tenant_rating,
                "updated_at": maintenance_request.updated_at.isoformat(),
            },
        ),
        request_id=maintenance_request.id,
        landlord_id=landlord.id,
        tenant_id=current_tenant.id,
    )
    if landlord.email:
        await _run_post_commit_task(
            "send_maintenance_completed_email_to_landlord",
            email_service.send_maintenance_update(
                recipient_name=landlord.name,
                recipient_email=landlord.email,
                actor_name=current_tenant.name,
                property_name=property_obj.name,
                room_name=room.name,
                request_title=maintenance_request.title,
                update_summary="Tenant marked the request completed",
                message=payload.tenant_feedback.strip()
                if payload.tenant_feedback
                else "Tenant marked the request as completed.",
            ),
            request_id=maintenance_request.id,
            landlord_id=landlord.id,
            tenant_id=current_tenant.id,
            recipient_email=landlord.email,
        )

    return build_maintenance_response(
        session, maintenance_request, viewer_type="tenant", include_comments=True
    )


@router.put("/maintenance/{request_id}/reopen", response_model=MaintenanceRequestResponse)
async def reopen_tenant_maintenance_request(
    request_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    maintenance_request, _, room, property_obj, landlord = get_request_for_tenant(
        session, request_id, current_tenant.id
    )
    assert_valid_status_transition(
        maintenance_request.status, MaintenanceStatus.ACKNOWLEDGED
    )
    maintenance_request.status = MaintenanceStatus.ACKNOWLEDGED
    maintenance_request.completed_at = None
    maintenance_request.updated_at = datetime.now(timezone.utc)
    session.add(maintenance_request)
    session.commit()
    session.refresh(maintenance_request)

    await _run_post_commit_task(
        "broadcast_maintenance_reopened_to_landlord",
        notification_service.broadcast_to_landlord(
            landlord.id,
            "maintenance_request_updated",
            {
                "request_id": maintenance_request.id,
                "title": "Tenant reopened a maintenance request",
                "message": maintenance_request.title,
                "request_title": maintenance_request.title,
                "status": maintenance_request.status.value,
                "updated_at": maintenance_request.updated_at.isoformat(),
            },
        ),
        request_id=maintenance_request.id,
        landlord_id=landlord.id,
        tenant_id=current_tenant.id,
    )
    if landlord.email:
        await _run_post_commit_task(
            "send_maintenance_reopened_email_to_landlord",
            email_service.send_maintenance_update(
                recipient_name=landlord.name,
                recipient_email=landlord.email,
                actor_name=current_tenant.name,
                property_name=property_obj.name,
                room_name=room.name,
                request_title=maintenance_request.title,
                update_summary="Tenant reopened the request",
                message="The tenant asked for more work or follow-up on this request.",
            ),
            request_id=maintenance_request.id,
            landlord_id=landlord.id,
            tenant_id=current_tenant.id,
            recipient_email=landlord.email,
        )

    return build_maintenance_response(
        session, maintenance_request, viewer_type="tenant", include_comments=True
    )

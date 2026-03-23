from datetime import datetime, timezone
from typing import Optional, Literal
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.models.payment import Payment
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment_dispute import (
    PaymentDispute,
    PaymentDisputeMessage,
    DisputeActorType,
    DisputeStatus,
)
from app.schemas.payment import PaymentDisputeMessageResponse, PaymentDisputeResponse

DisputeViewerType = Literal["landlord", "tenant"]

_ALLOWED_ATTACHMENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}
_MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
_DISPUTE_UPLOADS_DIR = os.path.normpath(os.path.join("uploads", "disputes"))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_payment_for_landlord(
    session: Session, payment_id: str, landlord_id: str
) -> tuple[Payment, Tenant, Property]:
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    tenant = session.get(Tenant, payment.tenant_id)
    room = session.get(Room, tenant.room_id) if tenant else None
    property_obj = session.get(Property, room.property_id) if room else None

    if not tenant or not room or not property_obj or property_obj.landlord_id != landlord_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    return payment, tenant, property_obj


def get_payment_for_tenant(session: Session, payment_id: str, tenant_id: str) -> Payment:
    payment = session.get(Payment, payment_id)
    if not payment or payment.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )
    return payment


def get_dispute_for_payment(session: Session, payment_id: str) -> Optional[PaymentDispute]:
    return session.exec(
        select(PaymentDispute).where(PaymentDispute.payment_id == payment_id)
    ).first()


def get_or_create_dispute(
    session: Session,
    payment_id: str,
    opened_by_type: DisputeActorType,
    opened_by_id: str,
) -> PaymentDispute:
    dispute = get_dispute_for_payment(session, payment_id)
    if dispute:
        return dispute

    created_at = now_utc()
    dispute = PaymentDispute(
        payment_id=payment_id,
        status=DisputeStatus.OPEN,
        opened_by_type=opened_by_type,
        opened_by_id=opened_by_id,
        opened_at=created_at,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(dispute)
    session.commit()
    session.refresh(dispute)
    return dispute


def _get_dispute_messages(session: Session, dispute_id: str) -> list[PaymentDisputeMessage]:
    return session.exec(
        select(PaymentDisputeMessage)
        .where(PaymentDisputeMessage.dispute_id == dispute_id)
        .order_by(PaymentDisputeMessage.created_at.asc())
    ).all()


def get_unread_count(
    session: Session, dispute: PaymentDispute, viewer_type: DisputeViewerType
) -> int:
    messages = _get_dispute_messages(session, dispute.id)
    if viewer_type == "landlord":
        unread_author = DisputeActorType.TENANT
        read_at = dispute.landlord_last_read_at
    else:
        unread_author = DisputeActorType.LANDLORD
        read_at = dispute.tenant_last_read_at

    unread_messages = [m for m in messages if m.author_type == unread_author]
    if not read_at:
        return len(unread_messages)
    return len([m for m in unread_messages if m.created_at > read_at])


def mark_dispute_read(dispute: PaymentDispute, viewer_type: DisputeViewerType) -> None:
    timestamp = now_utc()
    if viewer_type == "landlord":
        dispute.landlord_last_read_at = timestamp
    else:
        dispute.tenant_last_read_at = timestamp
    dispute.updated_at = timestamp


def assert_dispute_open(dispute: PaymentDispute) -> None:
    if dispute.status == DisputeStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dispute is resolved. Reopen to continue discussion.",
        )


def create_dispute_message(
    session: Session,
    payment_id: str,
    author_type: DisputeActorType,
    author_id: str,
    body: str,
    attachment_name: Optional[str] = None,
    attachment_url: Optional[str] = None,
    attachment_content_type: Optional[str] = None,
    attachment_size_bytes: Optional[int] = None,
) -> PaymentDispute:
    dispute = get_or_create_dispute(
        session,
        payment_id=payment_id,
        opened_by_type=author_type,
        opened_by_id=author_id,
    )
    assert_dispute_open(dispute)

    timestamp = now_utc()
    message = PaymentDisputeMessage(
        dispute_id=dispute.id,
        payment_id=payment_id,
        author_type=author_type,
        author_id=author_id,
        body=body,
        attachment_name=attachment_name,
        attachment_url=attachment_url,
        attachment_content_type=attachment_content_type,
        attachment_size_bytes=attachment_size_bytes,
        created_at=timestamp,
    )
    session.add(message)

    dispute.last_message_at = timestamp
    dispute.updated_at = timestamp
    if author_type == DisputeActorType.LANDLORD:
        dispute.landlord_last_read_at = timestamp
    elif author_type == DisputeActorType.TENANT:
        dispute.tenant_last_read_at = timestamp

    session.add(dispute)
    session.commit()
    session.refresh(dispute)
    return dispute


def resolve_dispute(
    session: Session,
    payment_id: str,
    actor_type: DisputeActorType,
    actor_id: str,
) -> PaymentDispute:
    dispute = get_dispute_for_payment(session, payment_id)
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found"
        )

    timestamp = now_utc()
    dispute.status = DisputeStatus.RESOLVED
    dispute.resolved_by_type = actor_type
    dispute.resolved_by_id = actor_id
    dispute.resolved_at = timestamp
    dispute.updated_at = timestamp
    session.add(dispute)
    session.commit()
    session.refresh(dispute)
    return dispute


def reopen_dispute(session: Session, payment_id: str) -> PaymentDispute:
    dispute = get_dispute_for_payment(session, payment_id)
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found"
        )

    timestamp = now_utc()
    dispute.status = DisputeStatus.OPEN
    dispute.resolved_by_type = None
    dispute.resolved_by_id = None
    dispute.resolved_at = None
    dispute.updated_at = timestamp
    session.add(dispute)
    session.commit()
    session.refresh(dispute)
    return dispute


def build_dispute_response(
    session: Session,
    dispute: PaymentDispute,
    viewer_type: DisputeViewerType,
) -> PaymentDisputeResponse:
    messages = _get_dispute_messages(session, dispute.id)
    unread_count = get_unread_count(session, dispute, viewer_type)

    return PaymentDisputeResponse(
        id=dispute.id,
        payment_id=dispute.payment_id,
        status=dispute.status,
        opened_by_type=dispute.opened_by_type,
        opened_by_id=dispute.opened_by_id,
        opened_at=dispute.opened_at,
        resolved_by_type=dispute.resolved_by_type,
        resolved_by_id=dispute.resolved_by_id,
        resolved_at=dispute.resolved_at,
        landlord_last_read_at=dispute.landlord_last_read_at,
        tenant_last_read_at=dispute.tenant_last_read_at,
        last_message_at=dispute.last_message_at,
        unread_count=unread_count,
        messages=[
            PaymentDisputeMessageResponse.model_validate(message)
            for message in messages
        ],
    )


async def save_dispute_attachment(
    file: UploadFile, payment_id: str
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
    safe_name = f"{payment_id}_{uuid.uuid4()}{extension}"
    os.makedirs(_DISPUTE_UPLOADS_DIR, exist_ok=True)
    file_path = os.path.join(_DISPUTE_UPLOADS_DIR, safe_name)

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    return (
        file.filename or safe_name,
        f"/uploads/disputes/{safe_name}",
        content_type,
        size_bytes,
    )


def resolve_dispute_attachment_file_path(attachment_url: str) -> str:
    if not attachment_url.startswith("/uploads/disputes/"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
        )

    filename = os.path.basename(attachment_url)
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
        )

    file_path = os.path.normpath(os.path.join(_DISPUTE_UPLOADS_DIR, filename))
    if os.path.commonpath([_DISPUTE_UPLOADS_DIR, file_path]) != _DISPUTE_UPLOADS_DIR:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
        )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
        )

    return file_path


from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from typing import Optional

from app.core.database import get_session
from app.core.security import get_current_landlord
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment import Payment
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse, NotificationListResponse
from app.services import notification_service, email_service, sms_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/stream")
async def notification_stream(
    current_landlord: Landlord = Depends(get_current_landlord),
):
    """
    Server-Sent Events endpoint for real-time notifications.
    Connect to this endpoint to receive live updates.
    """
    return StreamingResponse(
        notification_service.subscribe(current_landlord.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    List notifications for the current landlord.
    """
    query = select(Notification).where(Notification.landlord_id == current_landlord.id)

    if unread_only:
        query = query.where(Notification.is_read == False)

    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    notifications = session.exec(query).all()

    # Get total count
    total_query = select(Notification).where(
        Notification.landlord_id == current_landlord.id
    )
    total = len(session.exec(total_query).all())

    # Get unread count
    unread_query = select(Notification).where(
        Notification.landlord_id == current_landlord.id, Notification.is_read == False
    )
    unread_count = len(session.exec(unread_query).all())

    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Mark a notification as read.
    """
    notification = session.get(Notification, notification_id)
    if not notification or notification.landlord_id != current_landlord.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    notification.is_read = True
    session.add(notification)
    session.commit()

    return {"message": "Notification marked as read"}


@router.put("/read-all")
async def mark_all_notifications_read(
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Mark all notifications as read.
    """
    notifications = session.exec(
        select(Notification).where(
            Notification.landlord_id == current_landlord.id,
            Notification.is_read == False,
        )
    ).all()

    for notification in notifications:
        notification.is_read = True
        session.add(notification)

    session.commit()

    return {"message": f"Marked {len(notifications)} notifications as read"}


@router.post("/send-reminder/{payment_id}")
async def send_payment_reminder(
    payment_id: str,
    method: str = Query("email", regex="^(email|sms|both)$"),
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Send a payment reminder to the tenant.

    Args:
        payment_id: The payment to send reminder for
        method: "email", "sms", or "both"
    """
    # Get payment and verify ownership
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    # Get tenant
    tenant = session.get(Tenant, payment.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    # Get room and property
    room = session.get(Room, tenant.room_id)
    property = session.get(Property, room.property_id) if room else None

    if not property or property.landlord_id != current_landlord.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    results = {"email": None, "sms": None}

    # Send email
    if method in ["email", "both"] and tenant.email:
        email_sent = await email_service.send_payment_reminder(
            tenant_name=tenant.name,
            tenant_email=tenant.email,
            amount=payment.amount_due,
            due_date=payment.due_date.strftime("%B %d, %Y"),
            property_name=property.name,
            room_name=room.name,
            landlord_name=current_landlord.name,
        )
        results["email"] = "sent" if email_sent else "failed"
    elif method in ["email", "both"]:
        results["email"] = "no_email"

    # Send SMS
    if method in ["sms", "both"] and tenant.phone:
        sms_sent = await sms_service.send_payment_reminder_sms(
            phone_number=tenant.phone,
            tenant_name=tenant.name,
            amount=payment.amount_due,
            due_date=payment.due_date.strftime("%B %d"),
            property_name=property.name,
        )
        results["sms"] = "sent" if sms_sent else "failed"
    elif method in ["sms", "both"]:
        results["sms"] = "no_phone"

    # Record that reminder was sent
    await notification_service.notify_reminder_sent(
        landlord_id=current_landlord.id,
        tenant_name=tenant.name,
        method=method,
        payment_id=payment_id,
        session=session,
    )

    return {"message": f"Reminder sent via {method}", "results": results}

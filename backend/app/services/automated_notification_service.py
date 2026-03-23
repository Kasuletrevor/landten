"""
Automated payment reminder service.

Runs scheduled due/overdue reminder delivery and prevents duplicate sends
for the same payment on the same day.
"""

from datetime import date, datetime, time, timedelta, timezone

from sqlmodel import Session, select

from app.models.landlord import Landlord
from app.models.notification import Notification, NotificationType
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.services import email_service, notification_service

_DUE_DAY_OFFSETS = {0, 1, 3}
_OVERDUE_DAY_OFFSETS = {1, 7, 14}


def _already_sent_today(session: Session, payment_id: str, today: date) -> bool:
    existing = session.exec(
        select(Notification).where(
            Notification.payment_id == payment_id,
            Notification.type == NotificationType.REMINDER_SENT,
        )
        .order_by(Notification.created_at.desc())
    ).first()
    if existing is None:
        return False
    return existing.created_at.date() == today


def _load_payment_context(
    session: Session, payment: Payment
) -> tuple[Tenant, Room, Property, Landlord] | None:
    tenant = session.get(Tenant, payment.tenant_id)
    if tenant is None:
        return None

    room = session.get(Room, tenant.room_id)
    if room is None:
        return None

    property_obj = session.get(Property, room.property_id)
    if property_obj is None:
        return None

    landlord = session.get(Landlord, property_obj.landlord_id)
    if landlord is None:
        return None

    return tenant, room, property_obj, landlord


async def send_automated_payment_notifications(
    session: Session, today: date | None = None
) -> dict[str, int]:
    """
    Send automated payment reminders for due and overdue milestones.

    Returns summary counters for observability/testing.
    """
    target_day = today or date.today()
    due_dates = [target_day + timedelta(days=offset) for offset in _DUE_DAY_OFFSETS]

    due_candidates = session.exec(
        select(Payment).where(
            Payment.status.in_([PaymentStatus.UPCOMING, PaymentStatus.PENDING]),
            Payment.due_date.in_(due_dates),
        )
    ).all()

    overdue_candidates_raw = session.exec(
        select(Payment).where(Payment.status == PaymentStatus.OVERDUE)
    ).all()
    overdue_candidates = [
        payment
        for payment in overdue_candidates_raw
        if (target_day - payment.window_end_date).days in _OVERDUE_DAY_OFFSETS
    ]

    summary = {
        "due_candidates": len(due_candidates),
        "overdue_candidates": len(overdue_candidates),
        "reminders_sent": 0,
        "skipped_already_sent": 0,
        "skipped_no_contact": 0,
        "skipped_missing_context": 0,
        "failed_delivery": 0,
    }

    for payment in [*due_candidates, *overdue_candidates]:
        if _already_sent_today(session, payment.id, target_day):
            summary["skipped_already_sent"] += 1
            continue

        context = _load_payment_context(session, payment)
        if context is None:
            summary["skipped_missing_context"] += 1
            continue

        tenant, room, property_obj, landlord = context
        if not tenant.email:
            summary["skipped_no_contact"] += 1
            continue

        channels_sent: list[str] = []
        is_overdue = payment.status == PaymentStatus.OVERDUE

        if tenant.email:
            if is_overdue:
                sent_email = await email_service.send_overdue_notice(
                    tenant_name=tenant.name,
                    tenant_email=tenant.email,
                    amount=payment.amount_due,
                    due_date=payment.due_date.strftime("%B %d, %Y"),
                    property_name=property_obj.name,
                    room_name=room.name,
                    landlord_name=landlord.name,
                    currency=room.currency,
                )
            else:
                sent_email = await email_service.send_payment_reminder(
                    tenant_name=tenant.name,
                    tenant_email=tenant.email,
                    amount=payment.amount_due,
                    due_date=payment.due_date.strftime("%B %d, %Y"),
                    property_name=property_obj.name,
                    room_name=room.name,
                    landlord_name=landlord.name,
                    currency=room.currency,
                )
            if sent_email:
                channels_sent.append("email")

        if not channels_sent:
            summary["failed_delivery"] += 1
            continue

        await notification_service.notify_reminder_sent(
            landlord_id=landlord.id,
            tenant_name=tenant.name,
            method="+".join(channels_sent),
            payment_id=payment.id,
            session=session,
            created_at=datetime.combine(target_day, time(hour=9, minute=0), tzinfo=timezone.utc),
        )
        summary["reminders_sent"] += 1

    return summary

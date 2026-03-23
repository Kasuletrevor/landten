from datetime import date, timedelta

import pytest
from sqlmodel import Session, select

from app.models.notification import Notification, NotificationType
from app.models.payment import PaymentStatus
from app.services.automated_notification_service import (
    send_automated_payment_notifications,
)
from tests.factories import (
    LandlordFactory,
    PaymentFactory,
    PropertyFactory,
    RoomFactory,
    TenantFactory,
)


def _create_payment_context(
    session: Session,
    *,
    due_date: date,
    window_end_date: date,
    status: PaymentStatus,
    email: str | None = "tenant@test.com",
    phone: str | None = "555-1234",
):
    landlord = LandlordFactory.create(session=session)
    property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(session=session, property_id=property_obj.id)
    tenant = TenantFactory.create(
        session=session,
        room_id=room.id,
        email=email,
        phone=phone,
    )
    payment = PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        due_date=due_date,
        window_end_date=window_end_date,
        status=status,
    )
    return payment


@pytest.mark.asyncio
async def test_due_reminder_is_sent_and_recorded(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    today = date(2026, 2, 11)
    payment = _create_payment_context(
        session,
        due_date=today + timedelta(days=3),
        window_end_date=today + timedelta(days=8),
        status=PaymentStatus.UPCOMING,
    )

    async def _email_ok(*args, **kwargs):
        return True

    monkeypatch.setattr(
        "app.services.email_service.send_payment_reminder",
        _email_ok,
    )

    summary = await send_automated_payment_notifications(session, today=today)

    assert summary["due_candidates"] == 1
    assert summary["overdue_candidates"] == 0
    assert summary["reminders_sent"] == 1
    assert summary["skipped_already_sent"] == 0

    reminders = session.exec(
        select(Notification).where(
            Notification.payment_id == payment.id,
            Notification.type == NotificationType.REMINDER_SENT,
        )
    ).all()
    assert len(reminders) == 1


@pytest.mark.asyncio
async def test_same_day_runs_do_not_send_duplicate_reminder(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    today = date(2026, 2, 11)
    payment = _create_payment_context(
        session,
        due_date=today + timedelta(days=1),
        window_end_date=today + timedelta(days=6),
        status=PaymentStatus.PENDING,
    )
    calls = {"email": 0}

    async def _email_ok(*args, **kwargs):
        calls["email"] += 1
        return True

    monkeypatch.setattr(
        "app.services.email_service.send_payment_reminder",
        _email_ok,
    )

    first_run = await send_automated_payment_notifications(session, today=today)
    second_run = await send_automated_payment_notifications(session, today=today)

    assert first_run["reminders_sent"] == 1
    assert second_run["reminders_sent"] == 0
    assert second_run["skipped_already_sent"] == 1
    assert calls["email"] == 1

    reminders = session.exec(
        select(Notification).where(
            Notification.payment_id == payment.id,
            Notification.type == NotificationType.REMINDER_SENT,
        )
    ).all()
    assert len(reminders) == 1


@pytest.mark.asyncio
async def test_overdue_day_seven_notice_is_sent(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    today = date(2026, 2, 11)
    _ = _create_payment_context(
        session,
        due_date=today - timedelta(days=12),
        window_end_date=today - timedelta(days=7),
        status=PaymentStatus.OVERDUE,
    )
    calls = {"email": 0}

    async def _overdue_email_ok(*args, **kwargs):
        calls["email"] += 1
        return True

    monkeypatch.setattr(
        "app.services.email_service.send_overdue_notice",
        _overdue_email_ok,
    )

    summary = await send_automated_payment_notifications(session, today=today)

    assert summary["due_candidates"] == 0
    assert summary["overdue_candidates"] == 1
    assert summary["reminders_sent"] == 1
    assert calls["email"] == 1


@pytest.mark.asyncio
async def test_skips_when_tenant_has_no_contact_channels(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    today = date(2026, 2, 11)
    payment = _create_payment_context(
        session,
        due_date=today,
        window_end_date=today + timedelta(days=5),
        status=PaymentStatus.PENDING,
        email=None,
        phone=None,
    )

    async def _unexpected_call(*args, **kwargs):
        raise AssertionError("Delivery function should not be called")

    monkeypatch.setattr(
        "app.services.email_service.send_payment_reminder",
        _unexpected_call,
    )

    summary = await send_automated_payment_notifications(session, today=today)

    assert summary["due_candidates"] == 1
    assert summary["reminders_sent"] == 0
    assert summary["skipped_no_contact"] == 1

    reminders = session.exec(
        select(Notification).where(
            Notification.payment_id == payment.id,
            Notification.type == NotificationType.REMINDER_SENT,
        )
    ).all()
    assert reminders == []


@pytest.mark.asyncio
async def test_skips_when_tenant_has_phone_but_no_email(
    session: Session, monkeypatch: pytest.MonkeyPatch
):
    today = date(2026, 2, 11)
    payment = _create_payment_context(
        session,
        due_date=today,
        window_end_date=today + timedelta(days=5),
        status=PaymentStatus.PENDING,
        email=None,
        phone="555-1234",
    )

    async def _unexpected_call(*args, **kwargs):
        raise AssertionError("Email delivery should not be called without an email")

    monkeypatch.setattr(
        "app.services.email_service.send_payment_reminder",
        _unexpected_call,
    )

    summary = await send_automated_payment_notifications(session, today=today)

    assert summary["due_candidates"] == 1
    assert summary["reminders_sent"] == 0
    assert summary["skipped_no_contact"] == 1

    reminders = session.exec(
        select(Notification).where(
            Notification.payment_id == payment.id,
            Notification.type == NotificationType.REMINDER_SENT,
        )
    ).all()
    assert reminders == []

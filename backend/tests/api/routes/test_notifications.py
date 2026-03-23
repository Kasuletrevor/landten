from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token
from tests.factories import (
    LandlordFactory,
    PaymentFactory,
    PropertyFactory,
    RoomFactory,
    TenantFactory,
)


def _create_payment_for_landlord(session: Session):
    landlord = LandlordFactory.create(session=session)
    property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
    room = RoomFactory.create(session=session, property_id=property_obj.id)
    tenant = TenantFactory.create(session=session, room_id=room.id)
    payment = PaymentFactory.create(session=session, tenant_id=tenant.id)
    return landlord, tenant, payment


def test_send_payment_reminder_rejects_sms_method(
    client: TestClient, session: Session
):
    landlord, _, payment = _create_payment_for_landlord(session)
    headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': landlord.id, 'type': 'landlord'})}"
    }

    response = client.post(
        f"/api/notifications/send-reminder/{payment.id}?method=sms",
        headers=headers,
    )

    assert response.status_code == 422


def test_send_payment_reminder_email_only(
    client: TestClient, session: Session, monkeypatch
):
    landlord, tenant, payment = _create_payment_for_landlord(session)
    calls = {"email": 0}

    async def _email_ok(*args, **kwargs):
        calls["email"] += 1
        assert kwargs["tenant_email"] == tenant.email
        return True

    monkeypatch.setattr(
        "app.services.email_service.send_payment_reminder",
        _email_ok,
    )

    headers = {
        "Authorization": f"Bearer {create_access_token(data={'sub': landlord.id, 'type': 'landlord'})}"
    }

    response = client.post(
        f"/api/notifications/send-reminder/{payment.id}?method=email",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["results"] == {"email": "sent"}
    assert calls["email"] == 1

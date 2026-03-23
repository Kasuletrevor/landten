"""
Tests for payment dispute thread APIs.
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import AUTH_COOKIE_NAME, create_access_token
from app.models.notification import Notification, NotificationType
from app.models.payment import PaymentStatus
from tests.factories import (
    PropertyFactory,
    RoomFactory,
    TenantFactory,
    PaymentScheduleFactory,
    PaymentFactory,
    create_full_test_scenario,
)


def _create_landlord_payment_context(session: Session, landlord_id: str):
    """Create a payment tied to the given landlord and return tenant + payment."""
    property_obj = PropertyFactory.create(session=session, landlord_id=landlord_id)
    room = RoomFactory.create(session=session, property_id=property_obj.id)
    tenant = TenantFactory.create(session=session, room_id=room.id)
    schedule = PaymentScheduleFactory.create(session=session, tenant_id=tenant.id)
    payment = PaymentFactory.create(
        session=session,
        tenant_id=tenant.id,
        schedule_id=schedule.id,
        status=PaymentStatus.PENDING,
        due_date=date.today(),
        window_end_date=date.today() + timedelta(days=5),
    )
    return tenant, payment


def test_landlord_can_create_and_read_dispute(
    client: TestClient,
    session: Session,
    auth_landlord,
    auth_headers: dict,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)

    create_response = client.post(
        f"/api/payments/{payment.id}/dispute/messages",
        headers=auth_headers,
        json={"body": "The receipt amount does not match."},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "open"
    assert len(created["messages"]) == 1
    assert created["messages"][0]["author_type"] == "landlord"
    assert created["messages"][0]["body"] == "The receipt amount does not match."

    read_response = client.get(f"/api/payments/{payment.id}/dispute", headers=auth_headers)
    assert read_response.status_code == 200
    read_data = read_response.json()
    assert read_data["payment_id"] == payment.id
    assert len(read_data["messages"]) == 1
    assert read_data["unread_count"] == 0


def test_tenant_message_creates_landlord_notification(
    client: TestClient,
    session: Session,
    auth_landlord,
    auth_headers: dict,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)
    tenant_token = create_access_token(data={"sub": tenant.id, "type": "tenant"})
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    response = client.post(
        f"/api/tenant-auth/payments/{payment.id}/dispute/messages",
        headers=tenant_headers,
        json={"body": "I paid yesterday, please verify transaction ID 9982."},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "open"
    assert data["messages"][-1]["author_type"] == "tenant"

    list_response = client.get(f"/api/payments/{payment.id}", headers=auth_headers)
    assert list_response.status_code == 200
    payment_data = list_response.json()
    assert payment_data["dispute_status"] == "open"
    assert payment_data["dispute_unread_count"] == 1

    notifications = session.exec(
        select(Notification).where(Notification.payment_id == payment.id)
    ).all()
    assert any(n.type == NotificationType.PAYMENT_DISPUTE_MESSAGE for n in notifications)


def test_landlord_dispute_message_sends_tenant_email(
    client: TestClient,
    session: Session,
    auth_landlord,
    auth_headers: dict,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)

    with patch(
        "app.routers.payments.email_service.send_payment_dispute_update",
        new=AsyncMock(return_value=True),
    ) as email_mock:
        response = client.post(
            f"/api/payments/{payment.id}/dispute/messages",
            headers=auth_headers,
            json={"body": "Please clarify the transfer timestamp."},
        )

    assert response.status_code == 201
    assert response.json()["messages"][-1]["author_type"] == "landlord"
    email_mock.assert_awaited_once()
    email_kwargs = email_mock.await_args.kwargs
    assert email_kwargs["recipient_email"] == tenant.email
    assert email_kwargs["recipient_name"] == tenant.name
    assert email_kwargs["actor_name"] == auth_landlord.name


def test_tenant_dispute_message_sends_landlord_email(
    client: TestClient,
    session: Session,
    auth_landlord,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)
    tenant_token = create_access_token(data={"sub": tenant.id, "type": "tenant"})
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    with patch(
        "app.routers.tenant_auth.email_service.send_payment_dispute_update",
        new=AsyncMock(return_value=True),
    ) as email_mock:
        response = client.post(
            f"/api/tenant-auth/payments/{payment.id}/dispute/messages",
            headers=tenant_headers,
            json={"body": "Bank confirmed the transfer on my side."},
        )

    assert response.status_code == 201
    assert response.json()["messages"][-1]["author_type"] == "tenant"
    email_mock.assert_awaited_once()
    email_kwargs = email_mock.await_args.kwargs
    assert email_kwargs["recipient_name"] == auth_landlord.name
    assert email_kwargs["recipient_email"] == auth_landlord.email


def test_landlord_dispute_message_skips_email_for_email_less_tenant(
    client: TestClient,
    session: Session,
    auth_landlord,
    auth_headers: dict,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)
    tenant.email = None
    session.add(tenant)
    session.commit()

    with patch(
        "app.routers.payments.email_service.send_payment_dispute_update",
        new=AsyncMock(return_value=True),
    ) as email_mock:
        response = client.post(
            f"/api/payments/{payment.id}/dispute/messages",
            headers=auth_headers,
            json={"body": "Confirming the amount mismatch."},
        )

    assert response.status_code == 201
    email_mock.assert_not_awaited()


def test_resolved_dispute_blocks_posting_until_reopened(
    client: TestClient,
    session: Session,
    auth_landlord,
    auth_headers: dict,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)
    tenant_token = create_access_token(data={"sub": tenant.id, "type": "tenant"})
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    create_response = client.post(
        f"/api/payments/{payment.id}/dispute/messages",
        headers=auth_headers,
        json={"body": "Please confirm this discrepancy."},
    )
    assert create_response.status_code == 201

    resolve_response = client.put(
        f"/api/payments/{payment.id}/dispute/resolve", headers=auth_headers
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "resolved"

    blocked_response = client.post(
        f"/api/tenant-auth/payments/{payment.id}/dispute/messages",
        headers=tenant_headers,
        json={"body": "I still need clarification."},
    )
    assert blocked_response.status_code == 409

    reopen_response = client.put(
        f"/api/payments/{payment.id}/dispute/reopen", headers=auth_headers
    )
    assert reopen_response.status_code == 200
    assert reopen_response.json()["status"] == "open"

    allowed_response = client.post(
        f"/api/tenant-auth/payments/{payment.id}/dispute/messages",
        headers=tenant_headers,
        json={"body": "Thanks, adding more details here."},
    )
    assert allowed_response.status_code == 201


def test_tenant_cannot_access_other_tenant_dispute(
    client: TestClient,
    session: Session,
    auth_landlord,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)
    _ = tenant  # test setup clarity
    scenario = create_full_test_scenario(session)
    other_tenant = scenario["tenant"]
    other_tenant_token = create_access_token(data={"sub": other_tenant.id, "type": "tenant"})
    other_tenant_headers = {"Authorization": f"Bearer {other_tenant_token}"}

    get_response = client.get(
        f"/api/tenant-auth/payments/{payment.id}/dispute",
        headers=other_tenant_headers,
    )
    post_response = client.post(
        f"/api/tenant-auth/payments/{payment.id}/dispute/messages",
        headers=other_tenant_headers,
        json={"body": "Not my payment"},
    )

    assert get_response.status_code == 404
    assert post_response.status_code == 404


def test_tenant_can_post_dispute_attachment_and_download(
    client: TestClient,
    session: Session,
    auth_landlord,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)
    tenant_token = create_access_token(data={"sub": tenant.id, "type": "tenant"})
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    response = client.post(
        f"/api/tenant-auth/payments/{payment.id}/dispute/messages/attachments",
        headers=tenant_headers,
        data={"body": "Sharing transfer receipt as evidence."},
        files={
            "file": ("receipt-proof.pdf", b"%PDF-1.4\n%EOF", "application/pdf"),
        },
    )
    assert response.status_code == 201
    payload = response.json()
    message = payload["messages"][-1]
    assert message["author_type"] == "tenant"
    assert message["attachment_name"] == "receipt-proof.pdf"
    assert message["attachment_url"].startswith("/uploads/disputes/")

    download_response = client.get(
        f"/api/payments/{payment.id}/dispute/messages/{message['id']}/attachment",
        headers=tenant_headers,
    )
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"


def test_landlord_can_post_dispute_attachment(
    client: TestClient,
    session: Session,
    auth_landlord,
    auth_headers: dict,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)
    tenant_token = create_access_token(data={"sub": tenant.id, "type": "tenant"})
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    response = client.post(
        f"/api/payments/{payment.id}/dispute/messages/attachments",
        headers=auth_headers,
        data={"body": "Screenshot of ledger entry."},
        files={"file": ("ledger.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert response.status_code == 201
    data = response.json()
    landlord_message = data["messages"][-1]
    assert landlord_message["author_type"] == "landlord"
    assert landlord_message["attachment_name"] == "ledger.png"

    tenant_thread = client.get(
        f"/api/tenant-auth/payments/{payment.id}/dispute",
        headers=tenant_headers,
    )
    assert tenant_thread.status_code == 200
    tenant_data = tenant_thread.json()
    assert tenant_data["messages"][-1]["attachment_name"] == "ledger.png"


def test_dispute_attachment_download_rejects_query_token(
    client: TestClient,
    session: Session,
    auth_landlord,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)
    tenant_token = create_access_token(data={"sub": tenant.id, "type": "tenant"})
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    created = client.post(
        f"/api/tenant-auth/payments/{payment.id}/dispute/messages/attachments",
        headers=tenant_headers,
        files={"file": ("receipt.pdf", b"%PDF-1.4\n%EOF", "application/pdf")},
    )
    assert created.status_code == 201
    message_id = created.json()["messages"][-1]["id"]

    query_auth_download = client.get(
        f"/api/payments/{payment.id}/dispute/messages/{message_id}/attachment?token={tenant_token}"
    )
    assert query_auth_download.status_code == 401


def test_dispute_attachment_download_allows_cookie_auth(
    client: TestClient,
    session: Session,
    auth_landlord,
):
    tenant, payment = _create_landlord_payment_context(session, auth_landlord.id)
    tenant_token = create_access_token(data={"sub": tenant.id, "type": "tenant"})
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    created = client.post(
        f"/api/tenant-auth/payments/{payment.id}/dispute/messages/attachments",
        headers=tenant_headers,
        files={"file": ("proof.pdf", b"%PDF-1.4\n%EOF", "application/pdf")},
    )
    assert created.status_code == 201
    message_id = created.json()["messages"][-1]["id"]

    client.cookies.set(AUTH_COOKIE_NAME, tenant_token)
    cookie_auth_download = client.get(
        f"/api/payments/{payment.id}/dispute/messages/{message_id}/attachment"
    )
    assert cookie_auth_download.status_code == 200

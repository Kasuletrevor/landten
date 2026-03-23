from fastapi.testclient import TestClient
from sqlmodel import Session, select
from unittest.mock import AsyncMock, patch

from app.core.security import create_access_token
from app.models.landlord import Landlord
from app.models.maintenance import MaintenanceComment
from tests.factories import PropertyFactory, RoomFactory, TenantFactory


def _create_tenant_context(session: Session, landlord_id: str, name: str = "Tenant One"):
    property_obj = PropertyFactory.create(
        session=session,
        landlord_id=landlord_id,
        name=f"{name} Property",
    )
    room = RoomFactory.create(
        session=session,
        property_id=property_obj.id,
        name=f"{name} Room",
    )
    tenant = TenantFactory.create(
        session=session,
        room_id=room.id,
        name=name,
        email=f"{name.lower().replace(' ', '.')}.{property_obj.id[:6]}@test.com",
    )
    tenant_token = create_access_token(data={"sub": tenant.id, "type": "tenant"})
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}
    return tenant, property_obj, room, tenant_headers


def test_tenant_create_and_landlord_list_maintenance_requests(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    tenant, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)

    created = client.post(
        "/api/tenant-auth/maintenance",
        headers=tenant_headers,
        json={
            "category": "plumbing",
            "urgency": "high",
            "title": "Kitchen sink leak",
            "description": "Water is leaking from the pipe under the sink.",
            "preferred_entry_time": "Weekdays after 2pm",
        },
    )
    assert created.status_code == 201
    created_data = created.json()
    assert created_data["status"] == "submitted"
    assert created_data["tenant_id"] == tenant.id

    listed = client.get("/api/maintenance", headers=auth_headers)
    assert listed.status_code == 200
    listed_data = listed.json()
    assert listed_data["total"] == 1
    assert listed_data["requests"][0]["title"] == "Kitchen sink leak"
    assert listed_data["requests"][0]["tenant_name"] == tenant.name


def test_tenant_maintenance_request_sends_landlord_email(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
):
    _, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)

    with patch(
        "app.routers.tenant_auth.email_service.send_maintenance_update",
        new=AsyncMock(return_value=True),
    ) as email_mock:
        created = client.post(
            "/api/tenant-auth/maintenance",
            headers=tenant_headers,
            json={
                "category": "plumbing",
                "urgency": "high",
                "title": "Blocked drain",
                "description": "Water is backing up in the bathroom drain.",
            },
        )

    assert created.status_code == 201
    email_mock.assert_awaited_once()
    email_kwargs = email_mock.await_args.kwargs
    assert email_kwargs["recipient_name"] == auth_landlord.name
    assert email_kwargs["recipient_email"] == auth_landlord.email


def test_tenant_cannot_access_other_tenant_maintenance_request(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
):
    _, _, _, tenant_one_headers = _create_tenant_context(
        session, auth_landlord.id, name="Tenant One"
    )
    _, _, _, tenant_two_headers = _create_tenant_context(
        session, auth_landlord.id, name="Tenant Two"
    )

    created = client.post(
        "/api/tenant-auth/maintenance",
        headers=tenant_one_headers,
        json={
            "category": "electrical",
            "urgency": "medium",
            "title": "Bedroom light switch not working",
            "description": "Switch sparks and does not turn on the light.",
        },
    )
    assert created.status_code == 201
    request_id = created.json()["id"]

    read_other = client.get(
        f"/api/tenant-auth/maintenance/{request_id}",
        headers=tenant_two_headers,
    )
    assert read_other.status_code == 404

    comment_other = client.post(
        f"/api/tenant-auth/maintenance/{request_id}/comments",
        headers=tenant_two_headers,
        json={"body": "Trying to access another request"},
    )
    assert comment_other.status_code == 404


def test_landlord_can_update_maintenance_status_assignment_and_costs(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    _, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)
    created = client.post(
        "/api/tenant-auth/maintenance",
        headers=tenant_headers,
        json={
            "category": "appliance",
            "urgency": "medium",
            "title": "Fridge not cooling",
            "description": "The refrigerator is running but food is spoiling.",
        },
    )
    request_id = created.json()["id"]

    updated = client.put(
        f"/api/maintenance/{request_id}",
        headers=auth_headers,
        json={
            "status": "in_progress",
            "assigned_to": "CoolFix Contractors",
            "estimated_cost": 120000,
            "landlord_notes": "Technician booked for tomorrow morning.",
        },
    )
    assert updated.status_code == 200
    updated_data = updated.json()
    assert updated_data["status"] == "in_progress"
    assert updated_data["assigned_to"] == "CoolFix Contractors"
    assert updated_data["estimated_cost"] == 120000
    assert "Technician booked" in (updated_data["landlord_notes"] or "")


def test_landlord_maintenance_update_sends_tenant_email(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    _, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)
    created = client.post(
        "/api/tenant-auth/maintenance",
        headers=tenant_headers,
        json={
            "category": "appliance",
            "urgency": "medium",
            "title": "Fan not working",
            "description": "Ceiling fan spins briefly then stops.",
        },
    )
    request_id = created.json()["id"]

    with patch(
        "app.routers.maintenance.email_service.send_maintenance_update",
        new=AsyncMock(return_value=True),
    ) as email_mock:
        updated = client.put(
            f"/api/maintenance/{request_id}",
            headers=auth_headers,
            json={"status": "in_progress"},
        )

    assert updated.status_code == 200
    email_mock.assert_awaited_once()
    email_kwargs = email_mock.await_args.kwargs
    assert email_kwargs["recipient_name"] == "Tenant One"


def test_tenant_maintenance_request_returns_201_when_email_fails(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
):
    _, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)

    with patch(
        "app.routers.tenant_auth.email_service.send_maintenance_update",
        new=AsyncMock(side_effect=RuntimeError("smtp unavailable")),
    ):
        created = client.post(
            "/api/tenant-auth/maintenance",
            headers=tenant_headers,
            json={
                "category": "plumbing",
                "urgency": "high",
                "title": "Broken tap",
                "description": "The tap will not close fully.",
            },
        )

    assert created.status_code == 201


def test_landlord_maintenance_update_skips_email_for_email_less_tenant(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    tenant, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)
    tenant.email = None
    session.add(tenant)
    session.commit()

    created = client.post(
        "/api/tenant-auth/maintenance",
        headers=tenant_headers,
        json={
            "category": "appliance",
            "urgency": "medium",
            "title": "Heater issue",
            "description": "The heater is not turning on.",
        },
    )
    request_id = created.json()["id"]

    with patch(
        "app.routers.maintenance.email_service.send_maintenance_update",
        new=AsyncMock(return_value=True),
    ) as email_mock:
        updated = client.put(
            f"/api/maintenance/{request_id}",
            headers=auth_headers,
            json={"status": "in_progress"},
        )

    assert updated.status_code == 200
    email_mock.assert_not_awaited()


def test_internal_landlord_comments_hidden_from_tenant(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    _, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)
    created = client.post(
        "/api/tenant-auth/maintenance",
        headers=tenant_headers,
        json={
            "category": "structural",
            "urgency": "low",
            "title": "Wall paint peeling",
            "description": "Paint has peeled off near the window.",
        },
    )
    request_id = created.json()["id"]

    internal = client.post(
        f"/api/maintenance/{request_id}/comments",
        headers=auth_headers,
        json={"body": "Use approved vendor only.", "is_internal": True},
    )
    assert internal.status_code == 201

    landlord_view = client.get(f"/api/maintenance/{request_id}", headers=auth_headers)
    assert landlord_view.status_code == 200
    assert landlord_view.json()["comments_count"] == 1
    assert landlord_view.json()["comments"][0]["is_internal"] is True

    tenant_view = client.get(
        f"/api/tenant-auth/maintenance/{request_id}",
        headers=tenant_headers,
    )
    assert tenant_view.status_code == 200
    assert tenant_view.json()["comments_count"] == 0
    assert tenant_view.json()["comments"] == []


def test_tenant_can_upload_maintenance_attachment_comment(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
):
    _, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)
    created = client.post(
        "/api/tenant-auth/maintenance",
        headers=tenant_headers,
        json={
            "category": "plumbing",
            "urgency": "high",
            "title": "Bathroom flooding",
            "description": "Water leaks heavily when shower runs.",
        },
    )
    request_id = created.json()["id"]

    attachment = client.post(
        f"/api/tenant-auth/maintenance/{request_id}/comments/attachments",
        headers=tenant_headers,
        files={"file": ("issue.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        data={"body": "Attaching photo evidence"},
    )
    assert attachment.status_code == 201
    data = attachment.json()
    assert data["comments_count"] == 1
    comment = data["comments"][0]
    assert comment["attachment_name"] == "issue.png"
    assert comment["attachment_url"].startswith("/api/maintenance/")
    assert comment["attachment_content_type"] == "image/png"


def test_maintenance_attachment_requires_authenticated_access(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    _, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)
    _, _, _, other_tenant_headers = _create_tenant_context(
        session, auth_landlord.id, name="Tenant Two"
    )
    created = client.post(
        "/api/tenant-auth/maintenance",
        headers=tenant_headers,
        json={
            "category": "plumbing",
            "urgency": "high",
            "title": "Burst pipe",
            "description": "Water is leaking behind the sink.",
        },
    )
    request_id = created.json()["id"]

    attachment = client.post(
        f"/api/tenant-auth/maintenance/{request_id}/comments/attachments",
        headers=tenant_headers,
        files={"file": ("issue.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        data={"body": "Leak photo"},
    )

    assert attachment.status_code == 201
    comment_payload = attachment.json()["comments"][0]
    secure_url = comment_payload["attachment_url"]
    comment = session.exec(
        select(MaintenanceComment).where(MaintenanceComment.request_id == request_id)
    ).first()

    assert comment is not None
    assert comment.attachment_url is not None
    assert comment.attachment_url.startswith("/uploads/maintenance/")

    public_response = client.get(comment.attachment_url)
    assert public_response.status_code == 404

    tenant_response = client.get(secure_url, headers=tenant_headers)
    assert tenant_response.status_code == 200
    assert tenant_response.content == b"\x89PNG\r\n\x1a\n"

    landlord_response = client.get(secure_url, headers=auth_headers)
    assert landlord_response.status_code == 200
    assert landlord_response.content == b"\x89PNG\r\n\x1a\n"

    other_tenant_response = client.get(secure_url, headers=other_tenant_headers)
    assert other_tenant_response.status_code == 404


def test_tenant_can_resolve_then_reopen_request(
    client: TestClient,
    session: Session,
    auth_landlord: Landlord,
    auth_headers: dict,
):
    _, _, _, tenant_headers = _create_tenant_context(session, auth_landlord.id)
    created = client.post(
        "/api/tenant-auth/maintenance",
        headers=tenant_headers,
        json={
            "category": "electrical",
            "urgency": "high",
            "title": "Power outage in room",
            "description": "No power in sockets for two days.",
        },
    )
    request_id = created.json()["id"]

    set_in_progress = client.put(
        f"/api/maintenance/{request_id}",
        headers=auth_headers,
        json={"status": "in_progress"},
    )
    assert set_in_progress.status_code == 200

    resolved = client.put(
        f"/api/tenant-auth/maintenance/{request_id}/resolve",
        headers=tenant_headers,
        json={"tenant_rating": 4, "tenant_feedback": "Issue fixed well."},
    )
    assert resolved.status_code == 200
    resolved_data = resolved.json()
    assert resolved_data["status"] == "completed"
    assert resolved_data["tenant_rating"] == 4

    reopened = client.put(
        f"/api/tenant-auth/maintenance/{request_id}/reopen",
        headers=tenant_headers,
    )
    assert reopened.status_code == 200
    reopened_data = reopened.json()
    assert reopened_data["status"] == "acknowledged"
    assert reopened_data["completed_at"] is None

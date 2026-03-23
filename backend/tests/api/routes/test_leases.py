"""
Tests for lease agreement endpoints.
"""

import logging
import pytest
import os
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.routers import leases as lease_router
from app.models.lease_agreement import LeaseAgreement, LeaseStatus
from app.models.landlord import Landlord
from app.models.tenant import Tenant
from tests.factories import LandlordFactory, PropertyFactory, RoomFactory, TenantFactory


class TestLandlordLeaseEndpoints:
    """Test landlord-facing lease agreement endpoints."""

    def test_upload_original_lease_success(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict,
        sample_receipt_pdf: str,
    ):
        """Test successfully uploading an original lease agreement."""
        # Create test data
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant = TenantFactory.create(session=session, room_id=room.id)

        # Update auth headers with correct landlord
        from app.core.security import create_access_token

        token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
        headers = {"Authorization": f"Bearer {token}"}

        with open(sample_receipt_pdf, "rb") as f:
            response = client.post(
                f"/api/leases/upload-original/{tenant.id}",
                files={"file": ("lease.pdf", f, "application/pdf")},
                data={
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "rent_amount": "150000",
                },
                headers=headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["tenant_id"] == tenant.id
        assert data["property_id"] == property_obj.id
        assert data["status"] == "unsigned"
        assert data["original_url"] is not None
        assert data["uploaded_by_landlord"] is True

    def test_upload_lease_already_exists(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict,
        sample_receipt_pdf: str,
    ):
        """Test uploading a lease when one already exists for the tenant."""
        # Create test data
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant = TenantFactory.create(session=session, room_id=room.id)

        # Create existing lease
        existing_lease = LeaseAgreement(
            tenant_id=tenant.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/existing.pdf",
            status=LeaseStatus.UNSIGNED,
        )
        session.add(existing_lease)
        session.commit()

        from app.core.security import create_access_token

        token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
        headers = {"Authorization": f"Bearer {token}"}

        with open(sample_receipt_pdf, "rb") as f:
            response = client.post(
                f"/api/leases/upload-original/{tenant.id}",
                files={"file": ("lease.pdf", f, "application/pdf")},
                headers=headers,
            )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_list_leases(
        self, client: TestClient, session: Session, auth_headers: dict
    ):
        """Test listing lease agreements for landlord."""
        # Create test data
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant1 = TenantFactory.create(
            session=session, room_id=room.id, name="Tenant One"
        )
        tenant2 = TenantFactory.create(
            session=session, room_id=room.id, name="Tenant Two"
        )

        # Create leases
        lease1 = LeaseAgreement(
            tenant_id=tenant1.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease1.pdf",
            status=LeaseStatus.UNSIGNED,
        )
        lease2 = LeaseAgreement(
            tenant_id=tenant2.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease2.pdf",
            status=LeaseStatus.SIGNED,
            signed_url="/uploads/leases/lease2_signed.pdf",
            signed_uploaded_by="tenant",
        )
        session.add(lease1)
        session.add(lease2)
        session.commit()

        from app.core.security import create_access_token

        token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/leases", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["leases"]) == 2

    def test_list_leases_filter_by_status(
        self, client: TestClient, session: Session, auth_headers: dict
    ):
        """Test filtering leases by status."""
        # Create test data
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant1 = TenantFactory.create(session=session, room_id=room.id)
        tenant2 = TenantFactory.create(session=session, room_id=room.id)

        lease1 = LeaseAgreement(
            tenant_id=tenant1.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease1.pdf",
            status=LeaseStatus.UNSIGNED,
        )
        lease2 = LeaseAgreement(
            tenant_id=tenant2.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease2.pdf",
            status=LeaseStatus.SIGNED,
        )
        session.add(lease1)
        session.add(lease2)
        session.commit()

        from app.core.security import create_access_token

        token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/leases?status=signed", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["leases"][0]["status"] == "signed"

    def test_upload_signed_lease(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict,
        sample_receipt_pdf: str,
    ):
        """Test uploading a signed lease agreement."""
        # Create test data
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant = TenantFactory.create(session=session, room_id=room.id)

        lease = LeaseAgreement(
            tenant_id=tenant.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/original.pdf",
            status=LeaseStatus.UNSIGNED,
        )
        session.add(lease)
        session.commit()
        session.refresh(lease)

        from app.core.security import create_access_token

        token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
        headers = {"Authorization": f"Bearer {token}"}

        with open(sample_receipt_pdf, "rb") as f:
            response = client.post(
                f"/api/leases/{lease.id}/upload-signed",
                files={"file": ("signed_lease.pdf", f, "application/pdf")},
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "signed"
        assert data["signed_url"] is not None
        assert data["signed_uploaded_by"] == "landlord"

    def test_delete_lease(
        self, client: TestClient, session: Session, auth_headers: dict
    ):
        """Test deleting a lease agreement."""
        # Create test data
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant = TenantFactory.create(session=session, room_id=room.id)

        lease = LeaseAgreement(
            tenant_id=tenant.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease.pdf",
            status=LeaseStatus.UNSIGNED,
        )
        session.add(lease)
        session.commit()
        session.refresh(lease)

        from app.core.security import create_access_token

        token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete(f"/api/leases/{lease.id}", headers=headers)

        assert response.status_code == 204

        # Verify lease is deleted
        response = client.get(f"/api/leases/{lease.id}", headers=headers)
        assert response.status_code == 404

    def test_delete_lease_logs_file_delete_failures(
        self,
        client: TestClient,
        session: Session,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test lease deletion logs filesystem failures instead of swallowing them."""
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant = TenantFactory.create(session=session, room_id=room.id)

        lease = LeaseAgreement(
            tenant_id=tenant.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease.pdf",
            signed_url="/uploads/leases/lease-signed.pdf",
            status=LeaseStatus.SIGNED,
        )
        session.add(lease)
        session.commit()
        session.refresh(lease)

        from app.core.security import create_access_token

        token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
        headers = {"Authorization": f"Bearer {token}"}

        monkeypatch.setattr(lease_router, "_resolve_lease_file_path", lambda _url: "broken.pdf")
        monkeypatch.setattr(lease_router.os.path, "exists", lambda _path: True)

        def raise_remove(_path: str) -> None:
            raise OSError("disk failure")

        monkeypatch.setattr(lease_router.os, "remove", raise_remove)

        with caplog.at_level(logging.ERROR):
            response = client.delete(f"/api/leases/{lease.id}", headers=headers)

        assert response.status_code == 204
        assert "Failed to delete lease file" in caplog.text
        assert "disk failure" in caplog.text

    def test_lease_summary(
        self, client: TestClient, session: Session, auth_headers: dict
    ):
        """Test getting lease summary statistics."""
        # Create test data
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant1 = TenantFactory.create(session=session, room_id=room.id)
        tenant2 = TenantFactory.create(session=session, room_id=room.id)
        tenant3 = TenantFactory.create(session=session, room_id=room.id)

        lease1 = LeaseAgreement(
            tenant_id=tenant1.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease1.pdf",
            status=LeaseStatus.UNSIGNED,
        )
        lease2 = LeaseAgreement(
            tenant_id=tenant2.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease2.pdf",
            status=LeaseStatus.SIGNED,
        )
        lease3 = LeaseAgreement(
            tenant_id=tenant3.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease3.pdf",
            status=LeaseStatus.SIGNED,
        )
        session.add(lease1)
        session.add(lease2)
        session.add(lease3)
        session.commit()

        from app.core.security import create_access_token

        token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/leases/summary", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["total_unsigned"] == 1
        assert data["total_signed"] == 2


class TestTenantLeaseEndpoints:
    """Test tenant-facing lease agreement endpoints."""

    def test_tenant_get_my_lease(
        self,
        client: TestClient,
        session: Session,
        tenant_headers: dict,
        auth_tenant: Tenant,
    ):
        """Test tenant getting their own lease."""
        # Create lease for the tenant
        from datetime import date

        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        auth_tenant.room_id = room.id
        session.add(auth_tenant)

        lease = LeaseAgreement(
            tenant_id=auth_tenant.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease.pdf",
            status=LeaseStatus.UNSIGNED,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            rent_amount=150000,
        )
        session.add(lease)
        session.commit()

        response = client.get("/api/leases/tenant/my-lease", headers=tenant_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == auth_tenant.id
        assert data["status"] == "unsigned"
        assert data["start_date"] == "2024-01-01"

    def test_tenant_get_my_lease_not_found(
        self, client: TestClient, tenant_headers: dict
    ):
        """Test tenant getting lease when none exists."""
        response = client.get("/api/leases/tenant/my-lease", headers=tenant_headers)

        assert response.status_code == 404
        assert "no lease" in response.json()["detail"].lower()

    def test_tenant_upload_signed_lease(
        self,
        client: TestClient,
        session: Session,
        tenant_headers: dict,
        auth_tenant: Tenant,
        sample_receipt_pdf: str,
    ):
        """Test tenant uploading signed lease."""
        # Create lease for the tenant
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        auth_tenant.room_id = room.id
        session.add(auth_tenant)

        lease = LeaseAgreement(
            tenant_id=auth_tenant.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease.pdf",
            status=LeaseStatus.UNSIGNED,
        )
        session.add(lease)
        session.commit()

        with open(sample_receipt_pdf, "rb") as f:
            response = client.post(
                "/api/leases/tenant/my-lease/upload-signed",
                files={"file": ("signed_lease.pdf", f, "application/pdf")},
                headers=tenant_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "signed"
        assert data["signed_uploaded_by"] == "tenant"

    def test_tenant_download_lease(
        self,
        client: TestClient,
        session: Session,
        tenant_headers: dict,
        auth_tenant: Tenant,
    ):
        """Test tenant downloading lease."""
        # Create lease for the tenant
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        auth_tenant.room_id = room.id
        session.add(auth_tenant)

        lease = LeaseAgreement(
            tenant_id=auth_tenant.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease.pdf",
            status=LeaseStatus.UNSIGNED,
        )
        session.add(lease)
        session.commit()

        response = client.get(
            "/api/leases/tenant/my-lease/download", headers=tenant_headers
        )

        # Note: Returns 404 because the file doesn't exist on disk in tests
        # In production, the file would exist
        assert response.status_code == 404


class TestLeaseValidation:
    """Test lease agreement validation."""

    def test_upload_non_pdf_file(
        self,
        client: TestClient,
        session: Session,
        auth_headers: dict,
        sample_receipt_png: str,
    ):
        """Test uploading non-PDF file is rejected."""
        # Create test data
        landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(session=session, landlord_id=landlord.id)
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant = TenantFactory.create(session=session, room_id=room.id)

        from app.core.security import create_access_token

        token = create_access_token(data={"sub": landlord.id, "type": "landlord"})
        headers = {"Authorization": f"Bearer {token}"}

        with open(sample_receipt_png, "rb") as f:
            response = client.post(
                f"/api/leases/upload-original/{tenant.id}",
                files={"file": ("lease.png", f, "image/png")},
                headers=headers,
            )

        assert response.status_code == 400
        assert "pdf" in response.json()["detail"].lower()

    def test_upload_lease_for_nonexistent_tenant(
        self, client: TestClient, auth_headers: dict, sample_receipt_pdf: str
    ):
        """Test uploading lease for non-existent tenant."""
        with open(sample_receipt_pdf, "rb") as f:
            response = client.post(
                "/api/leases/upload-original/nonexistent-tenant-id",
                files={"file": ("lease.pdf", f, "application/pdf")},
                headers=auth_headers,
            )

        assert response.status_code == 404

    def test_access_other_landlord_lease(
        self, client: TestClient, session: Session, auth_headers: dict
    ):
        """Test accessing lease belonging to another landlord."""
        # Create another landlord's lease
        other_landlord = LandlordFactory.create(session=session)
        property_obj = PropertyFactory.create(
            session=session, landlord_id=other_landlord.id
        )
        room = RoomFactory.create(session=session, property_id=property_obj.id)
        tenant = TenantFactory.create(session=session, room_id=room.id)

        lease = LeaseAgreement(
            tenant_id=tenant.id,
            property_id=property_obj.id,
            original_url="/uploads/leases/lease.pdf",
            status=LeaseStatus.UNSIGNED,
        )
        session.add(lease)
        session.commit()
        session.refresh(lease)

        # Try to access with auth_landlord's token
        response = client.get(f"/api/leases/{lease.id}", headers=auth_headers)

        assert response.status_code == 404

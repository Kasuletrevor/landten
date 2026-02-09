from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime, timezone
import shutil
import os
import uuid
import mimetypes

from app.core.database import get_session
from app.core.security import get_current_landlord, get_current_tenant
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.lease_agreement import LeaseAgreement, LeaseStatus
from app.schemas.lease_agreement import (
    LeaseAgreementCreate,
    LeaseAgreementUpdate,
    LeaseAgreementResponse,
    LeaseAgreementWithTenant,
    LeaseAgreementListResponse,
    LeaseStatusSummary,
)

router = APIRouter(prefix="/leases", tags=["Lease Agreements"])


# Helper functions
def get_landlord_property_ids(landlord_id: str, session: Session) -> List[str]:
    """Get all property IDs for a landlord."""
    properties = session.exec(
        select(Property).where(Property.landlord_id == landlord_id)
    ).all()
    return [p.id for p in properties]


def get_landlord_tenant_ids(landlord_id: str, session: Session) -> List[str]:
    """Get all tenant IDs for a landlord's properties."""
    from app.models.room import Room

    property_ids = get_landlord_property_ids(landlord_id, session)
    if not property_ids:
        return []
    rooms = session.exec(select(Room).where(Room.property_id.in_(property_ids))).all()
    room_ids = [r.id for r in rooms]
    if not room_ids:
        return []
    tenants = session.exec(select(Tenant).where(Tenant.room_id.in_(room_ids))).all()
    return [t.id for t in tenants]


def verify_lease_access(
    lease_id: str, landlord_id: str, session: Session
) -> LeaseAgreement:
    """Verify lease exists and belongs to landlord's tenant."""
    lease = session.get(LeaseAgreement, lease_id)
    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lease agreement not found"
        )

    tenant_ids = get_landlord_tenant_ids(landlord_id, session)
    if lease.tenant_id not in tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lease agreement not found"
        )

    return lease


def enrich_lease_with_tenant(
    lease: LeaseAgreement, session: Session
) -> LeaseAgreementWithTenant:
    """Add tenant and property info to a lease agreement."""
    tenant = session.get(Tenant, lease.tenant_id)
    room = session.get(Room, tenant.room_id) if tenant else None
    property = session.get(Property, room.property_id) if room else None

    return LeaseAgreementWithTenant(
        **lease.model_dump(),
        tenant_name=tenant.name if tenant else None,
        tenant_email=tenant.email if tenant else None,
        tenant_phone=tenant.phone if tenant else None,
        room_name=room.name if room else None,
        property_name=property.name if property else None,
    )


def _resolve_lease_file_path(file_url: str) -> str:
    """Resolve a file_url to a safe local file path."""
    if not file_url or not file_url.startswith("/uploads/leases/"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    filename = os.path.basename(file_url)
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    base_dir = os.path.normpath(os.path.join("uploads", "leases"))
    file_path = os.path.normpath(os.path.join(base_dir, filename))

    # Prevent path traversal
    if os.path.commonpath([base_dir, file_path]) != base_dir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return file_path


# Landlord Endpoints
@router.get("", response_model=LeaseAgreementListResponse)
async def list_leases(
    property_id: Optional[str] = None,
    status: Optional[LeaseStatus] = None,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    List all lease agreements for the landlord's tenants.
    """
    tenant_ids = get_landlord_tenant_ids(current_landlord.id, session)
    if not tenant_ids:
        return LeaseAgreementListResponse(leases=[], total=0)

    query = select(LeaseAgreement).where(LeaseAgreement.tenant_id.in_(tenant_ids))

    if property_id:
        # Verify property belongs to landlord
        properties = get_landlord_property_ids(current_landlord.id, session)
        if property_id not in properties:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
            )
        query = query.where(LeaseAgreement.property_id == property_id)

    if status:
        query = query.where(LeaseAgreement.status == status)

    leases = session.exec(query.order_by(LeaseAgreement.created_at.desc())).all()

    result = [enrich_lease_with_tenant(lease, session) for lease in leases]
    return LeaseAgreementListResponse(leases=result, total=len(result))


@router.get("/summary", response_model=LeaseStatusSummary)
async def get_lease_summary(
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get summary statistics for lease agreements.
    """
    tenant_ids = get_landlord_tenant_ids(current_landlord.id, session)
    if not tenant_ids:
        return LeaseStatusSummary()

    leases = session.exec(
        select(LeaseAgreement).where(LeaseAgreement.tenant_id.in_(tenant_ids))
    ).all()

    unsigned = sum(1 for l in leases if l.status == LeaseStatus.UNSIGNED)
    signed = sum(1 for l in leases if l.status == LeaseStatus.SIGNED)

    return LeaseStatusSummary(
        total_unsigned=unsigned,
        total_signed=signed,
        total=len(leases),
    )


@router.get("/{lease_id}", response_model=LeaseAgreementWithTenant)
async def get_lease(
    lease_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get a specific lease agreement by ID.
    """
    lease = verify_lease_access(lease_id, current_landlord.id, session)
    return enrich_lease_with_tenant(lease, session)


@router.post(
    "/upload-original/{tenant_id}",
    response_model=LeaseAgreementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_original_lease(
    tenant_id: str,
    file: UploadFile = File(...),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    rent_amount: Optional[float] = None,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Upload an original lease agreement PDF for a tenant.
    """
    # Verify tenant belongs to landlord
    tenant_ids = get_landlord_tenant_ids(current_landlord.id, session)
    if tenant_id not in tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    # Check if lease already exists for this tenant
    existing = session.exec(
        select(LeaseAgreement).where(LeaseAgreement.tenant_id == tenant_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lease agreement already exists for this tenant. Delete it first.",
        )

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    # Generate unique filename
    file_ext = ".pdf"
    filename = f"lease_{tenant_id}_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join("uploads", "leases", filename)

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}",
        )

    # Create lease agreement record
    from datetime import date

    lease = LeaseAgreement(
        tenant_id=tenant_id,
        property_id=tenant.room.property_id if tenant.room else None,
        original_url=f"/uploads/leases/{filename}",
        signed_url=None,
        status=LeaseStatus.UNSIGNED,
        start_date=date.fromisoformat(start_date) if start_date else None,
        end_date=date.fromisoformat(end_date) if end_date else None,
        rent_amount=rent_amount,
        uploaded_by_landlord=True,
        signed_uploaded_by=None,
    )

    session.add(lease)
    session.commit()
    session.refresh(lease)

    return lease


@router.post(
    "/{lease_id}/upload-signed",
    response_model=LeaseAgreementResponse,
)
async def upload_signed_lease(
    lease_id: str,
    file: UploadFile = File(...),
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Upload a signed lease agreement PDF (landlord side).
    """
    lease = verify_lease_access(lease_id, current_landlord.id, session)

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    # Generate unique filename
    file_ext = ".pdf"
    filename = f"lease_signed_{lease.tenant_id}_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join("uploads", "leases", filename)

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}",
        )

    # Update lease record
    lease.signed_url = f"/uploads/leases/{filename}"
    lease.status = LeaseStatus.SIGNED
    lease.signed_uploaded_by = "landlord"
    lease.updated_at = datetime.now(timezone.utc)

    session.add(lease)
    session.commit()
    session.refresh(lease)

    return lease


@router.put("/{lease_id}", response_model=LeaseAgreementResponse)
async def update_lease(
    lease_id: str,
    update_data: LeaseAgreementUpdate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Update lease agreement details (dates, rent amount).
    """
    lease = verify_lease_access(lease_id, current_landlord.id, session)

    if update_data.start_date is not None:
        lease.start_date = update_data.start_date
    if update_data.end_date is not None:
        lease.end_date = update_data.end_date
    if update_data.rent_amount is not None:
        lease.rent_amount = update_data.rent_amount

    lease.updated_at = datetime.now(timezone.utc)
    session.add(lease)
    session.commit()
    session.refresh(lease)

    return lease


@router.delete("/{lease_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lease(
    lease_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Delete a lease agreement and its associated files.
    """
    lease = verify_lease_access(lease_id, current_landlord.id, session)

    # Delete files
    if lease.original_url:
        try:
            file_path = _resolve_lease_file_path(lease.original_url)
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass  # Ignore errors deleting files

    if lease.signed_url:
        try:
            file_path = _resolve_lease_file_path(lease.signed_url)
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

    session.delete(lease)
    session.commit()

    return None


@router.get("/{lease_id}/download-original")
async def download_original_lease(
    lease_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Download the original lease agreement PDF.
    """
    lease = verify_lease_access(lease_id, current_landlord.id, session)

    if not lease.original_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Original lease not found"
        )

    file_path = _resolve_lease_file_path(lease.original_url)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"lease_agreement_{lease.tenant_id}.pdf",
    )


@router.get("/{lease_id}/download-signed")
async def download_signed_lease(
    lease_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Download the signed lease agreement PDF.
    """
    lease = verify_lease_access(lease_id, current_landlord.id, session)

    if not lease.signed_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Signed lease not found"
        )

    file_path = _resolve_lease_file_path(lease.signed_url)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=f"lease_agreement_signed_{lease.tenant_id}.pdf",
    )


# Tenant Endpoints
@router.get("/tenant/my-lease", response_model=LeaseAgreementResponse)
async def get_my_lease(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Get the current tenant's lease agreement.
    """
    lease = session.exec(
        select(LeaseAgreement).where(LeaseAgreement.tenant_id == current_tenant.id)
    ).first()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No lease agreement found"
        )

    return lease


@router.post(
    "/tenant/my-lease/upload-signed",
    response_model=LeaseAgreementResponse,
)
async def tenant_upload_signed_lease(
    file: UploadFile = File(...),
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Upload a signed lease agreement PDF (tenant side).
    """
    lease = session.exec(
        select(LeaseAgreement).where(LeaseAgreement.tenant_id == current_tenant.id)
    ).first()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No lease agreement found"
        )

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    # Generate unique filename
    file_ext = ".pdf"
    filename = f"lease_signed_{current_tenant.id}_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join("uploads", "leases", filename)

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}",
        )

    # Update lease record
    lease.signed_url = f"/uploads/leases/{filename}"
    lease.status = LeaseStatus.SIGNED
    lease.signed_uploaded_by = "tenant"
    lease.updated_at = datetime.now(timezone.utc)

    session.add(lease)
    session.commit()
    session.refresh(lease)

    return lease


@router.get("/tenant/my-lease/download")
async def tenant_download_lease(
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Download the lease agreement PDF (tenant view).
    Returns the original if not signed, or signed version if available.
    """
    lease = session.exec(
        select(LeaseAgreement).where(LeaseAgreement.tenant_id == current_tenant.id)
    ).first()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No lease agreement found"
        )

    # Use signed version if available, otherwise original
    file_url = lease.signed_url or lease.original_url
    if not file_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lease file not found"
        )

    file_path = _resolve_lease_file_path(file_url)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename="lease_agreement.pdf",
    )

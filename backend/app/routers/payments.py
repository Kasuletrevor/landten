from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, Request
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from typing import Optional, List, Awaitable
from datetime import datetime, date, timezone
from dateutil.relativedelta import relativedelta
import mimetypes
import logging

from app.core.database import get_session
from app.core.security import (
    decode_token,
    get_current_landlord,
    get_current_tenant,
    get_token_from_request,
)
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment_schedule import PaymentSchedule, PaymentFrequency
from app.models.payment import Payment, PaymentStatus
from app.models.payment_dispute import DisputeActorType, PaymentDisputeMessage
from app.services import email_service, notification_service
from app.services.payment_dispute_service import (
    get_dispute_for_payment,
    get_unread_count,
    mark_dispute_read,
    build_dispute_response,
    create_dispute_message,
    get_payment_for_landlord,
    get_payment_for_tenant,
    resolve_dispute,
    reopen_dispute,
    save_dispute_attachment,
    resolve_dispute_attachment_file_path,
)
from app.schemas.payment import (
    PaymentMarkPaid,
    PaymentWaive,
    PaymentRejectReceipt,
    PaymentUpdate,
    ManualPaymentCreate,
    PaymentWithTenant,
    PaymentListResponse,
    PaymentSummary,
    PaymentDisputeResponse,
    PaymentDisputeMessageCreate,
)
from fastapi import UploadFile, File
import shutil
import os
import uuid
from typing import Annotated

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger(__name__)


async def _run_post_commit_task(
    task_name: str,
    coroutine: Awaitable[object],
    **context: object,
) -> None:
    try:
        await coroutine
    except Exception:
        logger.exception("Post-commit payment task failed", extra={"task_name": task_name, **context})


def _resolve_receipt_file_path(receipt_url: str) -> str:
    """Resolve a receipt_url to a safe local file path."""
    # We only support serving receipts from our mounted uploads path.
    if not receipt_url or not receipt_url.startswith("/uploads/receipts/"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
        )

    filename = os.path.basename(receipt_url)
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
        )

    base_dir = os.path.normpath(os.path.join("uploads", "receipts"))
    file_path = os.path.normpath(os.path.join(base_dir, filename))

    # Prevent path traversal.
    if os.path.commonpath([base_dir, file_path]) != base_dir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
        )

    return file_path


async def _get_current_receipt_viewer(
    request: Request,
    session: Session = Depends(get_session),
):
    """Authenticate either landlord or tenant for receipt viewing."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    bearer_token = get_token_from_request(request)
    if not bearer_token:
        raise credentials_exception

    payload = decode_token(bearer_token)
    if payload is None:
        raise credentials_exception

    token_type = payload.get("type", "landlord")
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    if token_type == "tenant":
        tenant = session.get(Tenant, user_id)
        if tenant is None or not tenant.is_active:
            raise credentials_exception
        return ("tenant", tenant)

    landlord = session.get(Landlord, user_id)
    if landlord is None:
        raise credentials_exception
    return ("landlord", landlord)


def get_frequency_months(frequency: PaymentFrequency) -> int:
    """Convert payment frequency to number of months."""
    if frequency == PaymentFrequency.MONTHLY:
        return 1
    elif frequency == PaymentFrequency.BI_MONTHLY:
        return 2
    elif frequency == PaymentFrequency.QUARTERLY:
        return 3
    return 1


def calculate_period_dates(
    schedule: PaymentSchedule, reference_date: date
) -> tuple[date, date, date, date]:
    """
    Calculate period start, end, due date, and window end for a payment.
    Returns (period_start, period_end, due_date, window_end_date)
    """
    months = get_frequency_months(schedule.frequency)

    # Calculate period start (align to due_day)
    period_start = date(reference_date.year, reference_date.month, schedule.due_day)
    if period_start > reference_date:
        period_start = period_start - relativedelta(months=months)

    # Calculate period end
    period_end = period_start + relativedelta(months=months) - relativedelta(days=1)

    # Due date is at the start of the period
    due_date = period_start

    # Window end date
    window_end_date = due_date + relativedelta(days=schedule.window_days)

    return period_start, period_end, due_date, window_end_date


def update_payment_status(payment: Payment, today: date) -> PaymentStatus:
    """
    Calculate the correct status for a payment based on current date.
    Only for unpaid payments (not ON_TIME, LATE, or WAIVED).
    """
    if payment.status in [
        PaymentStatus.ON_TIME,
        PaymentStatus.LATE,
        PaymentStatus.WAIVED,
        # Tenant has submitted proof; status should remain until landlord action.
        PaymentStatus.VERIFYING,
    ]:
        return payment.status

    if today < payment.due_date:
        return PaymentStatus.UPCOMING
    elif today <= payment.window_end_date:
        return PaymentStatus.PENDING
    elif today <= payment.period_end:
        # After window but still in period - technically overdue but could still be paid
        return PaymentStatus.OVERDUE
    else:
        # Period has ended
        return PaymentStatus.OVERDUE

    return payment.status


def get_landlord_property_ids(landlord_id: str, session: Session) -> List[str]:
    """Get all property IDs for a landlord."""
    properties = session.exec(
        select(Property).where(Property.landlord_id == landlord_id)
    ).all()
    return [p.id for p in properties]


def get_landlord_room_ids(landlord_id: str, session: Session) -> List[str]:
    """Get all room IDs for a landlord's properties."""
    property_ids = get_landlord_property_ids(landlord_id, session)
    if not property_ids:
        return []
    rooms = session.exec(select(Room).where(Room.property_id.in_(property_ids))).all()
    return [r.id for r in rooms]


def get_landlord_tenant_ids(landlord_id: str, session: Session) -> List[str]:
    """Get all tenant IDs for a landlord's properties."""
    room_ids = get_landlord_room_ids(landlord_id, session)
    if not room_ids:
        return []
    tenants = session.exec(select(Tenant).where(Tenant.room_id.in_(room_ids))).all()
    return [t.id for t in tenants]


def verify_payment_access(
    payment_id: str, landlord_id: str, session: Session
) -> Payment:
    """Verify payment exists and belongs to landlord's tenant."""
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    tenant_ids = get_landlord_tenant_ids(landlord_id, session)
    if payment.tenant_id not in tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    return payment


def enrich_payment_with_tenant(payment: Payment, session: Session) -> PaymentWithTenant:
    """Add tenant and property info to a payment, including computed date fields."""
    tenant = session.get(Tenant, payment.tenant_id)
    room = session.get(Room, tenant.room_id) if tenant else None
    property = session.get(Property, room.property_id) if room else None

    # Compute days_until_due and days_overdue
    today = date.today()
    days_until_due = None
    days_overdue = None

    # Only compute for unpaid payments
    if payment.status not in [
        PaymentStatus.ON_TIME,
        PaymentStatus.LATE,
        PaymentStatus.WAIVED,
    ]:
        delta = (payment.due_date - today).days
        days_until_due = delta  # Positive = future, Negative = past

        if delta < 0:
            days_overdue = abs(delta)  # Days since due date
        else:
            days_overdue = None

    dispute = get_dispute_for_payment(session, payment.id)
    dispute_status = dispute.status if dispute else None
    dispute_unread_count = (
        get_unread_count(session, dispute, "landlord") if dispute else 0
    )
    last_dispute_message_at = dispute.last_message_at if dispute else None

    return PaymentWithTenant(
        **payment.model_dump(),
        tenant_name=tenant.name if tenant else None,
        tenant_email=tenant.email if tenant else None,
        tenant_phone=tenant.phone if tenant else None,
        room_name=room.name if room else None,
        property_id=property.id if property else None,
        property_name=property.name if property else None,
        currency=room.currency if room else None,
        days_until_due=days_until_due,
        days_overdue=days_overdue,
        dispute_status=dispute_status,
        dispute_unread_count=dispute_unread_count,
        last_dispute_message_at=last_dispute_message_at,
    )


@router.get("", response_model=PaymentListResponse)
async def list_payments(
    status_filter: Optional[PaymentStatus] = Query(None, alias="status"),
    property_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    List all payments with optional filters.
    Automatically updates payment statuses based on current date.
    """
    today = date.today()

    # Build base query
    tenant_ids = get_landlord_tenant_ids(current_landlord.id, session)
    if not tenant_ids:
        return PaymentListResponse(payments=[], total=0)

    query = select(Payment).where(Payment.tenant_id.in_(tenant_ids))

    # Apply filters
    if tenant_id:
        if tenant_id not in tenant_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
            )
        query = query.where(Payment.tenant_id == tenant_id)

    if property_id:
        # Get room IDs for the property
        rooms = session.exec(select(Room).where(Room.property_id == property_id)).all()
        room_ids = [r.id for r in rooms]

        # Get tenant IDs for those rooms
        property_tenant_ids = [
            t.id
            for t in session.exec(
                select(Tenant).where(Tenant.room_id.in_(room_ids))
            ).all()
        ]
        query = query.where(Payment.tenant_id.in_(property_tenant_ids))

    payments = session.exec(query.order_by(Payment.due_date.desc())).all()

    # Update statuses and filter
    result = []
    for payment in payments:
        # Update status based on current date
        new_status = update_payment_status(payment, today)
        if new_status != payment.status:
            payment.status = new_status
            payment.updated_at = datetime.now(timezone.utc)
            session.add(payment)

        # Apply status filter
        if status_filter and payment.status != status_filter:
            continue

        result.append(enrich_payment_with_tenant(payment, session))

    session.commit()

    return PaymentListResponse(payments=result, total=len(result))


@router.get("/summary", response_model=PaymentSummary)
async def get_payment_summary(
    property_id: Optional[str] = None,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get payment summary statistics for the dashboard.
    """
    today = date.today()
    first_of_month = date(today.year, today.month, 1)

    tenant_ids = get_landlord_tenant_ids(current_landlord.id, session)
    if not tenant_ids:
        return PaymentSummary()

    # Filter by property if specified
    if property_id:
        rooms = session.exec(select(Room).where(Room.property_id == property_id)).all()
        room_ids = [r.id for r in rooms]
        tenant_ids = [
            t.id
            for t in session.exec(
                select(Tenant).where(Tenant.room_id.in_(room_ids))
            ).all()
        ]

    if not tenant_ids:
        return PaymentSummary()

    # Get all payments for these tenants
    payments = session.exec(
        select(Payment).where(Payment.tenant_id.in_(tenant_ids))
    ).all()

    # Update statuses and count
    upcoming = 0
    pending = 0
    overdue = 0
    paid_this_month = 0
    amount_collected = 0.0
    amount_outstanding = 0.0

    for payment in payments:
        # Update status
        new_status = update_payment_status(payment, today)
        if new_status != payment.status:
            payment.status = new_status
            payment.updated_at = datetime.now(timezone.utc)
            session.add(payment)

        if payment.status == PaymentStatus.UPCOMING:
            upcoming += 1
            amount_outstanding += payment.amount_due
        elif payment.status == PaymentStatus.PENDING:
            pending += 1
            amount_outstanding += payment.amount_due
        elif payment.status == PaymentStatus.OVERDUE:
            overdue += 1
            amount_outstanding += payment.amount_due
        elif payment.status in [PaymentStatus.ON_TIME, PaymentStatus.LATE]:
            if payment.paid_date and payment.paid_date >= first_of_month:
                paid_this_month += 1
                amount_collected += payment.amount_due

    session.commit()

    return PaymentSummary(
        total_upcoming=upcoming,
        total_pending=pending,
        total_overdue=overdue,
        total_paid_this_month=paid_this_month,
        amount_collected_this_month=amount_collected,
        amount_outstanding=amount_outstanding,
    )


@router.get("/upcoming", response_model=PaymentListResponse)
async def get_upcoming_payments(
    days: int = Query(30, ge=1, le=90),
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get upcoming payments in the next N days.
    """
    today = date.today()
    end_date = today + relativedelta(days=days)

    tenant_ids = get_landlord_tenant_ids(current_landlord.id, session)
    if not tenant_ids:
        return PaymentListResponse(payments=[], total=0)

    payments = session.exec(
        select(Payment)
        .where(
            Payment.tenant_id.in_(tenant_ids),
            Payment.due_date >= today,
            Payment.due_date <= end_date,
            Payment.status.in_([PaymentStatus.UPCOMING, PaymentStatus.PENDING]),
        )
        .order_by(Payment.due_date)
    ).all()

    result = [enrich_payment_with_tenant(p, session) for p in payments]
    return PaymentListResponse(payments=result, total=len(result))


# =============================================================================
# Export Endpoints
# =============================================================================

from app.services.export_service import ExportService
from app.schemas.export import ExportFormat
from fastapi.responses import StreamingResponse


@router.get("/export")
async def export_payments(
    format: ExportFormat = Query(..., description="Export format: 'excel' or 'pdf'"),
    start_date: Optional[date] = Query(
        None, description="Start date (default: Jan 1 of current year)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date (default: Dec 31 of current year)"
    ),
    property_id: Optional[str] = Query(None, description="Filter by property ID"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    status_filter: Optional[str] = Query(
        None, description="Filter by status (comma-separated for multiple)"
    ),
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Export payments to Excel or PDF format.

    - **format**: Export format ('excel' or 'pdf')
    - **start_date**: Filter payments from this date (inclusive). Default: Jan 1 of current year
    - **end_date**: Filter payments until this date (inclusive). Default: Dec 31 of current year
    - **property_id**: Filter by specific property
    - **tenant_id**: Filter by specific tenant
    - **status_filter**: Filter by payment status (comma-separated for multiple)

    Date range cannot exceed 2 years. Returns a file download.
    """
    # Validate and set default dates
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date(date.today().year, 12, 31)

    # Validate date range (max 2 years)
    date_range_days = (end_date - start_date).days
    if date_range_days > 730:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 2 years",
        )
    if date_range_days < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Get landlord's tenant IDs
    tenant_ids = get_landlord_tenant_ids(current_landlord.id, session)
    if not tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tenants found",
        )

    # Build base query
    query = select(Payment).where(Payment.tenant_id.in_(tenant_ids))

    # Apply date filter (use period_start for date range)
    query = query.where(Payment.period_start >= start_date)
    query = query.where(Payment.period_start <= end_date)

    # Apply property filter
    if property_id:
        # Get room IDs for the property
        rooms = session.exec(select(Room).where(Room.property_id == property_id)).all()
        room_ids = [r.id for r in rooms]
        property_tenant_ids = [
            t.id
            for t in session.exec(
                select(Tenant).where(Tenant.room_id.in_(room_ids))
            ).all()
        ]
        query = query.where(Payment.tenant_id.in_(property_tenant_ids))

    # Apply tenant filter
    if tenant_id:
        if tenant_id not in tenant_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found",
            )
        query = query.where(Payment.tenant_id == tenant_id)

    # Get payments
    payments = session.exec(query.order_by(Payment.period_start.desc())).all()

    # Apply status filter (if provided)
    if status_filter:
        status_list = [s.strip().upper() for s in status_filter.split(",")]
        payments = [p for p in payments if p.status.value in status_list]

    # Generate export
    filename_base = (
        f"payments_{current_landlord.name.replace(' ', '_')}_{start_date}_{end_date}"
    )

    if format == ExportFormat.EXCEL:
        buffer = ExportService.generate_excel(
            payments=payments,
            start_date=start_date,
            end_date=end_date,
            landlord_name=current_landlord.name,
        )
        filename = f"{filename_base}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:  # PDF
        buffer = ExportService.generate_pdf(
            payments=payments,
            start_date=start_date,
            end_date=end_date,
            landlord_name=current_landlord.name,
        )
        filename = f"{filename_base}.pdf"
        media_type = "application/pdf"

    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(buffer.getbuffer().nbytes),
        },
    )


@router.get("/overdue", response_model=PaymentListResponse)
async def get_overdue_payments(
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get all overdue payments.
    """
    today = date.today()

    tenant_ids = get_landlord_tenant_ids(current_landlord.id, session)
    if not tenant_ids:
        return PaymentListResponse(payments=[], total=0)

    # Get payments past their window
    payments = session.exec(
        select(Payment)
        .where(
            Payment.tenant_id.in_(tenant_ids),
            Payment.window_end_date < today,
            Payment.status.notin_(
                [PaymentStatus.ON_TIME, PaymentStatus.LATE, PaymentStatus.WAIVED]
            ),
        )
        .order_by(Payment.due_date)
    ).all()

    # Update statuses
    for payment in payments:
        if payment.status != PaymentStatus.OVERDUE:
            payment.status = PaymentStatus.OVERDUE
            payment.updated_at = datetime.now(timezone.utc)
            session.add(payment)

    session.commit()

    result = [enrich_payment_with_tenant(p, session) for p in payments]
    return PaymentListResponse(payments=result, total=len(result))


@router.get("/{payment_id}", response_model=PaymentWithTenant)
async def get_payment(
    payment_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get a specific payment by ID.
    """
    payment = verify_payment_access(payment_id, current_landlord.id, session)

    # Update status
    today = date.today()
    new_status = update_payment_status(payment, today)
    if new_status != payment.status:
        payment.status = new_status
        payment.updated_at = datetime.now(timezone.utc)
        session.add(payment)
        session.commit()

    return enrich_payment_with_tenant(payment, session)


@router.put("/{payment_id}/mark-paid", response_model=PaymentWithTenant)
async def mark_payment_paid(
    payment_id: str,
    paid_data: PaymentMarkPaid,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Mark a payment as paid with receipt reference.
    """
    payment = verify_payment_access(payment_id, current_landlord.id, session)

    if payment.status in [
        PaymentStatus.ON_TIME,
        PaymentStatus.LATE,
        PaymentStatus.WAIVED,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment already has status: {payment.status.value}",
        )

    paid_date = paid_data.paid_date or date.today()

    # Determine if on-time or late
    if paid_date <= payment.window_end_date:
        payment.status = PaymentStatus.ON_TIME
    else:
        payment.status = PaymentStatus.LATE

    payment.paid_date = paid_date
    payment.payment_reference = paid_data.payment_reference
    if paid_data.notes:
        payment.notes = paid_data.notes
    payment.updated_at = datetime.now(timezone.utc)

    session.add(payment)
    session.commit()
    session.refresh(payment)

    return enrich_payment_with_tenant(payment, session)


@router.put("/{payment_id}/waive", response_model=PaymentWithTenant)
async def waive_payment(
    payment_id: str,
    waive_data: PaymentWaive,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Waive a payment (forgive it).
    """
    payment = verify_payment_access(payment_id, current_landlord.id, session)

    if payment.status in [
        PaymentStatus.ON_TIME,
        PaymentStatus.LATE,
        PaymentStatus.WAIVED,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment already has status: {payment.status.value}",
        )

    payment.status = PaymentStatus.WAIVED
    if waive_data.notes:
        payment.notes = waive_data.notes
    payment.updated_at = datetime.now(timezone.utc)

    session.add(payment)
    session.commit()
    session.refresh(payment)

    return enrich_payment_with_tenant(payment, session)


@router.put("/{payment_id}/reject-receipt", response_model=PaymentWithTenant)
async def reject_payment_receipt(
    payment_id: str,
    reject_data: PaymentRejectReceipt,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Reject a receipt that was uploaded by the tenant.
    Returns payment to PENDING or OVERDUE status based on current date.
    """
    payment, tenant, property_obj = get_payment_for_landlord(
        session, payment_id, current_landlord.id
    )
    room = session.get(Room, tenant.room_id)

    if payment.status != PaymentStatus.VERIFYING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject receipt: payment status is {payment.status.value}, not VERIFYING",
        )

    # Determine the appropriate status based on current date
    today = date.today()
    if today < payment.due_date:
        payment.status = PaymentStatus.UPCOMING
    elif today <= payment.window_end_date:
        payment.status = PaymentStatus.PENDING
    else:
        payment.status = PaymentStatus.OVERDUE

    payment.rejection_reason = reject_data.reason
    payment.updated_at = datetime.now(timezone.utc)

    session.add(payment)
    session.commit()
    session.refresh(payment)

    await _run_post_commit_task(
        "broadcast_receipt_rejection",
        notification_service.broadcast_to_tenant(
            tenant.id,
            "payment_receipt_rejected",
            {
                "title": "Payment receipt rejected",
                "message": reject_data.reason,
                "payment_id": payment.id,
                "status": payment.status.value,
                "rejection_reason": payment.rejection_reason,
                "updated_at": payment.updated_at.isoformat(),
            },
        ),
        payment_id=payment.id,
        tenant_id=tenant.id,
    )

    if tenant.email:
        await _run_post_commit_task(
            "send_receipt_rejection_email",
            email_service.send_receipt_rejected(
                tenant_name=tenant.name,
                tenant_email=tenant.email,
                amount=payment.amount_due,
                currency=room.currency if room else None,
                property_name=property_obj.name,
                room_name=room.name if room else None,
                landlord_name=current_landlord.name,
                rejection_reason=reject_data.reason,
            ),
            payment_id=payment.id,
            tenant_id=tenant.id,
            recipient_email=tenant.email,
        )

    return enrich_payment_with_tenant(payment, session)


@router.put("/{payment_id}", response_model=PaymentWithTenant)
async def update_payment(
    payment_id: str,
    update_data: PaymentUpdate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Update payment details (amount, due date, notes).
    """
    payment = verify_payment_access(payment_id, current_landlord.id, session)

    if update_data.amount_due is not None:
        payment.amount_due = update_data.amount_due
    if update_data.due_date is not None:
        payment.due_date = update_data.due_date
    if update_data.notes is not None:
        payment.notes = update_data.notes

    payment.updated_at = datetime.now(timezone.utc)
    session.add(payment)
    session.commit()
    session.refresh(payment)

    return enrich_payment_with_tenant(payment, session)


@router.post(
    "/manual",
    response_model=PaymentWithTenant,
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_payment(
    payment_data: ManualPaymentCreate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Create a manual one-off payment/charge.
    """
    tenant_ids = get_landlord_tenant_ids(current_landlord.id, session)
    if payment_data.tenant_id not in tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    # Calculate window end (use default 5 days)
    window_end_date = payment_data.due_date + relativedelta(days=5)

    payment = Payment(
        tenant_id=payment_data.tenant_id,
        schedule_id=None,
        period_start=payment_data.period_start,
        period_end=payment_data.period_end,
        amount_due=payment_data.amount_due,
        due_date=payment_data.due_date,
        window_end_date=window_end_date,
        status=PaymentStatus.UPCOMING,
        notes=payment_data.notes,
        is_manual=True,
    )

    # Set initial status based on dates
    today = date.today()
    payment.status = update_payment_status(payment, today)

    session.add(payment)
    session.commit()
    session.refresh(payment)

    return enrich_payment_with_tenant(payment, session)


@router.post("/{payment_id}/upload-receipt", response_model=PaymentWithTenant)
async def upload_payment_receipt(
    payment_id: str,
    file: UploadFile = File(...),
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
):
    """
    Upload a proof of payment receipt for a specific payment.
    Changes status to VERIFYING.
    """
    # Verify payment belongs to tenant
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found"
        )

    if payment.tenant_id != current_tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this payment",
        )

    # Allow re-uploading if status is UPCOMING, PENDING, OVERDUE, or VERIFYING
    # Prevent if already approved (ON_TIME, LATE, WAIVED)
    if payment.status in [
        PaymentStatus.ON_TIME,
        PaymentStatus.LATE,
        PaymentStatus.WAIVED,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment is already finalized with status: {payment.status.value}",
        )

    # Validate file type (basic check)
    if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, and PDF are allowed.",
        )

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    filename = f"{payment.id}_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join("uploads", "receipts", filename)

    # ensure directory exists
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

    # Update payment record
    # Construct URL relative to base URL (client handles full URL construction)
    # We mounted "uploads" in main.py so this is accessible via /uploads/...
    payment.receipt_url = f"/uploads/receipts/{filename}"
    payment.status = PaymentStatus.VERIFYING
    payment.updated_at = datetime.now(timezone.utc)
    # Clear previous rejection reason when new receipt is uploaded
    payment.rejection_reason = None

    session.add(payment)
    session.commit()
    session.refresh(payment)

    return enrich_payment_with_tenant(payment, session)


@router.get("/{payment_id}/receipt")
async def get_payment_receipt(
    payment_id: str,
    viewer=Depends(_get_current_receipt_viewer),
    session: Session = Depends(get_session),
):
    """Download/view the uploaded receipt file (tenant + landlord access controlled)."""
    viewer_type, viewer_user = viewer

    if viewer_type == "landlord":
        payment = verify_payment_access(payment_id, viewer_user.id, session)
    else:
        payment = session.get(Payment, payment_id)
        if not payment or payment.tenant_id != viewer_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

    if not payment.receipt_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
        )

    file_path = _resolve_receipt_file_path(payment.receipt_url)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
        )

    media_type, _ = mimetypes.guess_type(file_path)
    return FileResponse(
        file_path,
        media_type=media_type or "application/octet-stream",
        filename=os.path.basename(file_path),
    )


@router.get("/{payment_id}/dispute", response_model=PaymentDisputeResponse)
async def get_payment_dispute(
    payment_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    _, _, _ = get_payment_for_landlord(session, payment_id, current_landlord.id)

    dispute = get_dispute_for_payment(session, payment_id)
    if not dispute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found"
        )

    mark_dispute_read(dispute, "landlord")
    session.add(dispute)
    session.commit()
    session.refresh(dispute)
    return build_dispute_response(session, dispute, "landlord")


@router.post(
    "/{payment_id}/dispute/messages",
    response_model=PaymentDisputeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_payment_dispute_message(
    payment_id: str,
    payload: PaymentDisputeMessageCreate,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    payment, tenant, property_obj = get_payment_for_landlord(
        session, payment_id, current_landlord.id
    )
    room = session.get(Room, tenant.room_id)

    body = payload.body.strip()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message body is required",
        )

    dispute = create_dispute_message(
        session,
        payment_id=payment.id,
        author_type=DisputeActorType.LANDLORD,
        author_id=current_landlord.id,
        body=body,
    )

    await _run_post_commit_task(
        "broadcast_dispute_message_to_tenant",
        notification_service.broadcast_to_tenant(
            tenant.id,
            "payment_dispute_message",
            {
                "title": "Landlord replied on payment discussion",
                "message": body,
                "payment_id": payment.id,
                "author_type": "landlord",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ),
        payment_id=payment.id,
        tenant_id=tenant.id,
    )
    if tenant.email:
        await _run_post_commit_task(
            "send_dispute_email_to_tenant",
            email_service.send_payment_dispute_update(
                recipient_name=tenant.name,
                recipient_email=tenant.email,
                actor_name=current_landlord.name,
                property_name=property_obj.name,
                room_name=room.name if room else None,
                amount=payment.amount_due,
                currency=room.currency if room else None,
                message=body,
            ),
            payment_id=payment.id,
            tenant_id=tenant.id,
            recipient_email=tenant.email,
        )
    return build_dispute_response(session, dispute, "landlord")


@router.post(
    "/{payment_id}/dispute/messages/attachments",
    response_model=PaymentDisputeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_payment_dispute_attachment(
    payment_id: str,
    file: UploadFile = File(...),
    body: Optional[str] = Form(None),
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    payment, tenant, property_obj = get_payment_for_landlord(
        session, payment_id, current_landlord.id
    )
    room = session.get(Room, tenant.room_id)
    (
        attachment_name,
        attachment_url,
        content_type,
        size_bytes,
    ) = await save_dispute_attachment(file, payment_id)
    message_body = (body or "").strip() or f"Attachment shared: {attachment_name}"

    dispute = create_dispute_message(
        session,
        payment_id=payment.id,
        author_type=DisputeActorType.LANDLORD,
        author_id=current_landlord.id,
        body=message_body,
        attachment_name=attachment_name,
        attachment_url=attachment_url,
        attachment_content_type=content_type,
        attachment_size_bytes=size_bytes,
    )

    await _run_post_commit_task(
        "broadcast_dispute_attachment_to_tenant",
        notification_service.broadcast_to_tenant(
            tenant.id,
            "payment_dispute_message",
            {
                "title": "Landlord shared an attachment",
                "message": message_body,
                "payment_id": payment.id,
                "author_type": "landlord",
                "attachment_name": attachment_name,
                "has_attachment": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ),
        payment_id=payment.id,
        tenant_id=tenant.id,
    )
    if tenant.email:
        await _run_post_commit_task(
            "send_dispute_attachment_email_to_tenant",
            email_service.send_payment_dispute_update(
                recipient_name=tenant.name,
                recipient_email=tenant.email,
                actor_name=current_landlord.name,
                property_name=property_obj.name,
                room_name=room.name if room else None,
                amount=payment.amount_due,
                currency=room.currency if room else None,
                message=message_body,
                has_attachment=True,
            ),
            payment_id=payment.id,
            tenant_id=tenant.id,
            recipient_email=tenant.email,
        )
    return build_dispute_response(session, dispute, "landlord")


@router.put("/{payment_id}/dispute/resolve", response_model=PaymentDisputeResponse)
async def resolve_payment_dispute(
    payment_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    _, _, _ = get_payment_for_landlord(session, payment_id, current_landlord.id)
    dispute = resolve_dispute(
        session,
        payment_id=payment_id,
        actor_type=DisputeActorType.LANDLORD,
        actor_id=current_landlord.id,
    )
    return build_dispute_response(session, dispute, "landlord")


@router.put("/{payment_id}/dispute/reopen", response_model=PaymentDisputeResponse)
async def reopen_payment_dispute(
    payment_id: str,
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    _, _, _ = get_payment_for_landlord(session, payment_id, current_landlord.id)
    dispute = reopen_dispute(session, payment_id=payment_id)
    return build_dispute_response(session, dispute, "landlord")


@router.get("/{payment_id}/dispute/messages/{message_id}/attachment")
async def get_payment_dispute_attachment(
    payment_id: str,
    message_id: str,
    viewer=Depends(_get_current_receipt_viewer),
    session: Session = Depends(get_session),
):
    viewer_type, viewer_user = viewer

    if viewer_type == "landlord":
        _, _, _ = get_payment_for_landlord(session, payment_id, viewer_user.id)
    else:
        _ = get_payment_for_tenant(session, payment_id, viewer_user.id)

    message = session.exec(
        select(PaymentDisputeMessage).where(
            PaymentDisputeMessage.id == message_id,
            PaymentDisputeMessage.payment_id == payment_id,
        )
    ).first()

    if not message or not message.attachment_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found"
        )

    file_path = resolve_dispute_attachment_file_path(message.attachment_url)
    return FileResponse(
        file_path,
        media_type=message.attachment_content_type or "application/octet-stream",
        filename=message.attachment_name or os.path.basename(file_path),
    )

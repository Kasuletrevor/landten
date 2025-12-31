from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from app.core.database import get_session
from app.core.security import get_current_landlord
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment_schedule import PaymentSchedule, PaymentFrequency
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import (
    PaymentMarkPaid,
    PaymentWaive,
    PaymentUpdate,
    ManualPaymentCreate,
    PaymentResponse,
    PaymentWithTenant,
    PaymentListResponse,
    PaymentSummary,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


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
    """Add tenant and property info to a payment."""
    tenant = session.get(Tenant, payment.tenant_id)
    room = session.get(Room, tenant.room_id) if tenant else None
    property = session.get(Property, room.property_id) if room else None

    return PaymentWithTenant(
        **payment.model_dump(),
        tenant_name=tenant.name if tenant else None,
        tenant_email=tenant.email if tenant else None,
        tenant_phone=tenant.phone if tenant else None,
        room_name=room.name if room else None,
        property_id=property.id if property else None,
        property_name=property.name if property else None,
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
            payment.updated_at = datetime.utcnow()
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
            payment.updated_at = datetime.utcnow()
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
            payment.updated_at = datetime.utcnow()
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
        payment.updated_at = datetime.utcnow()
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
    payment.updated_at = datetime.utcnow()

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
    payment.updated_at = datetime.utcnow()

    session.add(payment)
    session.commit()
    session.refresh(payment)

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

    payment.updated_at = datetime.utcnow()
    session.add(payment)
    session.commit()
    session.refresh(payment)

    return enrich_payment_with_tenant(payment, session)


@router.post(
    "/manual", response_model=PaymentWithTenant, status_code=status.HTTP_201_CREATED
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

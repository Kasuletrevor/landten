"""
Payment generation and status update service.
Handles auto-generating payments based on schedules.
"""

from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select
from typing import Optional, List

from app.models.tenant import Tenant
from app.models.payment_schedule import PaymentSchedule, PaymentFrequency
from app.models.payment import Payment, PaymentStatus


def get_frequency_months(frequency: PaymentFrequency) -> int:
    """Convert payment frequency to number of months."""
    if frequency == PaymentFrequency.MONTHLY:
        return 1
    elif frequency == PaymentFrequency.BI_MONTHLY:
        return 2
    elif frequency == PaymentFrequency.QUARTERLY:
        return 3
    return 1


def calculate_next_period(
    schedule: PaymentSchedule, after_date: date
) -> tuple[date, date, date, date]:
    """
    Calculate the next payment period after a given date.
    Returns (period_start, period_end, due_date, window_end_date)
    """
    months = get_frequency_months(schedule.frequency)

    # Start from the schedule's start date
    current_period_start = schedule.start_date

    # Find the period that comes after after_date
    while True:
        period_end = (
            current_period_start + relativedelta(months=months) - relativedelta(days=1)
        )

        if period_end >= after_date:
            # This is the period we want
            break

        # Move to next period
        current_period_start = current_period_start + relativedelta(months=months)

    # Due date is on the due_day of the period start month
    due_date = date(
        current_period_start.year, current_period_start.month, schedule.due_day
    )
    window_end_date = due_date + relativedelta(days=schedule.window_days)

    return current_period_start, period_end, due_date, window_end_date


def generate_payment_for_schedule(
    schedule: PaymentSchedule, session: Session, force: bool = False
) -> Optional[Payment]:
    """
    Generate the next payment for a schedule if needed.
    Only generates one period ahead.

    Args:
        schedule: The payment schedule
        session: Database session
        force: If True, generate even if not needed

    Returns:
        The generated Payment, or None if not needed
    """
    if not schedule.is_active:
        return None

    today = date.today()

    # Get the most recent payment for this schedule
    latest_payment = session.exec(
        select(Payment)
        .where(Payment.schedule_id == schedule.id)
        .order_by(Payment.period_end.desc())
    ).first()

    if latest_payment:
        # Check if we need to generate the next one
        # Generate when current is paid/waived or when current period ends
        should_generate = (
            latest_payment.status
            in [PaymentStatus.ON_TIME, PaymentStatus.LATE, PaymentStatus.WAIVED]
            or latest_payment.period_end < today
            or force
        )

        if not should_generate:
            return None

        # Calculate next period after the latest payment
        period_start, period_end, due_date, window_end = calculate_next_period(
            schedule, latest_payment.period_end + relativedelta(days=1)
        )
    else:
        # First payment - start from schedule start date
        period_start, period_end, due_date, window_end = calculate_next_period(
            schedule, schedule.start_date
        )

    # Don't generate payments too far in the future (more than one period ahead)
    max_future = today + relativedelta(
        months=get_frequency_months(schedule.frequency) * 2
    )
    if period_start > max_future:
        return None

    # Check if payment already exists for this period
    existing = session.exec(
        select(Payment).where(
            Payment.schedule_id == schedule.id, Payment.period_start == period_start
        )
    ).first()

    if existing:
        return None

    # Determine initial status
    if today < due_date:
        status = PaymentStatus.UPCOMING
    elif today <= window_end:
        status = PaymentStatus.PENDING
    else:
        status = PaymentStatus.OVERDUE

    # Create the payment
    payment = Payment(
        tenant_id=schedule.tenant_id,
        schedule_id=schedule.id,
        period_start=period_start,
        period_end=period_end,
        amount_due=schedule.amount,
        due_date=due_date,
        window_end_date=window_end,
        status=status,
        is_manual=False,
    )

    session.add(payment)
    return payment


def generate_all_due_payments(session: Session) -> List[Payment]:
    """
    Generate payments for all active schedules that need them.
    Should be called periodically (e.g., daily) or on-demand.

    Returns:
        List of generated payments
    """
    # Get all active schedules
    schedules = session.exec(
        select(PaymentSchedule).where(PaymentSchedule.is_active == True)
    ).all()

    generated = []
    for schedule in schedules:
        # Check if tenant is still active
        tenant = session.get(Tenant, schedule.tenant_id)
        if not tenant or not tenant.is_active:
            continue

        payment = generate_payment_for_schedule(schedule, session)
        if payment:
            generated.append(payment)

    if generated:
        session.commit()

    return generated


def update_payment_statuses(session: Session) -> int:
    """
    Update statuses for all unpaid payments based on current date.
    Should be called periodically or on-demand.

    Returns:
        Number of payments updated
    """
    today = date.today()
    updated_count = 0

    # Get all unpaid payments
    payments = session.exec(
        select(Payment).where(
            Payment.status.in_([PaymentStatus.UPCOMING, PaymentStatus.PENDING])
        )
    ).all()

    for payment in payments:
        new_status = payment.status

        if today < payment.due_date:
            new_status = PaymentStatus.UPCOMING
        elif today <= payment.window_end_date:
            new_status = PaymentStatus.PENDING
        else:
            new_status = PaymentStatus.OVERDUE

        if new_status != payment.status:
            payment.status = new_status
            payment.updated_at = datetime.now(timezone.utc)
            session.add(payment)
            updated_count += 1

    if updated_count > 0:
        session.commit()

    return updated_count


def get_payments_entering_window(session: Session) -> List[Payment]:
    """
    Get payments that are entering their payment window today.
    Useful for sending reminders.
    """
    today = date.today()

    return session.exec(
        select(Payment).where(
            Payment.due_date == today, Payment.status == PaymentStatus.UPCOMING
        )
    ).all()


def get_payments_becoming_overdue(session: Session) -> List[Payment]:
    """
    Get payments that are becoming overdue today (window just ended).
    Useful for sending overdue notices.
    """
    today = date.today()
    yesterday = today - relativedelta(days=1)

    return session.exec(
        select(Payment).where(
            Payment.window_end_date == yesterday,
            Payment.status.in_([PaymentStatus.UPCOMING, PaymentStatus.PENDING]),
        )
    ).all()

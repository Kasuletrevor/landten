"""
Analytics router for dashboard data.
Provides aggregated statistics across properties, payments, and vacancies.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Dict

from app.core.database import get_session
from app.core.security import get_current_landlord
from app.core.currency import convert_currency
from app.models.landlord import Landlord
from app.models.property import Property
from app.models.room import Room
from app.models.tenant import Tenant
from app.models.payment import Payment, PaymentStatus
from app.schemas.analytics import (
    DashboardAnalytics,
    CurrentMonthStats,
    MonthlyStats,
    VacancyStats,
    OverdueSummary,
    TrendComparison,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_landlord_data(landlord_id: str, session: Session) -> Dict:
    """
    Get all properties, rooms, tenants, and payments for a landlord.
    Returns a dict with all entities for further processing.
    """
    # Get properties
    properties = session.exec(
        select(Property).where(Property.landlord_id == landlord_id)
    ).all()
    property_ids = [p.id for p in properties]

    if not property_ids:
        return {
            "properties": [],
            "rooms": [],
            "tenants": [],
            "payments": [],
        }

    # Get rooms
    rooms = session.exec(select(Room).where(Room.property_id.in_(property_ids))).all()
    room_ids = [r.id for r in rooms]

    if not room_ids:
        return {
            "properties": properties,
            "rooms": [],
            "tenants": [],
            "payments": [],
        }

    # Get tenants (only active ones - those with room assignments)
    tenants = session.exec(select(Tenant).where(Tenant.room_id.in_(room_ids))).all()
    tenant_ids = [t.id for t in tenants]

    # Get payments
    payments = []
    if tenant_ids:
        payments = session.exec(
            select(Payment).where(Payment.tenant_id.in_(tenant_ids))
        ).all()

    return {
        "properties": properties,
        "rooms": rooms,
        "tenants": tenants,
        "payments": payments,
    }


def get_room_currency(room_id: str, rooms: List[Room]) -> str:
    """Get the currency for a room."""
    for room in rooms:
        if room.id == room_id:
            return room.currency
    return "UGX"


def get_tenant_room_id(tenant_id: str, tenants: List[Tenant]) -> str | None:
    """Get the room ID for a tenant."""
    for tenant in tenants:
        if tenant.id == tenant_id:
            return tenant.room_id
    return None


def calculate_month_stats(
    payments: List[Payment],
    tenants: List[Tenant],
    rooms: List[Room],
    target_currency: str,
    year: int,
    month: int,
) -> MonthlyStats:
    """
    Calculate statistics for a specific month.
    Converts all amounts to target_currency.
    """
    month_start = date(year, month, 1)
    month_end = month_start + relativedelta(months=1) - relativedelta(days=1)

    expected = 0.0
    received = 0.0

    for payment in payments:
        # Check if payment is within this month (by due date)
        if payment.due_date.year == year and payment.due_date.month == month:
            # Get room currency for conversion
            room_id = get_tenant_room_id(payment.tenant_id, tenants)
            room_currency = get_room_currency(room_id, rooms) if room_id else "UGX"

            # Convert amount to target currency
            converted_amount = convert_currency(
                payment.amount_due, room_currency, target_currency
            )

            expected += converted_amount

            # Check if paid
            if payment.status in [PaymentStatus.ON_TIME, PaymentStatus.LATE]:
                received += converted_amount

    collection_rate = (received / expected * 100) if expected > 0 else 0.0

    return MonthlyStats(
        month=f"{year}-{month:02d}",
        expected=round(expected, 2),
        received=round(received, 2),
        collection_rate=round(collection_rate, 1),
    )


def calculate_vacancy_stats(rooms: List[Room]) -> VacancyStats:
    """Calculate vacancy statistics across all rooms."""
    total = len(rooms)
    occupied = sum(1 for r in rooms if r.is_occupied)
    vacant = total - occupied

    vacancy_rate = (vacant / total * 100) if total > 0 else 0.0

    return VacancyStats(
        total_rooms=total,
        occupied=occupied,
        vacant=vacant,
        vacancy_rate=round(vacancy_rate, 1),
    )


def calculate_overdue_summary(
    payments: List[Payment],
    tenants: List[Tenant],
    rooms: List[Room],
    target_currency: str,
) -> OverdueSummary:
    """Calculate summary of overdue payments."""
    today = date.today()
    overdue_payments = [p for p in payments if p.status == PaymentStatus.OVERDUE]

    count = len(overdue_payments)
    total_amount = 0.0
    oldest_days = 0

    for payment in overdue_payments:
        # Convert to target currency
        room_id = get_tenant_room_id(payment.tenant_id, tenants)
        room_currency = get_room_currency(room_id, rooms) if room_id else "UGX"
        converted_amount = convert_currency(
            payment.amount_due, room_currency, target_currency
        )
        total_amount += converted_amount

        # Calculate days overdue
        days = (today - payment.due_date).days
        if days > oldest_days:
            oldest_days = days

    return OverdueSummary(
        count=count,
        total_amount=round(total_amount, 2),
        oldest_days=oldest_days,
    )


def calculate_trend_comparison(
    current_value: float,
    previous_value: float,
    higher_is_better: bool = True,
) -> TrendComparison:
    """
    Calculate trend comparison between two values.

    Args:
        current_value: Current period's value
        previous_value: Previous period's value
        higher_is_better: Whether an increase is considered an improvement
    """
    if previous_value == 0:
        change_percent = 100.0 if current_value > 0 else 0.0
    else:
        change_percent = ((current_value - previous_value) / previous_value) * 100

    is_improvement = (change_percent > 0) == higher_is_better

    return TrendComparison(
        current_value=round(current_value, 2),
        previous_value=round(previous_value, 2),
        change_percent=round(change_percent, 1),
        is_improvement=is_improvement,
    )


@router.get("/dashboard", response_model=DashboardAnalytics)
async def get_dashboard_analytics(
    current_landlord: Landlord = Depends(get_current_landlord),
    session: Session = Depends(get_session),
):
    """
    Get comprehensive analytics for the landlord's dashboard.

    Returns:
    - Current month statistics (expected, received, outstanding, collection rate)
    - 3-month trend data
    - Vacancy statistics
    - Overdue payment summary
    - Trend comparisons (month-over-month changes)

    All monetary amounts are converted to the landlord's primary currency.
    """
    # Get landlord's primary currency
    target_currency = current_landlord.primary_currency or "UGX"

    # Get all data
    data = get_landlord_data(current_landlord.id, session)
    payments = data["payments"]
    tenants = data["tenants"]
    rooms = data["rooms"]

    # Get current date info
    today = date.today()
    current_year = today.year
    current_month = today.month

    # Calculate current month stats
    current_month_stats = calculate_month_stats(
        payments, tenants, rooms, target_currency, current_year, current_month
    )

    current_month_data = CurrentMonthStats(
        expected=current_month_stats.expected,
        received=current_month_stats.received,
        outstanding=round(
            current_month_stats.expected - current_month_stats.received, 2
        ),
        collection_rate=current_month_stats.collection_rate,
    )

    # Calculate 3-month trend (current + previous 2 months)
    trend: List[MonthlyStats] = []
    for i in range(3):
        month_date = today - relativedelta(months=i)
        stats = calculate_month_stats(
            payments, tenants, rooms, target_currency, month_date.year, month_date.month
        )
        trend.append(stats)

    # trend[0] is current month, trend[1] is previous month, etc.
    # Reverse so oldest is first for chart display
    trend.reverse()

    # Calculate vacancy stats
    vacancy = calculate_vacancy_stats(rooms)

    # Calculate previous month vacancy for trend (based on room count, not historical)
    # For MVP, we don't track historical vacancy, so use current as baseline
    # In future, could track vacancy history
    vacancy_trend = calculate_trend_comparison(
        vacancy.vacancy_rate,
        vacancy.vacancy_rate,  # No historical data yet
        higher_is_better=False,  # Lower vacancy is better
    )

    # Calculate overdue summary
    overdue_summary = calculate_overdue_summary(
        payments, tenants, rooms, target_currency
    )

    # Calculate income trend (current vs previous month received)
    # trend is now [oldest, middle, newest]
    current_received = trend[2].received if len(trend) > 2 else 0
    previous_received = trend[1].received if len(trend) > 1 else 0
    income_trend = calculate_trend_comparison(
        current_received,
        previous_received,
        higher_is_better=True,
    )

    # Calculate collection rate trend
    current_collection = trend[2].collection_rate if len(trend) > 2 else 0
    previous_collection = trend[1].collection_rate if len(trend) > 1 else 0
    collection_trend = calculate_trend_comparison(
        current_collection,
        previous_collection,
        higher_is_better=True,
    )

    return DashboardAnalytics(
        current_month=current_month_data,
        trend=trend,
        vacancy=vacancy,
        overdue_summary=overdue_summary,
        income_trend=income_trend,
        collection_trend=collection_trend,
        vacancy_trend=vacancy_trend,
        primary_currency=target_currency,
        currency_note=f"Amounts shown in {target_currency}",
    )

"""
Analytics schemas for dashboard data.
"""

from pydantic import BaseModel
from typing import List, Optional


class MonthlyStats(BaseModel):
    """Statistics for a single month."""

    month: str  # Format: "YYYY-MM"
    expected: float
    received: float
    collection_rate: float  # Percentage 0-100


class CurrentMonthStats(BaseModel):
    """Current month's statistics."""

    expected: float
    received: float
    outstanding: float
    collection_rate: float


class VacancyStats(BaseModel):
    """Vacancy statistics across all properties."""

    total_rooms: int
    occupied: int
    vacant: int
    vacancy_rate: float  # Percentage 0-100


class OverdueSummary(BaseModel):
    """Summary of overdue payments."""

    count: int
    total_amount: float
    oldest_days: int  # Days since oldest overdue payment


class TrendComparison(BaseModel):
    """Month-over-month comparison."""

    current_value: float
    previous_value: float
    change_percent: float  # Positive = increase, Negative = decrease
    is_improvement: bool  # True if change is good (e.g., higher collection rate)


class DashboardAnalytics(BaseModel):
    """Complete analytics response for dashboard."""

    # Current month data
    current_month: CurrentMonthStats

    # 3-month trend (most recent first)
    trend: List[MonthlyStats]

    # Vacancy info
    vacancy: VacancyStats

    # Overdue summary
    overdue_summary: OverdueSummary

    # Trends for key metrics
    income_trend: TrendComparison
    collection_trend: TrendComparison
    vacancy_trend: TrendComparison

    # Currency info
    primary_currency: str
    currency_note: str  # e.g., "Amounts shown in UGX"

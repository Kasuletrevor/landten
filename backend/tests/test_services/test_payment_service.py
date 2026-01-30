"""
Comprehensive tests for the payment service module.
Tests all payment generation and status management functions.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from dateutil.relativedelta import relativedelta
from sqlmodel import select

from app.services.payment_service import (
    calculate_prorated_rent,
    create_prorated_payment,
    get_frequency_months,
    calculate_next_period,
    generate_payment_for_schedule,
    generate_all_due_payments,
    update_payment_statuses,
    get_payments_entering_window,
    get_payments_becoming_overdue,
)
from app.models.payment import Payment, PaymentStatus
from app.models.payment_schedule import PaymentSchedule, PaymentFrequency
from app.models.tenant import Tenant
from tests.factories import (
    LandlordFactory,
    PropertyFactory,
    RoomFactory,
    TenantFactory,
    PaymentScheduleFactory,
    PaymentFactory,
    create_full_test_scenario,
)


def setup_date_mock(mock_date_class, today_value):
    """
    Setup a date mock that:
    - Returns a real date object when called as a constructor (date(y, m, d))
    - Returns the specified value for date.today()
    """
    original_date = date

    def side_effect(*args, **kwargs):
        if len(args) == 3:
            return original_date(args[0], args[1], args[2])
        return original_date(*args, **kwargs)

    mock_date_class.side_effect = side_effect
    mock_date_class.today.return_value = today_value

    # Preserve other date attributes
    mock_date_class.__add__ = original_date.__add__
    mock_date_class.__sub__ = original_date.__sub__
    mock_date_class.__lt__ = original_date.__lt__
    mock_date_class.__le__ = original_date.__le__
    mock_date_class.__gt__ = original_date.__gt__
    mock_date_class.__ge__ = original_date.__ge__
    mock_date_class.__eq__ = original_date.__eq__

    return mock_date_class


# =============================================================================
# Tests for calculate_prorated_rent
# =============================================================================


class TestCalculateProratedRent:
    """Test prorated rent calculation for various move-in dates."""

    def test_move_in_beginning_of_month(self):
        """Test calculation when moving in on day 1."""
        move_in_date = date(2024, 1, 1)
        monthly_rent = 500000

        prorated_amount, due_date = calculate_prorated_rent(monthly_rent, move_in_date)

        # Full month (31 days in January)
        expected = (monthly_rent / 31) * 31
        assert prorated_amount == round(expected, 2)
        assert due_date == date(2024, 1, 4)

    def test_move_in_middle_of_month(self):
        """Test calculation when moving in on day 15 of 31-day month."""
        move_in_date = date(2024, 1, 15)
        monthly_rent = 500000

        prorated_amount, due_date = calculate_prorated_rent(monthly_rent, move_in_date)

        # 17 remaining days (including move-in day)
        expected = (monthly_rent / 31) * 17
        assert prorated_amount == round(expected, 2)
        assert due_date == date(2024, 1, 18)

    def test_move_in_end_of_month(self):
        """Test calculation when moving in on last day of 31-day month."""
        move_in_date = date(2024, 1, 31)
        monthly_rent = 500000

        prorated_amount, due_date = calculate_prorated_rent(monthly_rent, move_in_date)

        # 1 remaining day
        expected = (monthly_rent / 31) * 1
        assert prorated_amount == round(expected, 2)
        assert due_date == date(2024, 2, 3)

    def test_february_28_days(self):
        """Test calculation for February with 28 days (non-leap year)."""
        move_in_date = date(2023, 2, 15)
        monthly_rent = 500000

        prorated_amount, due_date = calculate_prorated_rent(monthly_rent, move_in_date)

        # 14 remaining days in 28-day February
        expected = (monthly_rent / 28) * 14
        assert prorated_amount == round(expected, 2)
        assert due_date == date(2023, 2, 18)

    def test_february_29_days(self):
        """Test calculation for February with 29 days (leap year)."""
        move_in_date = date(2024, 2, 15)
        monthly_rent = 500000

        prorated_amount, due_date = calculate_prorated_rent(monthly_rent, move_in_date)

        # 15 remaining days in 29-day February
        expected = (monthly_rent / 29) * 15
        assert prorated_amount == round(expected, 2)
        assert due_date == date(2024, 2, 18)

    def test_month_with_30_days(self):
        """Test calculation for 30-day month (April)."""
        move_in_date = date(2024, 4, 10)
        monthly_rent = 600000

        prorated_amount, due_date = calculate_prorated_rent(monthly_rent, move_in_date)

        # 21 remaining days in 30-day April
        expected = (monthly_rent / 30) * 21
        assert prorated_amount == round(expected, 2)
        assert due_date == date(2024, 4, 13)

    def test_calculation_accuracy_small_amount(self):
        """Test precision with small rent amounts."""
        move_in_date = date(2024, 1, 15)
        monthly_rent = 100000

        prorated_amount, due_date = calculate_prorated_rent(monthly_rent, move_in_date)

        expected = (monthly_rent / 31) * 17
        assert prorated_amount == round(expected, 2)

    def test_calculation_accuracy_large_amount(self):
        """Test precision with large rent amounts."""
        move_in_date = date(2024, 1, 20)
        monthly_rent = 2000000

        prorated_amount, due_date = calculate_prorated_rent(monthly_rent, move_in_date)

        # 12 remaining days
        expected = (monthly_rent / 31) * 12
        assert prorated_amount == round(expected, 2)


# =============================================================================
# Tests for create_prorated_payment
# =============================================================================


class TestCreateProratedPayment:
    """Test prorated payment creation for mid-month move-ins."""

    def test_returns_none_for_move_in_on_1st(self, session):
        """Test that no prorated payment is created when moving in on 1st."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        move_in_date = date(2024, 1, 1)

        result = create_prorated_payment(
            tenant_id=tenant.id,
            monthly_rent=500000,
            move_in_date=move_in_date,
            session=session,
        )

        assert result is None

    def test_returns_none_for_move_in_on_5th(self, session):
        """Test that no prorated payment is created when moving in on 5th."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        move_in_date = date(2024, 1, 5)

        result = create_prorated_payment(
            tenant_id=tenant.id,
            monthly_rent=500000,
            move_in_date=move_in_date,
            session=session,
        )

        assert result is None

    def test_creates_prorated_payment_for_move_in_after_5th(self, session):
        """Test prorated payment creation when moving in after 5th."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        move_in_date = date(2024, 1, 15)

        payment = create_prorated_payment(
            tenant_id=tenant.id,
            monthly_rent=500000,
            move_in_date=move_in_date,
            session=session,
        )

        assert payment is not None
        assert payment.tenant_id == tenant.id
        assert payment.schedule_id is None
        assert payment.is_manual is True
        assert "Prorated rent" in payment.notes

    @patch("app.services.payment_service.date")
    def test_status_upcoming_when_before_due_date(self, mock_date, session):
        """Test UPCOMING status when today is before due date."""
        setup_date_mock(mock_date, date(2024, 1, 10))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        move_in_date = date(2024, 1, 15)

        payment = create_prorated_payment(
            tenant_id=tenant.id,
            monthly_rent=500000,
            move_in_date=move_in_date,
            session=session,
        )

        assert payment.status == PaymentStatus.UPCOMING

    @patch("app.services.payment_service.date")
    def test_status_pending_when_in_window(self, mock_date, session):
        """Test PENDING status when today is in payment window."""
        # Due date is 18th, window ends 21st
        setup_date_mock(mock_date, date(2024, 1, 19))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        move_in_date = date(2024, 1, 15)

        payment = create_prorated_payment(
            tenant_id=tenant.id,
            monthly_rent=500000,
            move_in_date=move_in_date,
            session=session,
        )

        assert payment.status == PaymentStatus.PENDING

    @patch("app.services.payment_service.date")
    def test_status_overdue_when_after_window(self, mock_date, session):
        """Test OVERDUE status when today is after window end."""
        # Window ends on 21st
        setup_date_mock(mock_date, date(2024, 1, 25))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        move_in_date = date(2024, 1, 15)

        payment = create_prorated_payment(
            tenant_id=tenant.id,
            monthly_rent=500000,
            move_in_date=move_in_date,
            session=session,
        )

        assert payment.status == PaymentStatus.OVERDUE

    def test_period_calculations(self, session):
        """Test that period covers from move-in to end of month."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        move_in_date = date(2024, 1, 15)

        payment = create_prorated_payment(
            tenant_id=tenant.id,
            monthly_rent=500000,
            move_in_date=move_in_date,
            session=session,
        )

        assert payment.period_start == move_in_date
        assert payment.period_end == date(2024, 1, 31)
        # Due date is 3 days from move-in
        assert payment.due_date == date(2024, 1, 18)
        # Window is 3 days after due date
        assert payment.window_end_date == date(2024, 1, 21)

    def test_payment_saved_to_database(self, session):
        """Test that created payment is persisted."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        move_in_date = date(2024, 1, 10)

        payment = create_prorated_payment(
            tenant_id=tenant.id,
            monthly_rent=500000,
            move_in_date=move_in_date,
            session=session,
        )
        session.commit()

        # Verify payment exists in database
        db_payment = session.get(Payment, payment.id)
        assert db_payment is not None
        assert db_payment.tenant_id == tenant.id


# =============================================================================
# Tests for get_frequency_months
# =============================================================================


class TestGetFrequencyMonths:
    """Test conversion of payment frequency to months."""

    def test_monthly_returns_1(self):
        """Test MONTHLY frequency returns 1 month."""
        result = get_frequency_months(PaymentFrequency.MONTHLY)
        assert result == 1

    def test_bi_monthly_returns_2(self):
        """Test BI_MONTHLY frequency returns 2 months."""
        result = get_frequency_months(PaymentFrequency.BI_MONTHLY)
        assert result == 2

    def test_quarterly_returns_3(self):
        """Test QUARTERLY frequency returns 3 months."""
        result = get_frequency_months(PaymentFrequency.QUARTERLY)
        assert result == 3

    def test_invalid_frequency_defaults_to_1(self):
        """Test invalid/None frequency returns 1 (default)."""
        result = get_frequency_months(None)
        assert result == 1


# =============================================================================
# Tests for calculate_next_period
# =============================================================================


class TestCalculateNextPeriod:
    """Test calculation of next payment periods for different frequencies."""

    def test_monthly_period_calculation(self, session):
        """Test period calculation for monthly schedule."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        period_start, period_end, due_date, window_end = calculate_next_period(
            schedule, date(2024, 1, 1)
        )

        assert period_start == date(2024, 1, 1)
        assert period_end == date(2024, 1, 31)
        assert due_date == date(2024, 1, 5)
        assert window_end == date(2024, 1, 8)

    def test_bi_monthly_period_calculation(self, session):
        """Test period calculation for bi-monthly schedule."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            frequency=PaymentFrequency.BI_MONTHLY,
            due_day=10,
            window_days=5,
            start_date=date(2024, 1, 1),
        )

        period_start, period_end, due_date, window_end = calculate_next_period(
            schedule, date(2024, 1, 15)
        )

        assert period_start == date(2024, 1, 1)
        assert period_end == date(2024, 2, 29)  # 2024 is leap year
        assert due_date == date(2024, 1, 10)
        assert window_end == date(2024, 1, 15)

    def test_quarterly_period_calculation(self, session):
        """Test period calculation for quarterly schedule."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            frequency=PaymentFrequency.QUARTERLY,
            due_day=1,
            window_days=7,
            start_date=date(2024, 1, 1),
        )

        period_start, period_end, due_date, window_end = calculate_next_period(
            schedule, date(2024, 2, 1)
        )

        assert period_start == date(2024, 1, 1)
        assert period_end == date(2024, 3, 31)
        assert due_date == date(2024, 1, 1)
        assert window_end == date(2024, 1, 8)

    def test_finds_period_after_given_date(self, session):
        """Test that it finds the period that ends on or after the given date."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            frequency=PaymentFrequency.MONTHLY,
            due_day=1,
            window_days=5,
            start_date=date(2024, 1, 1),
        )

        # Looking for period after Feb 15th - Feb period (1-29) ends on Feb 29 which >= Feb 15
        period_start, period_end, due_date, window_end = calculate_next_period(
            schedule, date(2024, 2, 15)
        )

        # Feb 1-29 is the period that ends on or after Feb 15
        assert period_start == date(2024, 2, 1)
        assert period_end == date(2024, 2, 29)
        assert due_date == date(2024, 2, 1)

        # Looking for period on Mar 31st - Mar period ends on Mar 31 which >= Mar 31
        period_start, period_end, due_date, window_end = calculate_next_period(
            schedule, date(2024, 3, 31)
        )

        # Mar 1-31 is the period that ends on or after Mar 31
        assert period_start == date(2024, 3, 1)
        assert period_end == date(2024, 3, 31)
        assert due_date == date(2024, 3, 1)

        # Looking for period strictly after Mar 31st (Apr 1st) - should get Apr
        period_start, period_end, due_date, window_end = calculate_next_period(
            schedule, date(2024, 4, 1)
        )

        assert period_start == date(2024, 4, 1)
        assert period_end == date(2024, 4, 30)
        assert due_date == date(2024, 4, 1)

    def test_handles_year_boundaries(self, session):
        """Test period calculation across year boundaries."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            frequency=PaymentFrequency.MONTHLY,
            due_day=15,
            window_days=3,
            start_date=date(2024, 12, 1),
        )

        period_start, period_end, due_date, window_end = calculate_next_period(
            schedule, date(2024, 12, 1)
        )

        assert period_start == date(2024, 12, 1)
        assert period_end == date(2024, 12, 31)
        assert due_date == date(2024, 12, 15)
        assert window_end == date(2024, 12, 18)


# =============================================================================
# Tests for generate_payment_for_schedule
# =============================================================================


class TestGeneratePaymentForSchedule:
    """Test payment generation for payment schedules."""

    def test_generates_first_payment(self, session):
        """Test generating the first payment for a schedule."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        payment = generate_payment_for_schedule(schedule, session)

        assert payment is not None
        assert payment.tenant_id == tenant.id
        assert payment.schedule_id == schedule.id
        assert payment.amount_due == 100000
        assert payment.is_manual is False

    def test_generates_next_payment_after_paid_one(self, session):
        """Test generating next payment when current is paid."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        # Create first paid payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            schedule_id=schedule.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status=PaymentStatus.ON_TIME,
        )

        payment = generate_payment_for_schedule(schedule, session)

        assert payment is not None
        assert payment.period_start == date(2024, 2, 1)
        assert payment.period_end == date(2024, 2, 29)  # Leap year

    def test_generates_next_when_period_ends(self, session):
        """Test generating next payment when current period has ended."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        # Create first pending payment with ended period
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            schedule_id=schedule.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status=PaymentStatus.PENDING,
        )

        # Mock today to be after period end
        with patch("app.services.payment_service.date") as mock_date:
            setup_date_mock(mock_date, date(2024, 2, 1))
            payment = generate_payment_for_schedule(schedule, session)

        assert payment is not None
        assert payment.period_start == date(2024, 2, 1)

    def test_force_parameter_overrides_checks(self, session):
        """Test force=True generates payment even when not needed."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        # Create pending payment (normally wouldn't generate next)
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            schedule_id=schedule.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status=PaymentStatus.PENDING,
        )

        # Force generate
        payment = generate_payment_for_schedule(schedule, session, force=True)

        assert payment is not None
        assert payment.period_start == date(2024, 2, 1)

    def test_does_not_generate_too_far_in_future(self, session):
        """Test that payment is not generated more than 2 periods ahead."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        # Schedule starts far in future
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2025, 6, 1),
        )

        # Mock today to be in early 2024
        with patch("app.services.payment_service.date") as mock_date:
            setup_date_mock(mock_date, date(2024, 1, 1))
            payment = generate_payment_for_schedule(schedule, session)

        assert payment is None

    def test_returns_none_if_already_exists(self, session):
        """Test that no duplicate payment is created for same period."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        # Create first payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            schedule_id=schedule.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status=PaymentStatus.ON_TIME,
        )

        # Create second payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            schedule_id=schedule.id,
            period_start=date(2024, 2, 1),
            period_end=date(2024, 2, 29),
            status=PaymentStatus.UPCOMING,
        )

        # Try to generate - should return None since Feb payment exists
        # Mock today to be in Feb so period hasn't ended
        with patch("app.services.payment_service.date") as mock_date:
            setup_date_mock(mock_date, date(2024, 2, 15))
            payment = generate_payment_for_schedule(schedule, session)

        assert payment is None

    def test_returns_none_for_inactive_schedule(self, session):
        """Test that no payment is generated for inactive schedule."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
            is_active=False,
        )

        payment = generate_payment_for_schedule(schedule, session)

        assert payment is None

    @patch("app.services.payment_service.date")
    def test_status_upcoming_for_future_due_date(self, mock_date, session):
        """Test UPCOMING status when due date is in future."""
        setup_date_mock(mock_date, date(2024, 1, 1))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=10,
            window_days=5,
            start_date=date(2024, 1, 1),
        )

        payment = generate_payment_for_schedule(schedule, session)

        assert payment is not None
        assert payment.status == PaymentStatus.UPCOMING

    @patch("app.services.payment_service.date")
    def test_status_pending_when_in_window(self, mock_date, session):
        """Test PENDING status when today is in payment window."""
        setup_date_mock(mock_date, date(2024, 1, 12))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=10,
            window_days=5,
            start_date=date(2024, 1, 1),
        )

        payment = generate_payment_for_schedule(schedule, session)

        assert payment is not None
        assert payment.status == PaymentStatus.PENDING

    @patch("app.services.payment_service.date")
    def test_status_overdue_when_after_window(self, mock_date, session):
        """Test OVERDUE status when today is after window end."""
        setup_date_mock(mock_date, date(2024, 1, 20))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=10,
            window_days=5,
            start_date=date(2024, 1, 1),
        )

        payment = generate_payment_for_schedule(schedule, session)

        assert payment is not None
        assert payment.status == PaymentStatus.OVERDUE

    def test_payment_saved_to_database(self, session):
        """Test that generated payment is persisted."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        payment = generate_payment_for_schedule(schedule, session)
        session.commit()

        db_payment = session.get(Payment, payment.id)
        assert db_payment is not None
        assert db_payment.schedule_id == schedule.id

    def test_late_status_also_allows_generation(self, session):
        """Test that LATE status allows next payment generation."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        # Create late payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            schedule_id=schedule.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status=PaymentStatus.LATE,
        )

        payment = generate_payment_for_schedule(schedule, session)

        assert payment is not None
        assert payment.period_start == date(2024, 2, 1)

    def test_waived_status_allows_generation(self, session):
        """Test that WAIVED status allows next payment generation."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        # Create waived payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            schedule_id=schedule.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status=PaymentStatus.WAIVED,
        )

        payment = generate_payment_for_schedule(schedule, session)

        assert payment is not None
        assert payment.period_start == date(2024, 2, 1)

    def test_verifying_status_blocks_generation(self, session):
        """Test that VERIFYING status blocks next payment generation."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        # Create verifying payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            schedule_id=schedule.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status=PaymentStatus.VERIFYING,
        )

        # Mock today to be in Jan so period hasn't ended
        with patch("app.services.payment_service.date") as mock_date:
            setup_date_mock(mock_date, date(2024, 1, 15))
            payment = generate_payment_for_schedule(schedule, session)

        assert payment is None


# =============================================================================
# Tests for generate_all_due_payments
# =============================================================================


class TestGenerateAllDuePayments:
    """Test batch payment generation for all active schedules."""

    def test_generates_payments_for_multiple_schedules(self, session):
        """Test generating payments for multiple active schedules."""
        # Create first scenario with unique landlord email
        landlord1 = LandlordFactory.create(session=session, email="landlord1@test.com")
        property1 = PropertyFactory.create(session=session, landlord_id=landlord1.id)
        room1 = RoomFactory.create(session=session, property_id=property1.id)
        tenant1 = TenantFactory.create(session=session, room_id=room1.id)
        schedule1 = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant1.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        # Create second scenario with unique landlord email
        landlord2 = LandlordFactory.create(session=session, email="landlord2@test.com")
        property2 = PropertyFactory.create(session=session, landlord_id=landlord2.id)
        room2 = RoomFactory.create(session=session, property_id=property2.id)
        tenant2 = TenantFactory.create(session=session, room_id=room2.id)
        schedule2 = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant2.id,
            amount=200000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=10,
            window_days=5,
            start_date=date(2024, 1, 1),
        )

        generated = generate_all_due_payments(session)

        assert len(generated) == 2
        assert generated[0].schedule_id in [schedule1.id, schedule2.id]
        assert generated[1].schedule_id in [schedule1.id, schedule2.id]

    def test_skips_inactive_tenants(self, session):
        """Test that payments are not generated for inactive tenants."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        tenant.is_active = False
        session.add(tenant)
        session.commit()

        PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        generated = generate_all_due_payments(session)

        assert len(generated) == 0

    def test_skips_inactive_schedules(self, session):
        """Test that payments are not generated for inactive schedules."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
            is_active=False,
        )

        generated = generate_all_due_payments(session)

        assert len(generated) == 0

    def test_returns_list_of_generated_payments(self, session):
        """Test that function returns list of generated payment objects."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        generated = generate_all_due_payments(session)

        assert isinstance(generated, list)
        assert len(generated) == 1
        assert isinstance(generated[0], Payment)

    def test_commits_generated_payments(self, session):
        """Test that generated payments are committed to database."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        generated = generate_all_due_payments(session)

        # Verify payments exist in database
        for payment in generated:
            db_payment = session.get(Payment, payment.id)
            assert db_payment is not None

    def test_handles_multiple_payments_per_schedule(self, session):
        """Test that only one payment is generated per schedule at a time."""
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]
        schedule = PaymentScheduleFactory.create(
            session=session,
            tenant_id=tenant.id,
            amount=100000,
            frequency=PaymentFrequency.MONTHLY,
            due_day=5,
            window_days=3,
            start_date=date(2024, 1, 1),
        )

        # Create first paid payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            schedule_id=schedule.id,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status=PaymentStatus.ON_TIME,
        )

        generated = generate_all_due_payments(session)

        # Should generate second payment
        assert len(generated) == 1
        assert generated[0].period_start == date(2024, 2, 1)


# =============================================================================
# Tests for update_payment_statuses
# =============================================================================


class TestUpdatePaymentStatuses:
    """Test status updates based on current date."""

    @patch("app.services.payment_service.date")
    def test_upcoming_to_pending_transition(self, mock_date, session):
        """Test UPCOMING changes to PENDING when due date is today."""
        setup_date_mock(mock_date, date(2024, 1, 10))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        payment = PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.UPCOMING,
        )

        updated_count = update_payment_statuses(session)

        assert updated_count == 1
        assert payment.status == PaymentStatus.PENDING

    @patch("app.services.payment_service.date")
    def test_pending_to_overdue_transition(self, mock_date, session):
        """Test PENDING changes to OVERDUE when window ends."""
        setup_date_mock(mock_date, date(2024, 1, 16))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        payment = PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.PENDING,
        )

        updated_count = update_payment_statuses(session)

        assert updated_count == 1
        assert payment.status == PaymentStatus.OVERDUE

    @patch("app.services.payment_service.date")
    def test_upcoming_to_overdue_direct_transition(self, mock_date, session):
        """Test UPCOMING changes directly to OVERDUE if past window."""
        setup_date_mock(mock_date, date(2024, 1, 20))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        payment = PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.UPCOMING,
        )

        updated_count = update_payment_statuses(session)

        assert updated_count == 1
        assert payment.status == PaymentStatus.OVERDUE

    @patch("app.services.payment_service.date")
    def test_does_not_change_on_time_payments(self, mock_date, session):
        """Test that ON_TIME payments are not updated."""
        setup_date_mock(mock_date, date(2024, 1, 20))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.ON_TIME,
        )

        updated_count = update_payment_statuses(session)

        assert updated_count == 0

    @patch("app.services.payment_service.date")
    def test_does_not_change_late_payments(self, mock_date, session):
        """Test that LATE payments are not updated."""
        setup_date_mock(mock_date, date(2024, 1, 20))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.LATE,
        )

        updated_count = update_payment_statuses(session)

        assert updated_count == 0

    @patch("app.services.payment_service.date")
    def test_does_not_change_waived_payments(self, mock_date, session):
        """Test that WAIVED payments are not updated."""
        setup_date_mock(mock_date, date(2024, 1, 20))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.WAIVED,
        )

        updated_count = update_payment_statuses(session)

        assert updated_count == 0

    @patch("app.services.payment_service.date")
    def test_does_not_change_verifying_payments(self, mock_date, session):
        """Test that VERIFYING payments are not updated."""
        setup_date_mock(mock_date, date(2024, 1, 20))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.VERIFYING,
        )

        updated_count = update_payment_statuses(session)

        assert updated_count == 0

    @patch("app.services.payment_service.date")
    def test_returns_count_of_updated_payments(self, mock_date, session):
        """Test that function returns correct count of updated payments."""
        setup_date_mock(mock_date, date(2024, 1, 20))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        # Create multiple updatable payments
        for _ in range(3):
            PaymentFactory.create(
                session=session,
                tenant_id=tenant.id,
                due_date=date(2024, 1, 10),
                window_end_date=date(2024, 1, 15),
                status=PaymentStatus.UPCOMING,
            )

        updated_count = update_payment_statuses(session)

        assert updated_count == 3

    @patch("app.services.payment_service.date")
    def test_updates_timestamp(self, mock_date, session):
        """Test that updated_at is set when status changes."""
        setup_date_mock(mock_date, date(2024, 1, 20))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        payment = PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.UPCOMING,
        )

        update_payment_statuses(session)

        assert payment.updated_at is not None

    @patch("app.services.payment_service.date")
    def test_commits_changes(self, mock_date, session):
        """Test that changes are committed to database."""
        setup_date_mock(mock_date, date(2024, 1, 20))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        payment = PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.UPCOMING,
        )

        update_payment_statuses(session)

        # Verify in database
        db_payment = session.get(Payment, payment.id)
        assert db_payment.status == PaymentStatus.OVERDUE


# =============================================================================
# Tests for get_payments_entering_window
# =============================================================================


class TestGetPaymentsEnteringWindow:
    """Test retrieval of payments entering payment window today."""

    @patch("app.services.payment_service.date")
    def test_returns_payments_with_due_date_today(self, mock_date, session):
        """Test returns payments where due_date equals today."""
        setup_date_mock(mock_date, date(2024, 1, 10))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        payment = PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.UPCOMING,
        )

        entering = get_payments_entering_window(session)

        assert len(entering) == 1
        assert entering[0].id == payment.id

    @patch("app.services.payment_service.date")
    def test_only_returns_upcoming_payments(self, mock_date, session):
        """Test only returns payments with UPCOMING status."""
        setup_date_mock(mock_date, date(2024, 1, 10))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        # Create upcoming payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.UPCOMING,
        )

        # Create pending payment (should not be returned)
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.PENDING,
        )

        entering = get_payments_entering_window(session)

        assert len(entering) == 1
        assert entering[0].status == PaymentStatus.UPCOMING

    @patch("app.services.payment_service.date")
    def test_does_not_return_payments_with_different_due_date(self, mock_date, session):
        """Test does not return payments with due_date != today."""
        setup_date_mock(mock_date, date(2024, 1, 10))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 15),  # Different date
            window_end_date=date(2024, 1, 20),
            status=PaymentStatus.UPCOMING,
        )

        entering = get_payments_entering_window(session)

        assert len(entering) == 0

    @patch("app.services.payment_service.date")
    def test_returns_multiple_payments(self, mock_date, session):
        """Test returns multiple payments entering window today."""
        setup_date_mock(mock_date, date(2024, 1, 10))

        # Create multiple payments with unique landlords
        for i in range(3):
            landlord = LandlordFactory.create(
                session=session, email=f"landlord{i}@test.com"
            )
            property_obj = PropertyFactory.create(
                session=session, landlord_id=landlord.id
            )
            room = RoomFactory.create(session=session, property_id=property_obj.id)
            tenant = TenantFactory.create(session=session, room_id=room.id)
            PaymentFactory.create(
                session=session,
                tenant_id=tenant.id,
                due_date=date(2024, 1, 10),
                window_end_date=date(2024, 1, 15),
                status=PaymentStatus.UPCOMING,
            )

        entering = get_payments_entering_window(session)

        assert len(entering) == 3


# =============================================================================
# Tests for get_payments_becoming_overdue
# =============================================================================


class TestGetPaymentsBecomingOverdue:
    """Test retrieval of payments becoming overdue today."""

    @patch("app.services.payment_service.date")
    def test_returns_payments_with_window_end_yesterday(self, mock_date, session):
        """Test returns payments where window ended yesterday."""
        setup_date_mock(mock_date, date(2024, 1, 16))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        payment = PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),  # Yesterday
            status=PaymentStatus.PENDING,
        )

        overdue = get_payments_becoming_overdue(session)

        assert len(overdue) == 1
        assert overdue[0].id == payment.id

    @patch("app.services.payment_service.date")
    def test_returns_upcoming_and_pending_payments(self, mock_date, session):
        """Test returns both UPCOMING and PENDING payments."""
        setup_date_mock(mock_date, date(2024, 1, 16))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        # Create upcoming payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.UPCOMING,
        )

        # Create pending payment
        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 11),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.PENDING,
        )

        overdue = get_payments_becoming_overdue(session)

        assert len(overdue) == 2

    @patch("app.services.payment_service.date")
    def test_does_not_return_paid_payments(self, mock_date, session):
        """Test does not return already paid payments."""
        setup_date_mock(mock_date, date(2024, 1, 16))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 15),
            status=PaymentStatus.ON_TIME,
        )

        overdue = get_payments_becoming_overdue(session)

        assert len(overdue) == 0

    @patch("app.services.payment_service.date")
    def test_does_not_return_payments_with_different_window_end(
        self, mock_date, session
    ):
        """Test does not return payments with different window_end_date."""
        setup_date_mock(mock_date, date(2024, 1, 16))
        scenario = create_full_test_scenario(session)
        tenant = scenario["tenant"]

        PaymentFactory.create(
            session=session,
            tenant_id=tenant.id,
            due_date=date(2024, 1, 10),
            window_end_date=date(2024, 1, 20),  # Not yesterday
            status=PaymentStatus.PENDING,
        )

        overdue = get_payments_becoming_overdue(session)

        assert len(overdue) == 0

    @patch("app.services.payment_service.date")
    def test_returns_multiple_payments(self, mock_date, session):
        """Test returns multiple payments becoming overdue."""
        setup_date_mock(mock_date, date(2024, 1, 16))

        # Create multiple payments with unique landlords
        for i in range(3):
            landlord = LandlordFactory.create(
                session=session, email=f"landlord{i}@test.com"
            )
            property_obj = PropertyFactory.create(
                session=session, landlord_id=landlord.id
            )
            room = RoomFactory.create(session=session, property_id=property_obj.id)
            tenant = TenantFactory.create(session=session, room_id=room.id)
            PaymentFactory.create(
                session=session,
                tenant_id=tenant.id,
                due_date=date(2024, 1, 10),
                window_end_date=date(2024, 1, 15),
                status=PaymentStatus.PENDING,
            )

        overdue = get_payments_becoming_overdue(session)

        assert len(overdue) == 3

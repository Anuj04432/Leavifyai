from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import pytest

from app.modules.payroll.service import get_month_working_days
from app.schemas.payroll import PayrollBatchCreate


def test_get_month_working_days_november_2026():
    # November 2026: 30 days
    working_days, start_d, end_d = get_month_working_days(2026, 11)
    assert start_d == date(2026, 11, 1)
    assert end_d == date(2026, 11, 30)
    # There are 21 weekdays (Mon-Fri) in November 2026
    assert working_days == 21


def test_unpaid_leave_deduction_calculation():
    monthly_base = Decimal("6300.00")
    total_working_days = 21
    unpaid_days = Decimal("2.0")

    per_day_rate = (monthly_base / Decimal(str(total_working_days))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    assert per_day_rate == Decimal("300.00")

    unpaid_deduction = (per_day_rate * unpaid_days).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    assert unpaid_deduction == Decimal("600.00")


def test_paid_leave_zero_deduction():
    monthly_base = Decimal("5000.00")
    total_working_days = 22
    unpaid_days = Decimal("0.0")

    per_day_rate = (monthly_base / Decimal(str(total_working_days))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    unpaid_deduction = (per_day_rate * unpaid_days).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    assert unpaid_deduction == Decimal("0.00")


def test_statutory_deductions_and_net_pay():
    gross = Decimal("6000.00")
    monthly_base = Decimal("5000.00")
    unpaid_deduction = Decimal("200.00")

    # 10% tax on gross
    tax = (gross * Decimal("0.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert tax == Decimal("600.00")

    # 5% PF on base
    pf = (monthly_base * Decimal("0.05")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert pf == Decimal("250.00")

    total_deductions = unpaid_deduction + tax + pf
    assert total_deductions == Decimal("1050.00")

    net_pay = gross - total_deductions
    assert net_pay == Decimal("4950.00")


def test_payroll_batch_create_schema_validation():
    payload = PayrollBatchCreate(period_year=2026, period_month=11, notes="November standard run")
    assert payload.period_year == 2026
    assert payload.period_month == 11
    assert payload.notes == "November standard run"

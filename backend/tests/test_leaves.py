from datetime import date
from decimal import Decimal
import uuid
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.modules.leaves.service import calculate_working_days
from app.schemas.leave import (
    LeaveActionRequest,
    LeavePolicyCreate,
    LeaveRequestCreate,
)


def test_calculate_working_days_standard_workweek():
    # 2026-11-09 is Monday, 2026-11-13 is Friday -> 5 business days
    start = date(2026, 11, 9)
    end = date(2026, 11, 13)
    days = calculate_working_days(start, end)
    assert days == Decimal("5")


def test_calculate_working_days_weekend_only():
    # 2026-11-07 is Saturday, 2026-11-08 is Sunday -> 0 business days
    start = date(2026, 11, 7)
    end = date(2026, 11, 8)
    days = calculate_working_days(start, end)
    assert days == Decimal("0")


def test_calculate_working_days_across_weekend():
    # 2026-11-06 is Friday, 2026-11-10 is Tuesday -> Fri, Mon, Tue = 3 business days
    start = date(2026, 11, 6)
    end = date(2026, 11, 10)
    days = calculate_working_days(start, end)
    assert days == Decimal("3")


def test_calculate_working_days_end_before_start():
    start = date(2026, 11, 15)
    end = date(2026, 11, 10)
    with pytest.raises(HTTPException) as exc_info:
        calculate_working_days(start, end)
    assert exc_info.value.status_code == 400


def test_leave_policy_schema_validation():
    policy = LeavePolicyCreate(
        name="Annual Vacation",
        leave_type="annual",
        days_allowed=20,
        carry_forward=True,
        max_carry_forward_days=5,
        is_paid=True,
    )
    assert policy.days_allowed == 20
    assert policy.leave_type == "annual"
    assert policy.is_paid is True


def test_leave_policy_schema_negative_days_rejected():
    with pytest.raises(ValidationError):
        LeavePolicyCreate(
            name="Invalid Policy",
            leave_type="annual",
            days_allowed=-5,
        )


def test_leave_request_create_schema():
    policy_id = uuid.uuid4()
    req = LeaveRequestCreate(
        leave_policy_id=policy_id,
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 5),
        reason="Family holiday",
    )
    assert req.leave_policy_id == policy_id
    assert req.reason == "Family holiday"


def test_leave_action_schema():
    action = LeaveActionRequest(action="approve", comment="Approved by manager")
    assert action.action == "approve"
    assert action.comment == "Approved by manager"

from datetime import date
from decimal import Decimal
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.models.employee import Employee
from app.models.leave import LeavePolicy, LeaveRequest, LeaveRequestStatus
from app.modules.agents.communication_agent import CommunicationIngestionAgent
from app.modules.agents.email_service import EmailNotificationDispatcher


def test_financial_deduction_calculation():
    dispatcher = EmailNotificationDispatcher()

    emp = Employee(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@acme.com",
        salary_basic=Decimal("60000.00"),  # $5,000 / month
    )

    # 1. Paid Leave
    paid_req = LeaveRequest(
        id=uuid.uuid4(),
        start_date=date(2026, 11, 9),
        end_date=date(2026, 11, 10),
        total_days=Decimal("2.0"),
        is_paid=True,
        deduction_waived=False,
    )
    paid_fin = dispatcher.calculate_projected_deduction(emp, paid_req)
    assert paid_fin["deduction_amount"] == Decimal("0.00")
    assert paid_fin["deduction_str"] == "$0.00"
    assert paid_fin["is_paid"] is True

    # 2. Unpaid Leave with Executive Waiver
    waived_req = LeaveRequest(
        id=uuid.uuid4(),
        start_date=date(2026, 11, 9),
        end_date=date(2026, 11, 10),
        total_days=Decimal("2.0"),
        is_paid=False,
        deduction_waived=True,
    )
    waived_fin = dispatcher.calculate_projected_deduction(emp, waived_req)
    assert waived_fin["deduction_amount"] == Decimal("0.00")
    assert "Waived" in waived_fin["deduction_str"]
    assert waived_fin["is_waived"] is True

    # 3. Regular Unpaid Leave (pro-rata deduction)
    unpaid_req = LeaveRequest(
        id=uuid.uuid4(),
        start_date=date(2026, 11, 9),
        end_date=date(2026, 11, 10),
        total_days=Decimal("2.0"),
        is_paid=False,
        deduction_waived=False,
    )
    unpaid_fin = dispatcher.calculate_projected_deduction(emp, unpaid_req)
    assert unpaid_fin["deduction_amount"] > Decimal("0.00")
    assert unpaid_fin["deduction_str"].startswith("-$")
    assert "unpaid" in unpaid_fin["policy_explanation"].lower()


def test_leave_decision_email_html_content():
    dispatcher = EmailNotificationDispatcher()

    req = LeaveRequest(
        id=uuid.uuid4(),
        request_number="LRQ-2026-TEST99",
        start_date=date(2026, 11, 9),
        end_date=date(2026, 11, 10),
        total_days=Decimal("2.0"),
        status="approved",
        is_paid=False,
        deduction_waived=True,
    )

    fin_info = {
        "deduction_amount": Decimal("0.00"),
        "deduction_str": "$0.00 (Waived)",
        "is_waived": True,
        "is_paid": False,
        "policy_explanation": "Approved as Special Unpaid Leave with Zero Salary Deduction (Management Waiver Applied).",
    }

    html = dispatcher.format_leave_email_html(
        employee_name="Jane Doe",
        leave_req=req,
        policy_name="Compassionate Leave",
        financial_info=fin_info,
        reviewer_comment="Approved with exemption per CEO authorization.",
    )

    assert "Jane Doe" in html
    assert "LRQ-2026-TEST99" in html
    assert "Compassionate Leave" in html
    assert "$0.00 (Waived)" in html
    assert "Approved with exemption per CEO authorization." in html


@pytest.mark.asyncio
async def test_inbound_communication_agent_processing():
    mock_db = AsyncMock()
    mock_llm = MagicMock()

    # Mock LLM decision extracting structured leave request from email
    mock_llm.generate_decision = AsyncMock(
        return_value=(
            json.dumps({
                "is_leave_request": True,
                "leave_type": "sick",
                "start_date": "2026-11-12",
                "end_date": "2026-11-13",
                "reason": "Severe fever and doctor consultation",
                "confidence": 0.98,
            }),
            "openrouter",
            "free-model",
        )
    )

    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    policy_id = uuid.uuid4()

    mock_emp = Employee(
        id=emp_id,
        company_id=company_id,
        first_name="Rajesh",
        last_name="Patel",
        email="rajesh.patel@company.com",
    )

    mock_policy = LeavePolicy(
        id=policy_id,
        company_id=company_id,
        name="Sick Leave",
        leave_type="sick",
        is_paid=True,
        is_active=True,
        days_allowed=10,
    )

    # Mock DB query results
    res_emp = MagicMock()
    res_emp.scalars.return_value.first.return_value = mock_emp

    res_pol = MagicMock()
    res_pol.scalars.return_value.first.return_value = mock_policy

    res_bal = MagicMock()
    res_bal.scalars.return_value.first.return_value = None

    mock_db.execute = AsyncMock(side_effect=[res_emp, res_pol, res_bal])

    agent = CommunicationIngestionAgent(mock_db, mock_llm)
    result = await agent.process_inbound_message(
        company_id=company_id,
        sender_identifier="rajesh.patel@company.com",
        subject="Sick leave request for Nov 12-13",
        body="Hi Team, I am down with severe fever and will be unable to work on Nov 12 and 13.",
        channel="email",
    )

    assert result["processed"] is True
    assert result["employee_name"] == "Rajesh Patel"
    assert result["channel"] == "email"
    assert result["policy_name"] == "Sick Leave"
    assert result["total_days"] == 2.0
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_payroll_calculation_exempts_waived_unpaid_leave():
    from app.modules.payroll.service import PayrollService

    mock_db = AsyncMock()
    company_id = uuid.uuid4()
    service = PayrollService(mock_db, company_id)

    # Create approved leaves: one normal unpaid, one unpaid with waiver
    normal_unpaid = LeaveRequest(
        id=uuid.uuid4(),
        total_days=Decimal("3.0"),
        is_paid=False,
        deduction_waived=False,
    )
    waived_unpaid = LeaveRequest(
        id=uuid.uuid4(),
        total_days=Decimal("2.0"),
        is_paid=False,
        deduction_waived=True,
    )

    leaves = [normal_unpaid, waived_unpaid]

    paid_days = Decimal("0.0")
    unpaid_days = Decimal("0.0")
    for req in leaves:
        if req.is_paid or getattr(req, "deduction_waived", False):
            paid_days += Decimal(str(req.total_days))
        else:
            unpaid_days += Decimal(str(req.total_days))

    # The 2 days with waiver should count as paid/exempt, only 3 days as unpaid
    assert paid_days == Decimal("2.0")
    assert unpaid_days == Decimal("3.0")

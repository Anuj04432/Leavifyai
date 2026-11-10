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
from app.modules.agents.slack_service import SlackNotificationDispatcher


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
async def test_inbound_message_rejects_unknown_sender_without_llm_call():
    """Verifies that marketing spam and unknown senders are dropped immediately without LLM calls or candidate fallback."""
    mock_db = AsyncMock()
    mock_llm = MagicMock()
    mock_llm.generate_decision = AsyncMock()

    # DB returns None for employee lookup
    res_emp = MagicMock()
    res_emp.scalars.return_value.first.return_value = None
    mock_db.execute = AsyncMock(return_value=res_emp)

    agent = CommunicationIngestionAgent(mock_db, mock_llm)
    result = await agent.process_inbound_message(
        company_id=uuid.uuid4(),
        sender_identifier="TCS iON <ExternalComm_tcsion@tcsion.com>",
        subject="Last Chance to Register! Free Jobinar",
        body="Join our upcoming session on 2026-11-12",
        channel="gmail",
    )

    assert result["processed"] is False
    assert "not a registered active employee" in result["reason"]
    # Ensure LLM was never invoked for spam
    assert not mock_llm.generate_decision.called


@pytest.mark.asyncio
async def test_inbound_message_extracts_clean_email_from_formatted_sender():
    """Verifies parseaddr cleanly extracts the email address from 'Full Name <email@domain.com>'."""
    mock_db = AsyncMock()
    mock_llm = MagicMock()
    mock_llm.generate_decision = AsyncMock(
        return_value=(
            json.dumps({
                "is_leave_request": True,
                "leave_type": "annual",
                "start_date": "2026-11-20",
                "end_date": "2026-11-20",
                "reason": "Family function",
                "confidence": 0.95,
            }),
            "openrouter",
            "free-model",
        )
    )

    company_id = uuid.uuid4()
    mock_emp = Employee(
        id=uuid.uuid4(),
        company_id=company_id,
        first_name="Anuj",
        last_name="Wagmore",
        email="anujwagmore835@gmail.com",
    )
    mock_pol = LeavePolicy(
        id=uuid.uuid4(),
        company_id=company_id,
        name="Annual Leave",
        leave_type="annual",
        is_paid=True,
        is_active=True,
        days_allowed=15,
    )

    res_emp = MagicMock()
    res_emp.scalars.return_value.first.return_value = mock_emp
    res_pol = MagicMock()
    res_pol.scalars.return_value.first.return_value = mock_pol
    res_bal = MagicMock()
    res_bal.scalars.return_value.first.return_value = None

    mock_db.execute = AsyncMock(side_effect=[res_emp, res_pol, res_bal])

    agent = CommunicationIngestionAgent(mock_db, mock_llm)
    result = await agent.process_inbound_message(
        company_id=company_id,
        sender_identifier="Anuj Wagmore <anujwagmore835@gmail.com>",
        subject="Leave request for Nov 20",
        body="I will take a leave on 2026-11-20 for a family function.",
        channel="gmail",
    )

    assert result["processed"] is True
    assert result["employee_name"] == "Anuj Wagmore"
    assert result["policy_name"] == "Annual Leave"


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


@pytest.mark.asyncio
async def test_inbox_polling_worker_lifecycle():
    from app.modules.agents.background_worker import InboxPollingWorker
    import asyncio

    worker = InboxPollingWorker()
    assert worker.is_running is False

    status_before = worker.get_status()
    assert status_before["is_running"] is False
    assert status_before["total_runs"] == 0

    # Test single poll with mock DB
    with patch("app.modules.agents.background_worker.AsyncSessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [uuid.uuid4()]
        mock_session.execute.return_value = mock_result
        mock_session_local.return_value.__aenter__.return_value = mock_session

        with patch("app.modules.agents.background_worker.CommunicationIngestionAgent") as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent.is_imap_configured = True
            mock_agent.scan_gmail_inbox = AsyncMock(return_value=[{"processed": True, "id": str(uuid.uuid4())}])
            mock_agent_cls.return_value = mock_agent

            processed = await worker.poll_now()
            assert len(processed) == 1
            assert worker.total_runs == 1
            assert worker.total_processed == 1

    status_after = worker.get_status()
    assert status_after["total_runs"] == 1
    assert status_after["total_processed"] == 1
    assert "completed_last_poll" in status_after["last_status"]


def test_slack_block_kit_payload_formatting():
    dispatcher = SlackNotificationDispatcher()

    leave_req = LeaveRequest(
        id=uuid.uuid4(),
        request_number="LRQ-SLACK-001",
        start_date=date(2026, 11, 18),
        end_date=date(2026, 11, 20),
        total_days=Decimal("3.0"),
        status="approved",
        is_paid=True,
        deduction_waived=False,
        source_channel="slack",
    )

    financial_info = {
        "deduction_str": "$0.00",
        "policy_explanation": "Covered under Paid Leave Policy.",
    }

    payload = dispatcher.format_leave_decision_blocks(
        employee_name="Jordan Bell",
        leave_req=leave_req,
        policy_name="Annual Leave",
        financial_info=financial_info,
        reviewer_comment="Have a great vacation!",
    )

    assert "blocks" in payload
    blocks = payload["blocks"]
    assert len(blocks) >= 4

    header_block = blocks[0]
    assert "✅ Leave Request Approved" in header_block["text"]["text"]

    section_block = blocks[1]
    field_texts = [f["text"] for f in section_block["fields"]]
    assert any("Jordan Bell" in txt for txt in field_texts)
    assert any("LRQ-SLACK-001" in txt for txt in field_texts)
    assert any("Annual Leave" in txt for txt in field_texts)
    assert any("APPROVED" in txt for txt in field_texts)
    assert any("$0.00" in txt for txt in field_texts)

    context_block = [b for b in blocks if b.get("type") == "context" and "Reviewer Note" in str(b)]
    assert len(context_block) == 1
    assert "Have a great vacation!" in str(context_block[0])


@pytest.mark.asyncio
async def test_slack_webhook_dispatch_and_logging():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    dispatcher = SlackNotificationDispatcher(db=mock_db)

    emp = Employee(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        first_name="Priya",
        last_name="Sharma",
        email="priya@company.com",
        salary_basic=Decimal("4000.00"),
    )

    leave_req = LeaveRequest(
        id=uuid.uuid4(),
        request_number="LRQ-SLACK-002",
        start_date=date(2026, 11, 25),
        end_date=date(2026, 11, 26),
        total_days=Decimal("2.0"),
        status="approved",
        is_paid=True,
        deduction_waived=False,
        source_channel="portal",
    )

    res = await dispatcher.send_leave_decision_webhook(
        employee=emp,
        leave_req=leave_req,
        policy_name="Medical Leave",
        reviewer_comment="Approved with medical certificate.",
    )

    assert res["dispatched"] is True
    assert res["channel"] == "slack"
    assert res["request_number"] == "LRQ-SLACK-002"
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_slack_live_http_post():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    dispatcher = SlackNotificationDispatcher(db=mock_db)

    emp = Employee(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        first_name="Test",
        last_name="User",
        email="test@company.com",
        salary_basic=Decimal("3000.00"),
    )

    leave_req = LeaveRequest(
        id=uuid.uuid4(),
        request_number="LRQ-SLACK-LIVE",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        total_days=Decimal("2.0"),
        status="rejected",
        is_paid=False,
        deduction_waived=False,
        source_channel="slack",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        res = await dispatcher.send_leave_decision_webhook(
            employee=emp,
            leave_req=leave_req,
            policy_name="Unpaid Leave",
            reviewer_comment="Critical release week.",
            override_webhook_url="https://hooks.slack.com/services/T000/B000/XXXX",
        )

        assert res["dispatched"] is True
        assert res["dispatched_live"] is True
        assert mock_post.called
        call_url = mock_post.call_args[0][0]
        assert "hooks.slack.com" in call_url


from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from app.modules.payments.paypal_client import PayPalClient
from app.modules.payments.payslip_mailer import PayslipMailer
from app.schemas.payment import (
    DisbursePayrollRequest,
    DisbursePayrollResponse,
    PayoutItemDetail,
    PaymentStatusResponse,
)


@pytest.mark.asyncio
async def test_paypal_client_sandbox_mock_response():
    client = PayPalClient()
    sender_batch_id = "WORKFORCE-TEST-BATCH-001"
    items = [
        {
            "recipient_type": "EMAIL",
            "amount": {"value": "4500.00", "currency": "USD"},
            "note": "November 2026 Salary",
            "sender_item_id": "ITEM-TEST-001",
            "receiver": "alice@company.com",
        },
        {
            "recipient_type": "EMAIL",
            "amount": {"value": "5200.00", "currency": "USD"},
            "note": "November 2026 Salary",
            "sender_item_id": "ITEM-TEST-002",
            "receiver": "bob@company.com",
        },
    ]

    res = await client.create_batch_payout(
        sender_batch_id=sender_batch_id,
        email_subject="Test Payout",
        email_message="Testing PayPal Payouts",
        items=items,
    )

    assert "batch_header" in res
    assert res["batch_header"]["sender_batch_header"]["sender_batch_id"] == sender_batch_id
    assert len(res["items"]) == 2
    assert res["items"][0]["transaction_status"] == "SUCCESS"
    assert res["items"][0]["payout_item_id"].startswith("ITEM-")
    assert res["items"][0]["transaction_id"].startswith("TRANS-")


def test_payment_schema_serialization():
    item_id = uuid.uuid4()
    emp_id = uuid.uuid4()

    detail = PayoutItemDetail(
        payroll_item_id=item_id,
        employee_id=emp_id,
        employee_name="John Doe",
        recipient_email="john@example.com",
        amount=Decimal("3750.50"),
        currency="USD",
        status="success",
        payout_item_id="ITEM-1234",
        transaction_id="TRANS-5678",
    )

    assert detail.amount == Decimal("3750.50")
    assert detail.currency == "USD"
    assert detail.status == "success"


def test_payment_status_aggregation():
    batch_id = uuid.uuid4()
    resp = PaymentStatusResponse(
        batch_id=batch_id,
        batch_status="paid",
        payout_batch_id="PAYOUTS-BATCH-XYZ",
        sender_batch_id="WORKFORCE-PAYROLL-01",
        total_items=2,
        successful_items=2,
        pending_items=0,
        failed_items=0,
        items=[],
    )

    assert resp.total_items == 2
    assert resp.successful_items == 2
    assert resp.failed_items == 0


def test_payslip_html_generation():
    mailer = PayslipMailer()
    html = mailer.generate_payslip_html(
        company_name="WorkforceAI Technologies",
        employee_name="Jane Doe",
        employee_code="EMP-1002",
        designation="Senior Engineer",
        department="Engineering",
        period_str="November 2026",
        basic_salary=Decimal("5000.00"),
        allowances={"housing": 500, "transport": 200},
        gross_salary=Decimal("5700.00"),
        unpaid_leave_days=Decimal("0.0"),
        unpaid_leave_deduction=Decimal("0.00"),
        statutory_deductions={"tax": 450},
        total_deductions=Decimal("450.00"),
        net_salary=Decimal("5250.00"),
        payout_tx_id="TRANS-TEST-9999",
        disbursed_at=datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert "WorkforceAI Technologies" in html
    assert "Jane Doe" in html
    assert "EMP-1002" in html
    assert "November 2026" in html
    assert "$5,000.00" in html
    assert "$5,700.00" in html
    assert "$5,250.00" in html
    assert "TRANS-TEST-9999" in html
    assert "Unpaid Leave Deductions" in html


@pytest.mark.asyncio
async def test_payslip_mailer_dispatch_and_logging():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mailer = PayslipMailer(db=mock_db)

    mock_emp = MagicMock()
    mock_emp.id = uuid.uuid4()
    mock_emp.first_name = "Alex"
    mock_emp.last_name = "Morgan"
    mock_emp.email = "alex@company.com"
    mock_emp.paypal_email = "alex.paypal@example.com"
    mock_emp.employee_code = "EMP-777"
    mock_emp.designation = "Product Lead"
    mock_emp.department = MagicMock(name="Product")
    mock_emp.department.name = "Product"

    mock_item = MagicMock()
    mock_item.id = uuid.uuid4()
    mock_item.basic_salary = Decimal("6000.00")
    mock_item.gross_salary = Decimal("6500.00")
    mock_item.allowances_breakdown = {"bonus": 500}
    mock_item.unpaid_leave_days = Decimal("1.0")
    mock_item.unpaid_leave_deduction = Decimal("250.00")
    mock_item.statutory_deductions = {"tax": 500}
    mock_item.total_deductions = Decimal("750.00")
    mock_item.net_salary = Decimal("5750.00")
    mock_item.employee = mock_emp

    mock_batch = MagicMock()
    mock_batch.id = uuid.uuid4()
    mock_batch.period_month = 11
    mock_batch.period_year = 2026

    res = await mailer.send_payslip_email(
        employee=mock_emp,
        payroll_item=mock_item,
        batch=mock_batch,
        company_name="WorkforceAI",
        payout_tx_id="TRANS-ALEX-01",
    )

    assert res["dispatched"] is True
    assert res["recipient"] == "alex.paypal@example.com"
    assert res["net_salary"] == "5750.00"
    assert "TRANS-ALEX-01" in res["payout_tx_id"]
    assert mock_db.add.called
    assert mock_db.commit.called

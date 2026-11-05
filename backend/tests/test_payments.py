import uuid
from decimal import Decimal
import pytest
from app.modules.payments.paypal_client import PayPalClient
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

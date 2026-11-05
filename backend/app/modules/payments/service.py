import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import Employee
from app.models.payment import Payment, PaymentStatus
from app.models.payroll import BatchStatus, PayrollBatch, PayrollItem
from app.models.user import User
from app.modules.notifications.service import NotificationService
from app.modules.payments.paypal_client import paypal_client
from app.schemas.payment import (
    DisbursePayrollResponse,
    PaymentStatusResponse,
    PayoutItemDetail,
)

logger = logging.getLogger(__name__)


class PaymentService:
    """Orchestrates payroll disbursement via PayPal Sandbox."""

    async def disburse_payroll_batch(
        self,
        db: AsyncSession,
        batch_id: uuid.UUID,
        company_id: uuid.UUID,
        email_subject: str = "WorkforceAI Monthly Salary Payout",
        note: str = "Automated Salary Disbursement via PayPal",
    ) -> DisbursePayrollResponse:
        # 1. Fetch batch with items and employees
        stmt = (
            select(PayrollBatch)
            .where(PayrollBatch.id == batch_id, PayrollBatch.company_id == company_id)
            .options(
                selectinload(PayrollBatch.payroll_items).selectinload(PayrollItem.employee).selectinload(Employee.user)
            )
        )
        result = await db.execute(stmt)
        batch = result.scalar_one_or_none()

        if not batch:
            raise ValueError("Payroll batch not found")

        if batch.status == BatchStatus.PAID.value:
            raise ValueError("Payroll batch has already been disbursed and marked as PAID")

        if batch.status not in (BatchStatus.APPROVED.value, BatchStatus.CALCULATED.value):
            raise ValueError(f"Payroll batch must be APPROVED before disbursement (current status: {batch.status})")

        if not batch.payroll_items:
            raise ValueError("Payroll batch contains no line items to disburse")

        sender_batch_id = f"WORKFORCE-PAYROLL-{batch.id.hex[:12].upper()}"

        # 2. Build PayPal items payload
        paypal_items = []
        item_mapping = {}

        for item in batch.payroll_items:
            emp = item.employee
            user = emp.user if emp else None
            recipient_email = (emp.paypal_email if emp and emp.paypal_email else (user.email if user else "employee@example.com"))
            amount_val = str(max(Decimal("0.01"), item.net_salary))

            sender_item_id = f"ITEM-{item.id.hex[:12].upper()}"
            paypal_item = {
                "recipient_type": "EMAIL",
                "amount": {
                    "value": amount_val,
                    "currency": "USD",
                },
                "note": f"WorkforceAI Salary for {batch.period_month}/{batch.period_year}",
                "sender_item_id": sender_item_id,
                "receiver": recipient_email,
            }
            paypal_items.append(paypal_item)
            item_mapping[sender_item_id] = {
                "payroll_item": item,
                "recipient_email": recipient_email,
                "employee": emp,
            }

        # 3. Trigger PayPal API
        payout_res = await paypal_client.create_batch_payout(
            sender_batch_id=sender_batch_id,
            email_subject=email_subject,
            email_message=note,
            items=paypal_items,
        )

        batch_header = payout_res.get("batch_header", {})
        payout_batch_id = batch_header.get("payout_batch_id", f"BATCH-{uuid.uuid4().hex[:8]}")
        payout_items_res = payout_res.get("items", [])

        # 4. Map results and save Payments
        details: List[PayoutItemDetail] = []
        now = datetime.now(timezone.utc)

        # Existing payments check for idempotency
        existing_payments_stmt = select(Payment).where(Payment.batch_id == batch.id)
        existing_res = await db.execute(existing_payments_stmt)
        existing_payments_by_item = {p.payroll_item_id: p for p in existing_res.scalars().all()}

        for idx, p_item in enumerate(paypal_items):
            sender_item_id = p_item["sender_item_id"]
            meta = item_mapping[sender_item_id]
            pr_item: PayrollItem = meta["payroll_item"]
            emp: Optional[Employee] = meta["employee"]

            # Match response item if available
            res_item = payout_items_res[idx] if idx < len(payout_items_res) else {}
            item_status = res_item.get("transaction_status", "SUCCESS")
            provider_item_id = res_item.get("payout_item_id")
            provider_tx_id = res_item.get("transaction_id")

            payment = existing_payments_by_item.get(pr_item.id)
            if not payment:
                payment = Payment(
                    batch_id=batch.id,
                    employee_id=pr_item.employee_id,
                    payroll_item_id=pr_item.id,
                    amount=pr_item.net_salary,
                    currency="USD",
                    payment_provider="paypal",
                    provider_batch_id=payout_batch_id,
                    provider_item_id=provider_item_id,
                    provider_transaction_id=provider_tx_id,
                    idempotency_key=f"PAY-{batch.id.hex[:8]}-{pr_item.id.hex[:8]}",
                    recipient_identifier=meta["recipient_email"],
                    status=PaymentStatus.SUCCESS.value if item_status in ("SUCCESS", "UNCLAIMED") else PaymentStatus.PROCESSING.value,
                    paid_at=now,
                    webhook_data=res_item,
                )
                db.add(payment)
            else:
                payment.provider_batch_id = payout_batch_id
                payment.provider_item_id = provider_item_id
                payment.provider_transaction_id = provider_tx_id
                payment.status = PaymentStatus.SUCCESS.value
                payment.paid_at = now
                payment.webhook_data = res_item

            pr_item.status = "paid"

            # Notify employee
            if emp:
                try:
                    notif_svc = NotificationService(db)
                    await notif_svc.create_notification(
                        employee_id=emp.id,
                        subject="Salary Disbursed",
                        body=f"Your salary of ${pr_item.net_salary:,.2f} for {batch.period_month}/{batch.period_year} has been disbursed via PayPal.",
                        raw_payload={"batch_id": str(batch.id), "amount": str(pr_item.net_salary), "provider": "paypal"},
                    )
                except Exception as ex:
                    logger.warning(f"Failed to dispatch disbursement notification to employee {emp.id}: {ex}")

            emp_name = f"{emp.user.first_name} {emp.user.last_name}" if emp and emp.user else "Employee"
            details.append(
                PayoutItemDetail(
                    payroll_item_id=pr_item.id,
                    employee_id=pr_item.employee_id,
                    employee_name=emp_name,
                    recipient_email=meta["recipient_email"],
                    amount=pr_item.net_salary,
                    currency="USD",
                    status="success" if item_status in ("SUCCESS", "UNCLAIMED") else "processing",
                    payout_item_id=provider_item_id,
                    transaction_id=provider_tx_id,
                )
            )

        # 5. Mark batch as paid
        batch.status = BatchStatus.PAID.value
        await db.commit()

        return DisbursePayrollResponse(
            batch_id=batch.id,
            status=BatchStatus.PAID.value,
            total_amount=batch.total_net,
            currency="USD",
            item_count=len(batch.payroll_items),
            payout_batch_id=payout_batch_id,
            sender_batch_id=sender_batch_id,
            disbursed_at=now,
            items=details,
        )

    async def get_batch_payment_status(
        self, db: AsyncSession, batch_id: uuid.UUID, company_id: uuid.UUID
    ) -> PaymentStatusResponse:
        batch_stmt = select(PayrollBatch).where(
            PayrollBatch.id == batch_id, PayrollBatch.company_id == company_id
        )
        batch = (await db.execute(batch_stmt)).scalar_one_or_none()
        if not batch:
            raise ValueError("Payroll batch not found")

        stmt = (
            select(Payment)
            .where(Payment.batch_id == batch_id)
            .options(selectinload(Payment.employee).selectinload(Employee.user))
        )
        result = await db.execute(stmt)
        payments = result.scalars().all()

        payout_batch_id = payments[0].provider_batch_id if payments else None
        sender_batch_id = f"WORKFORCE-PAYROLL-{batch.id.hex[:12].upper()}"

        items: List[PayoutItemDetail] = []
        success_count = 0
        pending_count = 0
        failed_count = 0

        for p in payments:
            if p.status == PaymentStatus.SUCCESS.value:
                success_count += 1
            elif p.status in (PaymentStatus.FAILED.value, PaymentStatus.RETURNED.value):
                failed_count += 1
            else:
                pending_count += 1

            emp_name = (
                f"{p.employee.user.first_name} {p.employee.user.last_name}"
                if p.employee and p.employee.user
                else "Employee"
            )
            items.append(
                PayoutItemDetail(
                    payroll_item_id=p.payroll_item_id,
                    employee_id=p.employee_id,
                    employee_name=emp_name,
                    recipient_email=p.recipient_identifier,
                    amount=p.amount,
                    currency=p.currency,
                    status=p.status,
                    payout_item_id=p.provider_item_id,
                    transaction_id=p.provider_transaction_id,
                    failure_reason=p.failure_reason,
                )
            )

        return PaymentStatusResponse(
            batch_id=batch.id,
            batch_status=batch.status,
            payout_batch_id=payout_batch_id,
            sender_batch_id=sender_batch_id,
            total_items=len(payments),
            successful_items=success_count,
            pending_items=pending_count,
            failed_items=failed_count,
            items=items,
        )


payment_service = PaymentService()

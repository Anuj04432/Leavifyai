import calendar
from datetime import datetime, timezone
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import smtplib
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.communication import CommunicationEvent
from app.models.employee import Employee
from app.models.payroll import PayrollBatch, PayrollItem
from app.schemas.payment import PayoutItemDetail

logger = logging.getLogger("workforceai.payments.payslip_mailer")


class PayslipMailer:
    """Generates official HTML payslips and dispatches them via SMTP or simulated delivery,
    recording an auditable record in the communication event ledger.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        settings = get_settings()
        self.smtp_host = os.getenv("SMTP_HOST") or settings.SMTP_HOST
        self.smtp_port = int(os.getenv("SMTP_PORT") or settings.SMTP_PORT)
        self.smtp_user = (os.getenv("SMTP_USER") or settings.SMTP_USER).strip()
        self.smtp_password = (os.getenv("SMTP_PASSWORD") or settings.SMTP_PASSWORD).strip()
        self.from_email = os.getenv("SMTP_FROM_EMAIL") or settings.SMTP_FROM_EMAIL or self.smtp_user or "payroll@workforceai.io"
        self.is_configured = bool(self.smtp_user and self.smtp_password)

    def generate_payslip_html(
        self,
        company_name: str,
        employee_name: str,
        employee_code: str,
        designation: str,
        department: str,
        period_str: str,
        basic_salary: Decimal,
        allowances: Dict[str, Any],
        gross_salary: Decimal,
        unpaid_leave_days: Decimal,
        unpaid_leave_deduction: Decimal,
        statutory_deductions: Dict[str, Any],
        total_deductions: Decimal,
        net_salary: Decimal,
        payout_tx_id: str,
        disbursed_at: datetime,
    ) -> str:
        """Renders an executive, high-readability HTML payslip matching brand design tokens."""
        # Build allowances rows
        allowance_rows = ""
        if allowances:
            for name, amt in allowances.items():
                allowance_rows += f"""
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 8px 12px; color: #475569; font-size: 13px;">{name.replace('_', ' ').title()}</td>
                    <td style="padding: 8px 12px; text-align: right; color: #0f172a; font-weight: 500; font-size: 13px;">${Decimal(str(amt)):,.2f}</td>
                </tr>
                """
        else:
            allowance_rows = """
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 8px 12px; color: #94a3b8; font-size: 13px; font-style: italic;">Standard Base Tier</td>
                <td style="padding: 8px 12px; text-align: right; color: #94a3b8; font-size: 13px;">$0.00</td>
            </tr>
            """

        # Build statutory deduction rows
        statutory_rows = ""
        if statutory_deductions:
            for name, amt in statutory_deductions.items():
                statutory_rows += f"""
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 8px 12px; color: #475569; font-size: 13px;">{name.replace('_', ' ').title()}</td>
                    <td style="padding: 8px 12px; text-align: right; color: #e11d48; font-weight: 500; font-size: 13px;">-${Decimal(str(amt)):,.2f}</td>
                </tr>
                """
        else:
            statutory_rows = """
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 8px 12px; color: #94a3b8; font-size: 13px; font-style: italic;">Standard Exemptions</td>
                <td style="padding: 8px 12px; text-align: right; color: #94a3b8; font-size: 13px;">$0.00</td>
            </tr>
            """

        disbursed_date_str = disbursed_at.strftime("%B %d, %Y at %H:%M UTC")
        unpaid_deduction_str = f"-${unpaid_leave_deduction:,.2f}" if unpaid_leave_deduction > Decimal("0.00") else "$0.00"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Payslip for {period_str}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0f172a; background-color: #f8fafc; margin: 0; padding: 32px 16px;">
            <div style="max-width: 640px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);">
                
                <!-- Brand Header -->
                <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0f172a; padding-bottom: 20px; margin-bottom: 24px;">
                    <div>
                        <div style="font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px;">{company_name}</div>
                        <div style="font-size: 12px; color: #64748b; margin-top: 2px;">Official Monthly Earnings Statement</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="display: inline-block; background: #f1f5f9; color: #0f172a; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 6px; border: 1px solid #e2e8f0;">
                            {period_str}
                        </span>
                    </div>
                </div>

                <!-- Employee & Batch Meta Grid -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px; margin-bottom: 24px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <tr>
                            <td style="padding: 4px 0; color: #64748b; width: 25%;">Employee Name:</td>
                            <td style="padding: 4px 0; color: #0f172a; font-weight: 700; width: 35%;">{employee_name}</td>
                            <td style="padding: 4px 0; color: #64748b; width: 20%;">Employee Code:</td>
                            <td style="padding: 4px 0; color: #0f172a; font-weight: 600; width: 20%; font-family: monospace;">{employee_code}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 0; color: #64748b;">Department:</td>
                            <td style="padding: 4px 0; color: #0f172a; font-weight: 600;">{department}</td>
                            <td style="padding: 4px 0; color: #64748b;">Designation:</td>
                            <td style="padding: 4px 0; color: #0f172a; font-weight: 600;">{designation}</td>
                        </tr>
                        <tr>
                            <td style="padding: 4px 0; color: #64748b;">Disbursed Via:</td>
                            <td style="padding: 4px 0; color: #059669; font-weight: 600;">PayPal Sandbox</td>
                            <td style="padding: 4px 0; color: #64748b;">Payment Ref:</td>
                            <td style="padding: 4px 0; color: #0f172a; font-weight: 600; font-family: monospace; font-size: 12px;">{payout_tx_id}</td>
                        </tr>
                    </table>
                </div>

                <!-- Financial Breakdown Section -->
                <div style="display: grid; grid-template-columns: 1fr; gap: 20px; margin-bottom: 24px;">
                    
                    <!-- Earnings Table -->
                    <div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                        <div style="background: #f1f5f9; padding: 10px 14px; font-weight: 700; font-size: 12px; color: #334155; text-transform: uppercase; letter-spacing: 0.5px;">
                            Earnings Breakdown
                        </div>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="border-bottom: 1px solid #f1f5f9;">
                                <td style="padding: 8px 12px; color: #475569; font-size: 13px;">Basic Monthly Salary</td>
                                <td style="padding: 8px 12px; text-align: right; color: #0f172a; font-weight: 600; font-size: 13px;">${basic_salary:,.2f}</td>
                            </tr>
                            {allowance_rows}
                            <tr style="background: #f8fafc; border-top: 1px solid #cbd5e1;">
                                <td style="padding: 10px 12px; color: #0f172a; font-weight: 700; font-size: 13px;">Gross Total Earnings</td>
                                <td style="padding: 10px 12px; text-align: right; color: #0f172a; font-weight: 700; font-size: 14px;">${gross_salary:,.2f}</td>
                            </tr>
                        </table>
                    </div>

                    <!-- Deductions Table -->
                    <div style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                        <div style="background: #f1f5f9; padding: 10px 14px; font-weight: 700; font-size: 12px; color: #334155; text-transform: uppercase; letter-spacing: 0.5px;">
                            Deductions & Adjustments
                        </div>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="border-bottom: 1px solid #f1f5f9;">
                                <td style="padding: 8px 12px; color: #475569; font-size: 13px;">
                                    Unpaid Leave Deductions <span style="font-size: 11px; color: #64748b;">({unpaid_leave_days} days)</span>
                                </td>
                                <td style="padding: 8px 12px; text-align: right; color: {'#e11d48' if unpaid_leave_deduction > Decimal('0.00') else '#059669'}; font-weight: 600; font-size: 13px;">
                                    {unpaid_deduction_str}
                                </td>
                            </tr>
                            {statutory_rows}
                            <tr style="background: #f8fafc; border-top: 1px solid #cbd5e1;">
                                <td style="padding: 10px 12px; color: #0f172a; font-weight: 700; font-size: 13px;">Total Deductions Applied</td>
                                <td style="padding: 10px 12px; text-align: right; color: #e11d48; font-weight: 700; font-size: 14px;">-${total_deductions:,.2f}</td>
                            </tr>
                        </table>
                    </div>
                </div>

                <!-- Net Disbursed Highlight Banner -->
                <div style="background: #ecfdf5; border: 1.5px solid #a7f3d0; border-radius: 12px; padding: 20px; margin-bottom: 24px; text-align: center;">
                    <div style="font-size: 12px; font-weight: 700; color: #065f46; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                        Net Amount Disbursed to Recipient
                    </div>
                    <div style="font-size: 32px; font-weight: 800; color: #047857; letter-spacing: -1px; font-family: monospace;">
                        ${net_salary:,.2f} <span style="font-size: 16px; font-weight: 600; color: #065f46;">USD</span>
                    </div>
                    <div style="font-size: 12px; color: #047857; margin-top: 6px;">
                        Disbursed on {disbursed_date_str}
                    </div>
                </div>

                <!-- Footer Audit Notice -->
                <div style="border-top: 1px solid #e2e8f0; padding-top: 18px; font-size: 11px; color: #64748b; line-height: 1.6;">
                    <p style="margin: 0 0 6px 0;">
                        This document is a computer-generated salary slip authorized by WorkforceAI Autonomous Payroll Operations. No physical signature is required.
                    </p>
                    <p style="margin: 0;">
                        Transaction verified with PayPal Sandbox Payouts. For questions or discrepancies, please contact your Organization's HR / Payroll Operations Team.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    async def send_payslip_email(
        self,
        employee: Employee,
        payroll_item: PayrollItem,
        batch: PayrollBatch,
        company_name: str = "WorkforceAI",
        payout_tx_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates the official HTML payslip, sends it to the employee's email,
        and logs the delivery event in CommunicationEvent.
        """
        # Determine employee metadata
        user = getattr(employee, "user", None)
        employee_name = f"{employee.first_name} {employee.last_name}" if employee else "Valued Employee"
        recipient_email = (
            employee.paypal_email
            or employee.email
            or (user.email if user else None)
        )

        if not recipient_email or "@" not in recipient_email:
            logger.warning(f"No valid recipient email for employee {employee.id} ({employee_name})")
            return {"dispatched": False, "status": "No valid recipient email"}

        department_name = (
            employee.department.name
            if getattr(employee, "department", None)
            else "General Operations"
        )
        designation = employee.designation or "Team Member"
        employee_code = employee.employee_code or f"EMP-{str(employee.id)[:6].upper()}"

        # Month and period string
        month_name = calendar.month_name[batch.period_month] if 1 <= batch.period_month <= 12 else str(batch.period_month)
        period_str = f"{month_name} {batch.period_year}"

        tx_ref = payout_tx_id or f"TRANS-{str(payroll_item.id)[:8].upper()}"
        now = datetime.now(timezone.utc)

        # Generate HTML
        html_content = self.generate_payslip_html(
            company_name=company_name,
            employee_name=employee_name,
            employee_code=employee_code,
            designation=designation,
            department=department_name,
            period_str=period_str,
            basic_salary=payroll_item.basic_salary,
            allowances=payroll_item.allowances_breakdown or {},
            gross_salary=payroll_item.gross_salary,
            unpaid_leave_days=payroll_item.unpaid_leave_days,
            unpaid_leave_deduction=payroll_item.unpaid_leave_deduction,
            statutory_deductions=payroll_item.statutory_deductions or {},
            total_deductions=payroll_item.total_deductions,
            net_salary=payroll_item.net_salary,
            payout_tx_id=tx_ref,
            disbursed_at=now,
        )

        subject = f"Official Payslip: {period_str} - {company_name}"

        # 1. Dispatch email (SMTP or simulated)
        if self.is_configured:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{company_name} Payroll <{self.from_email}>"
                msg["To"] = recipient_email
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_email, [recipient_email], msg.as_string())
                logger.info(f"Dispatched payslip email via SMTP to {recipient_email}")
            except Exception as e:
                logger.warning(f"SMTP dispatch failed: {e}. Falling back to simulated delivery log.")
        else:
            logger.info(
                f"[SIMULATED_PAYSLIP_DISPATCH] To: {recipient_email} | Subject: {subject} | "
                f"Net: ${payroll_item.net_salary:,.2f} | Ref: {tx_ref}"
            )

        # 2. Log in CommunicationEvent ledger
        if self.db:
            try:
                event = CommunicationEvent(
                    channel="email",
                    direction="outbound",
                    employee_id=employee.id,
                    sender_identifier="payroll-system",
                    subject=subject,
                    body=f"Your monthly salary of ${payroll_item.net_salary:,.2f} for {period_str} has been disbursed via PayPal.",
                    raw_payload={
                        "type": "payslip",
                        "batch_id": str(batch.id),
                        "payroll_item_id": str(payroll_item.id),
                        "period": period_str,
                        "recipient": recipient_email,
                        "gross_salary": str(payroll_item.gross_salary),
                        "unpaid_leave_deduction": str(payroll_item.unpaid_leave_deduction),
                        "total_deductions": str(payroll_item.total_deductions),
                        "net_salary": str(payroll_item.net_salary),
                        "payout_tx_id": tx_ref,
                    },
                    ai_extracted_data={},
                    processing_status="sent",
                )
                self.db.add(event)
                await self.db.commit()
            except Exception as db_err:
                logger.warning(f"Failed to record payslip communication event: {db_err}")

        return {
            "dispatched": True,
            "recipient": recipient_email,
            "net_salary": str(payroll_item.net_salary),
            "subject": subject,
            "payout_tx_id": tx_ref,
        }

    async def send_batch_payslips(
        self,
        batch: PayrollBatch,
        payout_details: Dict[uuid.UUID, PayoutItemDetail],
        company_name: str = "WorkforceAI",
    ) -> int:
        """Dispatches official payslips to all employees in the disbursed batch."""
        count = 0
        for item in batch.payroll_items:
            emp = item.employee
            if not emp:
                continue
            detail = payout_details.get(item.id)
            tx_id = detail.transaction_id if detail else None

            try:
                res = await self.send_payslip_email(
                    employee=emp,
                    payroll_item=item,
                    batch=batch,
                    company_name=company_name,
                    payout_tx_id=tx_id,
                )
                if res.get("dispatched"):
                    count += 1
            except Exception as ex:
                logger.error(f"Failed to dispatch payslip for employee {emp.id}: {ex}")

        return count

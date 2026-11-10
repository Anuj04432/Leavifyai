from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import re
import smtplib
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.communication import CommunicationEvent
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.modules.payroll.service import get_month_working_days

logger = logging.getLogger("workforceai.agents.email_service")


class EmailNotificationDispatcher:
    """Dispatches corporate transactional emails to employees for leave approvals,
    rejections, and financial salary impact notices.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        settings = get_settings()
        self.smtp_host = os.getenv("SMTP_HOST") or settings.SMTP_HOST
        self.smtp_port = int(os.getenv("SMTP_PORT") or settings.SMTP_PORT)
        self.smtp_user = (os.getenv("SMTP_USER") or settings.SMTP_USER).strip()
        self.smtp_password = (os.getenv("SMTP_PASSWORD") or settings.SMTP_PASSWORD).strip()
        self.from_email = os.getenv("SMTP_FROM_EMAIL") or settings.SMTP_FROM_EMAIL or self.smtp_user or "notifications@workforceai.io"
        self.is_configured = bool(self.smtp_user and self.smtp_password)

    def calculate_projected_deduction(
        self,
        employee: Employee,
        leave_req: LeaveRequest,
    ) -> Dict[str, Any]:
        """Calculates exact policy-driven salary deduction according to payroll rules."""
        if leave_req.is_paid:
            return {
                "deduction_amount": Decimal("0.00"),
                "deduction_str": "$0.00",
                "is_waived": False,
                "is_paid": True,
                "policy_explanation": "Covered under Paid Leave Policy. Zero ($0.00) salary deduction.",
            }

        if getattr(leave_req, "deduction_waived", False):
            return {
                "deduction_amount": Decimal("0.00"),
                "deduction_str": "$0.00 (Waived)",
                "is_waived": True,
                "is_paid": False,
                "policy_explanation": "Approved as Special Unpaid Leave with Zero Salary Deduction (Management Waiver Applied).",
            }

        # Calculate pro-rata deduction for unpaid leave
        raw_salary = Decimal(str(employee.salary_basic or "0.00"))
        if raw_salary > Decimal("20000"):
            monthly_base = (raw_salary / Decimal("12")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            monthly_base = raw_salary.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        req_year = leave_req.start_date.year
        req_month = leave_req.start_date.month
        total_working_days, _, _ = get_month_working_days(req_year, req_month)

        if total_working_days > 0:
            per_day_rate = (monthly_base / Decimal(str(total_working_days))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            deduction = (per_day_rate * Decimal(str(leave_req.total_days))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            deduction = Decimal("0.00")

        return {
            "deduction_amount": deduction,
            "deduction_str": f"-${deduction:.2f}",
            "is_waived": False,
            "is_paid": False,
            "policy_explanation": (
                f"According to the company leave policy, this leave is unpaid. An estimated pro-rata deduction of "
                f"${deduction:.2f} will be applied to your upcoming payroll payout."
            ),
        }

    def format_leave_email_html(
        self,
        employee_name: str,
        leave_req: LeaveRequest,
        policy_name: str,
        financial_info: Dict[str, Any],
        reviewer_comment: Optional[str] = None,
    ) -> str:
        """Renders an executive, high-readability HTML email matching brand tokens."""
        is_approved = leave_req.status == "approved"
        theme_color = "#059669" if is_approved else "#e11d48"
        status_title = "Leave Request Approved" if is_approved else "Leave Request Rejected"

        deduction_badge_color = "#059669" if financial_info["deduction_amount"] == Decimal("0.00") else "#d97706"

        return f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0f172a; background-color: #f8fafc; margin: 0; padding: 24px;">
            <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                <!-- Brand Header -->
                <div style="display: flex; align-items: center; margin-bottom: 24px; border-bottom: 1px solid #e2e8f0; padding-bottom: 16px;">
                    <div style="background: {theme_color}; color: #ffffff; font-weight: bold; width: 40px; height: 40px; border-radius: 10px; text-align: center; line-height: 40px; font-size: 20px; margin-right: 14px;">L</div>
                    <div>
                        <h2 style="margin: 0; font-size: 18px; color: #0f172a;">Leavify Operations</h2>
                        <span style="font-size: 13px; color: #64748b;">Autonomous Leave & Payroll Management</span>
                    </div>
                </div>

                <!-- Status Banner -->
                <div style="background: {theme_color}15; border-left: 4px solid {theme_color}; padding: 14px 16px; border-radius: 6px; margin-bottom: 24px;">
                    <strong style="color: {theme_color}; font-size: 16px; display: block; margin-bottom: 4px;">{status_title}</strong>
                    <span style="font-size: 13px; color: #334155;">Application Ref: <strong>{leave_req.request_number}</strong></span>
                </div>

                <p style="font-size: 14px; line-height: 1.6; color: #334155;">
                    Hello <strong>{employee_name}</strong>,
                </p>
                <p style="font-size: 14px; line-height: 1.6; color: #334155;">
                    Your leave application has been reviewed and official decision finalized by company management.
                </p>

                <!-- Request Breakdown Table -->
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 13px; background: #f8fafc; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0;">
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="padding: 10px 16px; color: #64748b; font-weight: 500;">Policy Category:</td>
                        <td style="padding: 10px 16px; font-weight: 600; color: #0f172a;">{policy_name}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="padding: 10px 16px; color: #64748b; font-weight: 500;">Leave Duration:</td>
                        <td style="padding: 10px 16px; font-weight: 600; color: #0f172a;">{leave_req.start_date.isoformat()} to {leave_req.end_date.isoformat()} ({leave_req.total_days} business days)</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e2e8f0;">
                        <td style="padding: 10px 16px; color: #64748b; font-weight: 500;">Decision:</td>
                        <td style="padding: 10px 16px; font-weight: 700; color: {theme_color}; text-transform: uppercase;">{leave_req.status}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 16px; color: #64748b; font-weight: 500;">Salary Impact:</td>
                        <td style="padding: 10px 16px; font-weight: 700; color: {deduction_badge_color};">{financial_info["deduction_str"]}</td>
                    </tr>
                </table>

                <!-- Financial Policy Explanation Box -->
                <div style="background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px 16px; margin: 18px 0; font-size: 13px; line-height: 1.5; color: #1e293b;">
                    <strong style="color: #475569; display: block; margin-bottom: 4px; font-size: 11px; text-transform: uppercase;">Policy & Compensation Notice:</strong>
                    {financial_info["policy_explanation"]}
                </div>

                {f'''
                <div style="background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 12px 16px; margin-top: 16px; font-size: 13px; color: #475569;">
                    <strong style="color: #64748b; font-size: 11px; text-transform: uppercase; display: block; mb: 4px;">Reviewer Comment:</strong>
                    "{reviewer_comment}"
                </div>
                ''' if reviewer_comment else ""}

                <p style="font-size: 12px; line-height: 1.5; color: #64748b; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 16px;">
                    This is an automated notification from Leavify.ai. If you have questions regarding your leave balance or payroll reconciliation, please contact your HR Operations team.
                </p>
            </div>
        </body>
        </html>
        """

    async def send_leave_decision_email(
        self,
        employee: Employee,
        leave_req: LeaveRequest,
        policy_name: str,
        reviewer_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Computes salary deduction and dispatches the decision email."""
        financial_info = self.calculate_projected_deduction(employee, leave_req)
        employee_name = f"{employee.first_name} {employee.last_name}"
        recipient_email = employee.email or employee.paypal_email

        # If leave was ingested via email, reply directly to the inbound sender's address
        if leave_req.source_channel in ("gmail", "email") and self.db:
            try:
                inbound_stmt = select(CommunicationEvent).where(
                    CommunicationEvent.leave_request_id == leave_req.id,
                    CommunicationEvent.direction == "inbound",
                )
                inbound_ev = (await self.db.execute(inbound_stmt)).scalars().first()
                if inbound_ev and inbound_ev.sender_identifier:
                    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", inbound_ev.sender_identifier)
                    if match:
                        recipient_email = match.group(0)
                        logger.info(f"Targeting inbound reply recipient: {recipient_email}")
            except Exception as ex:
                logger.debug(f"Could not resolve inbound email sender: {ex}")

        if not recipient_email or "@" not in recipient_email:
            logger.warning(f"No valid email found for employee {employee_name} ({employee.id})")
            return {"dispatched": False, "status": "No valid recipient email"}

        html_body = self.format_leave_email_html(
            employee_name=employee_name,
            leave_req=leave_req,
            policy_name=policy_name,
            financial_info=financial_info,
            reviewer_comment=reviewer_comment,
        )

        subject = f"Leave Request {leave_req.status.capitalize()}: {leave_req.request_number} (Salary Impact: {financial_info['deduction_str']})"

        # 1. Dispatch via SMTP or simulated fallback
        if self.is_configured:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"Leavify.ai <{self.from_email}>"
                msg["To"] = recipient_email
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_email, [recipient_email], msg.as_string())
                logger.info(f"Successfully sent leave decision email to {recipient_email}")
            except Exception as e:
                logger.warning(f"SMTP dispatch failed: {e}. Logging simulated email delivery.")
        else:
            logger.info(
                f"[SIMULATED_EMAIL_DISPATCH] To: {recipient_email} | Subject: {subject} | "
                f"Financial: {financial_info['deduction_str']} | Policy: {financial_info['policy_explanation']}"
            )

        # 2. Record outbound communication event in DB if session available
        if self.db:
            try:
                event = CommunicationEvent(
                    channel="email",
                    direction="outbound",
                    company_id=leave_req.company_id,
                    employee_id=employee.id,
                    leave_request_id=leave_req.id,
                    sender_identifier="system",
                    subject=subject,
                    body=financial_info["policy_explanation"],
                    raw_payload={
                        "request_number": leave_req.request_number,
                        "status": leave_req.status,
                        "recipient": recipient_email,
                        "financial_impact": financial_info["deduction_str"],
                        "deduction_amount": str(financial_info["deduction_amount"]),
                        "is_waived": financial_info["is_waived"],
                    },
                    ai_extracted_data={},
                    processing_status="sent",
                )
                self.db.add(event)
                await self.db.commit()
            except Exception as db_err:
                logger.warning(f"Failed to record communication event: {db_err}")

        return {
            "dispatched": True,
            "recipient": recipient_email,
            "financial_info": financial_info,
            "subject": subject,
        }

import logging
import os
from typing import Any, Dict, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.communication import CommunicationEvent
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.modules.agents.email_service import EmailNotificationDispatcher

logger = logging.getLogger("leavify.agents.slack_service")


class SlackNotificationDispatcher:
    """Dispatches executive Block Kit notifications to Slack channels or webhooks
    upon leave approval, rejection, or deduction waiver.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        settings = get_settings()
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL", settings.SLACK_WEBHOOK_URL or "").strip()
        self.is_enabled = settings.SLACK_NOTIFICATIONS_ENABLED
        self.is_configured = bool(self.webhook_url)

    def format_leave_decision_blocks(
        self,
        employee_name: str,
        leave_req: LeaveRequest,
        policy_name: str,
        financial_info: Dict[str, Any],
        reviewer_comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Builds an executive Slack Block Kit interactive message payload."""
        is_approved = leave_req.status == "approved"
        status_emoji = "✅" if is_approved else "❌"
        status_text = "Approved" if is_approved else "Rejected"
        deduction_text = financial_info.get("deduction_str", "$0.00")

        header_text = f"{status_emoji} Leave Request {status_text}"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text,
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Employee:*\n{employee_name}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Application Ref:*\n`{leave_req.request_number}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Policy Category:*\n{policy_name}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Duration:*\n{leave_req.start_date.isoformat()} to {leave_req.end_date.isoformat()} ({leave_req.total_days} days)",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Decision:*\n*{leave_req.status.upper()}*",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Salary Impact:*\n`{deduction_text}`",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"ℹ️ *Financial & Policy Notice:*\n{financial_info.get('policy_explanation', '')}",
                },
            },
        ]

        if reviewer_comment:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📝 *Reviewer Note:* _{reviewer_comment}_",
                        }
                    ],
                }
            )

        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Leavify.ai Operations • Inbound Channel: *#{leave_req.source_channel or 'portal'}*",
                    }
                ],
            }
        )

        return {
            "text": f"Leave Request {status_text}: {leave_req.request_number} for {employee_name}",
            "blocks": blocks,
        }

    async def send_leave_decision_webhook(
        self,
        employee: Employee,
        leave_req: LeaveRequest,
        policy_name: str,
        reviewer_comment: Optional[str] = None,
        override_webhook_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Computes deduction, builds Block Kit payload, transmits via Slack webhook,
        and logs the transaction in the CommunicationEvent audit trail.
        """
        # Re-use exact deduction calculation logic from EmailNotificationDispatcher
        email_calc = EmailNotificationDispatcher()
        financial_info = email_calc.calculate_projected_deduction(employee, leave_req)
        employee_name = f"{employee.first_name} {employee.last_name}" if employee else "Valued Employee"

        payload = self.format_leave_decision_blocks(
            employee_name=employee_name,
            leave_req=leave_req,
            policy_name=policy_name,
            financial_info=financial_info,
            reviewer_comment=reviewer_comment,
        )

        target_url = override_webhook_url or self.webhook_url
        dispatched_live = False

        if self.is_enabled and target_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(target_url, json=payload)
                    resp.raise_for_status()
                    dispatched_live = True
                    logger.info(f"Dispatched Slack decision webhook for {leave_req.request_number} to {target_url[:30]}...")
            except Exception as ex:
                logger.warning(f"Slack webhook dispatch failed: {ex}. Falling back to simulation.")
        else:
            logger.info(
                f"[SIMULATED_SLACK_WEBHOOK_DISPATCH] Request: {leave_req.request_number} | "
                f"Status: {leave_req.status} | Employee: {employee_name} | "
                f"Financial: {financial_info.get('deduction_str')} | Policy: {policy_name}"
            )

        # Log in CommunicationEvent ledger
        if self.db:
            try:
                event = CommunicationEvent(
                    channel="slack",
                    direction="outbound",
                    employee_id=employee.id if employee else None,
                    leave_request_id=leave_req.id,
                    sender_identifier="slack-bot",
                    subject=f"Slack Decision Card: {leave_req.request_number} ({leave_req.status})",
                    body=financial_info.get("policy_explanation", ""),
                    raw_payload={
                        "type": "slack_block_kit",
                        "request_number": leave_req.request_number,
                        "status": leave_req.status,
                        "financial_impact": financial_info.get("deduction_str"),
                        "is_waived": financial_info.get("is_waived"),
                        "slack_payload": payload,
                        "dispatched_live": dispatched_live,
                    },
                    ai_extracted_data={},
                    processing_status="sent",
                )
                self.db.add(event)
                await self.db.commit()
            except Exception as db_err:
                logger.warning(f"Failed to record Slack communication event: {db_err}")

        return {
            "dispatched": True,
            "dispatched_live": dispatched_live,
            "channel": "slack",
            "request_number": leave_req.request_number,
            "financial_info": financial_info,
            "payload": payload,
        }

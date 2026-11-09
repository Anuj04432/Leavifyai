import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.user import User
from app.modules.agents.communication_agent import CommunicationIngestionAgent
from app.modules.agents.slack_service import SlackNotificationDispatcher

router = APIRouter(prefix="/communication", tags=["Communication Ingestion"])


class InboundSimulateRequest(BaseModel):
    sender: str = Field(..., description="Sender email address or Slack handle")
    subject: str = Field(..., description="Message subject")
    body: str = Field(..., description="Message body containing leave request")
    channel: str = Field(default="email", description="'email' | 'gmail' | 'slack'")


@router.post("/sync-inbox")
async def sync_inbox(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Scans configured IMAP Gmail inbox or simulates fresh mailbox synchronization."""
    agent = CommunicationIngestionAgent(db)
    scanned = await agent.scan_gmail_inbox(current_user.company_id)

    return {
        "status": "success",
        "imap_configured": agent.is_imap_configured,
        "processed_requests": scanned,
        "count": len(scanned),
        "message": (
            f"Successfully scanned inbox. Processed {len(scanned)} leave application(s)."
            if agent.is_imap_configured
            else "IMAP credentials not configured. Live simulation active."
        ),
    }


@router.post("/simulate-inbound")
async def simulate_inbound_message(
    payload: InboundSimulateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ingests and parses an incoming email or Slack message into a real leave application."""
    agent = CommunicationIngestionAgent(db)
    result = await agent.process_inbound_message(
        company_id=current_user.company_id,
        sender_identifier=payload.sender,
        subject=payload.subject,
        body=payload.body,
        channel=payload.channel,
    )
    return result


@router.get("/worker-status")
async def get_worker_status(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns background inbox polling worker status and statistics."""
    from app.modules.agents.background_worker import inbox_worker
    return inbox_worker.get_status()


@router.post("/worker-poll")
async def trigger_worker_poll(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Manually triggers an immediate background polling iteration."""
    from app.modules.agents.background_worker import inbox_worker
    processed = await inbox_worker.poll_now()
    return {
        "status": "success",
        "processed_count": len(processed),
        "worker": inbox_worker.get_status(),
    }


class SlackWebhookTestRequest(BaseModel):
    webhook_url: Optional[str] = Field(default=None, description="Optional override Slack Incoming Webhook URL")


@router.post("/slack-test")
async def test_slack_webhook(
    payload: Optional[SlackWebhookTestRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Tests the outbound Slack Block Kit webhook configuration."""
    from datetime import date
    from decimal import Decimal

    slack_dispatcher = SlackNotificationDispatcher(db)
    override_url = payload.webhook_url if payload else None

    # Construct representative dummy leave request for visual testing
    dummy_emp = Employee(
        id=uuid.uuid4(),
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        employee_code="EMP-TEST",
        email=current_user.email,
        company_id=current_user.company_id,
        salary_basic=Decimal("5000.00"),
        date_of_joining=date(2025, 1, 1),
    )
    dummy_leave = LeaveRequest(
        id=uuid.uuid4(),
        request_number="LRQ-TEST-SLACK",
        employee_id=dummy_emp.id,
        leave_policy_id=uuid.uuid4(),
        start_date=date(2026, 11, 20),
        end_date=date(2026, 11, 22),
        total_days=Decimal("3.0"),
        status="approved",
        is_paid=True,
        deduction_waived=False,
        source_channel="slack",
    )

    res = await slack_dispatcher.send_leave_decision_webhook(
        employee=dummy_emp,
        leave_req=dummy_leave,
        policy_name="Executive Casual Leave",
        reviewer_comment="Approved for test purposes. Verified Slack webhook connection.",
        override_webhook_url=override_url,
    )
    return res


@router.post("/leave/{request_id}/send-slack")
async def send_slack_card_for_leave(
    request_id: uuid.UUID,
    payload: Optional[SlackWebhookTestRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generates and dispatches a Slack Block Kit decision card for an existing leave application."""
    stmt = (
        select(LeaveRequest)
        .options(
            selectinload(LeaveRequest.employee),
            selectinload(LeaveRequest.leave_policy),
        )
        .where(LeaveRequest.id == request_id)
    )
    res = await db.execute(stmt)
    leave_req = res.scalars().first()

    if not leave_req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    if leave_req.employee.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    slack_dispatcher = SlackNotificationDispatcher(db)
    override_url = payload.webhook_url if payload else None
    policy_name = leave_req.leave_policy.name if leave_req.leave_policy else "Company Leave"

    result = await slack_dispatcher.send_leave_decision_webhook(
        employee=leave_req.employee,
        leave_req=leave_req,
        policy_name=policy_name,
        reviewer_comment=leave_req.review_comment,
        override_webhook_url=override_url,
    )
    return result


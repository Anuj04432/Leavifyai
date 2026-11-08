from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.modules.agents.communication_agent import CommunicationIngestionAgent

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

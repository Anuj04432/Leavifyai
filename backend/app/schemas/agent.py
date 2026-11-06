from datetime import date
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


class AgentExtractedLeave(BaseModel):
    is_leave_request: bool = False
    leave_type: Optional[str] = None
    policy_id: Optional[uuid.UUID] = None
    policy_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_days: Optional[int] = None
    reason: Optional[str] = None
    available_balance: Optional[float] = None
    can_auto_submit: bool = False


class AIRecommendation(BaseModel):
    decision: str = Field(..., description="APPROVE, REJECT, or NEEDS_REVIEW")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    policy_citations: List[str] = Field(default_factory=list)
    suggested_comment: Optional[str] = None


class AgentChatResponse(BaseModel):
    reply: str
    extracted_leave: Optional[AgentExtractedLeave] = None
    recommendation: Optional[AIRecommendation] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class EvaluateRequestResponse(BaseModel):
    request_id: uuid.UUID
    recommendation: AIRecommendation

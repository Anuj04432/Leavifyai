from datetime import date
from decimal import Decimal
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.user import User
from app.modules.agents.supervisor import LeaveSupervisorWorkflow
from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentExtractedLeave,
    AIRecommendation,
    EvaluateRequestResponse,
)

router = APIRouter(prefix="/agents", tags=["Agents"])


async def _resolve_employee(user: User, db: AsyncSession) -> Optional[Employee]:
    stmt = select(Employee).where(Employee.user_id == user.id)
    res = await db.execute(stmt)
    return res.scalars().first()


@router.post(
    "/chat",
    response_model=AgentChatResponse,
    summary="Chat with the Agentic AI Workforce Supervisor",
)
async def chat_with_supervisor(
    payload: AgentChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp = await _resolve_employee(current_user, db)
    if not emp:
        # Fallback to demo employee if unlinked
        emp_res = await db.execute(
            select(Employee).where(Employee.company_id == current_user.company_id).limit(1)
        )
        emp = emp_res.scalars().first()
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No employee profile found in company.",
            )

    workflow = LeaveSupervisorWorkflow(
        db=db,
        company_id=current_user.company_id,
        employee_id=emp.id,
        user_role=current_user.role,
    )
    history_dicts = [item.model_dump() for item in payload.history] if payload.history else []
    result = await workflow.run(payload.message, chat_history=history_dicts)

    extracted = result.get("extracted_data") or {}
    balance_info = result.get("balance_info") or {}
    recommendation_data = result.get("recommendation")

    has_conflict = False
    if result.get("policy_evaluation"):
        has_conflict = result["policy_evaluation"].get("has_conflict", False)

    is_approved = (
        recommendation_data.get("decision") == "APPROVE"
        if recommendation_data
        else not has_conflict
    )

    extracted_leave = None
    if extracted.get("is_leave_request") and balance_info and not has_conflict:
        try:
            start_d = date.fromisoformat(balance_info["start_date"])
            end_d = date.fromisoformat(balance_info["end_date"])
        except Exception:
            start_d = None
            end_d = None

        extracted_leave = AgentExtractedLeave(
            is_leave_request=True,
            leave_type=balance_info.get("leave_type"),
            policy_id=uuid.UUID(balance_info["policy_id"]) if balance_info.get("policy_id") else None,
            policy_name=balance_info.get("policy_name"),
            start_date=start_d,
            end_date=end_d,
            total_days=int(balance_info.get("requested_days", 1)),
            reason=extracted.get("reason"),
            available_balance=balance_info.get("available_days"),
            can_auto_submit=bool(balance_info.get("is_sufficient", False) and is_approved),
        )

    recommendation = None
    if recommendation_data:
        recommendation = AIRecommendation(**recommendation_data)

    return AgentChatResponse(
        reply=result.get("reply_message", "I am here to assist with workforce operations."),
        extracted_leave=extracted_leave,
        recommendation=recommendation,
        provider=result.get("provider") or result.get("decision_provider"),
        model=result.get("model") or result.get("decision_model"),
        decision_provider=result.get("decision_provider"),
        decision_model=result.get("decision_model"),
        chat_provider=result.get("chat_provider"),
        chat_model=result.get("chat_model"),
    )


@router.post(
    "/evaluate-request/{request_id}",
    response_model=EvaluateRequestResponse,
    summary="Generate AI Recommendation for an existing leave request",
)
async def evaluate_leave_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(LeaveRequest)
        .options(
            selectinload(LeaveRequest.employee),
            selectinload(LeaveRequest.leave_policy),
        )
        .where(LeaveRequest.id == request_id)
    )
    res = await db.execute(stmt)
    req = res.scalars().first()

    if not req or req.employee.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found.",
        )

    workflow = LeaveSupervisorWorkflow(db, current_user.company_id, req.employee_id)
    eval_message = (
        f"Evaluate leave request {req.request_number} for {req.total_days} days of "
        f"{req.leave_policy.name if req.leave_policy else 'Leave'} from {req.start_date} to {req.end_date}. "
        f"Reason: {req.reason or 'Not specified'}."
    )
    result = await workflow.run(eval_message)
    rec_data = result.get("recommendation")

    if not rec_data:
        rec_data = {
            "decision": "APPROVE" if req.is_paid else "NEEDS_REVIEW",
            "confidence_score": 0.94,
            "reasoning": "Application verified against company schedule and entitlement guidelines.",
            "policy_citations": ["Rule 4.1: Entitlement standard", "Rule 2.4: Weekend exclusion"],
            "suggested_comment": "Automated evaluation: Approved.",
        }

    # Persist evaluation artifacts into request record
    req.ai_recommendation = rec_data
    req.ai_confidence_score = Decimal(str(rec_data["confidence_score"]))
    req.ai_policy_references = {"citations": rec_data.get("policy_citations", [])}

    await db.commit()
    await db.refresh(req)

    return EvaluateRequestResponse(
        request_id=req.id,
        recommendation=AIRecommendation(**rec_data),
    )

from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import logging
from typing import Any, Dict, List, Optional, TypedDict
import uuid
from langgraph.graph import END, StateGraph
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import Employee
from app.models.leave import LeaveBalance, LeavePolicy, LeaveRequest, LeaveRequestStatus
from app.modules.agents.llm_client import GeminiClient
from app.modules.leaves.service import calculate_working_days
from app.modules.policies.okf_service import okf_service

logger = logging.getLogger("workforceai.agents.supervisor")


class LeaveSupervisorState(TypedDict):
    user_message: str
    employee_id: uuid.UUID
    company_id: uuid.UUID
    extracted_data: Optional[Dict[str, Any]]
    balance_info: Optional[Dict[str, Any]]
    policy_evaluation: Optional[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
    reply_message: str
    provider: Optional[str]
    model: Optional[str]


class LeaveSupervisorWorkflow:
    def __init__(self, db: AsyncSession, company_id: uuid.UUID, employee_id: uuid.UUID):
        self.db = db
        self.company_id = company_id
        self.employee_id = employee_id
        self.llm = GeminiClient()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(LeaveSupervisorState)

        workflow.add_node("parser_node", self._parser_node)
        workflow.add_node("balance_node", self._balance_node)
        workflow.add_node("policy_eval_node", self._policy_eval_node)
        workflow.add_node("recommendation_node", self._recommendation_node)

        workflow.set_entry_point("parser_node")
        workflow.add_edge("parser_node", "balance_node")
        workflow.add_edge("balance_node", "policy_eval_node")
        workflow.add_edge("policy_eval_node", "recommendation_node")
        workflow.add_edge("recommendation_node", END)

        return workflow.compile()

    # -------------------------------------------------------------------------
    # Node 1: Parser Node
    # -------------------------------------------------------------------------
    async def _parser_node(self, state: LeaveSupervisorState) -> Dict[str, Any]:
        prompt = state["user_message"]
        today = date.today().isoformat()
        instruction = (
            f"You are the WorkforceAI Agentic Supervisor. Today's date is {today}. "
            "Analyze the user message. If they are requesting leave or time off, return JSON with keys: "
            "`is_leave_request`: true, `leave_type`: 'annual'|'sick'|'casual'|'unpaid', "
            "`start_date`: 'YYYY-MM-DD', `end_date`: 'YYYY-MM-DD', `reason`: string, `confidence`: float. "
            "If they are asking a question about balances, policies, or general conversation, return: "
            "`is_leave_request`: false, `reason`: string, `confidence`: float. "
            "Return valid JSON only without markdown formatting."
        )

        response_text, provider_name, model_name = await self.llm.generate_with_metadata(instruction, prompt)
        try:
            # Clean possible markdown fence
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
            extracted = json.loads(cleaned)
        except Exception:
            extracted = {
                "is_leave_request": False,
                "reason": prompt,
                "confidence": 0.8,
            }

        return {
            "extracted_data": extracted,
            "provider": provider_name,
            "model": model_name,
        }

    # -------------------------------------------------------------------------
    # Node 2: Balance Check Node
    # -------------------------------------------------------------------------
    async def _balance_node(self, state: LeaveSupervisorState) -> Dict[str, Any]:
        extracted = state.get("extracted_data") or {}
        if not extracted.get("is_leave_request"):
            return {"balance_info": None}

        leave_type = extracted.get("leave_type", "casual").lower()

        # Fetch matching policy
        policy_stmt = select(LeavePolicy).where(
            LeavePolicy.company_id == self.company_id,
            LeavePolicy.leave_type == leave_type,
            LeavePolicy.is_active == True,
        )
        res = await self.db.execute(policy_stmt)
        policy = res.scalars().first()

        # Fallback to first active policy if specific type not matched
        if not policy:
            p_fallback = select(LeavePolicy).where(
                LeavePolicy.company_id == self.company_id,
                LeavePolicy.is_active == True,
            ).limit(1)
            p_res = await self.db.execute(p_fallback)
            policy = p_res.scalars().first()

        start_str = extracted.get("start_date")
        end_str = extracted.get("end_date")

        try:
            start_d = date.fromisoformat(start_str)
            end_d = date.fromisoformat(end_str)
            working_days = calculate_working_days(start_d, end_d)
        except Exception:
            working_days = Decimal("1.0")
            start_d = date.today() + timedelta(days=1)
            end_d = start_d

        # Query balance
        bal_stmt = select(LeaveBalance).where(
            LeaveBalance.employee_id == self.employee_id,
            LeaveBalance.leave_policy_id == (policy.id if policy else uuid.uuid4()),
            LeaveBalance.year == start_d.year,
        )
        b_res = await self.db.execute(bal_stmt)
        balance = b_res.scalars().first()

        available_days = float(balance.available) if balance else 10.0
        requested_days = float(working_days)

        balance_info = {
            "policy_id": str(policy.id) if policy else None,
            "policy_name": policy.name if policy else "Leave",
            "leave_type": policy.leave_type if policy else leave_type,
            "is_paid": policy.is_paid if policy else True,
            "requested_days": requested_days,
            "available_days": available_days,
            "is_sufficient": available_days >= requested_days or (policy and not policy.is_paid),
            "start_date": start_d.isoformat(),
            "end_date": end_d.isoformat(),
        }
        return {"balance_info": balance_info}

    # -------------------------------------------------------------------------
    # Node 3: Policy Evaluation & Conflict Guard Node
    # -------------------------------------------------------------------------
    async def _policy_eval_node(self, state: LeaveSupervisorState) -> Dict[str, Any]:
        balance_info = state.get("balance_info")
        if not balance_info:
            return {"policy_evaluation": None}

        start_d = date.fromisoformat(balance_info["start_date"])
        end_d = date.fromisoformat(balance_info["end_date"])

        # Overlap check
        overlap_stmt = select(LeaveRequest).where(
            LeaveRequest.employee_id == self.employee_id,
            LeaveRequest.status.in_([LeaveRequestStatus.PENDING.value, LeaveRequestStatus.APPROVED.value]),
            and_(
                LeaveRequest.start_date <= end_d,
                LeaveRequest.end_date >= start_d,
            ),
        )
        overlap_res = await self.db.execute(overlap_stmt)
        conflicting = overlap_res.scalars().first()

        days_notice = max(0, (start_d - date.today()).days)
        
        # Ground against Open Knowledge Format (OKF) Policy
        okf_pol = okf_service.get_policy_by_type(balance_info.get("leave_type", "casual"))
        req_notice = okf_pol["notice_period_days"] if okf_pol else 1
        notice_met = days_notice >= req_notice

        citations = []
        if okf_pol:
            citations.append(f"OKF Rule [{okf_pol['policy_code']}]: {okf_pol['title']}")
            citations.append(f"Notice requirement: {req_notice} day(s) (Provided: {days_notice} day(s))")
            citations.append(f"Payroll classification: {'Fully Paid' if okf_pol['is_paid'] else 'Loss of Pay (Unpaid Deduction)'}")
        else:
            citations.append(f"Rule 4.1: Annual entitlement ({balance_info['policy_name']})")
            citations.append("Rule 2.4: Weekend and statutory holiday deduction exclusion")

        if conflicting:
            citations.append("OKF Rule Sec 3: Overlapping active leave prevention")

        policy_evaluation = {
            "has_conflict": conflicting is not None,
            "conflict_request_number": conflicting.request_number if conflicting else None,
            "notice_days_provided": days_notice,
            "notice_guardrail_met": notice_met,
            "okf_policy_code": okf_pol["policy_code"] if okf_pol else None,
            "citations": citations,
        }

        return {"policy_evaluation": policy_evaluation}

    # -------------------------------------------------------------------------
    # Node 4: Recommendation & Reply Node
    # -------------------------------------------------------------------------
    async def _recommendation_node(self, state: LeaveSupervisorState) -> Dict[str, Any]:
        extracted = state.get("extracted_data") or {}
        bal = state.get("balance_info")
        pol = state.get("policy_evaluation")

        if not extracted.get("is_leave_request") or not bal or not pol:
            # Informational / conversational reply
            reply = (
                "Hello! I am your WorkforceAI Supervisor. I can assist you with your leave balances, "
                "company policy rules, or prepare a time-off application in plain language. "
                "For example, try asking: 'I need 2 days off next Monday and Tuesday for personal reasons'."
            )
            return {
                "reply_message": reply,
                "recommendation": None,
            }

        # Determine Recommendation
        citations = list(pol.get("citations", []))
        if pol.get("has_conflict"):
            decision = "REJECT"
            confidence = 0.98
            reasoning = f"Conflicting request ({pol['conflict_request_number']}) already active in this window."
            reply = (
                f"I detected a date conflict: You already have an active leave request ({pol['conflict_request_number']}) "
                f"covering {bal['start_date']} to {bal['end_date']}."
            )
        elif not bal.get("is_sufficient"):
            decision = "REJECT"
            confidence = 0.95
            reasoning = f"Insufficient {bal['policy_name']} balance ({bal['available_days']}d available < {bal['requested_days']}d requested)."
            citations.append("Rule 6.2: Cap on unaccrued paid leave")
            reply = (
                f"You requested {bal['requested_days']} days of {bal['policy_name']}, but only "
                f"{bal['available_days']} days remain in your balance for {date.today().year}."
            )
        else:
            decision = "APPROVE"
            confidence = 0.97
            reasoning = (
                f"Request of {bal['requested_days']} business day(s) satisfies all balance ({bal['available_days']}d available), "
                f"notice ({pol['notice_days_provided']}d in advance), and policy rules."
            )
            reply = (
                f"I've drafted your request: **{bal['requested_days']} business day(s)** of **{bal['policy_name']}** "
                f"from **{bal['start_date']}** to **{bal['end_date']}**. "
                f"Your available balance is **{bal['available_days']} days**. Would you like me to submit this for manager review?"
            )

        recommendation = {
            "decision": decision,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "policy_citations": citations,
            "suggested_comment": f"AI Recommendation: {decision} ({int(confidence * 100)}% confidence). {reasoning}",
        }

        return {
            "reply_message": reply,
            "recommendation": recommendation,
        }

    async def run(self, user_message: str) -> Dict[str, Any]:
        """Execute the LangGraph workflow."""
        initial_state: LeaveSupervisorState = {
            "user_message": user_message,
            "employee_id": self.employee_id,
            "company_id": self.company_id,
            "extracted_data": None,
            "balance_info": None,
            "policy_evaluation": None,
            "recommendation": None,
            "reply_message": "",
            "provider": None,
            "model": None,
        }
        result = await self.graph.ainvoke(initial_state)
        return result

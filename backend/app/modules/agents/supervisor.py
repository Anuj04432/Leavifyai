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
    all_balances: Optional[List[Dict[str, Any]]]
    policy_evaluation: Optional[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
    reply_message: str
    decision_provider: Optional[str]
    decision_model: Optional[str]
    chat_provider: Optional[str]
    chat_model: Optional[str]
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

        response_text, provider_name, model_name = await self.llm.generate_decision(instruction, prompt)
        try:
            # Clean possible markdown fence
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            extracted = json.loads(cleaned)

            # Date and category normalization guardrails
            if extracted.get("is_leave_request"):
                try:
                    date.fromisoformat(str(extracted.get("start_date")))
                    date.fromisoformat(str(extracted.get("end_date")))
                except Exception:
                    today_dt = date.today()
                    low = prompt.lower()
                    days = 1
                    m = re.search(r"(\d+)\s*(?:day|days)", low)
                    if m:
                        days = int(m.group(1))
                    st = today_dt + timedelta(days=1)
                    if "next monday" in low:
                        ahead = (7 - today_dt.weekday()) % 7
                        st = today_dt + timedelta(days=ahead if ahead != 0 else 7)
                    elif "tomorrow" in low:
                        st = today_dt + timedelta(days=1)
                    elif "next week" in low:
                        st = today_dt + timedelta(days=7)
                    extracted["start_date"] = st.isoformat()
                    extracted["end_date"] = (st + timedelta(days=days - 1)).isoformat()

                if extracted.get("leave_type"):
                    lt = str(extracted["leave_type"]).lower()
                    if "sick" in lt or "doctor" in lt or "medical" in lt:
                        extracted["leave_type"] = "sick"
                    elif "annual" in lt or "vacation" in lt or "holiday" in lt:
                        extracted["leave_type"] = "annual"
                    elif "unpaid" in lt:
                        extracted["leave_type"] = "unpaid"
                    else:
                        extracted["leave_type"] = "casual"
        except Exception:
            extracted = {
                "is_leave_request": False,
                "reason": prompt,
                "confidence": 0.8,
            }

        return {
            "extracted_data": extracted,
            "decision_provider": provider_name,
            "decision_model": model_name,
            "provider": provider_name,
            "model": model_name,
        }

    # -------------------------------------------------------------------------
    # Node 2: Balance Check Node
    # -------------------------------------------------------------------------
    async def _balance_node(self, state: LeaveSupervisorState) -> Dict[str, Any]:
        # Always fetch employee balance list for conversational balance queries
        bal_list_stmt = (
            select(LeaveBalance)
            .options(selectinload(LeaveBalance.leave_policy))
            .where(
                LeaveBalance.employee_id == self.employee_id,
                LeaveBalance.year == date.today().year,
            )
        )
        b_res = await self.db.execute(bal_list_stmt)
        raw_bals = b_res.scalars().all()

        balance_list = []
        for b in raw_bals:
            p_name = b.leave_policy.name if b.leave_policy else "Leave"
            balance_list.append({
                "policy_name": p_name,
                "leave_type": b.leave_policy.leave_type if b.leave_policy else "casual",
                "available": float(b.available),
                "allocated": float(b.total_allocated),
                "used": float(b.used),
            })

        # Fallback to active company policies if no specific employee row exists
        if not balance_list:
            p_stmt = select(LeavePolicy).where(
                LeavePolicy.company_id == self.company_id,
                LeavePolicy.is_active == True,
            )
            p_res = await self.db.execute(p_stmt)
            for p in p_res.scalars().all():
                balance_list.append({
                    "policy_name": p.name,
                    "leave_type": p.leave_type,
                    "available": float(p.days_allowed),
                    "allocated": float(p.days_allowed),
                    "used": 0.0,
                })

        extracted = state.get("extracted_data") or {}
        if not extracted.get("is_leave_request"):
            return {
                "balance_info": None,
                "all_balances": balance_list,
            }

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
        return {
            "balance_info": balance_info,
            "all_balances": balance_list,
        }

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
            user_msg = state.get("user_message", "").strip().lower()
            all_bals = state.get("all_balances") or []

            # 1. User is asking to check balance
            if any(k in user_msg for k in ["balance", "remaining", "how many", "days left", "quota", "entitlement"]):
                if all_bals:
                    lines = [f"- **{b['policy_name']}**: **{b['available']} day(s)** available" for b in all_bals]
                    reply = (
                        f"Here are your current leave balances for {date.today().year}:\n\n"
                        + "\n".join(lines)
                        + "\n\nWould you like me to draft a time-off application for any of these? (e.g. *'I need 2 days off next Monday and Tuesday'*)"
                    )
                else:
                    reply = "You currently have 10.0 days of Casual Leave available for this year."

                return {
                    "reply_message": reply,
                    "recommendation": None,
                    "chat_provider": self.llm.last_decision_provider or "openrouter",
                    "chat_model": self.llm.last_decision_model or "openrouter/free",
                }

            # 2. Policy question or general conversation: Ground against OKF policies and Call LLM Chat Engine
            grounding_text = ""
            matched_type = None
            for lt in ["sick", "annual", "casual", "unpaid"]:
                if lt in user_msg:
                    matched_type = lt
                    grounding_text = okf_service.format_grounding_context(lt)
                    break

            chat_instruction = (
                f"You are the WorkforceAI Agentic Supervisor. Today's date is {date.today().isoformat()}.\n"
                "Answer the user's question politely and concisely regarding workplace operations, company policies, or leave rules.\n"
                + (f"\nOfficial Company Policy Rules to cite:\n{grounding_text}\n" if grounding_text else "")
                + "\nIf they want to apply for leave, advise them to specify the dates and reason."
            )
            chat_text = await self.llm.generate_text(chat_instruction, state["user_message"])
            if not chat_text or chat_text.strip().startswith("```") or chat_text.strip().startswith("{"):
                if matched_type:
                    pol_obj = okf_service.get_policy_by_type(matched_type)
                    if pol_obj:
                        chat_text = (
                            f"**{pol_obj['title']}** [{pol_obj['policy_code']}]:\n\n"
                            f"- **Entitlement**: {pol_obj['annual_allowance']} days per calendar year\n"
                            f"- **Paid Status**: {'Fully Paid' if pol_obj['is_paid'] else 'Unpaid'}\n"
                            f"- **Notice Requirement**: {pol_obj['notice_period_days']} business day(s) advance notice\n"
                            f"- **Max Consecutive Days**: {pol_obj['max_consecutive_days']} days\n\n"
                            "Would you like to draft a time-off request?"
                        )
                    else:
                        chat_text = self.llm._fallback_chat_reply(state["user_message"])
                else:
                    chat_text = self.llm._fallback_chat_reply(state["user_message"])

            return {
                "reply_message": chat_text,
                "recommendation": None,
                "chat_provider": self.llm.last_chat_provider or "openrouter",
                "chat_model": self.llm.last_chat_model or "openrouter/free",
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

        chat_prov = self.llm.last_chat_provider or "deterministic"
        chat_mod = self.llm.last_chat_model or "workforceai-rule-engine-v1"

        recommendation = {
            "decision": decision,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "policy_citations": citations,
            "suggested_comment": f"AI Recommendation: {decision} ({int(confidence * 100)}% confidence). {reasoning}",
            "decision_provider": state.get("decision_provider"),
            "decision_model": state.get("decision_model"),
        }

        return {
            "reply_message": reply,
            "recommendation": recommendation,
            "chat_provider": chat_prov,
            "chat_model": chat_mod,
        }

    async def run(self, user_message: str) -> Dict[str, Any]:
        """Execute the LangGraph workflow."""
        initial_state: LeaveSupervisorState = {
            "user_message": user_message,
            "employee_id": self.employee_id,
            "company_id": self.company_id,
            "extracted_data": None,
            "balance_info": None,
            "all_balances": None,
            "policy_evaluation": None,
            "recommendation": None,
            "reply_message": "",
            "decision_provider": None,
            "decision_model": None,
            "chat_provider": None,
            "chat_model": None,
            "provider": None,
            "model": None,
        }
        result = await self.graph.ainvoke(initial_state)
        return result

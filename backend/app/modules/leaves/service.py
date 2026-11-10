from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.communication import CommunicationEvent
from app.models.employee import Employee
from app.models.leave import Approval, LeaveBalance, LeavePolicy, LeaveRequest, LeaveRequestStatus
from app.models.user import User
from app.modules.agents.email_service import EmailNotificationDispatcher
from app.modules.agents.slack_service import SlackNotificationDispatcher
from app.schemas.leave import (
    LeaveActionRequest,
    LeaveBalanceResponse,
    LeavePolicyCreate,
    LeavePolicyResponse,
    LeaveRequestCreate,
    LeaveRequestResponse,
)


def calculate_working_days(start_date: date, end_date: date) -> Decimal:
    """Calculate working days between two dates, excluding weekends (Saturday/Sunday)."""
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date cannot be prior to start date.",
        )
    current = start_date
    working_days = 0
    while current <= end_date:
        if current.weekday() < 5:  # 0 to 4 are Monday through Friday
            working_days += 1
        current += timedelta(days=1)
    return Decimal(str(working_days))


class LeaveService:
    def __init__(self, db: AsyncSession, company_id: uuid.UUID):
        self.db = db
        self.company_id = company_id

    # -------------------------------------------------------------------------
    # Policy Management
    # -------------------------------------------------------------------------
    async def create_policy(self, data: LeavePolicyCreate) -> LeavePolicyResponse:
        """Create a new leave policy category for the company."""
        policy = LeavePolicy(
            company_id=self.company_id,
            name=data.name.strip(),
            leave_type=data.leave_type.strip().lower(),
            days_allowed=data.days_allowed,
            carry_forward=data.carry_forward,
            max_carry_forward_days=data.max_carry_forward_days,
            requires_document=data.requires_document,
            min_days_notice=data.min_days_notice,
            max_consecutive_days=data.max_consecutive_days,
            applicable_after_months=data.applicable_after_months,
            is_paid=data.is_paid,
            approval_required=data.approval_required,
            policy_document_ref=data.policy_document_ref,
            is_active=True,
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return LeavePolicyResponse.model_validate(policy)

    async def list_policies(self, active_only: bool = True) -> List[LeavePolicyResponse]:
        """List leave policies for the company, auto-seeding defaults if empty."""
        stmt = select(LeavePolicy).where(LeavePolicy.company_id == self.company_id)
        if active_only:
            stmt = stmt.where(LeavePolicy.is_active == True)
        stmt = stmt.order_by(LeavePolicy.name)
        result = await self.db.execute(stmt)
        policies = result.scalars().all()

        if not policies and active_only:
            # Seed default starter policies for the company
            default_defs = [
                ("Annual Leave", "annual", 18, True, 6, True),
                ("Sick Leave", "sick", 12, False, 0, True),
                ("Casual Leave", "casual", 10, False, 0, True),
                ("Unpaid Leave", "unpaid", 30, False, 0, False),
            ]
            for name, l_type, days, cf, max_cf, is_p in default_defs:
                p = LeavePolicy(
                    company_id=self.company_id,
                    name=name,
                    leave_type=l_type,
                    days_allowed=days,
                    carry_forward=cf,
                    max_carry_forward_days=max_cf,
                    is_paid=is_p,
                    approval_required=True,
                    is_active=True,
                )
                self.db.add(p)
            await self.db.commit()

            result = await self.db.execute(stmt)
            policies = result.scalars().all()

        return [LeavePolicyResponse.model_validate(p) for p in policies]

    # -------------------------------------------------------------------------
    # Balance Ledger
    # -------------------------------------------------------------------------
    async def get_or_create_balances(
        self, employee_id: uuid.UUID, year: Optional[int] = None
    ) -> List[LeaveBalanceResponse]:
        """Fetch or initialize leave balances for an employee for the given calendar year."""
        current_year = year or date.today().year

        # 1. Fetch active policies
        policies_res = await self.db.execute(
            select(LeavePolicy).where(
                LeavePolicy.company_id == self.company_id,
                LeavePolicy.is_active == True,
            )
        )
        policies = policies_res.scalars().all()

        # 2. Fetch existing balances for this year
        balances_res = await self.db.execute(
            select(LeaveBalance)
            .options(selectinload(LeaveBalance.leave_policy))
            .where(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == current_year,
            )
        )
        existing_balances = {b.leave_policy_id: b for b in balances_res.scalars().all()}

        # 3. Create missing balances
        created_any = False
        for p in policies:
            if p.id not in existing_balances:
                new_bal = LeaveBalance(
                    employee_id=employee_id,
                    leave_policy_id=p.id,
                    year=current_year,
                    total_allocated=Decimal(str(p.days_allowed)),
                    used=Decimal("0.0"),
                    pending=Decimal("0.0"),
                    carried_forward=Decimal("0.0"),
                )
                self.db.add(new_bal)
                created_any = True

        if created_any:
            await self.db.commit()
            balances_res = await self.db.execute(
                select(LeaveBalance)
                .options(selectinload(LeaveBalance.leave_policy))
                .where(
                    LeaveBalance.employee_id == employee_id,
                    LeaveBalance.year == current_year,
                )
            )
            existing_balances = {b.leave_policy_id: b for b in balances_res.scalars().all()}

        return [
            LeaveBalanceResponse(
                id=b.id,
                employee_id=b.employee_id,
                leave_policy_id=b.leave_policy_id,
                year=b.year,
                total_allocated=b.total_allocated,
                used=b.used,
                pending=b.pending,
                carried_forward=b.carried_forward,
                available=b.available,
                policy_name=b.leave_policy.name if b.leave_policy else None,
                leave_type=b.leave_policy.leave_type if b.leave_policy else None,
                is_paid=b.leave_policy.is_paid if b.leave_policy else True,
            )
            for b in existing_balances.values()
        ]

    # -------------------------------------------------------------------------
    # Leave Application
    # -------------------------------------------------------------------------
    async def apply_leave(
        self, employee_id: uuid.UUID, data: LeaveRequestCreate
    ) -> LeaveRequestResponse:
        """Submit a new leave application with date validation and balance deduction."""
        # 1. Date calculation
        total_days = calculate_working_days(data.start_date, data.end_date)
        if total_days <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected date range contains no working days (e.g. falls entirely on a weekend).",
            )

        # 2. Check for overlapping requests
        overlap_stmt = select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_([LeaveRequestStatus.PENDING.value, LeaveRequestStatus.APPROVED.value]),
            and_(
                LeaveRequest.start_date <= data.end_date,
                LeaveRequest.end_date >= data.start_date,
            ),
        )
        overlap_res = await self.db.execute(overlap_stmt)
        conflicting = overlap_res.scalars().first()
        if conflicting:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Conflicting leave request exists ({conflicting.request_number}: "
                    f"{conflicting.start_date} to {conflicting.end_date}, status: {conflicting.status})."
                ),
            )

        # 3. Policy and Balance validation
        policy = await self.db.get(LeavePolicy, data.leave_policy_id)
        if not policy or policy.company_id != self.company_id or not policy.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected leave policy is invalid or inactive.",
            )

        current_year = data.start_date.year
        # Fetch or initialize employee balance
        balances = await self.get_or_create_balances(employee_id, year=current_year)
        balance_entry = next((b for b in balances if b.leave_policy_id == policy.id), None)

        if not balance_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leave balance ledger could not be located.",
            )

        if policy.is_paid and balance_entry.available < total_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient leave balance for {policy.name}. "
                    f"Available: {balance_entry.available} days, Requested: {total_days} days."
                ),
            )

        # 4. Generate unique request number
        random_suffix = uuid.uuid4().hex[:6].upper()
        req_number = f"LRQ-{current_year}-{random_suffix}"

        # 5. Create Leave Request
        req = LeaveRequest(
            request_number=req_number,
            employee_id=employee_id,
            leave_policy_id=policy.id,
            start_date=data.start_date,
            end_date=data.end_date,
            total_days=total_days,
            reason=data.reason,
            status=LeaveRequestStatus.PENDING.value,
            is_paid=policy.is_paid,
            source_channel="portal",
        )
        self.db.add(req)

        # 6. Increment pending in balance
        bal_record = await self.db.get(LeaveBalance, balance_entry.id)
        if bal_record:
            bal_record.pending += total_days

        # Fetch joined details for notification and clean response
        emp = await self.db.get(Employee, employee_id)
        applicant_name = f"{emp.first_name} {emp.last_name}" if emp else "An employee"

        # 7. Create in-app notification event for HR review queue
        notif = CommunicationEvent(
            channel="in_app",
            direction="outbound",
            company_id=self.company_id,
            employee_id=None,  # Broadcast to company HR/Admins
            leave_request_id=req.id,
            sender_identifier="system",
            subject=f"New Leave Application: {req.request_number}",
            body=f"{applicant_name} applied for {total_days} days of {policy.name} ({data.start_date} to {data.end_date}).",
            raw_payload={"request_number": req.request_number, "applicant": applicant_name, "days": str(total_days)},
            ai_extracted_data={},
            processing_status="unread",
        )
        self.db.add(notif)

        await self.db.commit()
        await self.db.refresh(req)

        return LeaveRequestResponse(
            id=req.id,
            request_number=req.request_number,
            employee_id=req.employee_id,
            employee_name=f"{emp.first_name} {emp.last_name}" if emp else None,
            employee_code=emp.employee_code if emp else None,
            leave_policy_id=req.leave_policy_id,
            policy_name=policy.name,
            leave_type=policy.leave_type,
            start_date=req.start_date,
            end_date=req.end_date,
            total_days=req.total_days,
            reason=req.reason,
            status=req.status,
            is_paid=req.is_paid,
            source_channel=req.source_channel,
            ai_recommendation=req.ai_recommendation or {},
            ai_confidence_score=req.ai_confidence_score,
            reviewed_by=req.reviewed_by,
            reviewed_at=req.reviewed_at,
            review_comment=req.review_comment,
            created_at=req.created_at,
        )

    # -------------------------------------------------------------------------
    # Approval / Rejection Workflow
    # -------------------------------------------------------------------------
    async def process_action(
        self,
        request_id: uuid.UUID,
        reviewer_user: User,
        action_data: LeaveActionRequest,
    ) -> LeaveRequestResponse:
        """Approve or reject a pending leave request, adjusting the ledger accordingly."""
        action_lower = action_data.action.lower().strip()
        if action_lower not in ["approve", "reject"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be either 'approve' or 'reject'.",
            )

        # Fetch request with row-level lock for optimistic concurrency control
        stmt = (
            select(LeaveRequest)
            .options(
                selectinload(LeaveRequest.employee),
                selectinload(LeaveRequest.leave_policy),
            )
            .where(LeaveRequest.id == request_id)
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        req = res.scalars().first()

        if not req or req.employee.company_id != self.company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found.",
            )

        if req.status != LeaveRequestStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: request has already been processed by another reviewer (Status: '{req.status}').",
            )

        # Locate employee balance entry for that policy and year
        bal_stmt = select(LeaveBalance).where(
            LeaveBalance.employee_id == req.employee_id,
            LeaveBalance.leave_policy_id == req.leave_policy_id,
            LeaveBalance.year == req.start_date.year,
        )
        bal_res = await self.db.execute(bal_stmt)
        bal = bal_res.scalars().first()

        now = datetime.now(timezone.utc)
        req.reviewed_by = reviewer_user.id
        req.reviewed_at = now
        req.review_comment = action_data.comment

        if action_lower == "approve":
            req.status = LeaveRequestStatus.APPROVED.value
            if action_data.waive_deduction:
                req.deduction_waived = True
            if bal:
                bal.pending = max(Decimal("0.0"), bal.pending - req.total_days)
                bal.used = bal.used + req.total_days
        else:
            req.status = LeaveRequestStatus.REJECTED.value
            if bal:
                bal.pending = max(Decimal("0.0"), bal.pending - req.total_days)

        # Audit trail
        approval_log = Approval(
            leave_request_id=req.id,
            approver_id=reviewer_user.id,
            action=action_lower,
            comment=action_data.comment,
            sequence_order=1,
        )
        self.db.add(approval_log)

        # Notify employee of decision
        decision_notif = CommunicationEvent(
            channel="in_app",
            direction="outbound",
            company_id=self.company_id,
            employee_id=req.employee_id,
            leave_request_id=req.id,
            sender_identifier="system",
            subject=f"Leave Request {req.status.capitalize()}: {req.request_number}",
            body=(
                f"Your request for {req.total_days} day(s) of "
                f"{req.leave_policy.name if req.leave_policy else 'Leave'} has been {req.status}. "
                f"{f'Note: {action_data.comment}' if action_data.comment else ''}"
            ).strip(),
            raw_payload={
                "request_number": req.request_number,
                "status": req.status,
                "action_by": reviewer_user.email,
                "comment": action_data.comment,
                "deduction_waived": getattr(req, "deduction_waived", False),
            },
            ai_extracted_data={},
            processing_status="unread",
        )
        self.db.add(decision_notif)

        # Dispatch transactional email with policy-driven salary deduction notice
        email_dispatcher = EmailNotificationDispatcher(self.db)
        policy_name = req.leave_policy.name if req.leave_policy else "Company Leave"
        await email_dispatcher.send_leave_decision_email(
            employee=req.employee,
            leave_req=req,
            policy_name=policy_name,
            reviewer_comment=action_data.comment,
        )

        # Dispatch outbound Slack Block Kit decision card
        slack_dispatcher = SlackNotificationDispatcher(self.db)
        await slack_dispatcher.send_leave_decision_webhook(
            employee=req.employee,
            leave_req=req,
            policy_name=policy_name,
            reviewer_comment=action_data.comment,
        )

        await self.db.commit()
        await self.db.refresh(req)

        return LeaveRequestResponse(
            id=req.id,
            request_number=req.request_number,
            employee_id=req.employee_id,
            employee_name=f"{req.employee.first_name} {req.employee.last_name}",
            employee_code=req.employee.employee_code,
            leave_policy_id=req.leave_policy_id,
            policy_name=req.leave_policy.name if req.leave_policy else None,
            leave_type=req.leave_policy.leave_type if req.leave_policy else None,
            start_date=req.start_date,
            end_date=req.end_date,
            total_days=req.total_days,
            reason=req.reason,
            status=req.status,
            is_paid=req.is_paid,
            deduction_waived=getattr(req, "deduction_waived", False),
            source_channel=req.source_channel,
            ai_recommendation=req.ai_recommendation or {},
            ai_confidence_score=req.ai_confidence_score,
            reviewed_by=req.reviewed_by,
            reviewed_at=req.reviewed_at,
            review_comment=req.review_comment,
            created_at=req.created_at,
        )

    # -------------------------------------------------------------------------
    # Listing Queries
    # -------------------------------------------------------------------------
    async def list_requests(
        self,
        employee_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[LeaveRequestResponse]:
        """List leave applications, optionally filtered by employee or status."""
        stmt = (
            select(LeaveRequest)
            .join(Employee, LeaveRequest.employee_id == Employee.id)
            .options(
                selectinload(LeaveRequest.employee),
                selectinload(LeaveRequest.leave_policy),
            )
            .where(Employee.company_id == self.company_id)
        )

        if employee_id:
            stmt = stmt.where(LeaveRequest.employee_id == employee_id)
        if status_filter:
            stmt = stmt.where(LeaveRequest.status == status_filter.lower().strip())

        stmt = stmt.order_by(LeaveRequest.created_at.desc())
        res = await self.db.execute(stmt)
        requests = res.scalars().all()

        return [
            LeaveRequestResponse(
                id=r.id,
                request_number=r.request_number,
                employee_id=r.employee_id,
                employee_name=f"{r.employee.first_name} {r.employee.last_name}" if r.employee else None,
                employee_code=r.employee.employee_code if r.employee else None,
                leave_policy_id=r.leave_policy_id,
                policy_name=r.leave_policy.name if r.leave_policy else None,
                leave_type=r.leave_policy.leave_type if r.leave_policy else None,
                start_date=r.start_date,
                end_date=r.end_date,
                total_days=r.total_days,
                reason=r.reason,
                status=r.status,
                is_paid=r.is_paid,
                source_channel=r.source_channel,
                ai_recommendation=r.ai_recommendation or {},
                ai_confidence_score=r.ai_confidence_score,
                reviewed_by=r.reviewed_by,
                reviewed_at=r.reviewed_at,
                review_comment=r.review_comment,
                created_at=r.created_at,
            )
            for r in requests
        ]

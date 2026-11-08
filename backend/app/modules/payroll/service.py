import calendar
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.employee import Employee
from app.models.leave import LeavePolicy, LeaveRequest, LeaveRequestStatus
from app.models.payroll import BatchStatus, PayrollBatch, PayrollItem
from app.models.user import User
from app.modules.notifications.service import NotificationService
from app.schemas.payroll import (
    PayrollBatchResponse,
    PayrollBatchSummary,
    PayrollItemResponse,
    PayslipView,
)


def get_month_working_days(year: int, month: int) -> Tuple[int, date, date]:
    """Calculate total Monday-Friday working days in a given calendar month."""
    _, num_days = calendar.monthrange(year, month)
    start_d = date(year, month, 1)
    end_d = date(year, month, num_days)

    working_days = 0
    cur = start_d
    while cur <= end_d:
        if cur.weekday() < 5:  # Mon to Fri
            working_days += 1
        cur += date.resolution
    return working_days, start_d, end_d


class PayrollService:
    def __init__(self, db: AsyncSession, company_id: uuid.UUID):
        self.db = db
        self.company_id = company_id

    # -------------------------------------------------------------------------
    # Batch Calculation Engine
    # -------------------------------------------------------------------------
    async def calculate_monthly_payroll(
        self,
        year: int,
        month: int,
        notes: Optional[str] = None,
    ) -> PayrollBatchResponse:
        """Deterministically calculate organization-wide payroll for a calendar month."""
        total_working_days, month_start, month_end = get_month_working_days(year, month)
        if total_working_days <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid period: working days cannot be zero.",
            )

        # 1. Check existing batch
        existing_stmt = (
            select(PayrollBatch)
            .options(selectinload(PayrollBatch.payroll_items).selectinload(PayrollItem.employee))
            .where(
                PayrollBatch.company_id == self.company_id,
                PayrollBatch.period_year == year,
                PayrollBatch.period_month == month,
            )
        )
        b_res = await self.db.execute(existing_stmt)
        batch = b_res.scalars().first()

        if batch and batch.status in [BatchStatus.APPROVED.value, BatchStatus.PAID.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payroll for {year}-{month:02d} is already locked ({batch.status}).",
            )

        # 2. Fetch all active employees
        emp_stmt = (
            select(Employee)
            .options(selectinload(Employee.department))
            .where(
                Employee.company_id == self.company_id,
                Employee.is_active == True,
            )
        )
        emp_res = await self.db.execute(emp_stmt)
        employees = emp_res.scalars().all()

        if not employees:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active employees found to process payroll.",
            )

        # Create or clear batch items
        if not batch:
            batch = PayrollBatch(
                company_id=self.company_id,
                period_year=year,
                period_month=month,
                status=BatchStatus.CALCULATING.value,
                notes=notes,
            )
            self.db.add(batch)
            await self.db.flush()
        else:
            # Clear previous draft items
            for item in list(batch.payroll_items):
                await self.db.delete(item)
            batch.status = BatchStatus.CALCULATING.value
            await self.db.flush()

        batch_gross = Decimal("0.00")
        batch_deductions = Decimal("0.00")
        batch_net = Decimal("0.00")
        created_items: List[PayrollItem] = []

        # 3. Calculate per-employee line items
        for emp in employees:
            raw_salary = Decimal(str(emp.salary_basic or "0.00"))
            # Standardize: If annual (> 20000), monthly is salary / 12, else monthly base
            if raw_salary > Decimal("20000"):
                monthly_base = (raw_salary / Decimal("12")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                monthly_base = raw_salary.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Sum fixed allowances
            allowances_dict = emp.salary_allowances or {}
            total_allowances = Decimal("0.00")
            for _, val in allowances_dict.items():
                try:
                    total_allowances += Decimal(str(val))
                except Exception:
                    pass
            total_allowances = total_allowances.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gross = (monthly_base + total_allowances).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Query approved leave requests in this calendar month
            leave_stmt = select(LeaveRequest).where(
                LeaveRequest.employee_id == emp.id,
                LeaveRequest.status == LeaveRequestStatus.APPROVED.value,
                and_(
                    LeaveRequest.start_date <= month_end,
                    LeaveRequest.end_date >= month_start,
                ),
            )
            l_res = await self.db.execute(leave_stmt)
            leaves = l_res.scalars().all()

            paid_days = Decimal("0.0")
            unpaid_days = Decimal("0.0")
            for req in leaves:
                if req.is_paid or getattr(req, "deduction_waived", False):
                    paid_days += Decimal(str(req.total_days))
                else:
                    unpaid_days += Decimal(str(req.total_days))

            # Deterministic Unpaid Leave Deduction Formula:
            # (Monthly Base / Working Days) * Unpaid Days
            per_day_rate = (monthly_base / Decimal(str(total_working_days))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            unpaid_deduction = (per_day_rate * unpaid_days).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Statutory Deductions:
            # 1. Income Tax / TDS (10% of gross)
            tax_withholding = (gross * Decimal("0.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            # 2. Provident Fund / Social Security (5% of monthly base)
            pf_contribution = (monthly_base * Decimal("0.05")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            statutory_breakdown = {
                "income_tax_tds": str(tax_withholding),
                "provident_fund": str(pf_contribution),
            }

            total_emp_deductions = (unpaid_deduction + tax_withholding + pf_contribution).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            net_salary = max(Decimal("0.00"), (gross - total_emp_deductions).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ))

            item = PayrollItem(
                batch_id=batch.id,
                employee_id=emp.id,
                basic_salary=monthly_base,
                total_allowances=total_allowances,
                allowances_breakdown=allowances_dict,
                gross_salary=gross,
                paid_leave_days=paid_days,
                unpaid_leave_days=unpaid_days,
                unpaid_leave_deduction=unpaid_deduction,
                attendance_days=Decimal(str(total_working_days)) - unpaid_days,
                attendance_adjustment=Decimal("0.00"),
                bonus=Decimal("0.00"),
                other_deductions=Decimal("0.00"),
                statutory_deductions=statutory_breakdown,
                total_deductions=total_emp_deductions,
                net_salary=net_salary,
                status="calculated",
            )
            self.db.add(item)
            created_items.append(item)

            batch_gross += gross
            batch_deductions += total_emp_deductions
            batch_net += net_salary

        # 4. Finalize batch
        batch.total_gross = batch_gross
        batch.total_deductions = batch_deductions
        batch.total_net = batch_net
        batch.employee_count = len(created_items)
        batch.status = BatchStatus.CALCULATED.value

        await self.db.commit()
        await self.db.refresh(batch)

        return await self.get_batch_detail(batch.id)

    # -------------------------------------------------------------------------
    # Batch Approvals
    # -------------------------------------------------------------------------
    async def approve_batch(self, batch_id: uuid.UUID, reviewer_user: User) -> PayrollBatchResponse:
        """Approve and lock a calculated payroll batch."""
        batch = await self.db.get(PayrollBatch, batch_id)
        if not batch or batch.company_id != self.company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll batch not found.",
            )

        if batch.status not in [BatchStatus.CALCULATED.value, BatchStatus.DRAFT.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve batch with status '{batch.status}'.",
            )

        now = datetime.now(timezone.utc)
        batch.status = BatchStatus.APPROVED.value
        batch.approved_by = reviewer_user.id
        batch.approved_at = now

        # Update item statuses
        items_stmt = select(PayrollItem).where(PayrollItem.batch_id == batch.id)
        i_res = await self.db.execute(items_stmt)
        items = i_res.scalars().all()
        for itm in items:
            itm.status = "approved"

        # Dispatch In-App Notification
        notif_service = NotificationService(self.db)
        await notif_service.create_notification(
            employee_id=None,
            subject=f"Payroll Batch Approved: {batch.period_year}-{batch.period_month:02d}",
            body=f"Monthly payroll of ${batch.total_net:,.2f} USD for {batch.employee_count} employees has been verified and approved.",
            raw_payload={"batch_id": str(batch.id), "total_net": str(batch.total_net)},
        )

        await self.db.commit()
        await self.db.refresh(batch)
        return await self.get_batch_detail(batch.id)

    # -------------------------------------------------------------------------
    # Listing & Details
    # -------------------------------------------------------------------------
    async def list_batches(self) -> List[PayrollBatchSummary]:
        """List all historical payroll batches for the company."""
        stmt = (
            select(PayrollBatch)
            .where(PayrollBatch.company_id == self.company_id)
            .order_by(desc(PayrollBatch.period_year), desc(PayrollBatch.period_month))
        )
        res = await self.db.execute(stmt)
        batches = res.scalars().all()
        return [PayrollBatchSummary.model_validate(b) for b in batches]

    async def get_batch_detail(self, batch_id: uuid.UUID) -> PayrollBatchResponse:
        """Fetch full payroll batch details with employee item lines."""
        stmt = (
            select(PayrollBatch)
            .options(
                selectinload(PayrollBatch.payroll_items).selectinload(PayrollItem.employee).selectinload(Employee.department)
            )
            .where(
                PayrollBatch.id == batch_id,
                PayrollBatch.company_id == self.company_id,
            )
        )
        res = await self.db.execute(stmt)
        batch = res.scalars().first()

        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payroll batch not found.",
            )

        items_resp: List[PayrollItemResponse] = []
        for itm in batch.payroll_items:
            emp = itm.employee
            dept_name = emp.department.name if emp and emp.department else None
            emp_name = f"{emp.first_name} {emp.last_name}" if emp else "Employee"
            emp_code = emp.employee_code if emp else ""
            paypal = emp.paypal_email if emp else None

            items_resp.append(
                PayrollItemResponse(
                    id=itm.id,
                    batch_id=itm.batch_id,
                    employee_id=itm.employee_id,
                    employee_name=emp_name,
                    employee_code=emp_code,
                    department_name=dept_name,
                    paypal_email=paypal,
                    basic_salary=itm.basic_salary,
                    total_allowances=itm.total_allowances,
                    allowances_breakdown=itm.allowances_breakdown or {},
                    gross_salary=itm.gross_salary,
                    paid_leave_days=itm.paid_leave_days,
                    unpaid_leave_days=itm.unpaid_leave_days,
                    unpaid_leave_deduction=itm.unpaid_leave_deduction,
                    attendance_days=itm.attendance_days,
                    attendance_adjustment=itm.attendance_adjustment,
                    bonus=itm.bonus,
                    other_deductions=itm.other_deductions,
                    statutory_deductions=itm.statutory_deductions or {},
                    total_deductions=itm.total_deductions,
                    net_salary=itm.net_salary,
                    status=itm.status,
                    created_at=itm.created_at,
                )
            )

        return PayrollBatchResponse(
            id=batch.id,
            company_id=batch.company_id,
            period_year=batch.period_year,
            period_month=batch.period_month,
            status=batch.status,
            total_gross=batch.total_gross,
            total_deductions=batch.total_deductions,
            total_net=batch.total_net,
            employee_count=batch.employee_count,
            approved_by=batch.approved_by,
            approved_at=batch.approved_at,
            notes=batch.notes,
            items=items_resp,
            created_at=batch.created_at,
        )

    # -------------------------------------------------------------------------
    # Payslips
    # -------------------------------------------------------------------------
    async def get_payslip(self, item_id: uuid.UUID) -> PayslipView:
        """Generate a complete itemized payslip view for an employee."""
        stmt = (
            select(PayrollItem)
            .options(
                selectinload(PayrollItem.payroll_batch),
                selectinload(PayrollItem.employee).selectinload(Employee.department),
            )
            .where(PayrollItem.id == item_id)
        )
        res = await self.db.execute(stmt)
        item = res.scalars().first()

        if not item or item.payroll_batch.company_id != self.company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payslip record not found.",
            )

        emp = item.employee
        batch = item.payroll_batch
        dept_name = emp.department.name if emp and emp.department else "General"

        return PayslipView(
            payroll_item_id=item.id,
            batch_period=f"{batch.period_year}-{batch.period_month:02d}",
            employee_name=f"{emp.first_name} {emp.last_name}",
            employee_code=emp.employee_code,
            department=dept_name,
            designation=emp.designation or "Team Member",
            paypal_email=emp.paypal_email,
            basic_salary=item.basic_salary,
            allowances=item.allowances_breakdown or {},
            gross_earnings=item.gross_salary,
            unpaid_leave_days=item.unpaid_leave_days,
            unpaid_leave_deduction=item.unpaid_leave_deduction,
            statutory_deductions=item.statutory_deductions or {},
            total_deductions=item.total_deductions,
            net_payable=item.net_salary,
            currency="USD",
            generation_date=datetime.now(timezone.utc),
        )

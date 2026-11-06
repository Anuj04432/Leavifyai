from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_roles
from app.models.user import User, UserRole
from app.modules.payroll.service import PayrollService
from app.schemas.payroll import (
    PayrollBatchAction,
    PayrollBatchCreate,
    PayrollBatchResponse,
    PayrollBatchSummary,
    PayslipView,
)

router = APIRouter(prefix="/payroll", tags=["Payroll"])


payroll_access_guard = require_permission(
    "can_run_payroll",
    fallback_roles=[
        UserRole.CEO.value,
        UserRole.SUPER_ADMIN.value,
        UserRole.FINANCE_MANAGER.value,
        UserRole.IR_MANAGER.value,
        UserRole.HR.value,
        "hr_manager",
    ],
)


@router.post(
    "/batches",
    response_model=PayrollBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate or recalculate organization payroll for a calendar month",
)
async def calculate_payroll_batch(
    payload: PayrollBatchCreate,
    current_user: User = Depends(payroll_access_guard),
    db: AsyncSession = Depends(get_db),
):
    service = PayrollService(db, current_user.company_id)
    return await service.calculate_monthly_payroll(
        year=payload.period_year,
        month=payload.period_month,
        notes=payload.notes,
    )


@router.get(
    "/batches",
    response_model=List[PayrollBatchSummary],
    summary="List all historical payroll batches",
)
async def list_payroll_batches(
    current_user: User = Depends(payroll_access_guard),
    db: AsyncSession = Depends(get_db),
):
    service = PayrollService(db, current_user.company_id)
    return await service.list_batches()


@router.get(
    "/batches/{batch_id}",
    response_model=PayrollBatchResponse,
    summary="Get complete itemized payroll batch details",
)
async def get_payroll_batch_detail(
    batch_id: uuid.UUID,
    current_user: User = Depends(payroll_access_guard),
    db: AsyncSession = Depends(get_db),
):
    service = PayrollService(db, current_user.company_id)
    return await service.get_batch_detail(batch_id)


@router.patch(
    "/batches/{batch_id}/approve",
    response_model=PayrollBatchResponse,
    summary="Approve and lock a calculated payroll batch",
)
async def approve_payroll_batch(
    batch_id: uuid.UUID,
    current_user: User = Depends(payroll_access_guard),
    db: AsyncSession = Depends(get_db),
):
    service = PayrollService(db, current_user.company_id)
    return await service.approve_batch(batch_id, current_user)


@router.get(
    "/payslips/{item_id}",
    response_model=PayslipView,
    summary="View itemized employee payslip",
)
async def view_payslip(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PayrollService(db, current_user.company_id)
    return await service.get_payslip(item_id)

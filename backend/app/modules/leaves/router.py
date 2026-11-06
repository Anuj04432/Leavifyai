from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_roles
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.modules.leaves.service import LeaveService
from app.schemas.leave import (
    LeaveActionRequest,
    LeaveBalanceResponse,
    LeavePolicyCreate,
    LeavePolicyResponse,
    LeaveRequestCreate,
    LeaveRequestResponse,
)

router = APIRouter(prefix="/leaves", tags=["Leaves"])


async def _get_current_employee(user: User, db: AsyncSession) -> Optional[Employee]:
    """Helper to resolve the employee profile belonging to the current user."""
    stmt = select(Employee).where(Employee.user_id == user.id)
    res = await db.execute(stmt)
    return res.scalars().first()


# -----------------------------------------------------------------------------
# Leave Policies
# -----------------------------------------------------------------------------
@router.get(
    "/policies",
    response_model=List[LeavePolicyResponse],
    summary="List active leave policies for current company",
)
async def list_policies(
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveService(db, current_user.company_id)
    return await service.list_policies(active_only=active_only)


@router.post(
    "/policies",
    response_model=LeavePolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new leave policy (HR/Admin)",
)
async def create_policy(
    data: LeavePolicyCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.HR.value])),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveService(db, current_user.company_id)
    return await service.create_policy(data)


# -----------------------------------------------------------------------------
# Leave Balances
# -----------------------------------------------------------------------------
@router.get(
    "/balances",
    response_model=List[LeaveBalanceResponse],
    summary="Fetch current leave balances ledger",
)
async def get_leave_balances(
    employee_id: Optional[uuid.UUID] = Query(None, description="Optional employee UUID for HR/Admin"),
    year: Optional[int] = Query(None, description="Calendar year"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveService(db, current_user.company_id)

    target_emp_id = employee_id
    if not target_emp_id:
        emp = await _get_current_employee(current_user, db)
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No linked employee profile found for the active user account.",
            )
        target_emp_id = emp.id

    return await service.get_or_create_balances(target_emp_id, year=year)


# -----------------------------------------------------------------------------
# Leave Requests
# -----------------------------------------------------------------------------
@router.post(
    "/requests",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new leave application",
)
async def apply_leave(
    data: LeaveRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_current_employee(current_user, db)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found. Cannot submit leave request.",
        )

    service = LeaveService(db, current_user.company_id)
    return await service.apply_leave(emp.id, data)


@router.get(
    "/requests",
    response_model=List[LeaveRequestResponse],
    summary="List leave applications with optional filters",
)
async def list_leave_requests(
    employee_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveService(db, current_user.company_id)

    # Regular employees only see their own requests unless they have approval capability
    can_view_all = (
        current_user.role in [UserRole.CEO.value, UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value, UserRole.HR.value, "hr_manager"]
        or bool((current_user.permissions or {}).get("can_approve_leaves", False))
    )
    if not can_view_all:
        emp = await _get_current_employee(current_user, db)
        if not emp:
            return []
        employee_id = emp.id

    return await service.list_requests(employee_id=employee_id, status_filter=status_filter)


@router.patch(
    "/requests/{request_id}/action",
    response_model=LeaveRequestResponse,
    summary="Approve or reject a leave request (HR/Manager/Admin/Authorized Personnel)",
)
async def action_leave_request(
    request_id: uuid.UUID,
    action_data: LeaveActionRequest,
    current_user: User = Depends(
        require_permission(
            "can_approve_leaves",
            fallback_roles=[UserRole.ADMIN.value, UserRole.HR.value, "hr_manager", UserRole.MANAGER.value],
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    service = LeaveService(db, current_user.company_id)
    return await service.process_action(request_id, current_user, action_data)

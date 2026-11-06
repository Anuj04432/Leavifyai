from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_roles
from app.models.company import Department
from app.models.user import User, UserRole
from app.schemas.department import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
)

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new department in the company",
)
async def create_department(
    data: DepartmentCreateRequest,
    current_user: User = Depends(
        require_permission(
            "can_manage_roster",
            fallback_roles=[UserRole.ADMIN.value, UserRole.HR.value, "hr_manager"],
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    # Check if department with same name exists in company
    existing_query = select(Department).where(
        Department.company_id == current_user.company_id,
        Department.name.ilike(data.name.strip()),
    )
    existing = (await db.execute(existing_query)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Department with name '{data.name}' already exists in your organization",
        )

    dept = Department(
        company_id=current_user.company_id,
        name=data.name.strip(),
        head_id=data.head_id,
        is_active=True,
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.get(
    "/",
    response_model=List[DepartmentResponse],
    summary="List all company departments",
)
async def list_departments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Department)
        .where(Department.company_id == current_user.company_id, Department.is_active == True)
        .order_by(Department.name.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/{id}",
    response_model=DepartmentResponse,
    summary="Get department details by ID",
)
async def get_department(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Department).where(
        Department.id == id,
        Department.company_id == current_user.company_id,
    )
    dept = (await db.execute(query)).scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return dept


@router.put(
    "/{id}",
    response_model=DepartmentResponse,
    summary="Update department details",
)
async def update_department(
    id: uuid.UUID,
    data: DepartmentUpdateRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.HR.value])),
    db: AsyncSession = Depends(get_db),
):
    query = select(Department).where(
        Department.id == id,
        Department.company_id == current_user.company_id,
    )
    dept = (await db.execute(query)).scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    if data.name is not None:
        dept.name = data.name.strip()
    if data.head_id is not None:
        dept.head_id = data.head_id
    if data.is_active is not None:
        dept.is_active = data.is_active

    await db.commit()
    await db.refresh(dept)
    return dept


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate department",
)
async def delete_department(
    id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.HR.value])),
    db: AsyncSession = Depends(get_db),
):
    query = select(Department).where(
        Department.id == id,
        Department.company_id == current_user.company_id,
    )
    dept = (await db.execute(query)).scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    dept.is_active = False
    await db.commit()
    return None

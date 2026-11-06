from typing import Optional
import uuid
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User, UserRole
from app.modules.employees.service import EmployeeService
from app.schemas.employee import (
    AnalyzeImportResponse,
    EmployeeCreateRequest,
    EmployeeImportResult,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdateRequest,
)

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post(
    "/",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an employee manually",
)
async def create_employee(
    data: EmployeeCreateRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.HR.value])),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db, current_user.company_id)
    return await service.create_employee(data)


@router.get(
    "/",
    response_model=EmployeeListResponse,
    summary="List paginated employees with search and department filtering",
)
async def list_employees(
    search: Optional[str] = Query(None, description="Search by name, email, employee code, or title"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department UUID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    status: Optional[str] = Query(None, description="Filter by active status string ('true'/'false')"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if is_active is None and status is not None and status.strip() != "":
        if status.strip().lower() == "true":
            is_active = True
        elif status.strip().lower() == "false":
            is_active = False

    service = EmployeeService(db, current_user.company_id)
    return await service.list_employees(
        search=search,
        department_id=department_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{id}",
    response_model=EmployeeResponse,
    summary="Get single employee profile by ID",
)
async def get_employee(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db, current_user.company_id)
    return await service.get_employee(id)


@router.put(
    "/{id}",
    response_model=EmployeeResponse,
    summary="Update an employee profile",
)
async def update_employee(
    id: uuid.UUID,
    data: EmployeeUpdateRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.HR.value])),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db, current_user.company_id)
    return await service.update_employee(id, data)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate an employee",
)
async def delete_employee(
    id: uuid.UUID,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.HR.value])),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db, current_user.company_id)
    await service.delete_employee(id)
    return None


@router.post(
    "/analyze-import",
    response_model=AnalyzeImportResponse,
    summary="AI pre-flight analysis of employee dataset columns and missing fields",
)
async def analyze_import(
    file: UploadFile = File(..., description="CSV or Excel (.xlsx) file to inspect"),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.HR.value])),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db, current_user.company_id)
    return await service.analyze_import_file(file)


@router.post(
    "/import",
    response_model=EmployeeImportResult,
    summary="Bulk import employees via CSV or Excel file",
)
async def import_employees(
    file: UploadFile = File(..., description="CSV or Excel (.xlsx) file with employee roster"),
    auto_generate_missing: bool = Query(True, description="Auto-generate missing corporate email and designation"),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.HR.value])),
    db: AsyncSession = Depends(get_db),
):
    service = EmployeeService(db, current_user.company_id)
    return await service.import_from_file(file, auto_generate_missing=auto_generate_missing)

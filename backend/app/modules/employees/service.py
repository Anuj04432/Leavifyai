import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import io
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException, UploadFile, status
import pandas as pd
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.security import get_password_hash
from app.models.company import Department
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.employee import (
    EmployeeCreateRequest,
    EmployeeImportResult,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdateRequest,
    ImportErrorDetail,
)


class EmployeeService:
    def __init__(self, db: AsyncSession, company_id: uuid.UUID):
        self.db = db
        self.company_id = company_id

    def _to_response(self, emp: Employee) -> EmployeeResponse:
        dept_name = emp.department.name if emp.department else None
        mgr_name = (
            f"{emp.reporting_manager.first_name} {emp.reporting_manager.last_name}"
            if emp.reporting_manager
            else None
        )
        return EmployeeResponse(
            id=emp.id,
            user_id=emp.user_id,
            company_id=emp.company_id,
            employee_code=emp.employee_code,
            first_name=emp.first_name,
            last_name=emp.last_name,
            email=emp.email,
            phone=emp.phone,
            designation=emp.designation,
            department_id=emp.department_id,
            department_name=dept_name,
            reporting_manager_id=emp.reporting_manager_id,
            reporting_manager_name=mgr_name,
            date_of_joining=emp.date_of_joining,
            date_of_exit=emp.date_of_exit,
            employment_type=emp.employment_type,
            salary_basic=emp.salary_basic,
            salary_allowances=emp.salary_allowances or {},
            paypal_email=emp.paypal_email,
            is_active=emp.is_active,
            created_at=emp.created_at,
            updated_at=emp.updated_at,
        )

    async def create_employee(self, data: EmployeeCreateRequest) -> EmployeeResponse:
        """Provisions a new employee record and associated user login."""
        # 1. Check email uniqueness in company
        email_clean = data.email.lower().strip()
        existing_emp = (
            await self.db.execute(
                select(Employee).where(
                    Employee.company_id == self.company_id,
                    Employee.email == email_clean,
                )
            )
        ).scalar_one_or_none()
        if existing_emp:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An employee with email '{email_clean}' already exists in your organization",
            )

        # 2. Check employee_code uniqueness
        code = data.employee_code.strip() if data.employee_code else f"EMP-{uuid.uuid4().hex[:6].upper()}"
        existing_code = (
            await self.db.execute(
                select(Employee).where(
                    Employee.company_id == self.company_id,
                    Employee.employee_code == code,
                )
            )
        ).scalar_one_or_none()
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Employee code '{code}' is already assigned to another employee",
            )

        # 3. Check or create User entity
        user = (
            await self.db.execute(select(User).where(User.email == email_clean))
        ).scalar_one_or_none()

        if not user:
            raw_password = data.initial_password or f"Welcome@{uuid.uuid4().hex[:4]}"
            user = User(
                email=email_clean,
                password_hash=get_password_hash(raw_password),
                role=UserRole.EMPLOYEE.value,
                company_id=self.company_id,
                is_active=True,
            )
            self.db.add(user)
            await self.db.flush()

        # 4. Create Employee record
        employee = Employee(
            user_id=user.id,
            company_id=self.company_id,
            employee_code=code,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            email=email_clean,
            phone=data.phone.strip() if data.phone else None,
            designation=data.designation.strip() if data.designation else None,
            department_id=data.department_id,
            reporting_manager_id=data.reporting_manager_id,
            date_of_joining=data.date_of_joining,
            employment_type=data.employment_type,
            salary_basic=data.salary_basic,
            salary_allowances=data.salary_allowances,
            bank_account_info=data.bank_account_info,
            paypal_email=data.paypal_email,
            is_active=True,
        )
        self.db.add(employee)
        await self.db.commit()

        # Re-query with eager loads
        return await self.get_employee(employee.id)

    async def get_employee(self, employee_id: uuid.UUID) -> EmployeeResponse:
        """Retrieves a single employee by ID."""
        query = (
            select(Employee)
            .options(
                selectinload(Employee.department),
                selectinload(Employee.reporting_manager),
            )
            .where(Employee.id == employee_id, Employee.company_id == self.company_id)
        )
        emp = (await self.db.execute(query)).scalar_one_or_none()
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return self._to_response(emp)

    async def list_employees(
        self,
        search: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> EmployeeListResponse:
        """Returns paginated, searchable list of employees."""
        query = (
            select(Employee)
            .options(
                selectinload(Employee.department),
                selectinload(Employee.reporting_manager),
            )
            .where(Employee.company_id == self.company_id)
        )

        if is_active is not None:
            query = query.where(Employee.is_active == is_active)

        if department_id:
            query = query.where(Employee.department_id == department_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Employee.first_name.ilike(term),
                    Employee.last_name.ilike(term),
                    Employee.email.ilike(term),
                    Employee.employee_code.ilike(term),
                    Employee.designation.ilike(term),
                )
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Apply pagination and sorting
        query = (
            query.order_by(Employee.last_name.asc(), Employee.first_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db.execute(query)).scalars().all()

        return EmployeeListResponse(
            items=[self._to_response(emp) for emp in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_employee(self, employee_id: uuid.UUID, data: EmployeeUpdateRequest) -> EmployeeResponse:
        """Updates an existing employee record."""
        query = select(Employee).where(Employee.id == employee_id, Employee.company_id == self.company_id)
        emp = (await self.db.execute(query)).scalar_one_or_none()
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(emp, field, value)

        await self.db.commit()
        return await self.get_employee(employee_id)

    async def delete_employee(self, employee_id: uuid.UUID) -> None:
        """Soft-deletes/deactivates an employee."""
        query = select(Employee).where(Employee.id == employee_id, Employee.company_id == self.company_id)
        emp = (await self.db.execute(query)).scalar_one_or_none()
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        emp.is_active = False
        emp.date_of_exit = date.today()

        # Deactivate user login as well
        user_query = select(User).where(User.id == emp.user_id)
        user = (await self.db.execute(user_query)).scalar_one_or_none()
        if user:
            user.is_active = False

        await self.db.commit()

    async def import_from_file(self, file: UploadFile) -> EmployeeImportResult:
        """Parses CSV or Excel file, validates fields, and provisions employees in batch."""
        filename = file.filename.lower() if file.filename else ""
        content = await file.read()

        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please upload a .csv or .xlsx file.",
            )

        # Standardize column headers
        df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

        required_cols = {"first_name", "last_name", "email"}
        missing = required_cols - set(df.columns)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required columns in header: {list(missing)}. Required: {list(required_cols)}",
            )

        # Fetch existing emails and codes in company to detect duplicates
        existing_emails_query = select(Employee.email).where(Employee.company_id == self.company_id)
        existing_emails = set((await self.db.execute(existing_emails_query)).scalars().all())

        existing_codes_query = select(Employee.employee_code).where(Employee.company_id == self.company_id)
        existing_codes = set((await self.db.execute(existing_codes_query)).scalars().all())

        # Map department names to IDs
        depts_query = select(Department).where(Department.company_id == self.company_id)
        depts = (await self.db.execute(depts_query)).scalars().all()
        dept_map = {d.name.lower(): d.id for d in depts}

        successful_count = 0
        errors: List[ImportErrorDetail] = []
        seen_file_emails = set()
        seen_file_codes = set()

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # 1-indexed, header is row 1

            # Validate Email
            email_val = str(row.get("email", "")).strip().lower()
            if not email_val or "@" not in email_val:
                errors.append(ImportErrorDetail(row=row_num, field="email", error="Invalid or missing email address"))
                continue

            if email_val in existing_emails:
                errors.append(ImportErrorDetail(row=row_num, field="email", error=f"Email '{email_val}' already exists in database"))
                continue

            if email_val in seen_file_emails:
                errors.append(ImportErrorDetail(row=row_num, field="email", error=f"Duplicate email '{email_val}' within file"))
                continue

            # Validate Employee Code
            raw_code = str(row.get("employee_code", "")).strip()
            if raw_code and raw_code != "nan":
                emp_code = raw_code
            else:
                emp_code = f"EMP-{uuid.uuid4().hex[:6].upper()}"

            if emp_code in existing_codes or emp_code in seen_file_codes:
                errors.append(ImportErrorDetail(row=row_num, field="employee_code", error=f"Employee code '{emp_code}' is duplicate"))
                continue

            # Validate Name
            first_name = str(row.get("first_name", "")).strip()
            last_name = str(row.get("last_name", "")).strip()
            if not first_name or first_name == "nan" or not last_name or last_name == "nan":
                errors.append(ImportErrorDetail(row=row_num, field="name", error="First and last name are required"))
                continue

            # Parse Salary
            raw_salary = row.get("salary_basic", 0)
            try:
                salary = Decimal(str(raw_salary)) if pd.notna(raw_salary) else Decimal("0.00")
            except (InvalidOperation, ValueError):
                salary = Decimal("0.00")

            # Match Department
            dept_id = None
            raw_dept = str(row.get("department", "")).strip().lower()
            if raw_dept and raw_dept != "nan":
                dept_id = dept_map.get(raw_dept)
                if not dept_id:
                    # Create department automatically if not exists
                    new_dept = Department(
                        company_id=self.company_id,
                        name=str(row.get("department", "")).strip(),
                        is_active=True,
                    )
                    self.db.add(new_dept)
                    await self.db.flush()
                    dept_id = new_dept.id
                    dept_map[raw_dept] = dept_id

            # Parse Joining Date
            raw_date = row.get("date_of_joining")
            if pd.notna(raw_date):
                try:
                    join_date = pd.to_datetime(raw_date).date()
                except Exception:
                    join_date = date.today()
            else:
                join_date = date.today()

            # Create User Account
            user = (
                await self.db.execute(select(User).where(User.email == email_val))
            ).scalar_one_or_none()

            if not user:
                default_password = get_password_hash(f"Welcome@{uuid.uuid4().hex[:4]}")
                user = User(
                    email=email_val,
                    password_hash=default_password,
                    role=UserRole.EMPLOYEE.value,
                    company_id=self.company_id,
                    is_active=True,
                )
                self.db.add(user)
                await self.db.flush()

            # Create Employee
            phone_val = str(row.get("phone", "")).strip()
            desig_val = str(row.get("designation", "")).strip()
            paypal_val = str(row.get("paypal_email", "")).strip()

            emp = Employee(
                user_id=user.id,
                company_id=self.company_id,
                employee_code=emp_code,
                first_name=first_name,
                last_name=last_name,
                email=email_val,
                phone=phone_val if phone_val and phone_val != "nan" else None,
                designation=desig_val if desig_val and desig_val != "nan" else None,
                department_id=dept_id,
                date_of_joining=join_date,
                employment_type=str(row.get("employment_type", "full_time")).strip(),
                salary_basic=salary,
                salary_allowances={},
                bank_account_info={},
                paypal_email=paypal_val if paypal_val and paypal_val != "nan" else None,
                is_active=True,
            )
            self.db.add(emp)

            seen_file_emails.add(email_val)
            seen_file_codes.add(emp_code)
            successful_count += 1

        await self.db.commit()

        return EmployeeImportResult(
            total_processed=len(df),
            successful_count=successful_count,
            failed_count=len(errors),
            errors=errors,
        )

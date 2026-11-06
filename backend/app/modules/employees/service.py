import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import io
import re
from typing import Any, Dict, List, Optional, Tuple
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
    AnalyzeImportResponse,
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
        """Deletes or soft-deactivates an employee record."""
        query = select(Employee).where(Employee.id == employee_id, Employee.company_id == self.company_id)
        emp = (await self.db.execute(query)).scalar_one_or_none()
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        # Try clean removal if no dependent financial records exist
        user_id = emp.user_id
        try:
            await self.db.delete(emp)
            if user_id:
                user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
                if user:
                    await self.db.delete(user)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            # If constrained by historical payroll or leaves, mark as inactive
            refreshed_emp = (await self.db.execute(query)).scalar_one_or_none()
            if refreshed_emp:
                refreshed_emp.is_active = False
                refreshed_emp.date_of_exit = date.today()
                if user_id:
                    user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
                    if user:
                        user.is_active = False
                await self.db.commit()

    async def analyze_import_file(self, file: UploadFile) -> AnalyzeImportResponse:
        """Inspects uploaded CSV or Excel file, discovers columns, and checks for missing workforce fields."""
        filename = file.filename.lower() if file.filename else ""
        content = await file.read()
        await file.seek(0)

        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format. Please upload a .csv or .xlsx file.",
            )

        raw_columns = [str(c).strip() for c in df.columns]
        norm_cols = [c.lower().replace(" ", "_") for c in raw_columns]

        column_aliases = {
            "employeeid": "employee_code",
            "empid": "employee_code",
            "emp_id": "employee_code",
            "id": "employee_code",
            "monthly_salary": "salary_basic",
            "salary": "salary_basic",
            "base_salary": "salary_basic",
            "ctc": "salary_basic",
            "dept": "department",
            "job_title": "designation",
            "role": "designation",
            "title": "designation",
            "email_id": "email",
            "work_email": "email",
            "mail": "email",
            "paypal": "paypal_email",
            "payout_email": "paypal_email",
            "name": "full_name",
            "employee_name": "full_name",
        }

        mapped_fields: Dict[str, str] = {}
        for orig, norm in zip(raw_columns, norm_cols):
            if norm in ("first_name", "last_name", "email", "salary_basic", "department", "designation", "employee_code", "paypal_email", "phone"):
                mapped_fields[orig] = norm
            elif norm in column_aliases:
                mapped_fields[orig] = column_aliases[norm]
            else:
                mapped_fields[orig] = norm

        # Determine missing fields
        values_mapped = set(mapped_fields.values())
        missing_fields: List[str] = []
        if "email" not in values_mapped:
            missing_fields.append("Corporate Email (email)")
        if "paypal_email" not in values_mapped:
            missing_fields.append("PayPal Payout Email (paypal_email)")
        if "designation" not in values_mapped:
            missing_fields.append("Designation / Role (designation)")
        if "salary_basic" not in values_mapped:
            missing_fields.append("Base Salary (salary_basic)")

        sample_preview = []
        for _, row in df.head(3).iterrows():
            item = {}
            for col in raw_columns[:7]:
                val = row[col]
                item[col] = None if pd.isna(val) else str(val)
            sample_preview.append(item)

        return AnalyzeImportResponse(
            total_rows=len(df),
            detected_columns=raw_columns,
            mapped_fields=mapped_fields,
            missing_fields=missing_fields,
            sample_preview=sample_preview,
        )

    async def import_from_file(self, file: UploadFile, auto_generate_missing: bool = True) -> EmployeeImportResult:
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

        # Smart column aliasing
        column_aliases = {
            "employeeid": "employee_code",
            "empid": "employee_code",
            "emp_id": "employee_code",
            "id": "employee_code",
            "monthly_salary": "salary_basic",
            "salary": "salary_basic",
            "base_salary": "salary_basic",
            "ctc": "salary_basic",
            "dept": "department",
            "job_title": "designation",
            "role": "designation",
            "title": "designation",
            "email_id": "email",
            "work_email": "email",
            "mail": "email",
            "paypal": "paypal_email",
            "payout_email": "paypal_email",
        }
        df.rename(columns={k: v for k, v in column_aliases.items() if k in df.columns and v not in df.columns}, inplace=True)

        # Check for minimum required identity (either first_name or a combined name column)
        has_name = "first_name" in df.columns or "name" in df.columns or "employee_name" in df.columns or "full_name" in df.columns
        if not has_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing employee name column in header. Expected 'first_name' & 'last_name' or a single 'Name' column.",
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

            # Validate / Resolve Employee Code
            raw_code = str(row.get("employee_code", "")).strip()
            if raw_code and raw_code != "nan":
                emp_code = raw_code
            else:
                emp_code = f"EMP-{row_num:03d}"

            if emp_code in existing_codes or emp_code in seen_file_codes:
                emp_code = f"{emp_code}-{uuid.uuid4().hex[:4].upper()}"

            # Validate / Resolve Name
            if "first_name" in df.columns:
                first_name = str(row.get("first_name", "")).strip()
                last_name = str(row.get("last_name", "")).strip()
            else:
                raw_name = str(row.get("name") or row.get("full_name") or row.get("employee_name") or "Employee").strip()
                parts = raw_name.split(maxsplit=1)
                first_name = parts[0] if parts else "Employee"
                last_name = parts[1] if len(parts) > 1 else ""

            if not first_name or first_name == "nan":
                first_name = "Employee"
            if not last_name or last_name == "nan":
                last_name = f"#{row_num}"

            # Validate / Resolve Email
            email_val = str(row.get("email", "")).strip().lower()
            if not email_val or email_val == "nan" or "@" not in email_val:
                clean_name = re.sub(r"[^a-zA-Z0-9]", "", first_name.lower()) or "emp"
                clean_code = re.sub(r"[^a-zA-Z0-9]", "", str(emp_code).lower()) or str(row_num)
                domain = "workforce.io" if auto_generate_missing else "company.local"
                email_val = f"{clean_name}.{clean_code}@{domain}"
                cnt = 1
                while email_val in existing_emails or email_val in seen_file_emails:
                    email_val = f"{clean_name}.{clean_code}.{cnt}@{domain}"
                    cnt += 1

            if email_val in existing_emails or email_val in seen_file_emails:
                domain = "workforce.io" if auto_generate_missing else "company.local"
                email_val = f"{email_val.split('@')[0]}.{uuid.uuid4().hex[:4]}@{domain}"

            # Parse Salary
            raw_salary = row.get("salary_basic", 0)
            try:
                salary = Decimal(str(int(float(raw_salary)))) if pd.notna(raw_salary) else (Decimal("50000.00") if auto_generate_missing else Decimal("0.00"))
            except (InvalidOperation, ValueError):
                salary = Decimal("50000.00") if auto_generate_missing else Decimal("0.00")

            # Match or Auto-Create Department
            dept_id = None
            raw_dept = str(row.get("department", "")).strip()
            if raw_dept and raw_dept != "nan":
                dept_key = raw_dept.lower()
                dept_id = dept_map.get(dept_key)
                if not dept_id:
                    new_dept = Department(
                        company_id=self.company_id,
                        name=raw_dept,
                        is_active=True,
                    )
                    self.db.add(new_dept)
                    await self.db.flush()
                    dept_id = new_dept.id
                    dept_map[dept_key] = dept_id

            # Parse Joining Date
            raw_date = row.get("date_of_joining")
            if pd.notna(raw_date):
                try:
                    join_date = pd.to_datetime(raw_date).date()
                except Exception:
                    join_date = date.today()
            else:
                join_date = date.today()

            # Resolve Designation
            raw_desig = str(row.get("designation", "")).strip()
            if raw_desig and raw_desig != "nan":
                desig_val = raw_desig
            elif auto_generate_missing:
                dept_name = raw_dept if raw_dept and raw_dept != "nan" else "Operations"
                exp = row.get("experience_years")
                try:
                    exp_num = float(exp) if pd.notna(exp) else 2
                except Exception:
                    exp_num = 2
                if exp_num >= 10:
                    desig_val = f"Senior {dept_name} Lead"
                elif exp_num >= 5:
                    desig_val = f"{dept_name} Specialist"
                else:
                    desig_val = f"{dept_name} Associate"
            else:
                desig_val = "Associate"

            # Resolve PayPal Email
            raw_paypal = str(row.get("paypal_email", "")).strip()
            if raw_paypal and raw_paypal != "nan" and "@" in raw_paypal:
                paypal_val = raw_paypal
            elif auto_generate_missing:
                paypal_val = email_val
            else:
                paypal_val = None

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

            emp = Employee(
                user_id=user.id,
                company_id=self.company_id,
                employee_code=emp_code,
                first_name=first_name,
                last_name=last_name,
                email=email_val,
                phone=phone_val if phone_val and phone_val != "nan" else None,
                designation=desig_val,
                department_id=dept_id,
                date_of_joining=join_date,
                employment_type=str(row.get("employment_type", "full_time")).strip(),
                salary_basic=salary,
                salary_allowances={},
                bank_account_info={},
                paypal_email=paypal_val,
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

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmployeeCreateRequest(BaseModel):
    """Payload to create a new employee profile and associated user account."""
    employee_code: Optional[str] = Field(None, max_length=50, description="Leave blank for auto-generated code")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = Field(None, description="Employee corporate email. If omitted, auto-generated from company domain")
    phone: Optional[str] = Field(None, max_length=20)
    designation: Optional[str] = Field(None, max_length=100)
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = Field(None, max_length=100, description="Name of new or existing department if department_id is omitted")
    reporting_manager_id: Optional[uuid.UUID] = None
    date_of_joining: date = Field(default_factory=date.today)
    employment_type: str = Field(default="full_time")
    salary_basic: Decimal = Field(default=Decimal("0.00"), ge=0)
    salary_allowances: Dict[str, Any] = Field(default_factory=dict)
    bank_account_info: Dict[str, Any] = Field(default_factory=dict)
    paypal_email: Optional[EmailStr] = None
    role: Optional[str] = Field("employee", description="System access role: ceo, admin, hr_manager, finance_manager, content_manager, manager, employee")
    permissions: Optional[Dict[str, bool]] = Field(default_factory=dict, description="Granular capability permissions")
    initial_password: Optional[str] = Field(None, min_length=8)


class EmployeeUpdateRequest(BaseModel):
    """Payload to update an existing employee."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    designation: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = Field(None, max_length=100, description="Name of new or existing department if department_id is omitted")
    reporting_manager_id: Optional[uuid.UUID] = None
    date_of_joining: Optional[date] = None
    date_of_exit: Optional[date] = None
    employment_type: Optional[str] = None
    salary_basic: Optional[Decimal] = Field(None, ge=0)
    salary_allowances: Optional[Dict[str, Any]] = None
    bank_account_info: Optional[Dict[str, Any]] = None
    paypal_email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, description="System access role: ceo, admin, hr_manager, finance_manager, content_manager, manager, employee")
    permissions: Optional[Dict[str, bool]] = Field(None, description="Granular capability permissions")
    is_active: Optional[bool] = None


class EmployeeResponse(BaseModel):
    """Complete employee profile view."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    designation: Optional[str] = None
    role: Optional[str] = "employee"
    permissions: Optional[Dict[str, bool]] = Field(default_factory=dict)
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    reporting_manager_id: Optional[uuid.UUID] = None
    reporting_manager_name: Optional[str] = None
    date_of_joining: date
    date_of_exit: Optional[date] = None
    employment_type: str
    salary_basic: Decimal
    salary_allowances: Dict[str, Any]
    paypal_email: Optional[str] = None
    is_active: bool
    initial_password: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    """Paginated employee list envelope."""
    items: List[EmployeeResponse]
    total: int
    page: int
    page_size: int


class ImportErrorDetail(BaseModel):
    row: int
    field: Optional[str] = None
    error: str


class EmployeeImportResult(BaseModel):
    """Result summary of bulk CSV / Excel upload."""
    total_processed: int
    successful_count: int
    failed_count: int
    errors: List[ImportErrorDetail]


class AnalyzeImportResponse(BaseModel):
    """AI analysis result of uploaded dataset columns, mappings, and missing fields."""
    total_rows: int
    detected_columns: List[str]
    mapped_fields: Dict[str, str]
    missing_fields: List[str]
    sample_preview: List[Dict[str, Any]]

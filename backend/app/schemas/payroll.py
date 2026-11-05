from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class PayrollBatchCreate(BaseModel):
    period_year: int = Field(..., ge=2020, le=2050)
    period_month: int = Field(..., ge=1, le=12)
    notes: Optional[str] = Field(None, max_length=500)


class PayrollBatchAction(BaseModel):
    action: str = Field(..., description="approve or recalculate")
    notes: Optional[str] = None


class PayrollItemResponse(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    department_name: Optional[str] = None
    paypal_email: Optional[str] = None

    basic_salary: Decimal
    total_allowances: Decimal
    allowances_breakdown: Dict[str, Any] = Field(default_factory=dict)
    gross_salary: Decimal

    paid_leave_days: Decimal
    unpaid_leave_days: Decimal
    unpaid_leave_deduction: Decimal

    attendance_days: Optional[Decimal] = None
    attendance_adjustment: Decimal = Decimal("0.00")
    bonus: Decimal = Decimal("0.00")
    other_deductions: Decimal = Decimal("0.00")
    statutory_deductions: Dict[str, Any] = Field(default_factory=dict)
    total_deductions: Decimal

    net_salary: Decimal
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PayrollBatchResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    period_year: int
    period_month: int
    status: str
    total_gross: Decimal
    total_deductions: Decimal
    total_net: Decimal
    employee_count: int
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[PayrollItemResponse] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class PayrollBatchSummary(BaseModel):
    id: uuid.UUID
    period_year: int
    period_month: int
    status: str
    total_gross: Decimal
    total_deductions: Decimal
    total_net: Decimal
    employee_count: int
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PayslipView(BaseModel):
    payroll_item_id: uuid.UUID
    batch_period: str
    employee_name: str
    employee_code: str
    department: str
    designation: str
    paypal_email: Optional[str]
    basic_salary: Decimal
    allowances: Dict[str, Any]
    gross_earnings: Decimal
    unpaid_leave_days: Decimal
    unpaid_leave_deduction: Decimal
    statutory_deductions: Dict[str, Any]
    total_deductions: Decimal
    net_payable: Decimal
    currency: str = "USD"
    generation_date: datetime

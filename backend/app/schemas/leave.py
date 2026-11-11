import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------
# Leave Policy Schemas
# ---------------------------------------------------------
class LeavePolicyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    leave_type: str = Field(..., max_length=30, description="annual, sick, casual, unpaid, etc.")
    days_allowed: int = Field(..., ge=0)
    carry_forward: bool = False
    max_carry_forward_days: int = Field(default=0, ge=0)
    requires_document: bool = False
    min_days_notice: int = Field(default=0, ge=0)
    max_consecutive_days: Optional[int] = Field(None, ge=1)
    applicable_after_months: int = Field(default=0, ge=0)
    is_paid: bool = True
    approval_required: bool = True
    policy_document_ref: Optional[str] = None


class LeavePolicyResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    leave_type: str
    days_allowed: int
    carry_forward: bool
    max_carry_forward_days: int
    requires_document: bool
    min_days_notice: int
    max_consecutive_days: Optional[int]
    applicable_after_months: int
    is_paid: bool
    approval_required: bool
    policy_document_ref: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------
# Leave Balance Schemas
# ---------------------------------------------------------
class LeaveBalanceResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    leave_policy_id: uuid.UUID
    year: int
    total_allocated: Decimal
    used: Decimal
    pending: Decimal
    carried_forward: Decimal
    available: Decimal
    policy_name: Optional[str] = None
    leave_type: Optional[str] = None
    is_paid: Optional[bool] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------
# Leave Request Schemas
# ---------------------------------------------------------
class LeaveRequestCreate(BaseModel):
    leave_policy_id: Optional[uuid.UUID] = None
    policy_id: Optional[uuid.UUID] = None
    start_date: date
    end_date: date
    reason: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def resolve_policy_id(self) -> "LeaveRequestCreate":
        if not self.leave_policy_id and self.policy_id:
            self.leave_policy_id = self.policy_id
        if not self.leave_policy_id:
            raise ValueError("leave_policy_id is required")
        return self


class LeaveActionRequest(BaseModel):
    action: str = Field(..., description="approve or reject")
    comment: Optional[str] = Field(None, max_length=500)
    waive_deduction: Optional[bool] = Field(default=False, description="Exempt unpaid leave from salary deduction (management override)")


class LeaveRequestResponse(BaseModel):
    id: uuid.UUID
    request_number: str
    employee_id: uuid.UUID
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    leave_policy_id: uuid.UUID
    policy_name: Optional[str] = None
    leave_type: Optional[str] = None
    start_date: date
    end_date: date
    total_days: Decimal
    reason: Optional[str]
    status: str
    is_paid: bool
    deduction_waived: bool = False
    source_channel: str
    ai_recommendation: Dict[str, Any] = Field(default_factory=dict)
    ai_confidence_score: Optional[Decimal] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

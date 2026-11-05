import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PayoutItemDetail(BaseModel):
    payroll_item_id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str
    recipient_email: str
    amount: Decimal
    currency: str = "USD"
    status: str
    payout_item_id: Optional[str] = None
    transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None


class DisbursePayrollRequest(BaseModel):
    batch_id: uuid.UUID
    email_subject: Optional[str] = "Your monthly salary has been disbursed via WorkforceAI"
    note: Optional[str] = "WorkforceAI Automated Payroll Disbursement"


class DisbursePayrollResponse(BaseModel):
    batch_id: uuid.UUID
    status: str
    total_amount: Decimal
    currency: str = "USD"
    item_count: int
    payout_batch_id: str
    sender_batch_id: str
    disbursed_at: datetime
    items: List[PayoutItemDetail] = []


class PaymentStatusResponse(BaseModel):
    batch_id: uuid.UUID
    batch_status: str
    payout_batch_id: Optional[str] = None
    sender_batch_id: Optional[str] = None
    total_items: int
    successful_items: int
    pending_items: int
    failed_items: int
    items: List[PayoutItemDetail] = []


class PayPalWebhookEvent(BaseModel):
    id: str
    event_type: str
    resource_type: str
    summary: Optional[str] = None
    resource: Dict[str, Any] = Field(default_factory=dict)

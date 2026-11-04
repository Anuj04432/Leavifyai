from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, Field


class DepartmentCreateRequest(BaseModel):
    """Payload to create a new department."""
    name: str = Field(..., min_length=2, max_length=100, description="Department name (e.g. Engineering, Sales)")
    head_id: Optional[uuid.UUID] = Field(None, description="Optional Head of Department employee ID")


class DepartmentUpdateRequest(BaseModel):
    """Payload to update an existing department."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    head_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    """Department presentation view."""
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    head_id: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

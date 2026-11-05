from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: uuid.UUID
    channel: str = "in_app"
    direction: str = "outbound"
    employee_id: Optional[uuid.UUID] = None
    leave_request_id: Optional[uuid.UUID] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    processing_status: str = Field(default="unread", description="unread or read")
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationMarkReadRequest(BaseModel):
    notification_ids: Optional[list[uuid.UUID]] = None

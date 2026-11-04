from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    """Payload for registering a new user / company administrator."""
    company_name: str = Field(..., min_length=2, max_length=255, description="Name of the company/organization")
    company_slug: Optional[str] = Field(None, max_length=100, description="Optional custom unique URL slug")
    email: EmailStr = Field(..., description="Corporate email address")
    password: str = Field(..., min_length=8, max_length=100, description="Account password (min 8 characters)")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.ADMIN, description="Initial role for registering user")


class UserLoginRequest(BaseModel):
    """Payload for user sign in."""
    email: EmailStr = Field(..., description="Registered user email")
    password: str = Field(..., min_length=1, description="Account password")


class TokenResponse(BaseModel):
    """JWT response returned after successful authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    """Payload for refreshing an expired access token."""
    refresh_token: str = Field(..., description="Valid refresh token")


class UserResponse(BaseModel):
    """Public user identity and profile view."""
    id: uuid.UUID
    email: str
    role: str
    company_id: uuid.UUID
    employee_id: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

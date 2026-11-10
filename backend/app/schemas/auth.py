from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class SendOtpRequest(BaseModel):
    """Payload to request an email verification OTP code."""
    email: EmailStr = Field(..., description="Organization Gmail address to verify")


class VerifyOtpRequest(BaseModel):
    """Payload to verify an email OTP code."""
    email: EmailStr = Field(..., description="Organization Gmail address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")


class CompanyCeoRegisterRequest(BaseModel):
    """Payload for registering a new company with CEO account and verified organization email."""
    company_name: str = Field(..., min_length=2, max_length=255, description="Official company / organization name")
    organization_email: EmailStr = Field(..., description="Verified official organization Gmail for inbound ingestion")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification code sent to organization_email")
    company_domain: Optional[str] = Field(None, max_length=100, description="Optional custom corporate domain (defaults to <slug>.com)")
    ceo_first_name: str = Field(..., min_length=1, max_length=100, description="CEO given name")
    ceo_last_name: str = Field(..., min_length=1, max_length=100, description="CEO family name")
    password: str = Field(..., min_length=8, max_length=100, description="Account password (min 8 characters)")


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


class UserResponse(BaseModel):
    """Public user identity and profile view."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    company_id: uuid.UUID
    employee_id: Optional[uuid.UUID] = None
    is_active: bool
    permissions: dict = Field(default_factory=dict)
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    organization_email: Optional[str] = None
    personal_email: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT response returned after successful authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional[UserResponse] = None


class TokenRefreshRequest(BaseModel):
    """Payload for refreshing an expired access token."""
    refresh_token: str = Field(..., description="Valid refresh token")


class ForgotPasswordRequest(BaseModel):
    """Payload to request password reset OTP code."""
    email: EmailStr = Field(..., description="Registered account email address")


class ResetPasswordRequest(BaseModel):
    """Payload to verify OTP and set a new password."""
    email: EmailStr = Field(..., description="Registered account email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password (min 8 characters)")

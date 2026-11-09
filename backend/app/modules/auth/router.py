from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.modules.auth.service import AuthService
from app.schemas.auth import (
    CompanyCeoRegisterRequest,
    SendOtpRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyOtpRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/send-org-otp",
    summary="Dispatch 6-digit OTP verification code to organization Gmail address",
)
async def send_organization_otp(
    data: SendOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.send_organization_otp(data.email)


@router.post(
    "/verify-org-otp",
    summary="Verify 6-digit OTP code for organization Gmail address",
)
async def verify_organization_otp(
    data: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.verify_organization_otp(data.email, data.otp)


@router.post(
    "/register-company",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new company and CEO account with verified organization email",
)
async def register_company(
    data: CompanyCeoRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.register_company_ceo(data)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new company and admin account",
)
async def register(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and receive JWT access & refresh tokens",
)
async def login(
    data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an expired access token using a valid refresh token",
)
async def refresh_token(
    data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.refresh_token(data.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    employee_id = current_user.employee.id if current_user.employee else None
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        company_id=current_user.company_id,
        employee_id=employee_id,
        is_active=current_user.is_active,
        permissions=current_user.permissions or {},
        company_name=current_user.company.name if current_user.company else None,
        company_domain=current_user.company.domain if current_user.company else None,
        organization_email=current_user.company.organization_email if current_user.company else None,
        personal_email=current_user.employee.personal_email if current_user.employee else None,
        created_at=current_user.created_at,
    )

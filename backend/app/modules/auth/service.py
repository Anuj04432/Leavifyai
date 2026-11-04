from datetime import datetime, timezone
import re
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.config import get_settings
from app.models.company import Company
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

settings = get_settings()


def slugify(text: str) -> str:
    """Generates an alphanumeric URL-safe slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserRegisterRequest) -> UserResponse:
        """Registers a new company, creates the primary administrator, and provisions linked employee record."""
        # 1. Check if user email already exists
        existing_user_query = select(User).where(User.email == data.email.lower())
        existing_user = (await self.db.execute(existing_user_query)).scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{data.email}' already exists",
            )

        # 2. Create or find company
        slug = data.company_slug or slugify(data.company_name)
        existing_company_query = select(Company).where(Company.slug == slug)
        existing_company = (await self.db.execute(existing_company_query)).scalar_one_or_none()

        if existing_company:
            # If company slug taken, append unique hex
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        company = Company(
            name=data.company_name,
            slug=slug,
            settings={},
            is_active=True,
        )
        self.db.add(company)
        await self.db.flush()

        # 3. Create user account
        hashed_password = get_password_hash(data.password)
        user = User(
            email=data.email.lower(),
            password_hash=hashed_password,
            role=data.role.value if isinstance(data.role, UserRole) else str(data.role),
            company_id=company.id,
            is_active=True,
            last_login_at=datetime.now(timezone.utc),
        )
        self.db.add(user)
        await self.db.flush()

        # 4. Create linked employee profile
        employee_code = f"EMP-{uuid.uuid4().hex[:6].upper()}"
        employee = Employee(
            user_id=user.id,
            company_id=company.id,
            employee_code=employee_code,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email.lower(),
            date_of_joining=datetime.now(timezone.utc).date(),
            employment_type="full_time",
            salary_basic=0,
            salary_allowances={},
            bank_account_info={},
            is_active=True,
        )
        self.db.add(employee)
        await self.db.commit()
        await self.db.refresh(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            company_id=user.company_id,
            employee_id=employee.id,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    async def login(self, data: UserLoginRequest) -> TokenResponse:
        """Authenticates user credentials and generates access & refresh JWT tokens."""
        query = (
            select(User)
            .options(selectinload(User.employee))
            .where(User.email == data.email.lower())
        )
        user = (await self.db.execute(query)).scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated. Please contact your HR administrator.",
            )

        # Update last login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()

        employee_id = user.employee.id if user.employee else None

        access_token = create_access_token(
            subject=user.id,
            role=user.role,
            company_id=user.company_id,
            employee_id=employee_id,
        )
        refresh_token = create_refresh_token(subject=user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        """Generates a new access token using a valid, non-expired refresh token."""
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type: refresh token required",
                )
            user_id = uuid.UUID(payload.get("sub"))
        except (ValueError, Exception) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired refresh token: {str(e)}",
            )

        query = (
            select(User)
            .options(selectinload(User.employee))
            .where(User.id == user_id, User.is_active == True)
        )
        user = (await self.db.execute(query)).scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with token no longer exists or is inactive",
            )

        employee_id = user.employee.id if user.employee else None

        new_access_token = create_access_token(
            subject=user.id,
            role=user.role,
            company_id=user.company_id,
            employee_id=employee_id,
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

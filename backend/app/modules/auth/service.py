from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import re
import secrets
import smtplib
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select
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
from app.models.verification import EmailVerificationCode
from app.schemas.auth import (
    CompanyCeoRegisterRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

logger = logging.getLogger("workforceai.auth.service")
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

    async def send_organization_otp(self, email: str) -> dict:
        """Generates a 6-digit OTP code, stores it, and sends it via SMTP to the organization Gmail."""
        clean_email = email.strip().lower()
        if not clean_email or "@" not in clean_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid email address is required.",
            )

        # Rate limit: Check if a code was issued in the last 45 seconds
        recent_cutoff = datetime.now(timezone.utc) - timedelta(seconds=45)
        recent_stmt = (
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == clean_email,
                EmailVerificationCode.created_at > recent_cutoff,
            )
        )
        recent_code = (await self.db.execute(recent_stmt)).scalars().first()
        if recent_code:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Verification code already sent recently. Please wait 45 seconds.",
            )

        # Generate 6-digit numeric OTP
        otp_code = f"{secrets.randbelow(900000) + 100000}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        record = EmailVerificationCode(
            email=clean_email,
            code_hash=otp_code,
            purpose="org_registration",
            expires_at=expires_at,
            is_verified=False,
        )
        self.db.add(record)
        await self.db.commit()

        # Send email via SMTP
        smtp_user = (os.getenv("SMTP_USER") or settings.SMTP_USER).strip()
        smtp_password = (os.getenv("SMTP_PASSWORD") or settings.SMTP_PASSWORD).strip()
        smtp_host = os.getenv("SMTP_HOST") or settings.SMTP_HOST
        smtp_port = int(os.getenv("SMTP_PORT") or settings.SMTP_PORT)
        from_email = os.getenv("SMTP_FROM_EMAIL") or settings.SMTP_FROM_EMAIL or smtp_user or "notifications@workforceai.io"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0c0a09; color: #FAF8F5; padding: 24px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #141210; border: 1px solid #292524; border-radius: 12px; padding: 32px; }}
            .brand {{ display: inline-block; background: #ea580c; color: #ffffff; padding: 6px 14px; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 20px; }}
            h2 {{ color: #FAF8F5; margin-top: 0; font-size: 20px; }}
            p {{ color: #a8a29e; font-size: 14px; line-height: 1.6; }}
            .code-box {{ background: #0c0a09; border: 1px solid #ea580c; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0; }}
            .code {{ font-family: monospace; font-size: 32px; letter-spacing: 8px; font-weight: 800; color: #f97316; }}
            .footer {{ border-top: 1px solid #292524; margin-top: 24px; padding-top: 16px; font-size: 11px; color: #78716c; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">Leavify.ai</div>
            <h2>Verify Your Organization Email</h2>
            <p>Use the 6-digit verification code below to verify your organization's official email address for Leavify.ai:</p>
            <div class="code-box">
              <span class="code">{otp_code}</span>
            </div>
            <p>This verification code expires in <strong>10 minutes</strong>. If you did not request this verification, you can safely ignore this email.</p>
            <div class="footer">
              Automated verification dispatch from Leavify.ai Autonomous Enterprise Engine.
            </div>
          </div>
        </body>
        </html>
        """

        if smtp_user and smtp_password:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"Leavify.ai Verification Code: {otp_code}"
                msg["From"] = f"Leavify.ai Security <{from_email}>"
                msg["To"] = clean_email
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(from_email, [clean_email], msg.as_string())
                logger.info(f"Verification OTP code sent to {clean_email}")
            except Exception as ex:
                logger.warning(f"SMTP OTP dispatch failed: {ex}. Simulated OTP: {otp_code}")
        else:
            logger.info(f"[SIMULATED_OTP] Organization {clean_email} OTP code: {otp_code}")

        return {
            "success": True,
            "message": f"Verification code sent to {clean_email}",
            # In sandbox / fallback mode, if smtp is unreachable, code can also be verified
        }

    async def verify_organization_otp(self, email: str, otp: str) -> dict:
        """Verifies an OTP code for an organization email."""
        clean_email = email.strip().lower()
        clean_code = otp.strip()

        stmt = (
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == clean_email,
                EmailVerificationCode.purpose == "org_registration",
                EmailVerificationCode.expires_at > datetime.now(timezone.utc),
            )
            .order_by(EmailVerificationCode.created_at.desc())
        )
        record = (await self.db.execute(stmt)).scalars().first()
        if not record or record.code_hash != clean_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code.",
            )

        record.is_verified = True
        await self.db.commit()
        return {"verified": True, "message": "Email verified successfully."}

    async def register_company_ceo(self, data: CompanyCeoRegisterRequest) -> TokenResponse:
        """Registers a new company, creates the CEO account with Antigravity corporate email, and provisions CEO profile."""
        # 1. Verify OTP for organization_email
        clean_org_email = data.organization_email.strip().lower()
        clean_otp = data.otp.strip()

        otp_stmt = (
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == clean_org_email,
                EmailVerificationCode.purpose == "org_registration",
                EmailVerificationCode.expires_at > datetime.now(timezone.utc),
            )
            .order_by(EmailVerificationCode.created_at.desc())
        )
        ver_record = (await self.db.execute(otp_stmt)).scalars().first()
        if not ver_record or (ver_record.code_hash != clean_otp and not ver_record.is_verified):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code for organization email.",
            )
        ver_record.is_verified = True

        # 2. Generate alphanumeric unique company slug
        base_slug = re.sub(r"[^a-z0-9]", "", data.company_name.lower())
        if not base_slug:
            base_slug = f"org{uuid.uuid4().hex[:6]}"

        slug = base_slug
        existing_company_query = select(Company).where(Company.slug == slug)
        existing_company = (await self.db.execute(existing_company_query)).scalar_one_or_none()
        if existing_company:
            slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

        # Corporate organization domain (defaults to <slug>.com or user-provided domain)
        if data.company_domain and data.company_domain.strip():
            domain = data.company_domain.strip().lower().replace("@", "").strip()
        else:
            domain = f"{slug}.com"

        # 3. Derive unique corporate email
        clean_first = re.sub(r"[^a-z0-9]", "", data.ceo_first_name.lower()) or "ceo"
        clean_last = re.sub(r"[^a-z0-9]", "", data.ceo_last_name.lower()) or "exec"
        corporate_email = f"{clean_first}.{clean_last}@{domain}"

        existing_user_query = select(User).where(User.email == corporate_email)
        existing_user = (await self.db.execute(existing_user_query)).scalar_one_or_none()
        if existing_user:
            corporate_email = f"{clean_first}.{clean_last}{uuid.uuid4().hex[:4]}@{domain}"

        # 4. Create Company with verified organization email
        company = Company(
            name=data.company_name.strip(),
            slug=slug,
            domain=domain,
            organization_email=clean_org_email,
            is_email_verified=True,
            settings={"organization_email": clean_org_email},
            is_active=True,
        )
        self.db.add(company)
        await self.db.flush()

        # 5. Create CEO User with full capability set
        ceo_permissions = {
            "can_handle_paypal": True,
            "can_run_payroll": True,
            "can_approve_leaves": True,
            "can_manage_roster": True,
            "can_manage_policies": True,
        }
        hashed_password = get_password_hash(data.password)
        user = User(
            email=corporate_email,
            password_hash=hashed_password,
            role=UserRole.CEO.value,
            company_id=company.id,
            is_active=True,
            permissions=ceo_permissions,
            last_login_at=datetime.now(timezone.utc),
        )
        self.db.add(user)
        await self.db.flush()

        # 6. Create linked Employee profile for CEO with personal_email set to organization_email
        employee = Employee(
            user_id=user.id,
            company_id=company.id,
            employee_code="EMP-001",
            first_name=data.ceo_first_name.strip(),
            last_name=data.ceo_last_name.strip(),
            email=corporate_email,
            personal_email=clean_org_email,
            date_of_joining=datetime.now(timezone.utc).date(),
            employment_type="full_time",
            department_id=None,
            designation="Chief Executive Officer",
            salary_basic=0,
            salary_allowances={},
            bank_account_info={},
            is_active=True,
        )
        self.db.add(employee)
        await self.db.commit()
        await self.db.refresh(user)

        # 7. Issue access & refresh tokens
        access_token = create_access_token(
            subject=user.id,
            role=user.role,
            company_id=user.company_id,
            employee_id=employee.id,
        )
        refresh_token = create_refresh_token(subject=user.id)

        user_info = UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            company_id=user.company_id,
            employee_id=employee.id,
            is_active=user.is_active,
            permissions=user.permissions or {},
            company_name=company.name,
            company_domain=company.domain,
            organization_email=company.organization_email,
            personal_email=employee.personal_email,
            created_at=user.created_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info,
        )

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
        clean_email = data.email.lower().strip()
        query = (
            select(User)
            .outerjoin(Employee, Employee.user_id == User.id)
            .options(selectinload(User.employee), selectinload(User.company))
            .where(
                (User.email == clean_email)
                | (Employee.personal_email == clean_email)
            )
        )
        user = (await self.db.execute(query)).scalars().first()

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

        user_info = UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            company_id=user.company_id,
            employee_id=employee_id,
            is_active=user.is_active,
            permissions=user.permissions or {},
            company_name=user.company.name if user.company else None,
            company_domain=user.company.domain if user.company else None,
            organization_email=user.company.organization_email if user.company else None,
            personal_email=user.employee.personal_email if user.employee else None,
            created_at=user.created_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_info,
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

    async def request_password_reset(self, email: str) -> dict:
        """Sends a 6-digit password reset OTP code to the registered user."""
        clean_email = email.strip().lower()

        # Check if user exists with this email or as employee personal email
        user_query = select(User).where(func.lower(User.email) == clean_email)
        user = (await self.db.execute(user_query)).scalar_one_or_none()
        if not user:
            emp_query = select(Employee).options(selectinload(Employee.user)).where(func.lower(Employee.personal_email) == clean_email)
            emp = (await self.db.execute(emp_query)).scalar_one_or_none()
            if emp and emp.user:
                user = emp.user

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active account registered with this email address.",
            )

        # Rate limit: reject if code requested in last 45 seconds
        time_limit = datetime.now(timezone.utc) - timedelta(seconds=45)
        stmt_check = select(EmailVerificationCode).where(
            EmailVerificationCode.email == clean_email,
            EmailVerificationCode.purpose == "forgot_password",
            EmailVerificationCode.created_at >= time_limit,
        )
        recent_code = (await self.db.execute(stmt_check)).scalar_one_or_none()
        if recent_code:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Password reset code already sent recently. Please wait 45 seconds.",
            )

        otp_code = f"{secrets.randbelow(900000) + 100000}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        record = EmailVerificationCode(
            email=clean_email,
            code_hash=otp_code,
            purpose="forgot_password",
            expires_at=expires_at,
            is_verified=False,
        )
        self.db.add(record)
        await self.db.commit()

        # Send email via SMTP
        smtp_user = (os.getenv("SMTP_USER") or settings.SMTP_USER).strip()
        smtp_password = (os.getenv("SMTP_PASSWORD") or settings.SMTP_PASSWORD).strip()
        smtp_host = os.getenv("SMTP_HOST") or settings.SMTP_HOST
        smtp_port = int(os.getenv("SMTP_PORT") or settings.SMTP_PORT)
        from_email = os.getenv("SMTP_FROM_EMAIL") or settings.SMTP_FROM_EMAIL or smtp_user or "security@leavify.ai"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0c0a09; color: #FAF8F5; padding: 24px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #141210; border: 1px solid #292524; border-radius: 12px; padding: 32px; }}
            .brand {{ display: inline-block; background: #ea580c; color: #ffffff; padding: 6px 14px; border-radius: 8px; font-weight: 700; font-size: 14px; margin-bottom: 20px; }}
            h2 {{ color: #FAF8F5; margin-top: 0; font-size: 20px; }}
            p {{ color: #a8a29e; font-size: 14px; line-height: 1.6; }}
            .code-box {{ background: #0c0a09; border: 1px solid #ea580c; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0; }}
            .code {{ font-family: monospace; font-size: 32px; letter-spacing: 8px; font-weight: 800; color: #f97316; }}
            .footer {{ border-top: 1px solid #292524; margin-top: 24px; padding-top: 16px; font-size: 11px; color: #78716c; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="brand">Leavify.ai</div>
            <h2>Password Reset Code</h2>
            <p>We received a request to reset your password for your Leavify.ai account. Use the 6-digit verification code below:</p>
            <div class="code-box">
              <span class="code">{otp_code}</span>
            </div>
            <p>This verification code expires in <strong>15 minutes</strong>. If you did not request a password reset, please secure your account immediately or ignore this email.</p>
            <div class="footer">
              Automated security dispatch from Leavify.ai Autonomous Workforce Platform.
            </div>
          </div>
        </body>
        </html>
        """

        if smtp_user and smtp_password:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"Leavify.ai Password Reset Code: {otp_code}"
                msg["From"] = f"Leavify.ai Security <{from_email}>"
                msg["To"] = clean_email
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(from_email, [clean_email], msg.as_string())
                logger.info(f"Password reset OTP sent to {clean_email}")
            except Exception as ex:
                logger.warning(f"SMTP reset dispatch failed: {ex}. Simulated OTP: {otp_code}")
        else:
            logger.info(f"[SIMULATED_OTP] Password reset for {clean_email}: {otp_code}")

        return {
            "success": True,
            "message": f"Password reset verification code sent to {clean_email}",
        }

    async def reset_password_with_otp(self, email: str, otp: str, new_password: str) -> dict:
        """Verifies OTP and resets the user's password."""
        clean_email = email.strip().lower()
        clean_code = otp.strip()

        # Verify OTP
        stmt = (
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == clean_email,
                EmailVerificationCode.code_hash == clean_code,
                EmailVerificationCode.purpose == "forgot_password",
                EmailVerificationCode.is_verified == False,
            )
            .order_by(EmailVerificationCode.created_at.desc())
        )
        record = (await self.db.execute(stmt)).scalar_one_or_none()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code or email address.",
            )

        now = datetime.now(timezone.utc)
        record_expires = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=timezone.utc)
        if record_expires < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Please request a new code.",
            )

        # Find user
        user_query = select(User).where(func.lower(User.email) == clean_email)
        user = (await self.db.execute(user_query)).scalar_one_or_none()
        if not user:
            emp_query = select(Employee).options(selectinload(Employee.user)).where(func.lower(Employee.personal_email) == clean_email)
            emp = (await self.db.execute(emp_query)).scalar_one_or_none()
            if emp and emp.user:
                user = emp.user

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found.",
            )

        # Update password
        user.password_hash = get_password_hash(new_password)
        record.is_verified = True
        await self.db.commit()

        logger.info(f"Password successfully reset for user: {user.email}")
        return {
            "success": True,
            "message": "Password reset successfully. You can now sign in with your new password.",
        }

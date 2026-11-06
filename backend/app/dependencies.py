from typing import List, Optional
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.security import decode_token
from app.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that extracts the JWT token, verifies its signature, and returns the User entity."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: access token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token subject missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = uuid.UUID(user_id_str)
    except (ValueError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user with linked employee profile
    query = (
        select(User)
        .options(selectinload(User.employee))
        .where(User.id == user_id, User.is_active == True)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def has_permission(user: User, permission_key: str) -> bool:
    """Checks if user has capability permission or is superuser (CEO, SUPER_ADMIN)."""
    if user.role in ["ceo", "super_admin"]:
        return True
    user_perms = user.permissions or {}
    return bool(user_perms.get(permission_key, False))


def require_roles(allowed_roles: List[str]):
    """Authorization factory that restricts endpoint access to specified roles."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # CEO and SUPER_ADMIN always have administrative access
        if current_user.role in ["ceo", "super_admin"]:
            return current_user
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {allowed_roles}. Your role: {current_user.role}",
            )
        return current_user

    return role_checker


def require_permission(permission_key: str, fallback_roles: Optional[List[str]] = None):
    """Authorization factory that checks granular capability permission or authorized roles."""
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if has_permission(current_user, permission_key):
            return current_user
        if fallback_roles and current_user.role in fallback_roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation not permitted. Requires capability '{permission_key}' or an authorized executive role.",
        )

    return permission_checker

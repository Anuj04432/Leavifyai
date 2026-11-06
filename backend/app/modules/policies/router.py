import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_roles
from app.models.leave import LeavePolicy
from app.models.user import User
from app.modules.policies.okf_service import okf_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/policies", tags=["Company Policies & OKF Knowledge"])


class PolicyUpdateRequest(BaseModel):
    markdown_content: str


@router.get(
    "/knowledge",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List all company policy documents (OKF format)",
)
async def list_policies(
    current_user: User = Depends(get_current_user),
):
    """Retrieve the company's active policy knowledge documents with YAML frontmatter."""
    return okf_service.list_policies()


@router.get(
    "/knowledge/{policy_code}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get policy document by code",
)
async def get_policy(
    policy_code: str,
    current_user: User = Depends(get_current_user),
):
    """Fetch single OKF policy document by code (e.g. POL-CAS-01)."""
    policy = okf_service.get_policy_by_code(policy_code)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with code '{policy_code}' not found",
        )
    return policy


@router.put(
    "/knowledge/{policy_code}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Update policy document markdown",
)
async def update_policy(
    policy_code: str,
    payload: PolicyUpdateRequest,
    current_user: User = Depends(
        require_permission(
            "can_manage_policies",
            fallback_roles=["super_admin", "admin", "hr", "hr_manager", "content_manager", "ceo"],
        )
    ),
):
    """Update company policy markdown rules."""
    try:
        updated = okf_service.update_policy_content(policy_code, payload.markdown_content)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update policy {policy_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save policy: {str(e)}",
        )


@router.post(
    "/knowledge/upload",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Upload new company leave policy document",
)
async def upload_policy(
    file: UploadFile = File(..., description="Markdown (.md) or text (.txt) policy document"),
    title: Optional[str] = Form(None),
    leave_type: Optional[str] = Form(None),
    annual_allowance: Optional[int] = Form(None),
    notice_period_days: Optional[int] = Form(None),
    max_consecutive_days: Optional[int] = Form(None),
    is_paid: Optional[bool] = Form(None),
    current_user: User = Depends(
        require_permission(
            "can_manage_policies",
            fallback_roles=["super_admin", "admin", "hr", "hr_manager", "content_manager", "ceo"],
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    """Upload custom company leave policy document (OKF format) and link to company leave policies."""
    try:
        content_bytes = await file.read()
        raw_text = content_bytes.decode("utf-8", errors="replace")

        meta = {}
        if title:
            meta["title"] = title
        if leave_type:
            meta["leave_type"] = leave_type.lower()
        if annual_allowance is not None:
            meta["annual_allowance"] = annual_allowance
        if notice_period_days is not None:
            meta["notice_period_days"] = notice_period_days
        if max_consecutive_days is not None:
            meta["max_consecutive_days"] = max_consecutive_days
        if is_paid is not None:
            meta["is_paid"] = is_paid

        saved_policy = okf_service.create_or_upload_policy(
            filename=file.filename or "custom_policy.md",
            content=raw_text,
            metadata=meta,
        )

        pol_leave_type = saved_policy.get("leave_type", "casual").lower()
        query = select(LeavePolicy).where(
            LeavePolicy.company_id == current_user.company_id,
            LeavePolicy.leave_type == pol_leave_type,
        )
        existing_pol = (await db.execute(query)).scalar_one_or_none()

        if existing_pol:
            existing_pol.name = saved_policy.get("title", existing_pol.name)
            existing_pol.days_allowed = saved_policy.get("annual_allowance", existing_pol.days_allowed)
            existing_pol.min_days_notice = saved_policy.get("notice_period_days", existing_pol.min_days_notice)
            existing_pol.max_consecutive_days = saved_policy.get("max_consecutive_days", existing_pol.max_consecutive_days)
            existing_pol.is_paid = saved_policy.get("is_paid", existing_pol.is_paid)
            existing_pol.is_active = True
        else:
            new_pol = LeavePolicy(
                company_id=current_user.company_id,
                name=saved_policy.get("title", f"{pol_leave_type.capitalize()} Leave"),
                leave_type=pol_leave_type,
                days_allowed=saved_policy.get("annual_allowance", 12),
                min_days_notice=saved_policy.get("notice_period_days", 1),
                max_consecutive_days=saved_policy.get("max_consecutive_days", 5),
                is_paid=saved_policy.get("is_paid", True),
                is_active=True,
            )
            db.add(new_pol)

        await db.commit()
        return saved_policy
    except Exception as e:
        logger.error(f"Failed to upload policy file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process policy upload: {str(e)}",
        )

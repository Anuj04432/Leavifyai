import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies import get_current_user, require_roles
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
    current_user: User = Depends(require_roles(["super_admin", "company_admin", "hr_manager"])),
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

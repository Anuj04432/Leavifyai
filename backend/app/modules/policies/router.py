import io
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
from app.modules.policies.rag_service import rag_service

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
    return okf_service.list_policies(company_id=current_user.company_id)


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
    policy = okf_service.get_policy_by_code(policy_code, company_id=current_user.company_id)
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
        updated = okf_service.update_policy_content(
            policy_code,
            payload.markdown_content,
            company_id=current_user.company_id,
        )
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
    file: UploadFile = File(..., description="PDF (.pdf), Markdown (.md), or text (.txt) policy document"),
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
    """Upload custom company leave policy document (PDF/OKF format) and link to company leave policies."""
    try:
        content_bytes = await file.read()
        filename_lower = (file.filename or "").lower()

        if filename_lower.endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(content_bytes))
                page_texts = []
                for p_idx, page in enumerate(reader.pages, start=1):
                    txt = page.extract_text() or ""
                    if txt.strip():
                        page_texts.append(f"## Page {p_idx}\n{txt.strip()}")
                raw_text = "\n\n".join(page_texts)
                if not raw_text.strip():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="The uploaded PDF contains no extractable text.",
                    )
            except HTTPException:
                raise
            except Exception as pdf_err:
                logger.error(f"Failed to extract text from PDF: {pdf_err}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to parse PDF document: {str(pdf_err)}",
                )
        else:
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
            company_id=current_user.company_id,
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

        # Index policy document into RAG knowledge base for deep semantic multi-page search
        try:
            await rag_service.index_document(
                db=db,
                company_id=current_user.company_id,
                policy_code=saved_policy.get("policy_code", "POL-GEN-01"),
                document_title=saved_policy.get("title", file.filename or "Company Policy"),
                markdown_content=raw_text,
                meta_info=saved_policy.get("metadata", {}),
            )
        except Exception as rag_err:
            logger.warning(f"RAG indexing warning on upload: {rag_err}")

        return saved_policy
    except Exception as e:
        logger.error(f"Failed to upload policy file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process policy upload: {str(e)}",
        )


@router.get(
    "/semantic-search",
    summary="Perform deep semantic RAG search across company policies and handbooks",
)
async def semantic_search_policies(
    query: str,
    top_k: int = 4,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve top-K semantic chunks from company documents and handbooks."""
    return await rag_service.search_knowledge(
        db=db,
        company_id=current_user.company_id,
        query=query,
        top_k=top_k,
    )

import logging
import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_role
from app.models.user import User
from app.modules.payments.service import payment_service
from app.schemas.payment import (
    DisbursePayrollRequest,
    DisbursePayrollResponse,
    PaymentStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["PayPal Payments & Payouts"])


@router.post(
    "/disburse-payroll/{batch_id}",
    response_model=DisbursePayrollResponse,
    status_code=status.HTTP_200_OK,
    summary="Disburse batch payroll via PayPal Sandbox",
)
async def disburse_payroll(
    batch_id: uuid.UUID,
    payload: DisbursePayrollRequest = None,
    current_user: User = Depends(require_role(["super_admin", "company_admin", "hr_manager"])),
    db: AsyncSession = Depends(get_db),
):
    """Execute automated PayPal batch payout for an approved payroll batch."""
    email_subj = payload.email_subject if payload and payload.email_subject else "WorkforceAI Monthly Salary Payout"
    email_note = payload.note if payload and payload.note else "Automated Salary Disbursement via PayPal"

    try:
        response = await payment_service.disburse_payroll_batch(
            db=db,
            batch_id=batch_id,
            company_id=current_user.company_id,
            email_subject=email_subj,
            note=email_note,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Payout disbursement failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PayPal payout disbursement failed: {str(e)}",
        )


@router.get(
    "/batch/{batch_id}/status",
    response_model=PaymentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get PayPal payout status for a batch",
)
async def get_batch_payout_status(
    batch_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Query itemized PayPal disbursement status for a payroll batch."""
    try:
        return await payment_service.get_batch_payment_status(
            db=db,
            batch_id=batch_id,
            company_id=current_user.company_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="PayPal Webhook event listener",
)
async def paypal_webhook(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """Receive and reconcile asynchronous PayPal event notifications."""
    event_type = payload.get("event_type", "UNKNOWN")
    logger.info(f"Received PayPal Webhook: {event_type}")
    return {"status": "received", "event_type": event_type}

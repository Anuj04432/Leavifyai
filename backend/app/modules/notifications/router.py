from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.employee import Employee
from app.models.user import User
from app.modules.notifications.service import NotificationService
from app.schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


async def _get_current_employee_id(user: User, db: AsyncSession) -> uuid.UUID | None:
    stmt = select(Employee.id).where(Employee.user_id == user.id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


@router.get(
    "/",
    response_model=List[NotificationResponse],
    summary="List recent in-app notifications for active user",
)
async def list_notifications(
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp_id = await _get_current_employee_id(current_user, db)
    service = NotificationService(db)
    return await service.list_notifications(employee_id=emp_id, limit=limit)


@router.patch(
    "/{notification_id}/read",
    summary="Mark single notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    success = await service.mark_as_read(notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    return {"status": "success", "message": "Notification marked as read"}


@router.post(
    "/read-all",
    summary="Mark all unread notifications as read",
)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    emp_id = await _get_current_employee_id(current_user, db)
    service = NotificationService(db)
    count = await service.mark_all_as_read(employee_id=emp_id)
    return {"status": "success", "marked_read": count}

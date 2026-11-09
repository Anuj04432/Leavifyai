from typing import List, Optional
import uuid
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import CommunicationEvent
from app.schemas.notification import NotificationResponse


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        company_id: Optional[uuid.UUID],
        employee_id: Optional[uuid.UUID],
        subject: str,
        body: str,
        leave_request_id: Optional[uuid.UUID] = None,
        raw_payload: Optional[dict] = None,
    ) -> CommunicationEvent:
        """Create a new in-app notification event."""
        event = CommunicationEvent(
            channel="in_app",
            direction="outbound",
            company_id=company_id,
            employee_id=employee_id,
            leave_request_id=leave_request_id,
            sender_identifier="system",
            subject=subject,
            body=body,
            raw_payload=raw_payload or {},
            ai_extracted_data={},
            processing_status="unread",
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def list_notifications(
        self,
        company_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
        limit: int = 30,
    ) -> List[NotificationResponse]:
        """Fetch latest in-app notifications strictly scoped to company and employee."""
        stmt = select(CommunicationEvent).where(CommunicationEvent.channel == "in_app")
        if company_id:
            stmt = stmt.where(CommunicationEvent.company_id == company_id)
        if employee_id:
            # Deliver employee's notifications or broadcasts (where employee_id is None)
            stmt = stmt.where(
                (CommunicationEvent.employee_id == employee_id)
                | (CommunicationEvent.employee_id.is_(None))
            )
        stmt = stmt.order_by(desc(CommunicationEvent.created_at)).limit(limit)

        result = await self.db.execute(stmt)
        events = result.scalars().all()
        return [NotificationResponse.model_validate(e) for e in events]

    async def mark_as_read(
        self,
        notification_id: uuid.UUID,
        company_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Mark a specific notification as read."""
        stmt = (
            update(CommunicationEvent)
            .where(CommunicationEvent.id == notification_id)
        )
        if company_id:
            stmt = stmt.where(CommunicationEvent.company_id == company_id)
        stmt = stmt.values(processing_status="read")
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    async def mark_all_as_read(
        self,
        company_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Mark all unread notifications as read."""
        stmt = (
            update(CommunicationEvent)
            .where(
                CommunicationEvent.channel == "in_app",
                CommunicationEvent.processing_status == "unread",
            )
        )
        if company_id:
            stmt = stmt.where(CommunicationEvent.company_id == company_id)
        if employee_id:
            stmt = stmt.where(
                (CommunicationEvent.employee_id == employee_id)
                | (CommunicationEvent.employee_id.is_(None))
            )
        stmt = stmt.values(processing_status="read")
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount

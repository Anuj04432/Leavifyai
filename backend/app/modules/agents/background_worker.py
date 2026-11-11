import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.company import Company
from app.modules.agents.communication_agent import CommunicationIngestionAgent

logger = logging.getLogger("leavify.agents.worker")


class InboxPollingWorker:
    """Autonomous Background Polling Worker.
    Continuously monitors external mailboxes (Gmail via IMAP) and communication channels
    in the background, parsing leave requests and notifying HR without manual scan triggers.
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self.last_poll_at: Optional[datetime] = None
        self.total_runs: int = 0
        self.total_processed: int = 0
        self.last_status: str = "initialized"
        self.is_running: bool = False

    def start(self):
        """Starts the background polling loop as an asyncio Task."""
        if self._task and not self._task.done():
            logger.info("InboxPollingWorker task is already active.")
            return

        self._stop_event.clear()
        self.is_running = True
        self.last_status = "running"
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("InboxPollingWorker background task launched successfully.")

    async def stop(self):
        """Gracefully halts the background polling loop."""
        if not self._task:
            return

        self.is_running = False
        self.last_status = "stopped"
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        logger.info("InboxPollingWorker background task stopped cleanly.")

    async def _poll_loop(self):
        """Main periodic polling execution loop."""
        settings = get_settings()
        interval = max(10, getattr(settings, "INBOX_POLL_INTERVAL_SECONDS", 60))
        logger.info(f"InboxPollingWorker active with poll interval: {interval}s")

        while not self._stop_event.is_set():
            try:
                await self.poll_now()
            except Exception as e:
                logger.warning(f"InboxPollingWorker iteration exception: {e}")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=float(interval))
            except asyncio.TimeoutError:
                pass

    async def poll_now(self) -> List[Dict[str, Any]]:
        """Executes a single poll sweep across all active organizations."""
        self.last_poll_at = datetime.now(timezone.utc)
        self.total_runs += 1
        all_processed: List[Dict[str, Any]] = []

        try:
            async with AsyncSessionLocal() as db:
                res = await db.execute(
                    select(Company.id).where(Company.is_active == True)
                )
                company_ids = res.scalars().all()

                agent = CommunicationIngestionAgent(db)
                if not agent.is_imap_configured:
                    self.last_status = "idle_no_imap_configured"
                    return []

                for cid in company_ids:
                    try:
                        processed = await agent.scan_gmail_inbox(cid)
                        all_processed.extend(processed)
                    except Exception as comp_err:
                        logger.warning(f"Error scanning inbox for company {cid}: {comp_err}")

            self.total_processed += len(all_processed)
            self.last_status = f"completed_last_poll ({len(all_processed)} new)"
            if all_processed:
                logger.info(f"InboxPollingWorker ingested {len(all_processed)} leave application(s).")
        except Exception as e:
            self.last_status = f"error: {str(e)[:100]}"
            logger.warning(f"InboxPollingWorker encountered poll error: {e}")

        return all_processed

    def get_status(self) -> Dict[str, Any]:
        """Returns runtime telemetry for UI status indicators."""
        settings = get_settings()
        return {
            "is_running": self.is_running,
            "last_status": self.last_status,
            "last_poll_at": self.last_poll_at.isoformat() if self.last_poll_at else None,
            "total_runs": self.total_runs,
            "total_processed": self.total_processed,
            "poll_interval_seconds": getattr(settings, "INBOX_POLL_INTERVAL_SECONDS", 60),
            "auto_poll_enabled": getattr(settings, "INBOX_AUTO_POLL_ENABLED", True),
        }


# Global Singleton Instance
inbox_worker = InboxPollingWorker()

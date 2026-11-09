from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import email
from email.header import decode_header
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.communication import CommunicationEvent
from app.models.employee import Employee
from app.models.leave import LeaveBalance, LeavePolicy, LeaveRequest, LeaveRequestStatus
from app.modules.agents.llm_client import MultiProviderLLMRouter
from app.modules.leaves.service import calculate_working_days

logger = logging.getLogger("workforceai.agents.communication")


class CommunicationIngestionAgent:
    """Autonomous Communication Ingestion Agent.
    Monitors, parses, and acts upon inbound emails (Gmail), Slack messages, and external
    channels using Agentic LLM comprehension to stage automated leave applications.
    """

    def __init__(self, db: AsyncSession, llm: Optional[MultiProviderLLMRouter] = None):
        self.db = db
        self.llm = llm or MultiProviderLLMRouter()
        settings = get_settings()
        self.imap_host = os.getenv("IMAP_HOST") or settings.IMAP_HOST
        self.imap_port = int(os.getenv("IMAP_PORT") or settings.IMAP_PORT)
        self.imap_user = (os.getenv("IMAP_USER") or settings.IMAP_USER or os.getenv("SMTP_USER") or settings.SMTP_USER).strip()
        self.imap_password = (os.getenv("IMAP_PASSWORD") or settings.IMAP_PASSWORD or os.getenv("SMTP_PASSWORD") or settings.SMTP_PASSWORD).strip()
        self.is_imap_configured = bool(self.imap_user and self.imap_password)

    async def parse_message_intent(self, sender: str, subject: str, body: str) -> Dict[str, Any]:
        """Extracts structured leave parameters from unstructured email/Slack text."""
        today = date.today().isoformat()
        instruction = (
            f"You are the WorkforceAI Inbound Communication Agent. Today's date is {today}.\n"
            "Analyze the incoming email/message. If it contains an employee requesting leave or time off, "
            "extract the structured details and return JSON with keys:\n"
            "- `is_leave_request`: true\n"
            "- `leave_type`: 'annual' | 'sick' | 'casual' | 'unpaid'\n"
            "- `start_date`: 'YYYY-MM-DD'\n"
            "- `end_date`: 'YYYY-MM-DD'\n"
            "- `reason`: string summary of reasons\n"
            "- `confidence`: float between 0.0 and 1.0\n\n"
            "If it is not a leave request, return: `{\"is_leave_request\": false, \"reason\": \"General message\", \"confidence\": 0.9}`.\n"
            "Return valid JSON only without markdown formatting."
        )
        content_prompt = f"From: {sender}\nSubject: {subject}\n\nBody:\n{body}"
        res, _, _ = await self.llm.generate_decision(instruction, content_prompt)

        try:
            cleaned = res.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            extracted = json.loads(cleaned)

            # Guardrails on dates
            if extracted.get("is_leave_request"):
                try:
                    date.fromisoformat(str(extracted.get("start_date")))
                    date.fromisoformat(str(extracted.get("end_date")))
                except Exception:
                    st = date.today() + timedelta(days=1)
                    extracted["start_date"] = st.isoformat()
                    extracted["end_date"] = st.isoformat()

                lt = str(extracted.get("leave_type", "casual")).lower()
                if "sick" in lt or "doctor" in lt or "medical" in lt:
                    extracted["leave_type"] = "sick"
                elif "annual" in lt or "vacation" in lt or "holiday" in lt:
                    extracted["leave_type"] = "annual"
                elif "unpaid" in lt:
                    extracted["leave_type"] = "unpaid"
                else:
                    extracted["leave_type"] = "casual"

            return extracted
        except Exception as e:
            logger.warning(f"Failed to parse inbound message: {e}")
            return {
                "is_leave_request": False,
                "reason": f"Parsing fallback: {subject}",
                "confidence": 0.5,
            }

    async def process_inbound_message(
        self,
        company_id: uuid.UUID,
        sender_identifier: str,
        subject: str,
        body: str,
        channel: str = "email",
    ) -> Dict[str, Any]:
        """Core workflow: Comprehend message -> Resolve employee & policy -> Stage Leave Request -> Notify HR."""
        parsed = await self.parse_message_intent(sender_identifier, subject, body)

        # 1. Log inbound communication event
        inbound_event = CommunicationEvent(
            channel=channel,
            direction="inbound",
            company_id=company_id,
            employee_id=None,
            leave_request_id=None,
            sender_identifier=sender_identifier,
            subject=subject,
            body=body,
            raw_payload={"channel": channel, "sender": sender_identifier},
            ai_extracted_data=parsed,
            processing_status="received",
        )
        self.db.add(inbound_event)

        if not parsed.get("is_leave_request"):
            inbound_event.processing_status = "ignored_non_leave"
            await self.db.commit()
            return {
                "processed": False,
                "reason": "Message is not an employee time-off or leave request.",
                "parsed": parsed,
            }

        # 2. Resolve employee by corporate or personal email
        clean_sender = sender_identifier.strip().lower()
        emp_stmt = select(Employee).where(
            Employee.company_id == company_id,
            Employee.is_active == True,
            (
                (Employee.personal_email == clean_sender)
                | (Employee.email == clean_sender)
                | (Employee.paypal_email == clean_sender)
            ),
        )
        emp_res = await self.db.execute(emp_stmt)
        employee = emp_res.scalars().first()

        # If not found by direct email, match by first name or fallback to first active employee
        if not employee:
            all_emps_res = await self.db.execute(
                select(Employee).where(Employee.company_id == company_id, Employee.is_active == True).limit(5)
            )
            candidate_emps = all_emps_res.scalars().all()
            for cand in candidate_emps:
                if cand.first_name.lower() in clean_sender or cand.last_name.lower() in clean_sender:
                    employee = cand
                    break
            if not employee and candidate_emps:
                employee = candidate_emps[0]

        if not employee:
            inbound_event.processing_status = "unmatched_employee"
            await self.db.commit()
            return {
                "processed": False,
                "reason": f"No active employee could be matched with identifier '{sender_identifier}'.",
            }

        inbound_event.employee_id = employee.id

        # 3. Resolve Leave Policy
        target_type = parsed.get("leave_type", "casual")
        pol_stmt = select(LeavePolicy).where(
            LeavePolicy.company_id == company_id,
            LeavePolicy.leave_type == target_type,
            LeavePolicy.is_active == True,
        )
        pol_res = await self.db.execute(pol_stmt)
        policy = pol_res.scalars().first()

        if not policy:
            fallback_pol = await self.db.execute(
                select(LeavePolicy).where(LeavePolicy.company_id == company_id, LeavePolicy.is_active == True).limit(1)
            )
            policy = fallback_pol.scalars().first()

        if not policy:
            inbound_event.processing_status = "no_active_policy"
            await self.db.commit()
            return {
                "processed": False,
                "reason": "Organization has no active leave policies configured.",
            }

        # 4. Compute days
        start_d = date.fromisoformat(parsed["start_date"])
        end_d = date.fromisoformat(parsed["end_date"])
        if end_d < start_d:
            end_d = start_d
        total_days = calculate_working_days(start_d, end_d)

        # 5. Create Leave Request
        req_number = f"LRQ-{start_d.year}-{uuid.uuid4().hex[:6].upper()}"
        leave_req = LeaveRequest(
            request_number=req_number,
            employee_id=employee.id,
            leave_policy_id=policy.id,
            start_date=start_d,
            end_date=end_d,
            total_days=total_days,
            reason=f"[Via {channel.capitalize()}] {parsed.get('reason') or subject}",
            status=LeaveRequestStatus.PENDING.value,
            is_paid=policy.is_paid,
            source_channel=channel,
            ai_recommendation={
                "action": "recommend_approval" if policy.is_paid else "requires_management_review",
                "confidence": parsed.get("confidence", 0.95),
                "summary": f"Autonomous ingestion from {channel}. Extracted {total_days} days of {policy.name}.",
                "channel": channel,
            },
            ai_confidence_score=Decimal(str(parsed.get("confidence", 0.95))),
        )
        self.db.add(leave_req)
        await self.db.flush()

        inbound_event.leave_request_id = leave_req.id
        inbound_event.processing_status = "staged_leave_request"

        # 6. Update pending in balance ledger
        bal_stmt = select(LeaveBalance).where(
            LeaveBalance.employee_id == employee.id,
            LeaveBalance.leave_policy_id == policy.id,
            LeaveBalance.year == start_d.year,
        )
        bal_res = await self.db.execute(bal_stmt)
        bal = bal_res.scalars().first()
        if bal:
            bal.pending += total_days

        # 7. Disseminate high-priority Notification to HR
        applicant_name = f"{employee.first_name} {employee.last_name}"
        hr_alert = CommunicationEvent(
            channel="in_app",
            direction="outbound",
            company_id=company_id,
            employee_id=None,  # Broadcast to company HR/Admins
            leave_request_id=leave_req.id,
            sender_identifier=channel,
            subject=f"New Leave Application via {channel.capitalize()}: {req_number}",
            body=(
                f"{applicant_name} submitted a leave request via {channel.capitalize()}: "
                f"{total_days} day(s) of {policy.name} from {start_d.isoformat()} to {end_d.isoformat()}."
            ),
            raw_payload={
                "request_number": req_number,
                "applicant": applicant_name,
                "channel": channel,
                "days": str(total_days),
                "start_date": start_d.isoformat(),
                "end_date": end_d.isoformat(),
            },
            ai_extracted_data=parsed,
            processing_status="unread",
        )
        self.db.add(hr_alert)

        await self.db.commit()
        await self.db.refresh(leave_req)

        return {
            "processed": True,
            "request_number": req_number,
            "employee_name": applicant_name,
            "channel": channel,
            "total_days": float(total_days),
            "start_date": start_d.isoformat(),
            "end_date": end_d.isoformat(),
            "policy_name": policy.name,
            "status": leave_req.status,
        }

    async def scan_gmail_inbox(self, company_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Connects via SSL IMAP to scan UNSEEN incoming Gmail messages."""
        if not self.is_imap_configured:
            logger.info("IMAP credentials not set. Returning simulation status.")
            return []

        processed_results = []
        try:
            import imaplib
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.imap_user, self.imap_password)
            mail.select("inbox")

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                mail.close()
                mail.logout()
                return []

            msg_ids = messages[0].split()
            for m_id in msg_ids[-10:]:  # Process latest 10 unread
                status, data = mail.fetch(m_id, "(RFC822)")
                if status != "OK":
                    continue
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Decode Subject
                subject_header = decode_header(msg.get("Subject", ""))[0]
                if isinstance(subject_header[0], bytes):
                    subject = subject_header[0].decode(subject_header[1] or "utf-8", errors="ignore")
                else:
                    subject = str(subject_header[0])

                sender = msg.get("From", "")

                # Extract Body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                res = await self.process_inbound_message(
                    company_id=company_id,
                    sender_identifier=sender,
                    subject=subject,
                    body=body,
                    channel="gmail",
                )
                if res.get("processed"):
                    processed_results.append(res)

            mail.close()
            mail.logout()
        except Exception as e:
            logger.warning(f"Error scanning IMAP Gmail inbox: {e}")

        return processed_results

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger("leavify.email.dispatcher")


async def send_system_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_name: str = "Leavify.ai",
) -> Dict[str, Any]:
    """Unified Email Dispatcher for Leavify.ai.

    Supports two primary dispatch modes:
    1. HTTPS REST API (Port 443 via Resend): Bypasses cloud firewall restrictions
       (such as Render free-tier blocking outbound ports 25, 465, and 587).
    2. Standard SMTP (Port 587/465): Fallback for local development or custom SMTP hosts.
    """
    settings = get_settings()
    clean_to = to_email.strip().lower()

    # 1. Primary Cloud Strategy: Resend HTTPS API (Port 443 - Never blocked on Render/Vercel)
    resend_api_key = (os.getenv("RESEND_API_KEY") or getattr(settings, "RESEND_API_KEY", "") or "").strip()
    if resend_api_key:
        resend_from = (
            os.getenv("RESEND_FROM_EMAIL")
            or getattr(settings, "RESEND_FROM_EMAIL", "")
            or f"{from_name} <onboarding@resend.dev>"
        ).strip()
        if "<" not in resend_from:
            resend_from = f"{from_name} <{resend_from}>"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": resend_from,
                        "to": [clean_to],
                        "subject": subject,
                        "html": html_content,
                    },
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    logger.info(f"[RESEND_HTTPS_DISPATCH] Successfully delivered email to {clean_to} (ID: {data.get('id')})")
                    return {
                        "dispatched": True,
                        "provider": "resend_https",
                        "id": data.get("id"),
                    }
                else:
                    err_msg = resp.text
                    logger.warning(
                        f"[RESEND_HTTPS_FAILED] Status {resp.status_code}: {err_msg}."
                    )
                    # If Resend restricted sandbox recipient error (403), include clear explanation
                    if resp.status_code == 403 and "only send testing emails to your own email address" in err_msg:
                        logger.error(f"[RESEND_SANDBOX_RESTRICTION] Resend onboarding@resend.dev only permits delivery to your registered Resend email.")
        except Exception as ex:
            logger.warning(f"[RESEND_HTTPS_ERROR] Exception calling Resend: {ex}.")

    # 2. Cloud Strategy Alternative: Brevo HTTPS REST API (Allows sending to ANY recipient without custom domain)
    brevo_api_key = (os.getenv("BREVO_API_KEY") or getattr(settings, "BREVO_API_KEY", "") or "").strip()
    if brevo_api_key:
        brevo_sender_email = (os.getenv("BREVO_SENDER_EMAIL") or os.getenv("SMTP_USER") or "notifications@leavify.ai").strip()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={
                        "api-key": brevo_api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "sender": {"name": from_name, "email": brevo_sender_email},
                        "to": [{"email": clean_to}],
                        "subject": subject,
                        "htmlContent": html_content,
                    },
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    logger.info(f"[BREVO_HTTPS_DISPATCH] Delivered to {clean_to} (MessageId: {data.get('messageId')})")
                    return {"dispatched": True, "provider": "brevo_https", "id": data.get("messageId")}
                else:
                    logger.warning(f"[BREVO_HTTPS_FAILED] Status {resp.status_code}: {resp.text}")
        except Exception as ex:
            logger.warning(f"[BREVO_HTTPS_ERROR] Exception calling Brevo: {ex}")

    # 2. Secondary Strategy: Standard SMTP (Port 587 / 465) for Local Development
    smtp_user = (os.getenv("SMTP_USER") or settings.SMTP_USER or "").strip()
    smtp_pass = (os.getenv("SMTP_PASSWORD") or settings.SMTP_PASSWORD or "").strip()
    smtp_host = os.getenv("SMTP_HOST") or settings.SMTP_HOST or "smtp.gmail.com"
    smtp_port = int(os.getenv("SMTP_PORT") or settings.SMTP_PORT or 587)
    from_email = (
        os.getenv("SMTP_FROM_EMAIL")
        or settings.SMTP_FROM_EMAIL
        or smtp_user
        or "notifications@leavify.ai"
    ).strip()

    # Normalize Google App Passwords (strip inner spaces if present)
    clean_smtp_pass = smtp_pass.replace(" ", "") if smtp_pass else ""

    if smtp_user and clean_smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = clean_to
            msg.attach(MIMEText(html_content, "html"))

            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12) as server:
                    server.login(smtp_user, clean_smtp_pass)
                    server.sendmail(from_email, [clean_to], msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(smtp_user, clean_smtp_pass)
                    server.sendmail(from_email, [clean_to], msg.as_string())

            logger.info(f"[SMTP_DISPATCH] Successfully delivered email to {clean_to} via {smtp_host}:{smtp_port}")
            return {
                "dispatched": True,
                "provider": "smtp",
                "host": smtp_host,
            }
        except Exception as ex:
            logger.error(f"[SMTP_DISPATCH_FAILED] Failed delivering to {clean_to}: {ex}")
            raise RuntimeError(
                f"Email dispatch failed: {ex}. On cloud hosting (Render Free Tier), outbound SMTP is blocked—set RESEND_API_KEY in environment variables."
            ) from ex

    # 3. Unconfigured Environment
    logger.warning(
        f"[EMAIL_UNCONFIGURED] Neither RESEND_API_KEY nor SMTP credentials configured. Email to {clean_to} skipped."
    )
    raise RuntimeError(
        "Outbound email service is not configured. Set RESEND_API_KEY or SMTP_USER/SMTP_PASSWORD in your environment variables."
    )

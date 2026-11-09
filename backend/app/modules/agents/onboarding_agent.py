import logging
import os
import smtplib
from typing import Any, Dict, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger("workforceai.agents.onboarding")


class OnboardingDispatchAgent:
    """Autonomous Onboarding Dispatch Agent.

    Crafts personalized corporate welcome letters and dispatches login
    credentials to the employee's personal contact email (e.g. Gmail) via
    standard SMTP (STARTTLS / SSL) without requiring Google Cloud APIs.
    """

    def __init__(self):
        settings = get_settings()
        self.smtp_host = os.getenv("SMTP_HOST") or settings.SMTP_HOST
        self.smtp_port = int(os.getenv("SMTP_PORT") or settings.SMTP_PORT)
        self.smtp_user = (os.getenv("SMTP_USER") or settings.SMTP_USER).strip()
        self.smtp_password = (os.getenv("SMTP_PASSWORD") or settings.SMTP_PASSWORD).strip()
        self.from_email = os.getenv("SMTP_FROM_EMAIL") or settings.SMTP_FROM_EMAIL or self.smtp_user or "notifications@workforceai.io"
        self.is_configured = bool(self.smtp_user and self.smtp_password)

    def format_email_body(
        self,
        employee_name: str,
        corporate_email: str,
        initial_password: str,
        company_name: str,
        personal_email: Optional[str] = None,
        organization_email: Optional[str] = None,
        portal_url: str = "http://localhost:3000/login",
    ) -> str:
        """Generates a professional corporate onboarding email body in clean HTML."""
        email_leave_instruction = ""
        if organization_email:
            email_leave_instruction = f"""
            <div style="background: #020617; border: 1px solid #1e293b; border-radius: 8px; padding: 14px; margin-top: 16px;">
                <span style="color: #38bdf8; font-weight: 600; font-size: 12px; display: block; margin-bottom: 4px;">Direct Email Leave Applications</span>
                <p style="margin: 0; font-size: 12px; color: #94a3b8; line-height: 1.5;">
                    You can apply for leaves or time-off without logging into the portal! Simply send an email from your registered personal email (<strong>{personal_email or 'your Gmail'}</strong>) directly to our company inbox:
                    <br/><strong style="color: #f1f5f9; font-family: monospace; display: inline-block; margin-top: 4px;">{organization_email}</strong>.
                    Our Autonomous AI Agent will parse your request, compute policy impacts, and submit it for approval automatically.
                </p>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f1f5f9; background-color: #090d16; margin: 0; padding: 24px;">
            <div style="max-width: 560px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);">
                <div style="display: flex; align-items: center; margin-bottom: 24px;">
                    <div style="background: #4f46e5; color: #ffffff; font-weight: 800; width: 40px; height: 40px; border-radius: 10px; text-align: center; line-height: 40px; font-size: 20px; margin-right: 14px;">W</div>
                    <div>
                        <h2 style="margin: 0; font-size: 18px; color: #ffffff;">Welcome to {company_name}</h2>
                        <span style="font-size: 12px; color: #94a3b8;">WorkforceAI Autonomous Enterprise Portal</span>
                    </div>
                </div>

                <p style="font-size: 14px; line-height: 1.6; color: #cbd5e1;">
                    Hello <strong>{employee_name}</strong>,
                </p>
                <p style="font-size: 14px; line-height: 1.6; color: #cbd5e1;">
                    You have been officially added as an employee at <strong>{company_name}</strong>. Your account has been provisioned. Below are your credentials to log in to the workforce portal:
                </p>

                <div style="background: #020617; border: 1px solid #312e81; border-radius: 8px; padding: 16px; margin: 20px 0; font-family: monospace; font-size: 13px;">
                    <div style="margin-bottom: 12px;">
                        <span style="color: #64748b; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;">Corporate On-Premise Email:</span><br/>
                        <strong style="color: #818cf8; font-size: 14px;">{corporate_email}</strong>
                    </div>
                    {f'<div style="margin-bottom: 12px;"><span style="color: #64748b; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;">Personal Sender Gmail:</span><br/><strong style="color: #38bdf8; font-size: 13px;">{personal_email}</strong></div>' if personal_email else ''}
                    <div>
                        <span style="color: #64748b; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;">Initial Login Password:</span><br/>
                        <strong style="color: #f1f5f9; font-size: 14px;">{initial_password}</strong>
                    </div>
                </div>

                <div style="text-align: center; margin: 24px 0;">
                    <a href="{portal_url}" style="background: #4f46e5; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 14px; display: inline-block;">
                        Sign In to WorkforceAI Portal
                    </a>
                </div>

                {email_leave_instruction}

                <div style="font-size: 11px; line-height: 1.5; color: #64748b; margin-top: 24px; border-top: 1px solid #1e293b; padding-top: 16px;">
                    <strong>Tip:</strong> You can sign in using either your Corporate On-Premise Email or your Personal Gmail with your initial password. Please update your password after your first login.
                </div>
            </div>
        </body>
        </html>
        """

    def dispatch_credentials(
        self,
        employee_name: str,
        corporate_email: str,
        initial_password: str,
        personal_email: Optional[str],
        company_name: str = "Workforce Organization",
        organization_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches onboarding credentials to the employee's personal Gmail via standard SMTP."""
        if not personal_email or "@" not in personal_email:
            return {
                "dispatched": False,
                "status": "No personal contact email provided",
            }

        clean_dest = personal_email.strip().lower()

        # If SMTP is not configured in .env, perform a safe logged simulation
        if not self.is_configured:
            logger.info(
                f"[SIMULATED_DISPATCH] Onboarding Agent prepared credentials for {employee_name} "
                f"to {clean_dest} (Login: {corporate_email}, Pass: {initial_password})"
            )
            return {
                "dispatched": True,
                "status": f"Simulated delivery to {clean_dest} (SMTP credentials unconfigured in .env)",
            }

        # Real SMTP dispatch via standard STARTTLS
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Welcome to {company_name}: Your WorkforceAI Portal Access Credentials"
            msg["From"] = f"WorkforceAI <{self.from_email}>"
            msg["To"] = clean_dest

            html_content = self.format_email_body(
                employee_name=employee_name,
                corporate_email=corporate_email,
                initial_password=initial_password,
                company_name=company_name,
                personal_email=clean_dest,
                organization_email=organization_email,
            )
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.ehlo()
                if self.smtp_port == 587:
                    server.starttls()
                    server.ehlo()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"[SMTP_DISPATCH] Successfully delivered welcome credentials for {employee_name} to {clean_dest}")
            return {
                "dispatched": True,
                "status": f"Dispatched via SMTP to {clean_dest}",
            }
        except Exception as e:
            logger.warning(f"[SMTP_DISPATCH_FAILED] Error sending to {clean_dest}: {e}")
            return {
                "dispatched": False,
                "status": f"SMTP Error: {str(e)[:60]}",
            }


onboarding_agent = OnboardingDispatchAgent()

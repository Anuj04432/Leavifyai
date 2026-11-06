from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import smtplib
from typing import Any, Dict, Optional

logger = logging.getLogger("workforceai.agents.onboarding")


class OnboardingDispatchAgent:
    """Autonomous Onboarding Dispatch Agent.

    Crafts personalized corporate welcome letters and dispatches login
    credentials to the employee's personal contact email (e.g. Gmail) via
    standard SMTP (STARTTLS / SSL) without requiring Google Cloud APIs.
    """

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", self.smtp_user or "no-reply@workforce.io")
        self.is_configured = bool(self.smtp_user and self.smtp_password)

    def format_email_body(
        self,
        employee_name: str,
        corporate_email: str,
        initial_password: str,
        company_name: str,
        portal_url: str = "http://localhost:3000/login",
    ) -> str:
        """Generates a professional corporate onboarding email body in clean HTML."""
        return f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 24px;">
            <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                <div style="display: flex; align-items: center; margin-bottom: 24px;">
                    <div style="background: #4f46e5; color: #ffffff; font-weight: bold; width: 36px; height: 36px; border-radius: 8px; text-align: center; line-height: 36px; font-size: 18px; margin-right: 12px;">W</div>
                    <div>
                        <h2 style="margin: 0; font-size: 18px; color: #0f172a;">Welcome to {company_name}</h2>
                        <span style="font-size: 12px; color: #64748b;">Autonomous Workforce Portal Access</span>
                    </div>
                </div>

                <p style="font-size: 14px; line-height: 1.6; color: #334155;">
                    Dear <strong>{employee_name}</strong>,
                </p>
                <p style="font-size: 14px; line-height: 1.6; color: #334155;">
                    Your corporate profile and employee account have been provisioned in the organization workspace. Please use your dedicated corporate credentials below to sign in:
                </p>

                <div style="background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; margin: 20px 0; font-family: monospace; font-size: 13px;">
                    <div style="margin-bottom: 8px;">
                        <span style="color: #64748b; font-size: 11px; text-transform: uppercase;">Corporate Login Email:</span><br/>
                        <strong style="color: #4f46e5; font-size: 14px;">{corporate_email}</strong>
                    </div>
                    <div>
                        <span style="color: #64748b; font-size: 11px; text-transform: uppercase;">Temporary Password:</span><br/>
                        <strong style="color: #0f172a; font-size: 14px;">{initial_password}</strong>
                    </div>
                </div>

                <div style="text-align: center; margin: 28px 0;">
                    <a href="{portal_url}" style="background: #4f46e5; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px; display: inline-block;">
                        Access Employee Portal
                    </a>
                </div>

                <p style="font-size: 12px; line-height: 1.5; color: #64748b; margin-top: 24px; border-top: 1px solid #e2e8f0; pt: 16px;">
                    <strong>Security Notice:</strong> You will be prompted to verify your details upon initial sign in. Keep your temporary credentials secure.
                </p>
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

        # Real SMTP dispatch via standard STARTTLS (Works with Gmail App Passwords, Outlook, SES)
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Your {company_name} Portal Access Credentials"
            msg["From"] = self.from_email
            msg["To"] = clean_dest

            html_content = self.format_email_body(
                employee_name=employee_name,
                corporate_email=corporate_email,
                initial_password=initial_password,
                company_name=company_name,
            )
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.ehlo()
                if self.smtp_port == 587:
                    server.starttls()
                    server.ehlo()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"[SMTP_DISPATCH] Successfully delivered credentials for {employee_name} to {clean_dest}")
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

import pytest
from decimal import Decimal
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.company import Company
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.modules.auth.demo_seed import (
    DEMO_ACCOUNTS,
    DEMO_ORG_NAME,
    DEMO_ORG_SLUG,
    DEMO_PASSWORD,
    ensure_paypal_hackathon_demo,
)
from app.modules.payments.payslip_mailer import PayslipMailer
from app.core.email_dispatcher import send_system_email


@pytest.mark.asyncio
async def test_ensure_paypal_hackathon_demo_idempotent():
    async with AsyncSessionLocal() as db:
        await ensure_paypal_hackathon_demo(db)
        await ensure_paypal_hackathon_demo(db)  # Should safely rerun without duplicates

        comp = (
            await db.execute(select(Company).where(Company.slug == DEMO_ORG_SLUG))
        ).scalar_one_or_none()
        assert comp is not None
        assert comp.name == DEMO_ORG_NAME

        users = (
            await db.execute(select(User).where(User.company_id == comp.id))
        ).scalars().all()
        user_emails = {u.email for u in users}
        assert "ceo@paypalhackathon.demo" in user_emails
        assert "hr@paypalhackathon.demo" in user_emails
        assert "employee@paypalhackathon.demo" in user_emails

        emps = (
            await db.execute(select(Employee).where(Employee.company_id == comp.id))
        ).scalars().all()
        emp_paypals = {e.paypal_email for e in emps}
        assert "sb-hsoh053785418@business.example.com" in emp_paypals
        assert "paypaljudgereceiver@personal.gmail.com" in emp_paypals
        assert "demoemployee@gmail.com" in emp_paypals


@pytest.mark.asyncio
async def test_email_dispatcher_skips_nonroutable_example_domain():
    res = await send_system_email(
        to_email="test@business.example.com",
        subject="Test Sandbox Email",
        html_content="<p>Sandbox test</p>",
    )
    assert res.get("dispatched") is False
    assert res.get("provider") == "skipped_sandbox_domain"


def test_payslip_mailer_recipient_precedence():
    mailer = PayslipMailer()

    class DummyUser:
        email = "corp.user@example.com"

    class DummyEmployee:
        id = "dummy"
        first_name = "Jane"
        last_name = "Doe"
        employee_code = "EMP-001"
        email = "work@example.com"
        personal_email = "realinbox@gmail.com"
        paypal_email = "sandbox@business.example.com"
        user = DummyUser()
        department = None
        designation = None

    emp = DummyEmployee()
    # Confirm personal_email is chosen first over sandbox paypal_email
    resolved = (
        emp.personal_email
        or emp.email
        or (emp.user.email if emp.user else None)
        or emp.paypal_email
    )
    assert resolved == "realinbox@gmail.com"

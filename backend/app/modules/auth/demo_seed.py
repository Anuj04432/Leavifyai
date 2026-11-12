import logging
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security import get_password_hash
from app.models.company import Company, Department
from app.models.employee import Employee
from app.models.leave import LeaveBalance, LeavePolicy
from app.models.user import User, UserRole

logger = logging.getLogger("leavify.demo_seed")

DEMO_ORG_NAME = "PayPal Hackathon"
DEMO_ORG_SLUG = "paypal-hackathon"
DEMO_ORG_DOMAIN = "paypalhackathon.demo"
DEMO_ORG_EMAIL = "inbox@paypalhackathon.demo"
DEMO_PASSWORD = "PayPalDemo2026!"

DEMO_ACCOUNTS = [
    {
        "email": "ceo@paypalhackathon.demo",
        "role": UserRole.CEO.value,
        "permissions": {
            "can_handle_paypal": True,
            "can_run_payroll": True,
            "can_approve_leaves": True,
            "can_manage_roster": True,
            "can_manage_policies": True,
        },
        "employee_code": "EMP-001",
        "first_name": "Alex",
        "last_name": "Mercer",
        "designation": "Chief Executive Officer",
        "personal_email": None,
        "paypal_email": "sb-hsoh053785418@business.example.com",
        "salary_basic": Decimal("12000.00"),
    },
    {
        "email": "hr@paypalhackathon.demo",
        "role": UserRole.HR_MANAGER.value,
        "permissions": {
            "can_handle_paypal": True,
            "can_run_payroll": True,
            "can_approve_leaves": True,
            "can_manage_roster": True,
            "can_manage_policies": True,
        },
        "employee_code": "EMP-002",
        "first_name": "Maya",
        "last_name": "Lin",
        "designation": "HR & Admin Manager",
        "personal_email": "paypaljudgereceiver@personal.gmail.com",
        "paypal_email": "paypaljudgereceiver@personal.gmail.com",
        "salary_basic": Decimal("6500.00"),
    },
    {
        "email": "employee@paypalhackathon.demo",
        "role": UserRole.EMPLOYEE.value,
        "permissions": {},
        "employee_code": "EMP-003",
        "first_name": "Jordan",
        "last_name": "Taylor",
        "designation": "Software Engineer",
        "personal_email": "demoemployee@gmail.com",
        "paypal_email": "demoemployee@gmail.com",
        "salary_basic": Decimal("4800.00"),
    },
]


async def ensure_paypal_hackathon_demo(db: AsyncSession) -> None:
    """Idempotently seeds the 'PayPal Hackathon' demo org, leave policies, and 3 demo accounts."""
    company = (
        await db.execute(select(Company).where(Company.slug == DEMO_ORG_SLUG))
    ).scalar_one_or_none()

    if not company:
        company = Company(
            name=DEMO_ORG_NAME,
            slug=DEMO_ORG_SLUG,
            domain=DEMO_ORG_DOMAIN,
            organization_email=DEMO_ORG_EMAIL,
            is_email_verified=True,
            settings={"organization_email": DEMO_ORG_EMAIL, "is_demo": True},
            is_active=True,
        )
        db.add(company)
        await db.flush()

    dept = (
        await db.execute(
            select(Department).where(Department.company_id == company.id).limit(1)
        )
    ).scalar_one_or_none()
    if not dept:
        dept = Department(company_id=company.id, name="Product & Operations", is_active=True)
        db.add(dept)
        await db.flush()

    # Ensure default leave policies exist for leave/copilot flows
    policies = (
        await db.execute(select(LeavePolicy).where(LeavePolicy.company_id == company.id))
    ).scalars().all()
    if not policies:
        policy_defs = [
            ("Annual Leave", "annual", 18, True, 6, True),
            ("Sick Leave", "sick", 12, False, 0, True),
            ("Casual Leave", "casual", 10, False, 0, True),
            ("Unpaid Leave", "unpaid", 30, False, 0, False),
        ]
        policies = [
            LeavePolicy(
                company_id=company.id,
                name=name,
                leave_type=l_type,
                days_allowed=days,
                carry_forward=cf,
                max_carry_forward_days=max_cf,
                is_paid=is_p,
                approval_required=True,
                is_active=True,
            )
            for name, l_type, days, cf, max_cf, is_p in policy_defs
        ]
        db.add_all(policies)
        await db.flush()

    now = datetime.now(timezone.utc)
    hashed_pw = get_password_hash(DEMO_PASSWORD)
    ceo_emp_id = None

    for spec in DEMO_ACCOUNTS:
        user = (
            await db.execute(select(User).where(User.email == spec["email"]))
        ).scalar_one_or_none()

        if not user:
            user = User(
                email=spec["email"],
                password_hash=hashed_pw,
                role=spec["role"],
                company_id=company.id,
                is_active=True,
                permissions=spec["permissions"],
            )
            db.add(user)
            await db.flush()

        emp = (
            await db.execute(select(Employee).where(Employee.user_id == user.id))
        ).scalar_one_or_none()

        if not emp:
            emp = Employee(
                user_id=user.id,
                company_id=company.id,
                employee_code=spec["employee_code"],
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                email=spec["email"],
                personal_email=spec["personal_email"],
                designation=spec["designation"],
                department_id=dept.id,
                reporting_manager_id=None if spec["role"] == UserRole.CEO.value else ceo_emp_id,
                date_of_joining=now.date(),
                employment_type="full_time",
                salary_basic=spec["salary_basic"],
                salary_allowances={},
                bank_account_info={},
                paypal_email=spec["paypal_email"],
                is_active=True,
            )
            db.add(emp)
            await db.flush()

            for p in policies:
                db.add(
                    LeaveBalance(
                        employee_id=emp.id,
                        leave_policy_id=p.id,
                        year=now.year,
                        total_allocated=Decimal(p.days_allowed),
                        used=Decimal("0.0"),
                        pending=Decimal("0.0"),
                        carried_forward=Decimal("0.0"),
                    )
                )
        else:
            # Keep sandbox PayPal & personal emails aligned with current demo specs
            emp.paypal_email = spec["paypal_email"]
            emp.personal_email = spec["personal_email"]

        if spec["role"] == UserRole.CEO.value:
            ceo_emp_id = emp.id

    await db.commit()
    logger.info("Verified 'PayPal Hackathon' demo organization and 3 demo accounts.")

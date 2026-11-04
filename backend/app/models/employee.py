import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Employee(Base, UUIDMixin, TimestampMixin):
    """Employee personal, organizational, and compensation profile."""
    __tablename__ = "employees"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reporting_manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)
    date_of_exit: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_type: Mapped[str] = mapped_column(String(30), default="full_time", nullable=False)

    # Financial details (strict arbitrary-precision decimal)
    salary_basic: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    salary_allowances: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    bank_account_info: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    paypal_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="employee")
    company: Mapped["Company"] = relationship(back_populates="employees")
    department: Mapped[Optional["Department"]] = relationship(
        back_populates="employees",
        foreign_keys=[department_id],
    )
    reporting_manager: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        remote_side="Employee.id",
        foreign_keys=[reporting_manager_id],
    )
    direct_reports: Mapped[List["Employee"]] = relationship(
        "Employee",
        back_populates="reporting_manager",
        foreign_keys=[reporting_manager_id],
    )
    leave_balances: Mapped[List["LeaveBalance"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    leave_requests: Mapped[List["LeaveRequest"]] = relationship(
        back_populates="employee",
        foreign_keys="[LeaveRequest.employee_id]",
        cascade="all, delete-orphan",
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    payroll_items: Mapped[List["PayrollItem"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["Payment"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )


class Document(Base, UUIDMixin, TimestampMixin):
    """Employee-uploaded document records."""
    __tablename__ = "documents"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leave_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leave_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    employee: Mapped["Employee"] = relationship(back_populates="documents")

import uuid
from typing import List, Optional
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Company(Base, UUIDMixin, TimestampMixin):
    """Company tenant entity."""
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    organization_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    departments: Mapped[List["Department"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    employees: Mapped[List["Employee"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    leave_policies: Mapped[List["LeavePolicy"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    payroll_batches: Mapped[List["PayrollBatch"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    integrations: Mapped[List["Integration"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Department(Base, UUIDMixin, TimestampMixin):
    """Department organization unit."""
    __tablename__ = "departments"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    head_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="departments")
    employees: Mapped[List["Employee"]] = relationship(
        back_populates="department",
        foreign_keys="[Employee.department_id]",
    )

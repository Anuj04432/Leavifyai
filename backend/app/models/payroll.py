import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class BatchStatus(str, enum.Enum):
    DRAFT = "draft"
    CALCULATING = "calculating"
    CALCULATED = "calculated"
    APPROVED = "approved"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"


class PayrollBatch(Base, UUIDMixin, TimestampMixin):
    """Monthly organization-wide payroll processing batch."""
    __tablename__ = "payroll_batches"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=BatchStatus.DRAFT.value, nullable=False, index=True)

    total_gross: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    total_net: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    employee_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="payroll_batches")
    payroll_items: Mapped[List["PayrollItem"]] = relationship(
        back_populates="payroll_batch",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["Payment"]] = relationship(
        back_populates="payroll_batch",
        cascade="all, delete-orphan",
    )


class PayrollItem(Base, UUIDMixin, TimestampMixin):
    """Per-employee itemized salary computation line in a batch."""
    __tablename__ = "payroll_items"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    basic_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_allowances: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    allowances_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    gross_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    paid_leave_days: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"), nullable=False)
    unpaid_leave_days: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"), nullable=False)
    unpaid_leave_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    attendance_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 1), nullable=True)
    attendance_adjustment: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    statutory_deductions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="calculated", nullable=False)

    # Relationships
    payroll_batch: Mapped["PayrollBatch"] = relationship(back_populates="payroll_items")
    employee: Mapped["Employee"] = relationship(back_populates="payroll_items")
    adjustments: Mapped[List["PayrollAdjustment"]] = relationship(
        back_populates="payroll_item",
        cascade="all, delete-orphan",
    )
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="payroll_item", uselist=False)


class PayrollAdjustment(Base, UUIDMixin, TimestampMixin):
    """Manual adjustment attached to an employee's payroll item."""
    __tablename__ = "payroll_adjustments"

    payroll_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    adjustment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    adjusted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    payroll_item: Mapped["PayrollItem"] = relationship(back_populates="adjustments")

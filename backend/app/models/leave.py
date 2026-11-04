import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class LeaveRequestStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    INFO_REQUESTED = "info_requested"


class LeavePolicy(Base, UUIDMixin, TimestampMixin):
    """Company leave configuration rules."""
    __tablename__ = "leave_policies"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    leave_type: Mapped[str] = mapped_column(String(30), nullable=False)
    days_allowed: Mapped[int] = mapped_column(Integer, nullable=False)
    carry_forward: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_carry_forward_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requires_document: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_days_notice: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_consecutive_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    applicable_after_months: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    policy_document_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="leave_policies")
    leave_balances: Mapped[List["LeaveBalance"]] = relationship(
        back_populates="leave_policy",
        cascade="all, delete-orphan",
    )
    leave_requests: Mapped[List["LeaveRequest"]] = relationship(back_populates="leave_policy")


class LeaveBalance(Base, UUIDMixin, TimestampMixin):
    """Annual leave balance ledger per employee per leave policy."""
    __tablename__ = "leave_balances"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leave_policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leave_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_allocated: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"), nullable=False)
    used: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"), nullable=False)
    pending: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"), nullable=False)
    carried_forward: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0.0"), nullable=False)

    # Relationships
    employee: Mapped["Employee"] = relationship(back_populates="leave_balances")
    leave_policy: Mapped["LeavePolicy"] = relationship(back_populates="leave_balances")

    @property
    def available(self) -> Decimal:
        return self.total_allocated + self.carried_forward - self.used - self.pending


class LeaveRequest(Base, UUIDMixin, TimestampMixin):
    """Leave application submitted by employee through any channel."""
    __tablename__ = "leave_requests"

    request_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leave_policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leave_policies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=LeaveRequestStatus.PENDING.value, nullable=False, index=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_channel: Mapped[str] = mapped_column(String(20), default="app", nullable=False)

    # AI Recommendation artifacts
    ai_recommendation: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ai_confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)
    ai_policy_references: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Human review authorization
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    employee: Mapped["Employee"] = relationship(
        back_populates="leave_requests",
        foreign_keys=[employee_id],
    )
    leave_policy: Mapped["LeavePolicy"] = relationship(back_populates="leave_requests")
    approvals: Mapped[List["Approval"]] = relationship(
        back_populates="leave_request",
        cascade="all, delete-orphan",
    )
    communication_events: Mapped[List["CommunicationEvent"]] = relationship(back_populates="leave_request")


class Approval(Base, UUIDMixin, TimestampMixin):
    """Historical audit of approval chain actions."""
    __tablename__ = "approvals"

    leave_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leave_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    leave_request: Mapped["LeaveRequest"] = relationship(back_populates="approvals")

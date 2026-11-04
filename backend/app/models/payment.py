import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETURNED = "returned"
    REFUNDED = "refunded"
    BLOCKED = "blocked"


class Payment(Base, UUIDMixin, TimestampMixin):
    """Payment transaction record for salary disbursements."""
    __tablename__ = "payments"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    payroll_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_items.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payment_provider: Mapped[str] = mapped_column(String(20), default="paypal", nullable=False)

    provider_batch_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    provider_item_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    provider_transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Idempotency token (strictly unique)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    recipient_identifier: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.PENDING.value, nullable=False, index=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    webhook_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    payroll_batch: Mapped["PayrollBatch"] = relationship(back_populates="payments")
    employee: Mapped["Employee"] = relationship(back_populates="payments")
    payroll_item: Mapped["PayrollItem"] = relationship(back_populates="payment")


class Integration(Base, UUIDMixin, TimestampMixin):
    """External third-party integration configuration."""
    __tablename__ = "integrations"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    credentials: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="inactive", nullable=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="integrations")

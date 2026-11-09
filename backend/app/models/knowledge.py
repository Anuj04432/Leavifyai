import uuid
from typing import Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class KnowledgeChunk(Base, UUIDMixin, TimestampMixin):
    """Semantic knowledge chunk for RAG policy and handbook grounding."""
    __tablename__ = "knowledge_chunks"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    section_header: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_info: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    embedding: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship()

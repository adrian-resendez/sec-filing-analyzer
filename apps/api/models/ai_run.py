from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.extensions import Base


class AIRun(Base):
    __tablename__ = "ai_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filings.id"), nullable=False, index=True
    )
    run_type: Mapped[str] = mapped_column(
        String(32), default="filing_insight", nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(
        String(32), default="v1", nullable=False
    )
    schema_version: Mapped[str] = mapped_column(
        String(32), default="v1", nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
        nullable=False,
    )

    filing: Mapped["Filing"] = relationship(back_populates="ai_runs")

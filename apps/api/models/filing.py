from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.extensions import Base


class Filing(Base):
    __tablename__ = "filings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    accession_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    form_type: Mapped[str] = mapped_column(String(16), default="10-Q", nullable=False)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_of_report: Mapped[date | None] = mapped_column(Date, nullable=True)
    filing_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_payload: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    processing_status: Mapped[str] = mapped_column(
        String(32), default="discovered", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
        nullable=False,
    )

    company: Mapped["Company"] = relationship(back_populates="filings")
    sections: Mapped[list["FilingSection"]] = relationship(
        back_populates="filing", cascade="all, delete-orphan"
    )
    ai_runs: Mapped[list["AIRun"]] = relationship(
        back_populates="filing", cascade="all, delete-orphan"
    )

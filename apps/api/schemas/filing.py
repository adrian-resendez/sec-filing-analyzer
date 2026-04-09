from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class FilingDiscoveryRequest(BaseModel):
    ticker: str
    cik: str
    start_date: date
    end_date: date

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("ticker is required")
        return cleaned

    @field_validator("cik")
    @classmethod
    def normalize_cik(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("cik is required")
        return cleaned


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticker: str
    cik: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    sp500_active: bool = False


class FilingRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    accession_no: str
    form_type: str
    filed_at: datetime
    period_of_report: date | None = None
    filing_url: str | None = None
    processing_status: str


class FilingSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filing_id: UUID
    section_code: str
    section_name: str | None = None
    content_text: str | None = None
    extraction_status: str


class AIRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filing_id: UUID
    run_type: str
    model_name: str
    prompt_version: str
    schema_version: str
    status: str
    raw_response: dict[str, Any]
    error_message: str | None = None


class FilingDetailResponse(BaseModel):
    filing: FilingRecordResponse
    company: CompanyResponse | None = None
    sections: list[FilingSectionResponse]
    ai_runs: list[AIRunResponse]

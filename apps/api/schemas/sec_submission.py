from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SecSubmissionFilingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accession_number: str
    form_type: str
    filing_date: str
    primary_document: str
    primary_document_url: str
    filing_index_url: str
    submission_text_url: str


class SecCompanySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cik: str
    name: str | None = None
    sic: str | None = None
    sic_description: str | None = None
    tickers: list[str]
    exchanges: list[str]
    filings: list[SecSubmissionFilingSchema]


class SecFilingsResponseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    cik: str
    filings: list[SecSubmissionFilingSchema]

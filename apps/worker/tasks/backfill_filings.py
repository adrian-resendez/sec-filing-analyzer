from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from httpx import HTTPError

from apps.api.extensions import get_session
from apps.api.models.company import Company
from apps.api.services.filing_service import FilingService
from apps.api.utils.logging import get_logger
from apps.worker.celery_app import celery_app
from apps.worker.tasks.analyze_filing import analyze_filing

logger = get_logger(__name__)


@celery_app.task(
    name="backfill_company_filings",
    autoretry_for=(HTTPError, RuntimeError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def backfill_company_filings(
    company_id: str, start_date: str, end_date: str, enqueue_analysis: bool = True
) -> dict[str, Any]:
    return asyncio.run(
        _backfill_company_filings_async(
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            enqueue_analysis=enqueue_analysis,
        )
    )


async def _backfill_company_filings_async(
    company_id: str, start_date: str, end_date: str, enqueue_analysis: bool
) -> dict[str, Any]:
    session = get_session()

    try:
        company = session.get(Company, UUID(company_id))
        if company is None:
            raise ValueError(f"Company {company_id} was not found")

        filing_service = FilingService(session)
        filings = await filing_service.backfill_10q_filings(company, start_date, end_date)

        queued_filing_ids: list[str] = []
        if enqueue_analysis:
            for filing in filings:
                if filing.processing_status in {
                    "pending_extraction",
                    "pending_analysis",
                    "analysis_failed",
                }:
                    analyze_filing.delay(str(filing.id))
                    queued_filing_ids.append(str(filing.id))

        logger.info(
            "Backfilled filings for ticker=%s filings=%s queued=%s",
            company.ticker,
            len(filings),
            len(queued_filing_ids),
        )
        return {
            "company_id": str(company.id),
            "ticker": company.ticker,
            "filings_seen": len(filings),
            "queued_for_analysis": queued_filing_ids,
        }
    finally:
        session.close()


@celery_app.task(name="backfill_active_companies")
def backfill_active_companies(
    start_date: str, end_date: str, limit: int | None = None
) -> dict[str, Any]:
    session = get_session()

    try:
        service = FilingService(session)
        companies = service.list_active_companies()
        if limit is not None:
            companies = companies[:limit]

        queued_company_ids: list[str] = []
        for company in companies:
            backfill_company_filings.delay(str(company.id), start_date, end_date, True)
            queued_company_ids.append(str(company.id))

        logger.info("Queued company filing backfills count=%s", len(queued_company_ids))
        return {"queued_company_ids": queued_company_ids}
    finally:
        session.close()

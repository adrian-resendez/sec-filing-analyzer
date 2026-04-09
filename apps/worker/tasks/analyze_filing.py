from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from httpx import HTTPError
from openai import OpenAIError
from sqlalchemy import select

from apps.api.extensions import get_session
from apps.api.models.filing import Filing
from apps.api.models.filing_section import FilingSection
from apps.api.services.extraction_service import ExtractionService
from apps.api.services.insight_service import InsightService
from apps.api.utils.logging import get_logger
from apps.worker.celery_app import celery_app

logger = get_logger(__name__)
SECTION_CODES = ("part1item2", "part2item1a")


@celery_app.task(
    name="analyze_filing",
    autoretry_for=(HTTPError, OpenAIError, RuntimeError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def analyze_filing(filing_id: str) -> dict[str, Any]:
    return asyncio.run(_analyze_filing_async(filing_id))


async def _analyze_filing_async(filing_id: str) -> dict[str, Any]:
    session = get_session()

    try:
        filing = session.get(Filing, UUID(filing_id))
        if filing is None:
            raise ValueError(f"Filing {filing_id} was not found")

        cached_sections = list(
            session.scalars(
                select(FilingSection)
                .where(
                    FilingSection.filing_id == filing.id,
                    FilingSection.section_code.in_(SECTION_CODES),
                    FilingSection.extraction_status == "completed",
                    FilingSection.content_text.is_not(None),
                )
                .order_by(FilingSection.section_code.asc())
            )
        )

        if cached_sections:
            logger.info(
                "Using %s cached sections for filing_id=%s",
                len(cached_sections),
                filing_id,
            )
            sections = cached_sections
        else:
            filing.processing_status = "extracting"
            session.add(filing)
            session.commit()

            sections = await ExtractionService(session).extract_and_store_sections(
                filing=filing,
                section_codes=SECTION_CODES,
            )

        filing.processing_status = "pending_analysis"
        session.add(filing)
        session.commit()

        ai_run = await InsightService(session).analyze_filing_sections(
            filing=filing,
            sections=sections,
        )

        payload = {
            "filing_id": str(filing.id),
            "section_ids": [str(section.id) for section in sections],
            "ai_run_id": str(ai_run.id),
            "status": ai_run.status,
        }
        logger.info("Completed filing analysis for filing_id=%s", filing_id)
        return payload
    finally:
        session.close()

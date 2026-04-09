from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.clients.sec_api_client import SecApiClient
from apps.api.models.filing import Filing
from apps.api.models.filing_section import FilingSection
from apps.api.utils.logging import get_logger

logger = get_logger(__name__)

SECTION_NAMES = {
    "part1item2": "Management Discussion & Analysis",
    "part2item1a": "Risk Factors",
}


class ExtractionService:
    def __init__(
        self, session: Session, sec_api_client: SecApiClient | None = None
    ) -> None:
        self.session = session
        self.sec_api_client = sec_api_client or SecApiClient()

    async def extract_and_store_section(
        self, filing: Filing, section_code: str
    ) -> FilingSection:
        if not filing.filing_url:
            raise ValueError("filing_url is required to extract a filing section")

        section = self.session.scalar(
            select(FilingSection).where(
                FilingSection.filing_id == filing.id,
                FilingSection.section_code == section_code,
            )
        )

        if section is not None and section.extraction_status == "completed" and section.content_text:
            return section

        section = section or FilingSection(
            filing_id=filing.id,
            section_code=section_code,
            section_name=SECTION_NAMES.get(section_code, section_code),
            extraction_status="running",
        )
        section.section_name = SECTION_NAMES.get(section_code, section.section_name)
        section.extraction_status = "running"
        self.session.add(section)
        self.session.commit()
        self.session.refresh(section)

        try:
            content_text = await self.sec_api_client.extract_section(
                filing_url=filing.filing_url,
                item_code=section_code,
            )

            if not content_text.strip():
                raise ValueError(f"sec-api returned an empty section for {section_code}")

            section.content_text = content_text
            section.extraction_status = "completed"
            self.session.add(section)
            self.session.commit()
            self.session.refresh(section)
            return section
        except Exception:
            section.content_text = None
            section.extraction_status = "failed"
            self.session.add(section)
            self.session.commit()
            logger.exception(
                "Failed extracting section %s for filing_id=%s", section_code, filing.id
            )
            raise

    async def extract_and_store_sections(
        self, filing: Filing, section_codes: Iterable[str]
    ) -> list[FilingSection]:
        extracted_sections: list[FilingSection] = []

        for section_code in section_codes:
            try:
                section = await self.extract_and_store_section(filing, section_code)
            except Exception:
                continue

            if section.content_text:
                extracted_sections.append(section)

        if not extracted_sections:
            raise ValueError(f"No sections could be extracted for filing {filing.id}")

        return extracted_sections

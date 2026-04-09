from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from apps.api.clients.sec_api_client import SecApiClient
from apps.api.clients.secgov_client import SecGovClient, SecGovClientError
from apps.api.config import get_settings
from apps.api.models.company import Company
from apps.api.models.filing import Filing
from apps.api.schemas.filing import FilingDetailResponse, FilingDiscoveryRequest
from apps.api.utils.logging import get_logger

QUERY_PAGE_SIZE = 50
SEC_GOV_FILING_LIMIT = 250
logger = get_logger(__name__)


class FilingService:
    def __init__(
        self,
        session: Session,
        sec_api_client: SecApiClient | None = None,
        sec_gov_client: SecGovClient | None = None,
    ) -> None:
        self.session = session
        self.sec_api_client = sec_api_client or SecApiClient()
        self.sec_gov_client = sec_gov_client or SecGovClient()

    async def discover_filings(
        self, payload: FilingDiscoveryRequest
    ) -> list[Filing]:
        company = self._get_or_create_company(payload.ticker, payload.cik)
        return await self.backfill_10q_filings(
            company=company,
            start_date=payload.start_date.isoformat(),
            end_date=payload.end_date.isoformat(),
        )

    async def backfill_10q_filings(
        self, company: Company, start_date: str, end_date: str
    ) -> list[Filing]:
        sec_gov_filings = await self._discover_recent_10q_filings_from_sec_gov(
            company=company,
            start_date=start_date,
            end_date=end_date,
        )
        if sec_gov_filings is not None:
            stored_filings = []
            for payload in sec_gov_filings:
                filing = self._upsert_filing_from_payload(company=company, payload=payload)
                if filing is not None:
                    stored_filings.append(filing)

            self.session.commit()
            logger.info(
                "Backfilled %s recent 10-Q filings from SEC.gov for ticker=%s",
                len(stored_filings),
                company.ticker,
            )
            return stored_filings

        logger.info(
            "SEC.gov submissions fetch failed for ticker=%s between %s and %s; "
            "falling back to sec-api query search.",
            company.ticker,
            start_date,
            end_date,
        )
        return await self._backfill_10q_filings_from_sec_api(
            company=company,
            start_date=start_date,
            end_date=end_date,
        )

    async def _backfill_10q_filings_from_sec_api(
        self, company: Company, start_date: str, end_date: str
    ) -> list[Filing]:
        stored_filings: list[Filing] = []
        offset = 0

        while True:
            api_result = await self.sec_api_client.search_10q_filings(
                cik=company.cik,
                start_date=start_date,
                end_date=end_date,
                from_offset=offset,
                size=QUERY_PAGE_SIZE,
            )

            filings_payload = api_result.get("filings", [])
            if not filings_payload:
                break

            for item in filings_payload:
                filing = self._upsert_filing_from_payload(company=company, payload=item)
                if filing is not None:
                    stored_filings.append(filing)

            self.session.commit()

            if len(filings_payload) < QUERY_PAGE_SIZE:
                break
            offset += QUERY_PAGE_SIZE

        return stored_filings

    async def _discover_recent_10q_filings_from_sec_gov(
        self, company: Company, start_date: str, end_date: str
    ) -> list[dict[str, object]] | None:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        try:
            submissions_payload = await self.sec_gov_client.get_company_submissions(company.cik)
        except SecGovClientError as exc:
            logger.warning(
                "SEC.gov submissions request failed for ticker=%s cik=%s: %s",
                company.ticker,
                company.cik,
                exc,
            )
            return None

        normalized_filings = self.sec_gov_client.normalize_filings(
            submissions_payload,
            filing_limit=SEC_GOV_FILING_LIMIT,
            form_type="10-Q",
        )

        in_range_filings = []
        for payload in normalized_filings:
            filed_on = self._parse_date(payload.get("filing_date"))
            if filed_on is None or filed_on < start or filed_on > end:
                continue
            in_range_filings.append(payload)

        return in_range_filings

    def get_filing(self, filing_id: str | UUID) -> Filing | None:
        filing_uuid = UUID(str(filing_id))
        statement = (
            select(Filing)
            .options(
                selectinload(Filing.company),
                selectinload(Filing.sections),
                selectinload(Filing.ai_runs),
            )
            .where(Filing.id == filing_uuid)
        )
        return self.session.scalar(statement)

    def list_recent_filings(self, limit: int = 25) -> list[Filing]:
        statement = (
            select(Filing)
            .options(selectinload(Filing.company))
            .order_by(Filing.filed_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def get_dashboard_summary(self, recent_limit: int = 25) -> dict[str, object]:
        settings = get_settings()
        active_companies = self.list_active_companies()
        recent_filings = self.list_recent_filings(limit=recent_limit)
        today = datetime.now(tz=UTC).date()
        current_quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        current_quarter_start = date(today.year, current_quarter_start_month, 1)
        if current_quarter_start.month <= 6:
            pilot_start = date(current_quarter_start.year - 1, current_quarter_start.month + 6, 1)
        else:
            pilot_start = date(current_quarter_start.year, current_quarter_start.month - 6, 1)

        total_filings = self.session.query(Filing).count()
        analyzed_filings = (
            self.session.query(Filing)
            .filter(Filing.processing_status == "analyzed")
            .count()
        )
        active_processing_filings = (
            self.session.query(Filing)
            .filter(Filing.processing_status.in_(["extracting", "pending_analysis", "analyzing"]))
            .count()
        )

        return {
            "company_count": len(active_companies),
            "filing_count": total_filings,
            "analyzed_count": analyzed_filings,
            "active_processing_count": active_processing_filings,
            "ai_provider": settings.ai_provider,
            "pilot_defaults": {
                "company_limit": 10,
                "start_date": pilot_start.isoformat(),
                "end_date": today.isoformat(),
            },
            "active_companies": [
                {
                    "ticker": company.ticker,
                    "name": company.name,
                    "sector": company.sector,
                }
                for company in active_companies[:100]
            ],
            "recent_filings": [
                {
                    "id": str(filing.id),
                    "ticker": filing.company.ticker if filing.company else None,
                    "company_name": filing.company.name if filing.company else None,
                    "accession_no": filing.accession_no,
                    "form_type": filing.form_type,
                    "filed_at": filing.filed_at.isoformat(),
                    "processing_status": filing.processing_status,
                }
                for filing in recent_filings
            ],
        }

    def serialize_filing_detail(self, filing: Filing) -> dict[str, object]:
        response = FilingDetailResponse(
            filing={
                "id": filing.id,
                "company_id": filing.company_id,
                "accession_no": filing.accession_no,
                "form_type": filing.form_type,
                "filed_at": filing.filed_at,
                "period_of_report": filing.period_of_report,
                "filing_url": filing.filing_url,
                "processing_status": filing.processing_status,
            },
            company={
                "id": filing.company.id,
                "ticker": filing.company.ticker,
                "cik": filing.company.cik,
                "name": filing.company.name,
                "sector": filing.company.sector,
                "industry": filing.company.industry,
                "sp500_active": filing.company.sp500_active,
            }
            if filing.company
            else None,
            sections=[
                {
                    "id": section.id,
                    "filing_id": section.filing_id,
                    "section_code": section.section_code,
                    "section_name": section.section_name,
                    "content_text": section.content_text,
                    "extraction_status": section.extraction_status,
                }
                for section in filing.sections
            ],
            ai_runs=[
                {
                    "id": ai_run.id,
                    "filing_id": ai_run.filing_id,
                    "run_type": ai_run.run_type,
                    "model_name": ai_run.model_name,
                    "prompt_version": ai_run.prompt_version,
                    "schema_version": ai_run.schema_version,
                    "status": ai_run.status,
                    "raw_response": ai_run.raw_response,
                    "error_message": ai_run.error_message,
                }
                for ai_run in filing.ai_runs
            ],
        )
        return response.model_dump(mode="json")

    def _get_or_create_company(self, ticker: str, cik: str) -> Company:
        company = self.session.scalar(select(Company).where(Company.cik == cik))
        normalized_ticker = ticker.strip().upper()

        if company is None:
            company = Company(ticker=normalized_ticker, cik=cik.strip())
            self.session.add(company)
            self.session.flush()
            return company

        company.ticker = normalized_ticker
        return company

    def list_active_companies(self) -> list[Company]:
        return list(
            self.session.scalars(
                select(Company).where(Company.sp500_active.is_(True)).order_by(Company.ticker)
            )
        )

    def _upsert_filing_from_payload(
        self, company: Company, payload: dict[str, object]
    ) -> Filing | None:
        accession_no = str(
            payload.get("accessionNo") or payload.get("accession_number") or ""
        ).strip()
        if not accession_no:
            return None

        filing = self.session.scalar(
            select(Filing).where(Filing.accession_no == accession_no)
        )

        filing_url = (
            payload.get("linkToFilingDetails")
            or payload.get("filing_index_url")
            or payload.get("linkToHtml")
            or payload.get("primary_document_url")
            or payload.get("submission_text_url")
            or payload.get("filingUrl")
        )
        form_type = str(payload.get("formType") or payload.get("form_type") or "10-Q")
        filed_at_value = payload.get("filedAt") or payload.get("filing_date")
        period_of_report = payload.get("periodOfReport") or payload.get("period_of_report")

        if filing is None:
            filing = Filing(
                company_id=company.id,
                accession_no=accession_no,
                form_type=form_type,
                filed_at=self._parse_datetime(filed_at_value),
                period_of_report=self._parse_date(period_of_report),
                filing_url=str(filing_url) if filing_url else None,
                source_payload=payload,
                processing_status="pending_extraction",
            )
            self.session.add(filing)
            self.session.flush()
            return filing

        filing.company_id = company.id
        filing.form_type = form_type
        filing.filed_at = self._parse_datetime(filed_at_value)
        filing.period_of_report = self._parse_date(period_of_report)
        filing.filing_url = str(filing_url) if filing_url else filing.filing_url
        filing.source_payload = payload
        return filing

    @staticmethod
    def _parse_datetime(value: object | None) -> datetime:
        if value is None:
            return datetime.now(tz=UTC)

        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    @staticmethod
    def _parse_date(value: object | None) -> date | None:
        if value in (None, ""):
            return None
        raw_value = str(value)
        try:
            return date.fromisoformat(raw_value)
        except ValueError:
            return datetime.fromisoformat(raw_value).date()

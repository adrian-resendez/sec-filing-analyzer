from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from apps.api.clients.market_data_client import MassiveClient
from apps.api.models.ai_run import AIRun
from apps.api.models.company import Company
from apps.api.models.filing import Filing

SECTION_LABELS = {
    "part1item2": "Management Discussion & Analysis",
    "part2item1a": "Risk Factors",
}


class CompanyResearchService:
    def __init__(
        self, session: Session, market_data_client: MassiveClient | None = None
    ) -> None:
        self.session = session
        self.market_data_client = market_data_client or MassiveClient()

    def list_companies(
        self,
        search: str = "",
        only_with_filings: bool = False,
    ) -> list[dict[str, Any]]:
        statement = (
            select(Company)
            .options(
                selectinload(Company.filings).selectinload(Filing.ai_runs),
            )
            .where(Company.sp500_active.is_(True))
            .order_by(Company.ticker.asc())
        )
        companies = list(self.session.scalars(statement))

        normalized_search = search.strip().lower()
        items: list[dict[str, Any]] = []
        for company in companies:
            filing_count = len(company.filings)
            analyzed_count = sum(
                1 for filing in company.filings if self._latest_completed_ai_run(filing)
            )
            if only_with_filings and filing_count == 0:
                continue
            if normalized_search and normalized_search not in (
                f"{company.ticker} {company.name or ''} {company.sector or ''} {company.industry or ''}"
            ).lower():
                continue

            latest_filing = max(company.filings, key=lambda item: item.filed_at) if company.filings else None
            items.append(
                {
                    "ticker": company.ticker,
                    "name": company.name,
                    "sector": company.sector,
                    "industry": company.industry,
                    "filing_count": filing_count,
                    "analyzed_count": analyzed_count,
                    "latest_filed_at": latest_filing.filed_at.isoformat() if latest_filing else None,
                    "latest_status": latest_filing.processing_status if latest_filing else "no_filings",
                }
            )

        return sorted(
            items,
            key=lambda item: (
                item["analyzed_count"] == 0,
                item["filing_count"] == 0,
                item["ticker"],
            ),
        )

    async def get_company_workspace(self, ticker: str) -> dict[str, Any]:
        company = self.session.scalar(
            select(Company)
            .options(
                selectinload(Company.filings).selectinload(Filing.ai_runs),
                selectinload(Company.filings).selectinload(Filing.sections),
            )
            .where(Company.ticker == ticker.strip().upper())
        )

        if company is None:
            raise ValueError(f"Ticker {ticker.strip().upper()} was not found")

        filings = sorted(company.filings, key=lambda item: item.filed_at, reverse=True)
        serialized_filings = [self._serialize_filing(company, filing) for filing in filings]
        analyzed_count = sum(
            1 for filing in filings if self._latest_completed_ai_run(filing) is not None
        )

        try:
            market = await self.market_data_client.get_company_market_snapshot(company.ticker)
        except Exception as exc:
            # Log the exception with traceback so operators can inspect the cause
            import logging

            logging.exception("Failed to fetch market data for %s: %s", company.ticker, exc)
            market = {
                "error": (
                    "Polygon market data is unavailable right now. "
                    "The filing workspace still works from local PostgreSQL data."
                ),
                "history": [],
            }

        return {
            "company": {
                "ticker": company.ticker,
                "name": company.name,
                "sector": company.sector,
                "industry": company.industry,
                "exchange": company.exchange,
                "security_category": company.security_category,
            },
            "coverage": {
                "filing_count": len(filings),
                "analyzed_count": analyzed_count,
            },
            "market": market,
            "summary": self._build_company_summary(company, filings),
            "filings": serialized_filings,
        }

    def _serialize_filing(self, company: Company, filing: Filing) -> dict[str, Any]:
        ai_run = self._latest_completed_ai_run(filing)
        insight = ai_run.raw_response if ai_run else None
        section_map = {
            section.section_code: section.section_name or SECTION_LABELS.get(section.section_code, section.section_code)
            for section in filing.sections
        }

        return {
            "id": str(filing.id),
            "ticker": company.ticker,
            "accession_no": filing.accession_no,
            "form_type": filing.form_type,
            "filed_at": filing.filed_at.isoformat(),
            "processing_status": filing.processing_status,
            "filing_url": filing.filing_url,
            "source_links": self._build_source_links(filing),
            "insight": {
                "executive_summary": insight.get("executive_summary") if insight else None,
                "sentiment": insight.get("sentiment") if insight else None,
                "confidence": insight.get("confidence") if insight else None,
                "investor_pros": insight.get("investor_pros") if insight else [],
                "investor_cons": insight.get("investor_cons") if insight else [],
                "themes": [
                    {
                        **theme,
                        "evidence": [
                            {
                                **evidence,
                                "section_name": section_map.get(
                                    evidence.get("section_code", ""),
                                    SECTION_LABELS.get(evidence.get("section_code", ""), evidence.get("section_code", "")),
                                ),
                            }
                            for evidence in theme.get("evidence", [])
                        ],
                    }
                    for theme in (insight.get("themes") if insight else [])
                ],
                "key_risks": insight.get("key_risks") if insight else [],
                "key_opportunities": insight.get("key_opportunities") if insight else [],
            }
            if insight
            else None,
            "citations": self._build_filing_citations(filing, insight, section_map),
        }

    def _build_company_summary(
        self, company: Company, filings: list[Filing]
    ) -> dict[str, Any]:
        analyzed_filings = [
            filing for filing in filings if self._latest_completed_ai_run(filing) is not None
        ]
        if not analyzed_filings:
            return {
                "headline": f"No stored AI summary yet for {company.ticker}",
                "subheadline": "Market data is still available, but this company does not yet have a completed local quarterly analysis.",
                "sections": [
                    {
                        "title": "Coverage Status",
                        "paragraphs": [
                            (
                                f"{company.name or company.ticker} is in your local S&P 500 universe, "
                                "but there is no completed AI summary saved yet for its recent 10-Q filings. "
                                "Once a filing is analyzed, this workspace will surface a fuller research narrative with citations."
                            )
                        ],
                        "citations": [],
                    }
                ],
            }

        latest_filing = analyzed_filings[0]
        latest_run = self._latest_completed_ai_run(latest_filing)
        latest_insight = latest_run.raw_response if latest_run else {}

        headline = latest_insight.get("executive_summary") or (
            f"{company.name or company.ticker} has {len(analyzed_filings)} analyzed filing(s) stored locally."
        )
        positive_items = self._normalize_items(
            latest_insight.get("investor_pros", []),
            latest_insight.get("key_opportunities", []),
        )
        risk_items = self._normalize_items(
            latest_insight.get("investor_cons", []),
            latest_insight.get("key_risks", []),
        )
        top_themes = self._top_themes(analyzed_filings)
        sentiment_values = [
            self._latest_completed_ai_run(filing).raw_response.get("sentiment")
            for filing in analyzed_filings
            if self._latest_completed_ai_run(filing)
        ]

        sections = [
            {
                "title": "Quarterly Overview",
                "paragraphs": [
                    headline,
                    (
                        f"The latest local read on {company.ticker} comes from the 10-Q filed "
                        f"{self._format_date(latest_filing.filed_at)}. "
                        f"The stored model sentiment is {latest_insight.get('sentiment', 'unrated')}, "
                        f"with a confidence score of {self._format_confidence(latest_insight.get('confidence'))}."
                    ),
                ],
                "citations": self._build_filing_citations(
                    latest_filing,
                    latest_insight,
                    self._section_map(latest_filing),
                    limit=4,
                ),
            },
            {
                "title": "What Is Going Right",
                "paragraphs": [
                    self._items_to_paragraph(
                        f"In the latest filing, the strongest constructive signals for {company.ticker}",
                        positive_items,
                    ),
                    (
                        f"Across the stored analyzed quarters, the themes appearing most often are "
                        f"{self._join_phrases(top_themes) if top_themes else 'not yet stable enough to rank confidently'}. "
                        "That gives you a quick sense of what management keeps returning to when explaining performance."
                    ),
                ],
                "citations": self._collect_theme_citations(latest_filing, latest_insight, limit=4),
            },
            {
                "title": "What Needs Watching",
                "paragraphs": [
                    self._items_to_paragraph(
                        f"The main watch items flagged in the latest local analysis for {company.ticker}",
                        risk_items,
                    ),
                    (
                        "Risk citations below are pulled directly from the evidence snippets attached "
                        "to the stored filing analysis, with section names preserved so you can trace "
                        "the claim back to MD&A or Risk Factors quickly."
                    ),
                ],
                "citations": self._collect_theme_citations(
                    latest_filing, latest_insight, negative_only=True, limit=4
                ),
            },
            {
                "title": "Across Stored Quarters",
                "paragraphs": [
                    (
                        f"You currently have {len(analyzed_filings)} analyzed filing(s) for {company.ticker}. "
                        f"Sentiment across those filings has ranged through {self._join_phrases(sorted(set(sentiment_values)))}."
                    ),
                    (
                        "Treat this as a growing local research file rather than a finished archive. "
                        "As additional quarters are added, this section will get more useful for trend work, "
                        "especially around recurring themes, changing risk language, and eventual price reaction overlays."
                    ),
                ],
                "citations": [
                    self._basic_citation(filing, "Quarterly filing")
                    for filing in analyzed_filings[:4]
                ],
            },
        ]

        return {
            "headline": headline,
            "subheadline": (
                f"{company.name or company.ticker} | {len(analyzed_filings)} analyzed quarter(s) | "
                "citations are drawn from saved local filing evidence."
            ),
            "sections": sections,
        }

    @staticmethod
    def _latest_completed_ai_run(filing: Filing) -> AIRun | None:
        completed = [run for run in filing.ai_runs if run.status == "completed"]
        if not completed:
            return None
        return max(completed, key=lambda run: run.updated_at)

    @staticmethod
    def _build_source_links(filing: Filing) -> list[dict[str, str]]:
        links: list[dict[str, str]] = []
        source_payload = filing.source_payload or {}
        candidates = [
            ("Filing index", filing.filing_url),
            ("Primary document", source_payload.get("primary_document_url")),
            ("Submission text", source_payload.get("submission_text_url")),
            ("SEC details", source_payload.get("linkToFilingDetails")),
        ]
        seen: set[str] = set()
        for label, url in candidates:
            if not url or url in seen:
                continue
            links.append({"label": label, "url": str(url)})
            seen.add(str(url))
        return links

    def _build_filing_citations(
        self,
        filing: Filing,
        insight: dict[str, Any] | None,
        section_map: dict[str, str],
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []
        if insight:
            for theme in insight.get("themes", []):
                for evidence in theme.get("evidence", []):
                    citations.append(
                        self._evidence_citation(
                            filing=filing,
                            section_code=str(evidence.get("section_code", "")),
                            section_name=section_map.get(
                                str(evidence.get("section_code", "")),
                                SECTION_LABELS.get(str(evidence.get("section_code", "")), "Filing Section"),
                            ),
                            excerpt=str(evidence.get("excerpt", "")).strip(),
                        )
                    )
                    if len(citations) >= limit:
                        return citations
        if not citations:
            citations.append(self._basic_citation(filing, "Quarterly filing"))
        return citations[:limit]

    def _collect_theme_citations(
        self,
        filing: Filing,
        insight: dict[str, Any] | None,
        negative_only: bool = False,
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        if not insight:
            return [self._basic_citation(filing, "Quarterly filing")]

        section_map = self._section_map(filing)
        citations: list[dict[str, Any]] = []
        for theme in insight.get("themes", []):
            direction = str(theme.get("direction", "")).lower()
            if negative_only and direction == "positive":
                continue
            for evidence in theme.get("evidence", []):
                section_code = str(evidence.get("section_code", ""))
                citations.append(
                    self._evidence_citation(
                        filing=filing,
                        section_code=section_code,
                        section_name=section_map.get(section_code, SECTION_LABELS.get(section_code, section_code)),
                        excerpt=str(evidence.get("excerpt", "")).strip(),
                    )
                )
                if len(citations) >= limit:
                    return citations
        return citations or [self._basic_citation(filing, "Quarterly filing")]

    @staticmethod
    def _section_map(filing: Filing) -> dict[str, str]:
        return {
            section.section_code: section.section_name or SECTION_LABELS.get(section.section_code, section.section_code)
            for section in filing.sections
        }

    def _evidence_citation(
        self,
        filing: Filing,
        section_code: str,
        section_name: str,
        excerpt: str,
    ) -> dict[str, Any]:
        return {
            "label": f"{filing.form_type} filed {self._format_date(filing.filed_at)}",
            "accession_no": filing.accession_no,
            "section_code": section_code,
            "section_name": section_name,
            "excerpt": excerpt,
            "url": filing.filing_url,
        }

    def _basic_citation(self, filing: Filing, section_name: str) -> dict[str, Any]:
        return {
            "label": f"{filing.form_type} filed {self._format_date(filing.filed_at)}",
            "accession_no": filing.accession_no,
            "section_code": "",
            "section_name": section_name,
            "excerpt": "",
            "url": filing.filing_url,
        }

    @staticmethod
    def _top_themes(filings: list[Filing], limit: int = 3) -> list[str]:
        counter: Counter[str] = Counter()
        for filing in filings:
            ai_run = CompanyResearchService._latest_completed_ai_run(filing)
            if ai_run is None:
                continue
            counter.update(theme.get("theme", "") for theme in ai_run.raw_response.get("themes", []))
        return [theme.replace("_", " ") for theme, _ in counter.most_common(limit) if theme]

    @staticmethod
    def _normalize_items(*groups: list[str]) -> list[str]:
        items: list[str] = []
        seen: set[str] = set()
        for group in groups:
            for item in group or []:
                cleaned = str(item).strip().rstrip(".")
                if not cleaned:
                    continue
                if cleaned.lower() in seen:
                    continue
                items.append(cleaned)
                seen.add(cleaned.lower())
        return items[:6]

    def _items_to_paragraph(self, intro: str, items: list[str]) -> str:
        if not items:
            return (
                f"{intro} are not yet rich enough in the saved local analysis to produce a strong "
                "ranked list, so this section should be treated as provisional."
            )
        return f"{intro} include {self._join_phrases(items)}."

    @staticmethod
    def _join_phrases(items: list[str]) -> str:
        cleaned = [item for item in items if item]
        if not cleaned:
            return "no clear themes"
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return f"{cleaned[0]} and {cleaned[1]}"
        return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"

    @staticmethod
    def _format_date(value: datetime) -> str:
        return value.strftime("%b %d, %Y")

    @staticmethod
    def _format_confidence(value: Any) -> str:
        if value is None:
            return "n/a"
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api.clients.openai_client import OpenAIClient
from apps.api.models.ai_run import AIRun
from apps.api.models.filing import Filing
from apps.api.models.filing_section import FilingSection

PROMPT_VERSION = "v1"
SCHEMA_VERSION = "v1"


class InsightService:
    def __init__(
        self, session: Session, openai_client: OpenAIClient | None = None
    ) -> None:
        self.session = session
        self.openai_client = openai_client or OpenAIClient()

    async def analyze_filing_sections(
        self, filing: Filing, sections: list[FilingSection]
    ) -> AIRun:
        analysis_input = self._build_analysis_input(sections)
        ai_run = AIRun(
            filing_id=filing.id,
            run_type="filing_insight",
            model_name=self.openai_client.model_name,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            status="running",
            raw_response={"status": "running"},
        )
        self.session.add(ai_run)
        filing.processing_status = "analyzing"
        self.session.commit()
        self.session.refresh(ai_run)

        try:
            insight = await self.openai_client.analyze_sections(analysis_input)
            ai_run.status = "completed"
            ai_run.raw_response = insight.model_dump(mode="json")
            ai_run.error_message = None
            filing.processing_status = "analyzed"
        except Exception as exc:
            ai_run.status = "failed"
            ai_run.raw_response = {"error": str(exc)}
            ai_run.error_message = str(exc)
            filing.processing_status = "analysis_failed"
            self.session.add(ai_run)
            self.session.add(filing)
            self.session.commit()
            raise

        self.session.add(ai_run)
        self.session.add(filing)
        self.session.commit()
        self.session.refresh(ai_run)
        return ai_run

    @staticmethod
    def _build_analysis_input(sections: list[FilingSection]) -> str:
        blocks: list[str] = []
        for section in sections:
            content = (section.content_text or "").strip()
            if not content:
                continue
            blocks.append(
                "\n".join(
                    [
                        f"SECTION_CODE: {section.section_code}",
                        f"SECTION_NAME: {section.section_name or section.section_code}",
                        "CONTENT:",
                        content,
                    ]
                )
            )

        if not blocks:
            raise ValueError("At least one non-empty section is required for AI analysis")

        return "\n\n".join(blocks)

from __future__ import annotations

import json

from google import genai
from google.genai import types
from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from apps.api.config import get_settings
from apps.api.schemas.insight import InsightResponse
from apps.api.utils.logging import get_logger

logger = get_logger(__name__)


class AIClientError(Exception):
    pass

INSIGHT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "executive_summary": {"type": "string"},
        "investor_pros": {"type": "array", "items": {"type": "string"}},
        "investor_cons": {"type": "array", "items": {"type": "string"}},
        "sentiment": {
            "type": "string",
            "enum": ["bullish", "bearish", "neutral"],
        },
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "theme": {
                        "type": "string",
                        "enum": [
                            "growth",
                            "cost_pressures",
                            "macro_exposure",
                            "regulatory_risk",
                            "innovation",
                        ],
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["positive", "negative", "mixed"],
                    },
                    "strength": {"type": "number"},
                    "summary": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "section_code": {"type": "string"},
                                "excerpt": {"type": "string"},
                            },
                            "required": ["section_code", "excerpt"],
                        },
                    },
                },
                "required": ["theme", "direction", "strength", "summary", "evidence"],
            },
        },
        "key_risks": {"type": "array", "items": {"type": "string"}},
        "key_opportunities": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": [
        "executive_summary",
        "investor_pros",
        "investor_cons",
        "sentiment",
        "themes",
        "key_risks",
        "key_opportunities",
        "confidence",
    ],
}


class OpenAIClient:
    def __init__(
        self, api_key: str | None = None, model_name: str | None = None
    ) -> None:
        settings = get_settings()
        self.provider = settings.ai_provider.strip().lower()

        if self.provider == "gemini":
            self.api_key = api_key or settings.gemini_api_key
            self.model_name = model_name or settings.gemini_model
            self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        else:
            self.api_key = api_key or settings.openai_api_key
            self.model_name = model_name or settings.openai_model
            self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    @retry(
        reraise=True,
        retry=retry_if_exception_type((RuntimeError, ValidationError, AIClientError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
    )
    async def analyze_sections(self, text: str) -> InsightResponse:
        if self.client is None:
            if self.provider == "gemini":
                raise RuntimeError("GEMINI_API_KEY is required")
            raise RuntimeError("OPENAI_API_KEY is required")

        if self.provider == "gemini":
            return await self._analyze_with_gemini(text)
        return await self._analyze_with_openai(text)

    async def _analyze_with_openai(self, text: str) -> InsightResponse:
        try:
            response = await self.client.responses.create(
                model=self.model_name,
                reasoning={"effort": "medium"},
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "You are a financial filings analyst focused on SEC 10-Qs. "
                                    "Return only schema-valid output. Base every claim on the "
                                    "provided filing sections. Use the allowed themes only."
                                ),
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "Analyze the following 10-Q filing sections and produce "
                                    "structured investor insights. Consider management tone, "
                                    "growth drivers, cost pressures, macro exposure, regulatory "
                                    "risk, and innovation signals.\n\n"
                                    f"{text}"
                                ),
                            }
                        ],
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "filing_insight",
                        "strict": True,
                        "schema": INSIGHT_SCHEMA,
                    }
                },
            )
        except OpenAIError as exc:
            raise AIClientError(str(exc)) from exc

        payload = json.loads(response.output_text)
        parsed = InsightResponse.model_validate(payload)
        logger.info("Generated %s insight with model=%s", self.provider, self.model_name)
        return parsed

    async def _analyze_with_gemini(self, text: str) -> InsightResponse:
        prompt = (
            "You are a financial filings analyst focused on SEC 10-Qs. "
            "Return only structured investor insights that strictly match the schema. "
            "Base every claim on the provided filing sections. Use only the allowed theme labels.\n\n"
            f"{text}"
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=INSIGHT_SCHEMA,
                ),
            )
        except Exception as exc:
            raise AIClientError(str(exc)) from exc

        if not response.text:
            raise AIClientError("Gemini returned an empty response")

        payload = json.loads(response.text)
        parsed = InsightResponse.model_validate(payload)
        logger.info("Generated %s insight with model=%s", self.provider, self.model_name)
        return parsed

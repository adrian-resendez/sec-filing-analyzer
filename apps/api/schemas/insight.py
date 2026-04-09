from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ThemeEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_code: str
    excerpt: str


class ThemeInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: Literal[
        "growth",
        "cost_pressures",
        "macro_exposure",
        "regulatory_risk",
        "innovation",
    ]
    direction: Literal["positive", "negative", "mixed"]
    strength: float
    summary: str
    evidence: list[ThemeEvidence]


class InsightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    investor_pros: list[str]
    investor_cons: list[str]
    sentiment: Literal["bullish", "bearish", "neutral"]
    themes: list[ThemeInsight]
    key_risks: list[str]
    key_opportunities: list[str]
    confidence: float

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SecXbrlFactValueSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    end: str | None = None
    value: float | int | str | None = None
    filed: str | None = None
    form: str | None = None
    fy: int | None = None
    fp: str | None = None
    frame: str | None = None
    accession_number: str | None = None


class SecXbrlUnitSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: str
    values: list[SecXbrlFactValueSchema]


class SecXbrlConceptSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    taxonomy: str
    tag: str
    label: str | None = None
    description: str | None = None
    units: list[SecXbrlUnitSchema]


class SecXbrlResponseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    cik: str
    entity_name: str | None = None
    concepts: list[SecXbrlConceptSchema]

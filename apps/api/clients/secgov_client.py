from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx
from redis import Redis
from redis.exceptions import RedisError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from apps.api.config import get_settings

DEFAULT_USER_AGENT = "FilingIntelligence/1.0 (ops@filing-intelligence.local)"
CACHE_TTL_SECONDS = 6 * 60 * 60
MIN_REQUEST_INTERVAL_SECONDS = 0.11


@dataclass(slots=True)
class SecGovClientError(Exception):
    message: str
    status_code: int = 502

    def __str__(self) -> str:
        return self.message


class _RateLimiter:
    _lock = threading.Lock()
    _next_request_at = 0.0

    @classmethod
    async def wait_turn(cls) -> None:
        delay = 0.0
        with cls._lock:
            now = time.monotonic()
            if now < cls._next_request_at:
                delay = cls._next_request_at - now
            cls._next_request_at = max(now, cls._next_request_at) + MIN_REQUEST_INTERVAL_SECONDS

        if delay > 0:
            await asyncio.sleep(delay)


class SecGovClient:
    base_url = "https://data.sec.gov"

    def __init__(
        self,
        user_agent: str | None = None,
        redis_client: Redis | None = None,
    ) -> None:
        settings = get_settings()
        self.user_agent = user_agent or getattr(settings, "sec_user_agent", None) or DEFAULT_USER_AGENT
        self.redis_client = redis_client if redis_client is not None else self._build_redis_client(settings.redis_url)

    async def get_company_submissions(
        self, cik: str, force_refresh: bool = False
    ) -> dict[str, Any]:
        padded_cik = self.pad_cik(cik)
        cache_key = f"secgov:submissions:{padded_cik}"

        if not force_refresh:
            cached = await self._cache_get(cache_key)
            if cached is not None:
                return cached

        payload = await self._fetch_json(f"/submissions/CIK{padded_cik}.json")
        await self._cache_set(cache_key, payload)
        return payload

    async def get_company_facts(
        self, cik: str, force_refresh: bool = False
    ) -> dict[str, Any]:
        padded_cik = self.pad_cik(cik)
        cache_key = f"secgov:companyfacts:{padded_cik}"

        if not force_refresh:
            cached = await self._cache_get(cache_key)
            if cached is not None:
                return cached

        payload = await self._fetch_json(f"/api/xbrl/companyfacts/CIK{padded_cik}.json")
        await self._cache_set(cache_key, payload)
        return payload

    async def invalidate_cache(self, cik: str) -> None:
        padded_cik = self.pad_cik(cik)
        if self.redis_client is None:
            return

        try:
            await asyncio.to_thread(
                self.redis_client.delete,
                f"secgov:submissions:{padded_cik}",
                f"secgov:companyfacts:{padded_cik}",
            )
        except RedisError:
            return

    @staticmethod
    def pad_cik(cik: str) -> str:
        digits_only = "".join(character for character in str(cik) if character.isdigit())
        if not digits_only:
            raise SecGovClientError("A valid CIK is required", status_code=400)
        return digits_only.zfill(10)

    @classmethod
    def normalize_company_metadata(
        cls, submissions_payload: dict[str, Any], filing_limit: int = 20
    ) -> dict[str, Any]:
        filings = cls.normalize_filings(submissions_payload, filing_limit=filing_limit)
        tickers = submissions_payload.get("tickers") or []
        exchanges = submissions_payload.get("exchanges") or []

        return {
            "cik": cls.pad_cik(str(submissions_payload.get("cik", ""))),
            "name": submissions_payload.get("name"),
            "sic": submissions_payload.get("sic"),
            "sic_description": submissions_payload.get("sicDescription"),
            "tickers": [str(item) for item in tickers],
            "exchanges": [str(item) for item in exchanges],
            "filings": filings,
        }

    @classmethod
    def normalize_filings(
        cls,
        submissions_payload: dict[str, Any],
        filing_limit: int = 100,
        form_type: str | None = None,
    ) -> list[dict[str, Any]]:
        recent = submissions_payload.get("filings", {}).get("recent", {})
        accession_numbers = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        primary_documents = recent.get("primaryDocument", [])

        count = min(
            len(accession_numbers),
            len(forms),
            len(filing_dates),
            len(primary_documents),
        )

        cik_no_padding = str(submissions_payload.get("cik", "")).lstrip("0")
        filings: list[dict[str, Any]] = []
        for index in range(count):
            current_form = str(forms[index])
            if form_type and current_form.upper() != form_type.upper():
                continue

            accession_number = str(accession_numbers[index])
            accession_no_dashes = accession_number.replace("-", "")
            primary_document = str(primary_documents[index])
            archive_base = (
                f"https://www.sec.gov/Archives/edgar/data/{cik_no_padding}/{accession_no_dashes}"
            )

            filings.append(
                {
                    "accession_number": accession_number,
                    "form_type": current_form,
                    "filing_date": str(filing_dates[index]),
                    "primary_document": primary_document,
                    "primary_document_url": f"{archive_base}/{primary_document}",
                    "filing_index_url": f"{archive_base}/{accession_number}-index.html",
                    "submission_text_url": f"{archive_base}/{accession_number}.txt",
                }
            )

            if len(filings) >= filing_limit:
                break

        return filings

    @classmethod
    def normalize_company_facts(
        cls,
        company_facts_payload: dict[str, Any],
        taxonomy_filter: str | None = None,
        concept_limit: int = 25,
        fact_limit: int = 10,
    ) -> dict[str, Any]:
        facts = company_facts_payload.get("facts", {})
        concepts: list[dict[str, Any]] = []

        taxonomies = sorted(facts.keys())
        for taxonomy in taxonomies:
            if taxonomy_filter and taxonomy != taxonomy_filter:
                continue

            for tag, concept in sorted(facts.get(taxonomy, {}).items()):
                units_payload = concept.get("units", {})
                units: list[dict[str, Any]] = []
                for unit_name, values in units_payload.items():
                    normalized_values = [
                        {
                            "end": value.get("end"),
                            "value": value.get("val"),
                            "filed": value.get("filed"),
                            "form": value.get("form"),
                            "fy": value.get("fy"),
                            "fp": value.get("fp"),
                            "frame": value.get("frame"),
                            "accession_number": value.get("accn"),
                        }
                        for value in values[:fact_limit]
                    ]
                    units.append({"unit": unit_name, "values": normalized_values})

                concepts.append(
                    {
                        "taxonomy": taxonomy,
                        "tag": tag,
                        "label": concept.get("label"),
                        "description": concept.get("description"),
                        "units": units,
                    }
                )

                if len(concepts) >= concept_limit:
                    return {
                        "cik": cls.pad_cik(str(company_facts_payload.get("cik", ""))),
                        "entity_name": company_facts_payload.get("entityName"),
                        "concepts": concepts,
                    }

        return {
            "cik": cls.pad_cik(str(company_facts_payload.get("cik", ""))),
            "entity_name": company_facts_payload.get("entityName"),
            "concepts": concepts,
        }

    @retry(
        reraise=True,
        retry=retry_if_exception(
            lambda exc: isinstance(exc, httpx.TimeoutException)
            or (
                isinstance(exc, SecGovClientError)
                and exc.status_code in {502, 503, 504}
            )
        ),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _fetch_json(self, path: str) -> dict[str, Any]:
        await _RateLimiter.wait_turn()

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Host": "data.sec.gov",
        }

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(20.0, connect=10.0),
                follow_redirects=True,
            ) as client:
                response = await client.get(path)
        except httpx.TimeoutException as exc:
            raise exc
        except httpx.HTTPError as exc:
            raise SecGovClientError(f"SEC request failed: {exc}", status_code=502) from exc

        if response.status_code == 404:
            raise SecGovClientError("SEC resource not found", status_code=404)
        if response.status_code in {403, 429, 500, 502, 503, 504}:
            raise SecGovClientError(
                f"SEC request returned status {response.status_code}",
                status_code=502,
            )
        if response.status_code >= 400:
            raise SecGovClientError(
                f"SEC request failed with status {response.status_code}",
                status_code=502,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise SecGovClientError("SEC response was not valid JSON", status_code=502) from exc

        if not isinstance(payload, dict):
            raise SecGovClientError("SEC response JSON had an unexpected structure", status_code=502)

        return payload

    async def _cache_get(self, key: str) -> dict[str, Any] | None:
        if self.redis_client is None:
            return None

        try:
            cached = await asyncio.to_thread(self.redis_client.get, key)
        except RedisError:
            return None

        if not cached:
            return None

        try:
            return json.loads(cached)
        except (TypeError, json.JSONDecodeError):
            return None

    async def _cache_set(self, key: str, payload: dict[str, Any]) -> None:
        if self.redis_client is None:
            return

        try:
            await asyncio.to_thread(
                self.redis_client.setex,
                key,
                CACHE_TTL_SECONDS,
                json.dumps(payload),
            )
        except RedisError:
            return

    @staticmethod
    def _build_redis_client(redis_url: str) -> Redis | None:
        try:
            return Redis.from_url(redis_url, decode_responses=True)
        except RedisError:
            return None

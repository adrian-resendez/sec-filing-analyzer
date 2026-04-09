from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from apps.api.config import get_settings
from apps.api.utils.logging import get_logger

logger = get_logger(__name__)


class SecApiClient:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.sec_api_key
        self.base_url = "https://api.sec-api.io"
        self.mapping_url = "https://api.sec-api.io/mapping"
        self.extractor_url = "https://api.sec-api.io/extractor"

    @retry(
        reraise=True,
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
    )
    async def search_10q_filings(
        self,
        cik: str,
        start_date: str,
        end_date: str,
        from_offset: int = 0,
        size: int = 50,
    ) -> dict[str, Any]:
        self._require_api_key()
        normalized_cik = cik.lstrip("0") or "0"

        payload = {
            "query": (
                f'cik:{normalized_cik} AND formType:"10-Q" '
                f"AND filedAt:[{start_date} TO {end_date}]"
            ),
            "from": str(from_offset),
            "size": str(size),
            "sort": [{"filedAt": {"order": "desc"}}],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url, json=payload, headers=self._headers()
            )
            response.raise_for_status()
            data = response.json()
            logger.info(
                "Fetched SEC filings for cik=%s start=%s end=%s offset=%s size=%s",
                normalized_cik,
                start_date,
                end_date,
                from_offset,
                size,
            )
            return data if isinstance(data, dict) else {"filings": data}

    @retry(
        reraise=True,
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
    )
    async def resolve_ticker(self, ticker: str) -> dict[str, Any] | None:
        self._require_api_key()
        normalized_ticker = ticker.strip().upper()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.mapping_url}/ticker/{normalized_ticker}",
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, list):
            return None

        exact_match = next(
            (
                item
                for item in payload
                if str(item.get("ticker", "")).upper() == normalized_ticker
                and not bool(item.get("isDelisted", False))
            ),
            None,
        )

        if exact_match is not None:
            logger.info("Resolved ticker %s to cik=%s", normalized_ticker, exact_match.get("cik"))
            return exact_match

        fallback = next(
            (
                item
                for item in payload
                if str(item.get("ticker", "")).upper() == normalized_ticker
            ),
            None,
        )
        logger.info("Resolved ticker %s using fallback mapping", normalized_ticker)
        return fallback

    @retry(
        reraise=True,
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
    )
    async def extract_section(self, filing_url: str, item_code: str) -> str:
        self._require_api_key()

        params = {
            "url": filing_url,
            "item": item_code,
            "type": "text",
            "token": self.api_key,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(self.extractor_url, params=params)
            response.raise_for_status()
            logger.info("Extracted filing section %s", item_code)
            return response.text.strip()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    def _require_api_key(self) -> None:
        if not self.api_key:
            raise RuntimeError("SEC_API_KEY is required")

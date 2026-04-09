# apps/api/clients/massive_client.py

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from apps.api.config import get_settings


class MarketDataClientError(Exception):
    """Raised when market data requests fail."""


class MassiveClient:
    hosts = ["https://api.massive.com"]

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.massive_api_key

    async def get_company_market_snapshot(self, ticker: str) -> dict[str, Any]:
        if not self.api_key:
            raise MarketDataClientError("MASSIVE_API_KEY is required")

        normalized_ticker = ticker.strip().upper()
        today = date.today()
        six_months_ago = today - timedelta(days=183)

        snapshot_payload = await self._fetch_json(
            f"/v2/snapshot/locale/us/markets/stocks/tickers/{normalized_ticker}"
        )

        history_payload = await self._fetch_json(
            f"/v2/aggs/ticker/{normalized_ticker}/range/1/day/"
            f"{six_months_ago.isoformat()}/{today.isoformat()}",
            params={
                "adjusted": "true",
                "sort": "asc",
                "limit": "5000",
            },
        )

        overview_payload = await self._fetch_json(
            f"/v3/reference/tickers/{normalized_ticker}"
        )

        return self._normalize_market_payload(
            ticker=normalized_ticker,
            snapshot_payload=snapshot_payload,
            history_payload=history_payload,
            overview_payload=overview_payload,
        )

    @retry(
        reraise=True,
        retry=retry_if_exception_type((httpx.HTTPError, MarketDataClientError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
    )
    async def _fetch_json(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        if not self.api_key:
            raise MarketDataClientError("Missing API key")

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        last_exc: Exception | None = None

        for host in self.hosts:
            try:
                async with httpx.AsyncClient(
                    base_url=host,
                    timeout=httpx.Timeout(20.0, connect=10.0),
                    follow_redirects=True,
                ) as client:
                    response = await client.get(path, params=params, headers=headers)

                if response.status_code >= 400:
                    raise MarketDataClientError(
                        f"{host}{path} -> {response.status_code}: {(response.text or '')[:300]}"
                    )

                payload = response.json()

                if not isinstance(payload, dict):
                    raise MarketDataClientError("Invalid response shape")

                return payload

            except (httpx.HTTPError, MarketDataClientError) as exc:
                last_exc = exc

        raise MarketDataClientError(f"All Massive requests failed: {last_exc}")

    @staticmethod
    def _normalize_market_payload(
        ticker: str,
        snapshot_payload: dict[str, Any],
        history_payload: dict[str, Any],
        overview_payload: dict[str, Any],
    ) -> dict[str, Any]:
        snapshot = snapshot_payload.get("ticker") or {}
        day = snapshot.get("day") or {}
        minute = snapshot.get("min") or {}
        prev_day = snapshot.get("prevDay") or {}
        last_trade = snapshot.get("lastTrade") or {}
        overview = overview_payload.get("results") or {}

        current_price = (
            last_trade.get("p")
            or minute.get("c")
            or day.get("c")
            or prev_day.get("c")
        )

        history_results = history_payload.get("results") or []

        history = [
            {
                "date": MassiveClient._timestamp_to_date(point.get("t")),
                "open": point.get("o"),
                "high": point.get("h"),
                "low": point.get("l"),
                "close": point.get("c"),
                "volume": point.get("v"),
            }
            for point in history_results
            if point.get("c") is not None and point.get("t") is not None
        ]

        first_close = history[0]["close"] if history else None
        last_close = history[-1]["close"] if history else current_price

        six_month_return = None
        six_month_low = None
        six_month_high = None

        if history:
            closes = [p["close"] for p in history if p["close"] is not None]
            if closes:
                six_month_low = min(closes)
                six_month_high = max(closes)
                if first_close:
                    six_month_return = ((last_close / first_close) - 1) * 100

        return {
            "ticker": ticker,
            "current_price": current_price,
            "today_change": snapshot.get("todaysChange"),
            "today_change_percent": snapshot.get("todaysChangePerc"),
            "previous_close": prev_day.get("c"),
            "open": day.get("o") or prev_day.get("o"),
            "high": day.get("h") or prev_day.get("h"),
            "low": day.get("l") or prev_day.get("l"),
            "volume": day.get("v") or prev_day.get("v"),
            "market_cap": overview.get("market_cap"),
            "shares_outstanding": overview.get("share_class_shares_outstanding"),
            "currency_name": overview.get("currency_name") or "USD",
            "homepage_url": overview.get("homepage_url"),
            "description": overview.get("description"),
            "six_month_return": six_month_return,
            "six_month_low": six_month_low,
            "six_month_high": six_month_high,
            "history": history,
        }

    @staticmethod
    def _timestamp_to_date(value: Any) -> str:
        if value is None:
            return ""
        return date.fromtimestamp(float(value) / 1000).isoformat()
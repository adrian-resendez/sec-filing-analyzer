# scripts/check_massive_api.py

from __future__ import annotations

import os
import httpx


BASE_URL = "https://api.massive.com"
TEST_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers/AAPL"


def try_massive(key: str) -> None:
    url = f"{BASE_URL}{TEST_PATH}"

    try:
        r = httpx.get(
            url,
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text[:500])
    except Exception as e:
        print("ERROR:", e)


def main() -> None:
    key = os.getenv("MASSIVE_API_KEY", "")

    if not key:
        print("❌ MASSIVE_API_KEY not set in environment")
        return

    print("🔍 Testing Massive API...\n")
    try_massive(key)


if __name__ == "__main__":
    main()
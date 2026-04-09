from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from apps.api.clients.secgov_client import SecGovClient


SUBMISSIONS_PAYLOAD = {
    "cik": "320193",
    "name": "Apple Inc.",
    "tickers": ["AAPL"],
    "exchanges": ["Nasdaq"],
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-25-000010"],
            "form": ["10-Q"],
            "filingDate": ["2025-02-01"],
            "primaryDocument": ["aapl-20241228x10q.htm"],
        }
    },
}

COMPANY_FACTS_PAYLOAD = {
    "cik": "320193",
    "entityName": "Apple Inc.",
    "facts": {
        "us-gaap": {
            "Assets": {
                "label": "Assets",
                "description": "Total assets",
                "units": {
                    "USD": [
                        {
                            "end": "2024-12-28",
                            "val": 364980000000,
                            "filed": "2025-02-01",
                            "form": "10-Q",
                            "fy": 2025,
                            "fp": "Q1",
                            "frame": "CY2024Q4I",
                            "accn": "0000320193-25-000010",
                        }
                    ]
                },
            }
        }
    },
}


class SecGovClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_company_submissions(self) -> None:
        client = SecGovClient(redis_client=None)

        with patch.object(
            SecGovClient,
            "_fetch_json",
            new=AsyncMock(return_value=SUBMISSIONS_PAYLOAD),
        ) as fetch_mock:
            payload = await client.get_company_submissions("320193")

        self.assertEqual(payload["name"], "Apple Inc.")
        fetch_mock.assert_awaited_once_with("/submissions/CIK0000320193.json")

    async def test_fetch_company_facts(self) -> None:
        client = SecGovClient(redis_client=None)

        with patch.object(
            SecGovClient,
            "_fetch_json",
            new=AsyncMock(return_value=COMPANY_FACTS_PAYLOAD),
        ) as fetch_mock:
            payload = await client.get_company_facts("320193")

        self.assertEqual(payload["entityName"], "Apple Inc.")
        fetch_mock.assert_awaited_once_with(
            "/api/xbrl/companyfacts/CIK0000320193.json"
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from apps.api.clients.secgov_client import SecGovClient
from apps.api.models.company import Company
from apps.api.routes.secgov import bp as secgov_bp
from flask import Flask


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
                "units": {"USD": [{"end": "2024-12-28", "val": 1}]},
            }
        }
    },
}


class SecGovRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = Flask(__name__)
        self.app.register_blueprint(secgov_bp)
        self.client = self.app.test_client()
        self.company = Company(
            ticker="AAPL",
            cik="0000320193",
            name="Apple Inc.",
            sp500_active=True,
        )

    def test_company_endpoint(self) -> None:
        with patch(
            "apps.api.routes.secgov._get_company_by_ticker",
            return_value=self.company,
        ), patch.object(
            SecGovClient, "get_company_submissions", new=AsyncMock(return_value=SUBMISSIONS_PAYLOAD)
        ):
            response = self.client.get("/api/v1/sec/company/AAPL")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["cik"], "0000320193")
        self.assertEqual(payload["filings"][0]["form_type"], "10-Q")

    def test_filings_endpoint(self) -> None:
        with patch(
            "apps.api.routes.secgov._get_company_by_ticker",
            return_value=self.company,
        ), patch.object(
            SecGovClient, "get_company_submissions", new=AsyncMock(return_value=SUBMISSIONS_PAYLOAD)
        ):
            response = self.client.get("/api/v1/sec/filings/AAPL?limit=5")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["ticker"], "AAPL")
        self.assertEqual(len(payload["filings"]), 1)

    def test_xbrl_endpoint(self) -> None:
        with patch(
            "apps.api.routes.secgov._get_company_by_ticker",
            return_value=self.company,
        ), patch.object(
            SecGovClient, "get_company_facts", new=AsyncMock(return_value=COMPANY_FACTS_PAYLOAD)
        ):
            response = self.client.get("/api/v1/sec/xbrl/AAPL")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        assert payload is not None
        self.assertEqual(payload["ticker"], "AAPL")
        self.assertEqual(payload["concepts"][0]["tag"], "Assets")


if __name__ == "__main__":
    unittest.main()

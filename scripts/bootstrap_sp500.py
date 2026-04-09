from __future__ import annotations

import argparse
import asyncio
import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from apps.api.clients.sec_api_client import SecApiClient
from apps.api.config import get_settings
from apps.api.extensions import get_session, initialize_database
from apps.api.models.company import Company
from apps.api.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)
DEFAULT_CSV_PATH = Path(__file__).resolve().parents[1] / "sp500_constituents.csv"


@dataclass(slots=True)
class ConstituencyRow:
    ticker: str
    name: str
    sector: str
    industry: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap S&P 500 companies into PostgreSQL.")
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_CSV_PATH),
        help="Path to the S&P 500 constituents CSV.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Concurrent mapping requests to sec-api.",
    )
    return parser.parse_args()


def load_rows(csv_path: Path) -> list[ConstituencyRow]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [
            ConstituencyRow(
                ticker=(row.get("ticker") or "").strip().upper(),
                name=(row.get("name") or "").strip(),
                sector=(row.get("sector") or "").strip(),
                industry=(row.get("industry") or "").strip(),
            )
            for row in reader
            if (row.get("ticker") or "").strip()
        ]

    if not rows:
        raise ValueError(f"No constituents were loaded from {csv_path}")

    return rows


async def resolve_rows(
    rows: list[ConstituencyRow], concurrency: int
) -> list[tuple[ConstituencyRow, dict[str, Any] | None]]:
    client = SecApiClient()
    semaphore = asyncio.Semaphore(concurrency)

    async def resolve(row: ConstituencyRow) -> tuple[ConstituencyRow, dict[str, Any] | None]:
        async with semaphore:
            try:
                mapping = await client.resolve_ticker(row.ticker)
                return row, mapping
            except Exception:
                logger.exception("Failed resolving ticker=%s", row.ticker)
                return row, None

    tasks = [resolve(row) for row in rows]
    return await asyncio.gather(*tasks)


def upsert_companies(
    resolved_rows: list[tuple[ConstituencyRow, dict[str, Any] | None]]
) -> dict[str, int]:
    session = get_session()
    csv_tickers = {row.ticker for row, _ in resolved_rows}
    inserted = 0
    updated = 0
    failed = 0
    today = date.today()

    try:
        for row, mapping in resolved_rows:
            if mapping is None:
                failed += 1
                logger.warning("Skipping ticker=%s because no mapping result was found", row.ticker)
                continue

            cik = str(mapping.get("cik", "")).strip()
            if not cik:
                failed += 1
                logger.warning("Skipping ticker=%s because no CIK was returned", row.ticker)
                continue

            normalized_cik = cik.zfill(10)
            company = session.scalar(
                select(Company).where(
                    (Company.ticker == row.ticker) | (Company.cik == normalized_cik)
                )
            )

            is_new = company is None
            if company is None:
                company = Company(
                    ticker=row.ticker,
                    cik=normalized_cik,
                    sp500_added_at=today,
                )
                session.add(company)

            company.ticker = row.ticker
            company.cik = normalized_cik
            company.name = str(mapping.get("name") or row.name or company.name or "").strip() or None
            company.sector = str(mapping.get("sector") or row.sector or "").strip() or None
            company.industry = str(mapping.get("industry") or row.industry or "").strip() or None
            company.exchange = str(mapping.get("exchange") or "").strip() or None
            company.security_category = str(mapping.get("category") or "").strip() or None
            company.sp500_active = True
            company.sp500_removed_at = None
            if company.sp500_added_at is None:
                company.sp500_added_at = today

            if is_new:
                inserted += 1
            else:
                updated += 1

            logger.info("Upserted company ticker=%s cik=%s", company.ticker, company.cik)

        active_companies = session.scalars(
            select(Company).where(Company.sp500_active.is_(True))
        )
        for company in active_companies:
            if company.ticker not in csv_tickers:
                company.sp500_active = False
                if company.sp500_removed_at is None:
                    company.sp500_removed_at = today
                logger.info("Marked company inactive ticker=%s", company.ticker)

        session.commit()
        return {"inserted": inserted, "updated": updated, "failed": failed}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    configure_logging()
    args = parse_args()
    csv_path = Path(args.csv_path).resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file was not found: {csv_path}")

    settings = get_settings()
    initialize_database(settings.database_url)

    rows = load_rows(csv_path)
    logger.info("Loaded %s rows from %s", len(rows), csv_path)
    resolved_rows = asyncio.run(resolve_rows(rows, args.concurrency))
    result = upsert_companies(resolved_rows)
    logger.info(
        "Bootstrap complete inserted=%s updated=%s failed=%s",
        result["inserted"],
        result["updated"],
        result["failed"],
    )


if __name__ == "__main__":
    main()

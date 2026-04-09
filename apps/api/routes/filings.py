from __future__ import annotations

import asyncio
import socket
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from sqlalchemy import select

from apps.api.config import get_settings
from apps.api.extensions import get_session
from apps.api.models.filing import Filing
from apps.api.schemas.filing import FilingDiscoveryRequest, FilingRecordResponse
from apps.api.services.filing_service import FilingService
from apps.api.utils.logging import get_logger
from apps.worker.tasks.backfill_filings import backfill_active_companies
from apps.worker.tasks.analyze_filing import analyze_filing as analyze_filing_task

bp = Blueprint("filings", __name__, url_prefix="/filings")
logger = get_logger(__name__)
PENDING_ANALYSIS_STATUSES = ("pending_extraction", "pending_analysis", "analysis_failed")


def _should_run_inline() -> bool:
    settings = get_settings()
    redis_url = (settings.redis_url or "").strip()
    if not redis_url:
        return True

    parsed = urlparse(redis_url)
    hostname = parsed.hostname or ""
    port = parsed.port or 6379

    if hostname in {"", "redis"}:
        return True

    try:
        with socket.create_connection((hostname, port), timeout=0.3):
            return False
    except OSError:
        return True


@bp.get("")
def list_filings() -> tuple[dict[str, object], int]:
    session = get_session()

    try:
        limit = int(request.args.get("limit", 25))
        filings = FilingService(session).list_recent_filings(limit=max(1, min(limit, 100)))
        data = [
            {
                "id": str(filing.id),
                "ticker": filing.company.ticker if filing.company else None,
                "company_name": filing.company.name if filing.company else None,
                "accession_no": filing.accession_no,
                "form_type": filing.form_type,
                "filed_at": filing.filed_at.isoformat(),
                "processing_status": filing.processing_status,
            }
            for filing in filings
        ]
        return jsonify({"filings": data}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    finally:
        session.close()


@bp.post("/discover")
def discover_filings() -> tuple[dict[str, object], int]:
    session = get_session()

    try:
        payload = FilingDiscoveryRequest.model_validate(request.get_json() or {})
        filings = asyncio.run(FilingService(session).discover_filings(payload))
        data = [
            FilingRecordResponse.model_validate(filing).model_dump(mode="json")
            for filing in filings
        ]
        return jsonify({"filings": data}), 201
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 400
    except Exception as exc:
        logger.exception("Failed to discover filings")
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()


@bp.get("/<filing_id>")
def get_filing(filing_id: str) -> tuple[dict[str, object], int]:
    session = get_session()

    try:
        service = FilingService(session)
        filing = service.get_filing(filing_id)
        if filing is None:
            return jsonify({"error": "filing not found"}), 404

        return jsonify(service.serialize_filing_detail(filing)), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Failed to load filing")
        return jsonify({"error": str(exc)}), 500
    finally:
        session.close()


@bp.post("/<filing_id>/analyze")
def queue_filing_analysis(filing_id: str) -> tuple[dict[str, str], int]:
    session = get_session()

    try:
        filing = FilingService(session).get_filing(filing_id)
        if filing is None:
            return jsonify({"error": "filing not found"}), 404

        if _should_run_inline():
            result = analyze_filing_task(filing_id)
            return (
                jsonify(
                    {
                        "filing_id": filing_id,
                        "status": "completed_inline",
                        "result": result,
                    }
                ),
                200,
            )

        try:
            task = analyze_filing_task.delay(filing_id)
            return (
                jsonify(
                    {
                        "task_id": task.id,
                        "filing_id": filing_id,
                        "status": "queued",
                    }
                ),
                202,
            )
        except Exception as exc:
            logger.warning(
                "Celery unavailable for filing_id=%s, running inline instead: %s",
                filing_id,
                exc,
            )
            result = analyze_filing_task(filing_id)
            return (
                jsonify(
                    {
                        "filing_id": filing_id,
                        "status": "completed_inline",
                        "result": result,
                    }
                ),
                200,
            )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    finally:
        session.close()


@bp.post("/analyze-pending")
def analyze_pending_filings() -> tuple[dict[str, object], int]:
    session = get_session()

    try:
        payload = request.get_json(silent=True) or {}
        limit = int(payload.get("limit", 25))
        limit = max(1, min(limit, 100))

        filings = list(
            session.scalars(
                select(Filing)
                .where(Filing.processing_status.in_(PENDING_ANALYSIS_STATUSES))
                .order_by(Filing.filed_at.desc())
                .limit(limit)
            )
        )

        if not filings:
            return jsonify({"status": "nothing_to_do", "completed": [], "failed": []}), 200

        if not _should_run_inline():
            try:
                queued = []
                for filing in filings:
                    task = analyze_filing_task.delay(str(filing.id))
                    queued.append(
                        {
                            "task_id": task.id,
                            "filing_id": str(filing.id),
                            "ticker": filing.company.ticker if filing.company else None,
                        }
                    )
                return jsonify({"status": "queued", "queued": queued}), 202
            except Exception as exc:
                logger.warning(
                    "Celery unavailable for bulk analysis, running inline instead: %s",
                    exc,
                )

        completed: list[dict[str, object]] = []
        failed: list[dict[str, object]] = []
        for filing in filings:
            queued = []
            try:
                result = analyze_filing_task(str(filing.id))
                completed.append(
                    {
                        "filing_id": str(filing.id),
                        "ticker": filing.company.ticker if filing.company else None,
                        "result": result,
                    }
                )
            except Exception as exc:
                logger.exception("Inline analysis failed for filing_id=%s", filing.id)
                failed.append(
                    {
                        "filing_id": str(filing.id),
                        "ticker": filing.company.ticker if filing.company else None,
                        "error": str(exc),
                    }
                )

        status_code = 200 if not failed else 207
        return (
            jsonify(
                {
                    "status": "completed_inline",
                    "completed": completed,
                    "failed": failed,
                }
            ),
            status_code,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    finally:
        session.close()


@bp.post("/backfill")
def queue_backfill() -> tuple[dict[str, object], int]:
    payload = request.get_json() or {}

    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    limit = payload.get("limit")

    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date are required"}), 400

    if not _should_run_inline():
        try:
            task = backfill_active_companies.delay(str(start_date), str(end_date), limit)
            return (
                jsonify(
                    {
                        "task_id": task.id,
                        "status": "queued",
                        "start_date": start_date,
                        "end_date": end_date,
                        "limit": limit,
                    }
                ),
                202,
            )
        except Exception as exc:
            logger.warning("Celery unavailable for backfill, running inline instead: %s", exc)

    session = get_session()
    try:
        service = FilingService(session)
        companies = service.list_active_companies()
        if limit is not None:
            companies = companies[: max(1, min(int(limit), 500))]

        async def run_inline() -> list[dict[str, object]]:
            results: list[dict[str, object]] = []
            failures: list[dict[str, object]] = []
            for company in companies:
                try:
                    filings = await service.backfill_10q_filings(
                        company=company,
                        start_date=str(start_date),
                        end_date=str(end_date),
                    )
                    results.append(
                        {
                            "company_id": str(company.id),
                            "ticker": company.ticker,
                            "filings_seen": len(filings),
                        }
                    )
                except Exception as exc:
                    logger.exception("Inline backfill failed for ticker=%s", company.ticker)
                    failures.append(
                        {
                            "company_id": str(company.id),
                            "ticker": company.ticker,
                            "error": str(exc),
                        }
                    )
            return {"results": results, "failures": failures}

        outcome = asyncio.run(run_inline())
        status_code = 200 if not outcome["failures"] else 207
        return (
            jsonify(
                {
                    "status": "completed_inline",
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": len(companies),
                    "results": outcome["results"],
                    "failures": outcome["failures"],
                }
            ),
            status_code,
        )
    finally:
        session.close()

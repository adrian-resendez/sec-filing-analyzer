from __future__ import annotations

import asyncio

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from apps.api.clients.secgov_client import SecGovClient, SecGovClientError
from apps.api.extensions import get_session
from apps.api.models.company import Company
from apps.api.schemas.sec_submission import SecCompanySchema, SecFilingsResponseSchema
from apps.api.schemas.sec_xbrl import SecXbrlResponseSchema

bp = Blueprint("secgov", __name__, url_prefix="/api/v1/sec")


def _get_company_by_ticker(ticker: str) -> Company | None:
    session = get_session()
    try:
        normalized_ticker = ticker.strip().upper()
        statement = select(Company).where(Company.ticker == normalized_ticker)
        return session.scalar(statement)
    finally:
        session.close()


def _should_refresh() -> bool:
    refresh_value = str(request.args.get("refresh", "")).strip().lower()
    return refresh_value in {"1", "true", "yes"}


@bp.get("/company/<ticker>")
def get_company(ticker: str) -> tuple[dict[str, object], int]:
    company = _get_company_by_ticker(ticker)
    if company is None:
        return jsonify({"error": f"Ticker {ticker.upper()} was not found in the local database"}), 404

    try:
        filing_limit = max(1, min(int(request.args.get("limit", 20)), 100))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    client = SecGovClient()

    try:
        if _should_refresh():
            asyncio.run(client.invalidate_cache(company.cik))
        submissions_payload = asyncio.run(
            client.get_company_submissions(company.cik, force_refresh=_should_refresh())
        )
        normalized = client.normalize_company_metadata(
            submissions_payload,
            filing_limit=filing_limit,
        )
        response = SecCompanySchema.model_validate(normalized).model_dump(mode="json")
        return jsonify(response), 200
    except SecGovClientError as exc:
        return jsonify({"error": str(exc)}), exc.status_code


@bp.get("/filings/<ticker>")
def get_filings(ticker: str) -> tuple[dict[str, object], int]:
    company = _get_company_by_ticker(ticker)
    if company is None:
        return jsonify({"error": f"Ticker {ticker.upper()} was not found in the local database"}), 404

    try:
        filing_limit = max(1, min(int(request.args.get("limit", 100)), 250))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    form_type = request.args.get("form")
    client = SecGovClient()

    try:
        if _should_refresh():
            asyncio.run(client.invalidate_cache(company.cik))
        submissions_payload = asyncio.run(
            client.get_company_submissions(company.cik, force_refresh=_should_refresh())
        )
        filings = client.normalize_filings(
            submissions_payload,
            filing_limit=filing_limit,
            form_type=form_type,
        )
        response = SecFilingsResponseSchema(
            ticker=company.ticker,
            cik=SecGovClient.pad_cik(company.cik),
            filings=filings,
        ).model_dump(mode="json")
        return jsonify(response), 200
    except SecGovClientError as exc:
        return jsonify({"error": str(exc)}), exc.status_code


@bp.get("/xbrl/<ticker>")
def get_xbrl(ticker: str) -> tuple[dict[str, object], int]:
    company = _get_company_by_ticker(ticker)
    if company is None:
        return jsonify({"error": f"Ticker {ticker.upper()} was not found in the local database"}), 404

    taxonomy = request.args.get("taxonomy")
    try:
        concept_limit = max(1, min(int(request.args.get("concept_limit", 25)), 100))
        fact_limit = max(1, min(int(request.args.get("fact_limit", 10)), 50))
    except ValueError:
        return jsonify({"error": "concept_limit and fact_limit must be integers"}), 400
    client = SecGovClient()

    try:
        if _should_refresh():
            asyncio.run(client.invalidate_cache(company.cik))
        company_facts_payload = asyncio.run(
            client.get_company_facts(company.cik, force_refresh=_should_refresh())
        )
        normalized = client.normalize_company_facts(
            company_facts_payload,
            taxonomy_filter=taxonomy,
            concept_limit=concept_limit,
            fact_limit=fact_limit,
        )
        response = SecXbrlResponseSchema(
            ticker=company.ticker,
            cik=normalized["cik"],
            entity_name=normalized["entity_name"],
            concepts=normalized["concepts"],
        ).model_dump(mode="json")
        return jsonify(response), 200
    except SecGovClientError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

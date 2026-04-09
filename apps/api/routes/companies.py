from __future__ import annotations

import asyncio

from flask import Blueprint, jsonify, request

from apps.api.extensions import get_session
from apps.api.services.company_research_service import CompanyResearchService

bp = Blueprint("companies", __name__, url_prefix="/api/v1/companies")


@bp.get("")
def list_companies() -> tuple[dict[str, object], int]:
    session = get_session()

    try:
        search = str(request.args.get("search", ""))
        only_with_filings = str(request.args.get("with_filings", "0")).strip().lower() in {
            "1",
            "true",
            "yes",
        }
        companies = CompanyResearchService(session).list_companies(
            search=search,
            only_with_filings=only_with_filings,
        )
        return jsonify({"companies": companies}), 200
    finally:
        session.close()


@bp.get("/<ticker>/workspace")
def get_company_workspace(ticker: str) -> tuple[dict[str, object], int]:
    session = get_session()

    try:
        data = asyncio.run(CompanyResearchService(session).get_company_workspace(ticker))
        return jsonify(data), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    finally:
        session.close()

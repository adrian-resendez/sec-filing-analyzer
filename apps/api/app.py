from __future__ import annotations

from flask import Flask

from apps.api.config import get_settings
from apps.api.extensions import init_extensions
from apps.api.routes.companies import bp as companies_bp
from apps.api.routes.filings import bp as filings_bp
from apps.api.routes.health import bp as health_bp
from apps.api.routes.research import bp as research_bp
from apps.api.routes.secgov import bp as secgov_bp
from apps.api.utils.logging import configure_logging


def create_app() -> Flask:
    configure_logging()
    settings = get_settings()

    app = Flask(__name__)
    app.config.update(
        AI_PROVIDER=settings.ai_provider,
        OPENAI_API_KEY=settings.openai_api_key,
        GEMINI_API_KEY=settings.gemini_api_key,
        SEC_API_KEY=settings.sec_api_key,
        SEC_USER_AGENT=settings.sec_user_agent,
        MASSIVE_API_KEY=settings.massive_api_key,
        DATABASE_URL=settings.database_url,
        REDIS_URL=settings.redis_url,
        OPENAI_MODEL=settings.openai_model,
        GEMINI_MODEL=settings.gemini_model,
    )

    init_extensions(app)
    app.register_blueprint(research_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(companies_bp)
    app.register_blueprint(filings_bp)
    app.register_blueprint(secgov_bp)

    return app


app = create_app()

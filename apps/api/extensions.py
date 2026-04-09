from __future__ import annotations

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, scoped_session, sessionmaker

from apps.api.config import get_settings


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
_active_database_url: str | None = None
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False)
)


def _import_models() -> None:
    import apps.api.models.ai_run  # noqa: F401
    import apps.api.models.company  # noqa: F401
    import apps.api.models.filing  # noqa: F401
    import apps.api.models.filing_section  # noqa: F401


def init_engine(database_url: str) -> Engine:
    global engine, _active_database_url

    if engine is not None and _active_database_url == database_url:
        return engine

    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    SessionLocal.configure(bind=engine)
    _active_database_url = database_url
    return engine


def initialize_database(database_url: str) -> Engine:
    db_engine = init_engine(database_url)
    _import_models()
    Base.metadata.create_all(bind=db_engine)
    return db_engine


def get_session() -> Session:
    settings = get_settings()
    initialize_database(settings.database_url)
    return SessionLocal()


def init_extensions(app: Flask) -> None:
    settings = get_settings()
    initialize_database(settings.database_url)

    @app.teardown_appcontext
    def teardown_session(_: BaseException | None) -> None:
        SessionLocal.remove()

"""Database wiring.

The engine is created lazily so that unit tests (SQLite) never require the
Postgres driver at import time, and so that the test suite can inject its own
SessionLocal before any engine is built.
"""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal: sessionmaker | None = None


def init_engine(url: str | None = None) -> None:
    global engine, SessionLocal
    engine = create_engine(url or settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    if SessionLocal is None:  # lazy init for real runs; tests inject their own
        init_engine()
    assert SessionLocal is not None
    with SessionLocal() as session:
        yield session

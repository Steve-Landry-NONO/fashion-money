import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.capture.models  # noqa: F401
import app.catalog.models  # noqa: F401
import app.db as db_module
import app.decision.models  # noqa: F401

# import all models so create_all builds the full schema
import app.identity.models  # noqa: F401
import app.matching.models  # noqa: F401
import app.wallet.models  # noqa: F401
from app.db import Base
from app.identity.deps import DEV_TOKEN


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # enforce FK constraints on SQLite so integrity tests are meaningful
    @event.listens_for(eng, "connect")
    def _fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def session(engine, monkeypatch):
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db_module, "SessionLocal", TestingSession)
    with TestingSession() as s:
        yield s


@pytest.fixture()
def client(engine, monkeypatch):
    from app.main import app
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db_module, "SessionLocal", TestingSession)
    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {DEV_TOKEN}"})
        yield c

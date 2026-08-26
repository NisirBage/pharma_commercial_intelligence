from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all models on Base.metadata
from app.db.base import Base

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pharma_mini"


@pytest.fixture
def raw_fixture_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sqlite_engine():
    """In-memory SQLite, standing in for Postgres in tests — no Postgres
    credentials were available for this milestone (see M2 completion
    report). StaticPool keeps the same in-memory DB alive across
    connections within a test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys = ON")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    with Session(sqlite_engine) as session:
        yield session

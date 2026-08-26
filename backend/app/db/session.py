from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def make_engine(database_url: str | None = None) -> Engine:
    """Create an engine. Defaults to the configured Postgres URL; tests pass
    an explicit SQLite URL instead (see tests/conftest.py)."""
    url = database_url or settings.sqlalchemy_database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

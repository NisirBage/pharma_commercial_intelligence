"""FastAPI dependency-injection providers — kept separate from route
handlers so routes stay thin (M6 Sec. 33) and dependencies are trivial to
override in tests (M6 Sec. 30, see tests/api/conftest.py).
"""

from collections.abc import Generator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import make_engine, make_session_factory

_engine = None
_session_factory = None


def _ensure_session_factory():
    global _engine, _session_factory
    if _session_factory is None:
        _engine = make_engine()
        _session_factory = make_session_factory(_engine)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """Per-request DB session, properly scoped — never a single global
    persistent session (M6 Sec. 22). Most endpoints do NOT depend on
    this: the analytics/forecasting/optimization layers default to the
    CSV-derived canonical frame when no database is reachable (the same
    architecture M2-M5 already established, see
    app.analytics.data_access.load_canonical_frame). Only the health
    check uses this, and treats a connection failure as a normal,
    reportable state rather than letting it crash the request."""
    session_factory = _ensure_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def check_database_connection() -> str:
    """Lightweight liveness check for GET /health — a single trivial
    query, never an expensive analytics computation (M6 Sec. 6)."""
    try:
        session_factory = _ensure_session_factory()
        with session_factory() as session:
            session.execute(text("SELECT 1"))
        return "connected"
    except Exception:  # noqa: BLE001 — deliberately broad: a liveness probe must degrade to "unreachable" for ANY failure mode (connection refused, auth, timeout, driver error), never crash the health endpoint itself
        return "unreachable"

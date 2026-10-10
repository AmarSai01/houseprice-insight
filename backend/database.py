"""
Database configuration and session management (PostgreSQL only).

Engine creation is lazy so importing the FastAPI app (required by Vercel’s
ASGI loader) does not require DATABASE_URL at module-import time. The same
fail-closed validation still runs on first use via ensure_engine().
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from database_settings import resolve_database_url

Base = declarative_base()

DATABASE_URL: Optional[str] = None
engine: Optional[Engine] = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def ensure_engine() -> Engine:
    """
    Create and bind the process engine on first use.

    Raises RuntimeError when DATABASE_URL is missing or not PostgreSQL
    (same messages as resolve_database_url / validate_postgres_database_url).
    """
    global engine, DATABASE_URL

    if engine is not None:
        return engine

    DATABASE_URL = resolve_database_url()
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )
    SessionLocal.configure(bind=engine)
    return engine


def get_db():
    """Dependency to get database session."""
    ensure_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables (create_all for empty target databases)."""
    ensure_engine()
    assert engine is not None
    Base.metadata.create_all(bind=engine)


def ping_database() -> bool:
    """
    Lightweight connectivity check (SELECT 1).

    Does not expose connection details; callers must not return exceptions to clients.
    """
    try:
        ensure_engine()
        assert engine is not None
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def configure_engine(database_url: str):
    """
    Rebind the process engine/session factory to a validated database URL.

    Used by the test harness after TEST_DATABASE_URL safety checks.
    """
    global engine, DATABASE_URL

    if engine is not None:
        engine.dispose()

    DATABASE_URL = database_url
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal.configure(bind=engine)
    return engine

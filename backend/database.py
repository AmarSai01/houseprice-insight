"""
Database configuration and session management (PostgreSQL only).
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from database_settings import resolve_database_url

DATABASE_URL = resolve_database_url()

# PostgreSQL via psycopg v3. pool_pre_ping avoids stale hosted connections.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables (create_all for empty target databases)."""
    Base.metadata.create_all(bind=engine)


def ping_database() -> bool:
    """
    Lightweight connectivity check (SELECT 1).

    Does not expose connection details; callers must not return exceptions to clients.
    """
    try:
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
    DATABASE_URL = database_url
    engine.dispose()
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal.configure(bind=engine)
    return engine

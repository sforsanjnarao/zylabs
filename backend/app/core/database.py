"""Database setup using SQLAlchemy.

Defines the engine (connection to the database), a session factory (how we open
short-lived conversations with the DB), and the Base class that all of our
table models inherit from.

Works with both SQLite (local dev) and Postgres (production) — the connection
arguments are chosen based on the DATABASE_URL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Some providers (e.g. Neon, Heroku) hand out "postgres://" URLs, but
# SQLAlchemy requires the "postgresql://" scheme — normalize it.
_db_url = settings.database_url
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

_is_sqlite = _db_url.startswith("sqlite")

# check_same_thread=False is required only for SQLite (we use threads).
# pool_pre_ping verifies connections before use — important for managed
# Postgres (e.g. Neon) that may close idle connections.
engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)

# SessionLocal() creates a new DB session (a unit of work) each time.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All ORM models inherit from this base class."""
    pass


def get_db():
    """FastAPI dependency: open a DB session, hand it to the route,
    then always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

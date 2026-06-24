"""Database setup using SQLAlchemy.

Defines the engine (connection to SQLite), a session factory (how we open
short-lived conversations with the DB), and the Base class that all of our
table models inherit from.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# The engine is the core connection to the database.
# check_same_thread=False is required for SQLite when used by FastAPI.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
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

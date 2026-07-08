"""Database engine, session factory, and FastAPI dependency."""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables (dev convenience; production uses Alembic migrations)."""
    # Import models so they register on Base.metadata
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

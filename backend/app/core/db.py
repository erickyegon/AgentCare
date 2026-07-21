"""Database engine, session factory, and declarative base.

Synchronous SQLAlchemy 2.0 is used deliberately: the LangGraph agent tools and the
checkpointer run synchronously, and mixing sync tool code inside async request handlers
is a common source of subtle bugs. FastAPI runs sync path operations in a threadpool, so
this remains fully concurrent while keeping the agent/tool/db code straightforward.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _engine_kwargs() -> dict:
    kwargs: dict = {"pool_pre_ping": True, "future": True}
    if settings.is_sqlite:
        # SQLite needs this to be usable across FastAPI's threadpool workers.
        kwargs["connect_args"] = {"check_same_thread": False}
    return kwargs


engine = create_engine(settings.database_url, **_engine_kwargs())

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def session_scope() -> Session:
    """Return a new session for use outside request scope (agents, scripts, tools)."""
    return SessionLocal()

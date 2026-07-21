"""Database initialization helpers."""

from __future__ import annotations

from app.core.db import Base, engine

# Import models so metadata is populated before create_all.
import app.models  # noqa: F401


def create_all() -> None:
    """Create all tables directly from metadata (used by tests and quick-start)."""
    Base.metadata.create_all(engine)


def drop_all() -> None:
    Base.metadata.drop_all(engine)

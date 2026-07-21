"""Reusable model mixins."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column

from app.models.types import UtcDateTime


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` columns."""

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

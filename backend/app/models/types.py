"""Custom column types.

``UtcDateTime`` guarantees timezone-aware UTC datetimes on the way in and out of the
database. SQLite does not preserve tzinfo, which otherwise leads to
'can't compare offset-naive and offset-aware datetimes' errors; this normalizes both
SQLite and PostgreSQL to consistent aware-UTC values.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

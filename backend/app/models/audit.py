"""Immutable audit trail of every consequential action in the system."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ``actor_id`` is null for autonomous agent actions; ``actor`` names the agent/human.
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    action: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

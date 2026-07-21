"""Audit-log tool — appends an immutable event to the audit trail."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent


def write_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    actor: str = "system",
    actor_id: int | None = None,
    workflow_run_id: int | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditEvent:
    """Persist an audit event. Flushes so the id is available; caller commits."""
    event = AuditEvent(
        actor=actor,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        workflow_run_id=workflow_run_id,
        meta=meta or {},
    )
    db.add(event)
    db.flush()
    return event

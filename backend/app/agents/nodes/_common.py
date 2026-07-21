"""Shared helpers for agent nodes: step recording and state persistence.

Each node opens its own DB session (state stays JSON-serializable), does real work, records
a ``WorkflowStep`` (the visible trace), updates the authoritative ``WorkflowRun.state``, and
commits. This is where 'state handed between agents' is persisted to SQL after every hop.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import WorkflowRun, WorkflowStep, WorkflowStatus


def next_sequence(db: Session, run_id: int) -> int:
    current = db.scalar(
        select(func.count(WorkflowStep.id)).where(WorkflowStep.run_id == run_id)
    )
    return int(current or 0) + 1


def record_step(
    db: Session,
    *,
    run_id: int,
    agent: str,
    action: str,
    message: str = "",
    data: dict[str, Any] | None = None,
    status: str = "completed",
) -> dict[str, Any]:
    """Persist a WorkflowStep and return a serializable trace event."""
    seq = next_sequence(db, run_id)
    step = WorkflowStep(
        run_id=run_id,
        sequence=seq,
        agent=agent,
        action=action,
        status=status,
        message=message,
        data=data or {},
    )
    db.add(step)
    db.flush()
    return {
        "id": step.id,
        "sequence": seq,
        "agent": agent,
        "action": action,
        "status": status,
        "message": message,
        "data": data or {},
        "created_at": step.created_at.isoformat(),
    }


def persist_run_state(
    db: Session,
    *,
    run_id: int,
    state_patch: dict[str, Any],
    current_step: str,
    status: WorkflowStatus | None = None,
    summary: str | None = None,
    error: str | None = None,
) -> None:
    """Merge a patch into WorkflowRun.state and update run bookkeeping columns."""
    run = db.get(WorkflowRun, run_id)
    if run is None:
        return
    merged = dict(run.state or {})
    merged.update(state_patch)
    run.state = merged
    run.current_step = current_step
    if status is not None:
        run.status = status
    if summary is not None:
        run.summary = summary
    if error is not None:
        run.error = error
    db.add(run)
    db.flush()

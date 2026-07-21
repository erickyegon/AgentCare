"""Escalation / approval tool — creates and resolves human-review records.

This is the backbone of human oversight: the safety and routing agents call
``create_escalation`` to hand a case to staff; staff call ``resolve_escalation`` (via the
API) to approve or reject, and the workflow is gated on that persisted decision.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Escalation, EscalationStatus, WorkflowRun
from app.tools.audit_tool import write_audit
from app.tools.base import ToolResult


def create_escalation(
    db: Session,
    *,
    run_id: int,
    category: str,
    reason: str,
    severity: str = "medium",
    requires_approval: bool = False,
    payload: dict | None = None,
    actor: str = "safety_agent",
) -> ToolResult:
    """Raise a human-review escalation attached to a workflow run."""
    if db.get(WorkflowRun, run_id) is None:
        return ToolResult(ok=False, message=f"No workflow run with id {run_id}.")

    escalation = Escalation(
        run_id=run_id,
        category=category,
        reason=reason,
        severity=severity,
        requires_approval=requires_approval,
        status=EscalationStatus.PENDING,
        payload=payload or {},
    )
    db.add(escalation)
    db.flush()
    write_audit(
        db,
        action="escalation.created",
        entity_type="escalation",
        entity_id=escalation.id,
        actor=actor,
        workflow_run_id=run_id,
        meta={"category": category, "severity": severity, "requires_approval": requires_approval},
    )
    return ToolResult(
        ok=True,
        message=f"Escalated to human review ({category}, severity={severity}).",
        data={
            "escalation_id": escalation.id,
            "category": category,
            "requires_approval": requires_approval,
            "status": EscalationStatus.PENDING.value,
        },
    )


def resolve_escalation(
    db: Session,
    *,
    escalation_id: int,
    approve: bool,
    reviewer_user_id: int,
    note: str = "",
) -> ToolResult:
    """Staff decision on an escalation. Persists approval/rejection + reviewer identity."""
    escalation = db.get(Escalation, escalation_id)
    if escalation is None:
        return ToolResult(ok=False, message=f"No escalation with id {escalation_id}.")
    if escalation.status != EscalationStatus.PENDING:
        return ToolResult(
            ok=False,
            message=f"Escalation already {escalation.status.value}.",
            data={"status": escalation.status.value},
        )

    escalation.status = EscalationStatus.APPROVED if approve else EscalationStatus.REJECTED
    escalation.reviewed_by = reviewer_user_id
    escalation.resolution_note = note
    db.flush()
    write_audit(
        db,
        action="escalation.resolved",
        entity_type="escalation",
        entity_id=escalation.id,
        actor="staff",
        actor_id=reviewer_user_id,
        workflow_run_id=escalation.run_id,
        meta={"approved": approve, "note": note},
    )
    return ToolResult(
        ok=True,
        message=f"Escalation {escalation.status.value} by reviewer #{reviewer_user_id}.",
        data={"escalation_id": escalation.id, "status": escalation.status.value},
    )

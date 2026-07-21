"""Staff / administrator routes — oversight, approvals, and audit.

The escalation-decision endpoint is where human oversight becomes real: approving a gated
'sensitive_action' (e.g. a late cancellation) actually performs the held action; rejecting it
restores prior state. Both outcomes are persisted and audited.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.api.errors import AppError, NotFoundError
from app.core.db import get_db
from app.models import (
    Appointment,
    AppointmentStatus,
    AuditEvent,
    Escalation,
    EscalationStatus,
    PatientProfile,
    User,
    UserRole,
    WorkflowRun,
)
from app.schemas.auth import UserOut
from app.schemas.clinical import (
    AuditEventOut,
    EscalationDecision,
    EscalationOut,
    WorkflowRunOut,
)
from app.services.analytics import compute_analytics
from app.tools import cancel_appointment, resolve_escalation, write_audit

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/workflows", response_model=list[WorkflowRunOut])
def list_workflows(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[WorkflowRun]:
    stmt = select(WorkflowRun).order_by(WorkflowRun.id.desc())
    if status_filter:
        stmt = stmt.where(WorkflowRun.status == status_filter)
    return list(db.scalars(stmt.limit(200)))


@router.get("/escalations", response_model=list[EscalationOut])
def list_escalations(
    status_filter: str = Query(default="pending", alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[Escalation]:
    stmt = select(Escalation).order_by(Escalation.id.desc())
    if status_filter != "all":
        stmt = stmt.where(Escalation.status == status_filter)
    return list(db.scalars(stmt.limit(200)))


@router.post("/escalations/{escalation_id}/decision", response_model=EscalationOut)
def decide_escalation(
    escalation_id: int,
    payload: EscalationDecision,
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> Escalation:
    escalation = db.get(Escalation, escalation_id)
    if escalation is None:
        raise NotFoundError("Escalation not found")

    result = resolve_escalation(
        db, escalation_id=escalation_id, approve=payload.approve,
        reviewer_user_id=staff.id, note=payload.note,
    )
    if not result.ok:
        raise AppError(result.message)

    # Execute (or unwind) any gated action attached to this escalation.
    if escalation.category == "sensitive_action":
        appt_id = (escalation.payload or {}).get("appointment_id")
        appt = db.get(Appointment, appt_id) if appt_id else None
        if appt is not None:
            if payload.approve and (escalation.payload or {}).get("action") == "cancel":
                cancel_appointment(db, appointment_id=appt.id)
            elif not payload.approve:
                # Restore the held appointment.
                appt.status = AppointmentStatus.CONFIRMED
                write_audit(db, action="appointment.approval_rejected", entity_type="appointment",
                            entity_id=appt.id, actor="staff", actor_id=staff.id,
                            workflow_run_id=escalation.run_id, meta={})

    db.commit()
    db.refresh(escalation)
    return escalation


@router.get("/analytics")
def analytics(db: Session = Depends(get_db), _: User = Depends(require_staff)) -> dict:
    """Live operational analytics aggregated from the database."""
    return compute_analytics(db)


@router.get("/audit", response_model=list[AuditEventOut])
def audit_log(
    limit: int = Query(default=100, le=500),
    workflow_run_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.id.desc())
    if workflow_run_id is not None:
        stmt = stmt.where(AuditEvent.workflow_run_id == workflow_run_id)
    return list(db.scalars(stmt.limit(limit)))


@router.get("/patients", response_model=list[UserOut])
def list_patients(
    db: Session = Depends(get_db), _: User = Depends(require_staff)
) -> list[User]:
    return list(
        db.scalars(select(User).where(User.role == UserRole.PATIENT).order_by(User.id.desc()))
    )


@router.get("/patients/{patient_profile_id}/summary")
def patient_summary(
    patient_profile_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> dict:
    profile = db.get(PatientProfile, patient_profile_id)
    if profile is None:
        raise NotFoundError("Patient not found")
    user = db.get(User, profile.user_id)
    appts = db.scalars(
        select(Appointment).where(Appointment.patient_id == profile.id)
    ).all()
    return {
        "patient_id": profile.id,
        "name": user.name if user else None,
        "email": user.email if user else None,
        "mrn": profile.mrn,
        "appointments": len(appts),
        "preferred_language": profile.preferred_language,
    }

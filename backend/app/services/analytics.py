"""Operational analytics computed live from the database (no precomputed/fixed values)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AuditEvent,
    Department,
    Doctor,
    Escalation,
    PatientDocument,
    PatientProfile,
    Reminder,
    WorkflowRun,
    WorkflowStep,
)


def _counts(db: Session, column) -> dict[str, int]:
    rows = db.execute(select(column, func.count()).group_by(column)).all()
    out: dict[str, int] = {}
    for value, count in rows:
        key = value.value if hasattr(value, "value") else str(value)
        out[key] = int(count)
    return out


def compute_analytics(db: Session) -> dict:
    """Aggregate operational metrics across the whole system."""
    total_runs = int(db.scalar(select(func.count(WorkflowRun.id))) or 0)
    total_steps = int(db.scalar(select(func.count(WorkflowStep.id))) or 0)

    # Appointments per department (join Appointment -> Doctor -> Department).
    dept_rows = db.execute(
        select(Department.name, func.count(Appointment.id))
        .join(Doctor, Doctor.department_id == Department.id)
        .join(Appointment, Appointment.doctor_id == Doctor.id)
        .group_by(Department.name)
        .order_by(func.count(Appointment.id).desc())
    ).all()

    escalation_pending = int(
        db.scalar(select(func.count(Escalation.id)).where(Escalation.status == "pending")) or 0
    )

    return {
        "totals": {
            "workflows": total_runs,
            "patients": int(db.scalar(select(func.count(PatientProfile.id))) or 0),
            "appointments": int(db.scalar(select(func.count(Appointment.id))) or 0),
            "documents": int(db.scalar(select(func.count(PatientDocument.id))) or 0),
            "reminders": int(db.scalar(select(func.count(Reminder.id))) or 0),
            "escalations": int(db.scalar(select(func.count(Escalation.id))) or 0),
            "escalations_pending": escalation_pending,
            "audit_events": int(db.scalar(select(func.count(AuditEvent.id))) or 0),
            "avg_steps_per_workflow": round(total_steps / total_runs, 1) if total_runs else 0.0,
        },
        "workflows_by_status": _counts(db, WorkflowRun.status),
        "appointments_by_status": _counts(db, Appointment.status),
        "escalations_by_category": _counts(db, Escalation.category),
        "escalations_by_status": _counts(db, Escalation.status),
        "documents_by_type": _counts(db, PatientDocument.document_type),
        "reminders_by_type": _counts(db, Reminder.reminder_type),
        "appointments_by_department": [
            {"department": name, "count": int(count)} for name, count in dept_rows
        ],
        "duplicate_documents": int(
            db.scalar(select(func.count(PatientDocument.id)).where(
                PatientDocument.is_duplicate.is_(True))) or 0
        ),
    }

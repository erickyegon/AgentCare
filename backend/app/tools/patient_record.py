"""Patient-record tool — find or create the patient profile behind a request."""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PatientProfile, User
from app.tools.audit_tool import write_audit
from app.tools.base import ToolResult


def _generate_mrn(db: Session) -> str:
    """Generate a unique synthetic Medical Record Number."""
    for _ in range(20):
        candidate = "MRN-" + secrets.token_hex(4).upper()
        exists = db.scalar(select(PatientProfile).where(PatientProfile.mrn == candidate))
        if not exists:
            return candidate
    raise RuntimeError("Could not allocate a unique MRN")


def get_patient(db: Session, patient_id: int) -> PatientProfile | None:
    return db.get(PatientProfile, patient_id)


def get_or_create_patient(
    db: Session, *, user_id: int, workflow_run_id: int | None = None
) -> ToolResult:
    """Ensure the requesting user has a patient profile; create one if missing.

    Real logic: reads the user, looks up an existing profile, and provisions an MRN
    on first contact. Every creation is audited.
    """
    user = db.get(User, user_id)
    if user is None:
        return ToolResult(ok=False, message=f"No user with id {user_id}")

    profile = db.scalar(select(PatientProfile).where(PatientProfile.user_id == user_id))
    created = False
    if profile is None:
        profile = PatientProfile(user_id=user_id, mrn=_generate_mrn(db))
        db.add(profile)
        db.flush()
        created = True
    elif not profile.mrn:
        # Backfill an MRN for profiles created outside this tool (e.g. via seed/registration).
        profile.mrn = _generate_mrn(db)
        db.flush()

    if created:
        write_audit(
            db,
            action="patient.created",
            entity_type="patient_profile",
            entity_id=profile.id,
            actor="coordinator_agent",
            workflow_run_id=workflow_run_id,
            meta={"mrn": profile.mrn, "user_id": user_id},
        )

    return ToolResult(
        ok=True,
        message=("Created new patient record" if created else "Matched existing patient record")
        + f" (MRN {profile.mrn}).",
        data={
            "patient_id": profile.id,
            "mrn": profile.mrn,
            "name": user.name,
            "email": user.email,
            "created": created,
            "preferred_language": profile.preferred_language,
        },
    )

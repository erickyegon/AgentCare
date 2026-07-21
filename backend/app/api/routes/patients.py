"""Patient self-service routes — appointments, documents, reminders (own data only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient_profile
from app.api.errors import AppError, ForbiddenError, NotFoundError
from app.core.config import settings
from app.core.db import get_db
from app.models import Appointment, PatientDocument, PatientProfile, Reminder
from app.schemas.clinical import AppointmentOut, DocumentOut, ReminderOut
from app.tools import cancel_appointment, store_document

router = APIRouter(prefix="/me", tags=["patient"])


@router.get("/appointments", response_model=list[AppointmentOut])
def my_appointments(
    db: Session = Depends(get_db), profile: PatientProfile = Depends(get_current_patient_profile)
) -> list[Appointment]:
    return list(
        db.scalars(
            select(Appointment).where(Appointment.patient_id == profile.id)
            .order_by(Appointment.id.desc())
        )
    )


@router.get("/documents", response_model=list[DocumentOut])
def my_documents(
    db: Session = Depends(get_db), profile: PatientProfile = Depends(get_current_patient_profile)
) -> list[PatientDocument]:
    return list(
        db.scalars(
            select(PatientDocument).where(PatientDocument.patient_id == profile.id)
            .order_by(PatientDocument.id.desc())
        )
    )


@router.get("/reminders", response_model=list[ReminderOut])
def my_reminders(
    db: Session = Depends(get_db), profile: PatientProfile = Depends(get_current_patient_profile)
) -> list[Reminder]:
    return list(
        db.scalars(
            select(Reminder).where(Reminder.patient_id == profile.id)
            .order_by(Reminder.scheduled_at.asc())
        )
    )


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(get_current_patient_profile),
) -> PatientDocument:
    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) == 0:
        raise AppError("Uploaded file is empty.")
    if len(content) > max_bytes:
        raise AppError(f"File exceeds the {settings.max_upload_mb} MB limit.")

    result = store_document(
        db,
        patient_id=profile.id,
        filename=file.filename or "document",
        content=content,
        content_type=file.content_type or "application/octet-stream",
    )
    db.commit()
    if not result.ok:
        raise AppError(result.message)
    doc = db.get(PatientDocument, result.data["document_id"])
    return doc


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_my_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    profile: PatientProfile = Depends(get_current_patient_profile),
) -> Appointment:
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise NotFoundError("Appointment not found")
    if appt.patient_id != profile.id:  # ownership enforced in backend
        raise ForbiddenError("You can only cancel your own appointments.")
    result = cancel_appointment(db, appointment_id=appointment_id)
    db.commit()
    if not result.ok:
        raise AppError(result.message)
    db.refresh(appt)
    return appt

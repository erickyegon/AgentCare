"""Appointment-booking tool — book, reschedule, and cancel with conflict detection.

All operations mutate persistent state (Appointment + AppointmentSlot) inside the caller's
transaction and write audit events. Slot transitions guard against double-booking.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AppointmentSlot,
    AppointmentStatus,
    Doctor,
    PatientProfile,
    SlotStatus,
)
from app.tools.audit_tool import write_audit
from app.tools.base import ToolResult


def _confirmation_code() -> str:
    return "AC-" + secrets.token_hex(3).upper()


def _patient_has_conflict(db: Session, patient_id: int, slot: AppointmentSlot) -> bool:
    """True if the patient already has an active appointment overlapping this slot's time."""
    active = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED,
              AppointmentStatus.RESCHEDULED, AppointmentStatus.AWAITING_APPROVAL)
    stmt = (
        select(Appointment)
        .join(AppointmentSlot, Appointment.slot_id == AppointmentSlot.id)
        .where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.status.in_(active),
                AppointmentSlot.start_time < slot.end_time,
                AppointmentSlot.end_time > slot.start_time,
            )
        )
    )
    return db.scalar(stmt) is not None


def book_appointment(
    db: Session,
    *,
    patient_id: int,
    slot_id: int,
    reason: str = "",
    initial_status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    workflow_run_id: int | None = None,
) -> ToolResult:
    """Book a specific available slot for a patient, guarding against conflicts."""
    patient = db.get(PatientProfile, patient_id)
    if patient is None:
        return ToolResult(ok=False, message=f"No patient with id {patient_id}.")

    slot = db.get(AppointmentSlot, slot_id)
    if slot is None:
        return ToolResult(ok=False, message=f"No slot with id {slot_id}.")
    if slot.status != SlotStatus.AVAILABLE:
        return ToolResult(
            ok=False,
            message=f"Slot {slot_id} is no longer available (status={slot.status.value}).",
            data={"conflict": "slot_taken"},
        )
    if slot.start_time <= datetime.now(timezone.utc):
        return ToolResult(ok=False, message="Cannot book a slot in the past.")
    if _patient_has_conflict(db, patient_id, slot):
        return ToolResult(
            ok=False,
            message="Patient already has an appointment overlapping this time.",
            data={"conflict": "patient_double_booking"},
        )

    doctor = db.get(Doctor, slot.doctor_id)
    slot.status = SlotStatus.BOOKED
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=slot.doctor_id,
        slot_id=slot.id,
        status=initial_status,
        reason=reason,
        confirmation_code=_confirmation_code(),
    )
    db.add(appointment)
    db.flush()
    write_audit(
        db,
        action="appointment.booked",
        entity_type="appointment",
        entity_id=appointment.id,
        actor="appointment_agent",
        workflow_run_id=workflow_run_id,
        meta={"slot_id": slot.id, "doctor_id": slot.doctor_id, "status": initial_status.value},
    )
    return ToolResult(
        ok=True,
        message=(
            f"Appointment {appointment.confirmation_code} with {doctor.name if doctor else 'doctor'} "
            f"on {slot.start_time.isoformat()} — status {initial_status.value}."
        ),
        data={
            "appointment_id": appointment.id,
            "confirmation_code": appointment.confirmation_code,
            "doctor_id": slot.doctor_id,
            "doctor_name": doctor.name if doctor else None,
            "slot_id": slot.id,
            "start_time": slot.start_time.isoformat(),
            "status": initial_status.value,
        },
    )


def reschedule_appointment(
    db: Session,
    *,
    appointment_id: int,
    new_slot_id: int,
    workflow_run_id: int | None = None,
) -> ToolResult:
    """Move an appointment to a new available slot; frees the old slot."""
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        return ToolResult(ok=False, message=f"No appointment with id {appointment_id}.")
    if appt.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
        return ToolResult(ok=False, message=f"Cannot reschedule a {appt.status.value} appointment.")

    new_slot = db.get(AppointmentSlot, new_slot_id)
    if new_slot is None or new_slot.status != SlotStatus.AVAILABLE:
        return ToolResult(ok=False, message="Requested new slot is not available.")
    if new_slot.start_time <= datetime.now(timezone.utc):
        return ToolResult(ok=False, message="Cannot reschedule into a past slot.")

    old_slot = db.get(AppointmentSlot, appt.slot_id) if appt.slot_id else None
    if old_slot is not None:
        old_slot.status = SlotStatus.AVAILABLE
    new_slot.status = SlotStatus.BOOKED
    appt.slot_id = new_slot.id
    appt.doctor_id = new_slot.doctor_id
    appt.status = AppointmentStatus.RESCHEDULED
    db.flush()
    write_audit(
        db,
        action="appointment.rescheduled",
        entity_type="appointment",
        entity_id=appt.id,
        actor="appointment_agent",
        workflow_run_id=workflow_run_id,
        meta={"old_slot_id": old_slot.id if old_slot else None, "new_slot_id": new_slot.id},
    )
    return ToolResult(
        ok=True,
        message=f"Appointment {appt.confirmation_code} rescheduled to {new_slot.start_time.isoformat()}.",
        data={
            "appointment_id": appt.id,
            "new_slot_id": new_slot.id,
            "start_time": new_slot.start_time.isoformat(),
            "status": appt.status.value,
        },
    )


def cancel_appointment(
    db: Session,
    *,
    appointment_id: int,
    workflow_run_id: int | None = None,
) -> ToolResult:
    """Cancel an appointment and free its slot."""
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        return ToolResult(ok=False, message=f"No appointment with id {appointment_id}.")
    if appt.status == AppointmentStatus.CANCELLED:
        return ToolResult(ok=True, message="Appointment already cancelled.",
                          data={"appointment_id": appt.id, "status": "cancelled"})

    slot = db.get(AppointmentSlot, appt.slot_id) if appt.slot_id else None
    if slot is not None:
        slot.status = SlotStatus.AVAILABLE
    appt.status = AppointmentStatus.CANCELLED
    db.flush()
    write_audit(
        db,
        action="appointment.cancelled",
        entity_type="appointment",
        entity_id=appt.id,
        actor="appointment_agent",
        workflow_run_id=workflow_run_id,
        meta={"freed_slot_id": slot.id if slot else None},
    )
    return ToolResult(
        ok=True,
        message=f"Appointment {appt.confirmation_code} cancelled.",
        data={"appointment_id": appt.id, "status": "cancelled"},
    )

"""Appointment Agent — availability, conflict checks, and book/reschedule/cancel.

A sensitive-action gate demonstrates human approval: cancelling within 24h of the visit is
not performed autonomously; it is escalated for staff approval instead.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.agents.state import WorkflowState
from app.core.db import session_scope
from app.models import Appointment, AppointmentSlot, AppointmentStatus, WorkflowStatus
from app.agents.nodes._common import persist_run_state, record_step
from app.tools import (
    book_appointment,
    cancel_appointment,
    create_escalation,
    find_available_slots,
    reschedule_appointment,
    write_audit,
)

AGENT = "appointment_agent"
_ACTIVE = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED,
           AppointmentStatus.RESCHEDULED, AppointmentStatus.AWAITING_APPROVAL)


def _timeframe_window(timeframe: str | None) -> tuple[datetime | None, datetime | None]:
    now = datetime.now(timezone.utc)
    if not timeframe:
        return now, None
    tf = timeframe.lower()
    if "today" in tf:
        return now, now + timedelta(days=1)
    if "tomorrow" in tf:
        return now + timedelta(hours=12), now + timedelta(days=2)
    if "this week" in tf:
        return now, now + timedelta(days=7)
    if "next week" in tf:
        return now + timedelta(days=6), now + timedelta(days=15)
    if "next month" in tf:
        return now + timedelta(days=25), now + timedelta(days=45)
    return now, None


def _latest_active_appointment(db, patient_id: int) -> Appointment | None:
    return db.scalar(
        select(Appointment)
        .where(Appointment.patient_id == patient_id, Appointment.status.in_(_ACTIVE))
        .order_by(Appointment.id.desc())
    )


def appointment_node(state: WorkflowState) -> dict:
    run_id = state["run_id"]
    intent = state.get("intent", {})
    routing = state.get("routing", {})
    patient_id = state.get("patient_id")
    escalation_ids = list(state.get("escalation_ids", []))

    # If no appointment action is implied, record a no-op step and continue.
    if not (intent.get("wants_appointment") or intent.get("wants_reschedule")
            or intent.get("wants_cancel")):
        with session_scope() as db:
            step = record_step(db, run_id=run_id, agent=AGENT, action="appointment",
                               message="No appointment action requested.", data={"skipped": True})
            persist_run_state(db, run_id=run_id, state_patch={"appointment": {"skipped": True}},
                              current_step="document", status=WorkflowStatus.RUNNING)
            db.commit()
        return {"appointment": {"skipped": True}, "current_step": "document", "trace": [step]}

    with session_scope() as db:
        appt_data: dict = {}
        message = ""
        status = "completed"

        if intent.get("wants_cancel"):
            existing = _latest_active_appointment(db, patient_id)
            if existing is None:
                message = "No active appointment found to cancel."
                appt_data = {"action": "cancel", "result": "none"}
            else:
                slot = db.get(AppointmentSlot, existing.slot_id) if existing.slot_id else None
                within_24h = slot and slot.start_time - datetime.now(timezone.utc) < timedelta(hours=24)
                if within_24h:
                    # Sensitive action → require human approval instead of auto-cancelling.
                    existing.status = AppointmentStatus.AWAITING_APPROVAL
                    esc = create_escalation(
                        db, run_id=run_id, category="sensitive_action",
                        reason="Late cancellation (<24h) requires staff approval.",
                        severity="medium", requires_approval=True,
                        payload={"appointment_id": existing.id, "action": "cancel"}, actor=AGENT,
                    )
                    if esc.ok:
                        escalation_ids.append(esc.data["escalation_id"])
                    message = ("Cancellation within 24h flagged for staff approval; "
                               "appointment held as awaiting approval.")
                    status = "escalated"
                    appt_data = {"action": "cancel", "result": "awaiting_approval",
                                 "appointment_id": existing.id}
                else:
                    res = cancel_appointment(db, appointment_id=existing.id, workflow_run_id=run_id)
                    message = res.message
                    appt_data = {"action": "cancel", **res.data}

        elif intent.get("wants_reschedule"):
            existing = _latest_active_appointment(db, patient_id)
            if existing is None:
                message = "No active appointment found to reschedule."
                appt_data = {"action": "reschedule", "result": "none"}
            else:
                dept_id = routing.get("department_id")
                after, before = _timeframe_window(intent.get("timeframe"))
                slots = find_available_slots(db, department_id=dept_id, after=after, before=before) \
                    if dept_id else None
                if slots and slots.ok:
                    new_slot_id = slots.data["slots"][0]["slot_id"]
                    res = reschedule_appointment(db, appointment_id=existing.id,
                                                 new_slot_id=new_slot_id, workflow_run_id=run_id)
                    message = res.message
                    appt_data = {"action": "reschedule", **res.data}
                    status = "completed" if res.ok else "failed"
                else:
                    message = "No alternative slots available to reschedule into."
                    appt_data = {"action": "reschedule", "result": "no_slots"}
                    status = "failed"

        else:  # book / follow-up
            dept_id = routing.get("department_id")
            after, before = _timeframe_window(intent.get("timeframe"))
            slots = find_available_slots(db, department_id=dept_id, after=after, before=before) \
                if dept_id else None
            if not dept_id:
                message = "No department resolved; cannot book."
                appt_data = {"action": "book", "result": "no_department"}
                status = "failed"
            elif slots and slots.ok:
                chosen = slots.data["slots"][0]
                res = book_appointment(
                    db, patient_id=patient_id, slot_id=chosen["slot_id"],
                    reason=intent.get("summary", state["request_text"])[:500],
                    initial_status=AppointmentStatus.CONFIRMED, workflow_run_id=run_id,
                )
                message = res.message
                appt_data = {"action": "book", "alternatives": slots.data["slots"][1:4], **res.data}
                status = "completed" if res.ok else "failed"
            else:
                # Availability gap is a genuine operational case → escalate for manual scheduling.
                esc = create_escalation(
                    db, run_id=run_id, category="no_availability",
                    reason="No available slots in the requested department/timeframe.",
                    severity="low", requires_approval=False,
                    payload={"department_id": dept_id, "timeframe": intent.get("timeframe")},
                    actor=AGENT,
                )
                if esc.ok:
                    escalation_ids.append(esc.data["escalation_id"])
                message = "No available slots; escalated for manual scheduling."
                appt_data = {"action": "book", "result": "no_slots"}
                status = "escalated"

        write_audit(db, action="appointment.processed", entity_type="workflow_run",
                    entity_id=run_id, actor=AGENT, workflow_run_id=run_id,
                    meta={"action": appt_data.get("action"), "status": status})
        step = record_step(db, run_id=run_id, agent=AGENT, action="appointment",
                           message=message, data=appt_data, status=status)
        persist_run_state(db, run_id=run_id,
                          state_patch={"appointment": appt_data, "escalation_ids": escalation_ids},
                          current_step="document", status=WorkflowStatus.RUNNING)
        db.commit()

    return {"appointment": appt_data, "escalation_ids": escalation_ids,
            "current_step": "document", "trace": [step]}

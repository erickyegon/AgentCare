"""Coordinator Agent — entry (understand + identify patient) and finalize (compose the
confirmation strictly from persisted records)."""

from __future__ import annotations

from sqlalchemy import select

from app.agents.heuristics import detect_intent
from app.agents.llm import get_llm
from app.agents.prompts import COORDINATOR_PROMPT
from app.agents.schemas import IntentDecision
from app.agents.state import WorkflowState
from app.core.db import session_scope
from app.models import (
    Appointment,
    AppointmentSlot,
    Doctor,
    Escalation,
    PatientDocument,
    Reminder,
    WorkflowRun,
    WorkflowStatus,
)
from app.agents.nodes._common import persist_run_state, record_step
from app.tools import get_or_create_patient, write_audit

AGENT = "coordinator_agent"


def coordinator_node(state: WorkflowState) -> dict:
    run_id = state["run_id"]
    with session_scope() as db:
        # 1) Identify or create the patient record (tool).
        patient_res = get_or_create_patient(db, user_id=state["user_id"], workflow_run_id=run_id)
        if not patient_res.ok:
            step = record_step(db, run_id=run_id, agent=AGENT, action="identify_patient",
                               message=patient_res.message, status="failed")
            persist_run_state(db, run_id=run_id, state_patch={}, current_step="coordinator",
                              status=WorkflowStatus.FAILED, error=patient_res.message)
            db.commit()
            return {"status": "failed", "error": patient_res.message, "trace": [step],
                    "current_step": "coordinator"}

        patient_id = patient_res.data["patient_id"]

        # 2) Understand the administrative intent (LLM structured output, mock-backed).
        llm = get_llm()
        text = state["request_text"]
        intent, provider = llm.structured(
            system=COORDINATOR_PROMPT,
            user=f"Patient request:\n{text}",
            schema=IntentDecision,
            mock=lambda: detect_intent(text),
        )

        write_audit(db, action="workflow.intent_detected", entity_type="workflow_run",
                    entity_id=run_id, actor=AGENT, workflow_run_id=run_id,
                    meta={"intent": intent.primary_intent, "provider": provider})

        step = record_step(
            db, run_id=run_id, agent=AGENT, action="understand_request",
            message=f"{patient_res.message} Intent: {intent.summary}",
            data={"patient": patient_res.data, "intent": intent.model_dump(), "llm_provider": provider},
        )
        patch = {"patient": patient_res.data, "intent": intent.model_dump(), "patient_id": patient_id}
        persist_run_state(db, run_id=run_id, state_patch=patch, current_step="safety",
                          status=WorkflowStatus.RUNNING)
        db.commit()

    return {
        "patient_id": patient_id,
        "patient": patient_res.data,
        "intent": intent.model_dump(),
        "current_step": "safety",
        "trace": [step],
    }


def _compose_summary(db, run: WorkflowRun) -> str:
    """Build the patient-facing confirmation from persisted records only."""
    lines: list[str] = []
    state = run.state or {}

    if run.patient_id:
        # Most recent appointment created for this patient in this workflow.
        appt = db.scalar(
            select(Appointment)
            .where(Appointment.patient_id == run.patient_id)
            .order_by(Appointment.id.desc())
        )
        if appt and state.get("appointment", {}).get("appointment_id") == appt.id:
            doctor = db.get(Doctor, appt.doctor_id)
            slot = db.get(AppointmentSlot, appt.slot_id) if appt.slot_id else None
            when = slot.start_time.strftime("%a %d %b %Y, %H:%M UTC") if slot else "a scheduled time"
            lines.append(
                f"✅ Appointment {appt.confirmation_code} with "
                f"{doctor.name if doctor else 'your doctor'} is {appt.status.value} for {when}."
            )

    docs = state.get("documents", {})
    if docs.get("processed"):
        parts = [f"{docs.get('stored', 0)} document(s) processed"]
        if docs.get("duplicates"):
            parts.append(f"{docs['duplicates']} duplicate(s) flagged")
        if docs.get("missing"):
            parts.append(f"missing: {', '.join(docs['missing'])}")
        lines.append("📄 " + "; ".join(parts) + ".")

    reminders = db.scalars(
        select(Reminder).where(Reminder.patient_id == run.patient_id)
    ).all() if run.patient_id else []
    run_reminder_ids = set(state.get("followup", {}).get("reminder_ids", []))
    made = [r for r in reminders if r.id in run_reminder_ids]
    if made:
        lines.append(f"🔔 {len(made)} reminder(s) scheduled.")

    open_esc = db.scalars(
        select(Escalation).where(Escalation.run_id == run.id)
    ).all()
    if open_esc:
        lines.append(
            f"⚠️ {len(open_esc)} item(s) escalated to the care team for human review."
        )

    if not lines:
        lines.append("Your request was received and recorded. No administrative actions were required.")
    return "\n".join(lines)


def finalize_node(state: WorkflowState) -> dict:
    run_id = state["run_id"]
    with session_scope() as db:
        run = db.get(WorkflowRun, run_id)
        halted = bool(state.get("halted"))
        error = state.get("error")

        if error:
            status = WorkflowStatus.FAILED
        elif halted:
            status = WorkflowStatus.ESCALATED
        else:
            status = WorkflowStatus.COMPLETED

        summary = _compose_summary(db, run) if run else ""
        # Prepend any safety message so the patient always sees safety guidance first.
        safety_msg = (state.get("safety") or {}).get("patient_message")
        if safety_msg:
            summary = f"{safety_msg}\n\n{summary}" if summary else safety_msg

        step = record_step(
            db, run_id=run_id, agent=AGENT, action="finalize",
            message=f"Workflow {status.value}.", data={"status": status.value},
        )
        persist_run_state(db, run_id=run_id, state_patch={"summary": summary},
                          current_step="done", status=status, summary=summary)
        write_audit(db, action=f"workflow.{status.value}", entity_type="workflow_run",
                    entity_id=run_id, actor=AGENT, workflow_run_id=run_id,
                    meta={"halted": halted, "error": error})
        db.commit()

    return {"status": status.value, "summary": summary, "current_step": "done", "trace": [step]}

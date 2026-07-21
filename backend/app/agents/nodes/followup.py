"""Follow-up Agent — reminders, notifications, and post-visit follow-up tasks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.agents.state import WorkflowState
from app.core.db import session_scope
from app.models import NotificationChannel, ReminderType, WorkflowStatus
from app.agents.nodes._common import persist_run_state, record_step
from app.tools import schedule_reminder, send_notification, write_audit

AGENT = "followup_agent"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def followup_node(state: WorkflowState) -> dict:
    run_id = state["run_id"]
    patient_id = state.get("patient_id")
    appt = state.get("appointment", {})
    docs = state.get("documents", {})
    reminder_ids: list[int] = []
    notifications: list[int] = []

    with session_scope() as db:
        actions: list[str] = []
        start_time = _parse_iso(appt.get("start_time"))
        appointment_id = appt.get("appointment_id")

        # 1) Appointment reminder (24h before) + confirmation notification.
        if appointment_id and start_time:
            remind_at = max(start_time - timedelta(hours=24), datetime.now(timezone.utc))
            r = schedule_reminder(
                db, patient_id=patient_id, scheduled_at=remind_at,
                message=f"Reminder: your appointment {appt.get('confirmation_code', '')} is on "
                        f"{start_time.strftime('%a %d %b %Y, %H:%M UTC')}.",
                reminder_type=ReminderType.APPOINTMENT, appointment_id=appointment_id,
                workflow_run_id=run_id,
            )
            if r.ok:
                reminder_ids.append(r.data["reminder_id"])
                actions.append("appointment reminder")

            n = send_notification(
                db, patient_id=patient_id,
                subject=f"Appointment confirmed: {appt.get('confirmation_code', '')}",
                body=f"Your appointment is {appt.get('status', 'scheduled')} for "
                     f"{start_time.strftime('%a %d %b %Y, %H:%M UTC')}.",
                channel=NotificationChannel.EMAIL, reminder_id=reminder_ids[-1] if reminder_ids else None,
                workflow_run_id=run_id,
            )
            if n.ok:
                notifications.append(n.data["notification_id"])
                actions.append("confirmation email")

            # 2) Post-visit follow-up task (2 days after).
            fu = schedule_reminder(
                db, patient_id=patient_id, scheduled_at=start_time + timedelta(days=2),
                message="Post-visit follow-up: check whether any further coordination is needed.",
                reminder_type=ReminderType.FOLLOW_UP, appointment_id=appointment_id,
                workflow_run_id=run_id,
            )
            if fu.ok:
                reminder_ids.append(fu.data["reminder_id"])
                actions.append("post-visit follow-up")

        # 3) Missing-document reminder.
        if docs.get("missing"):
            dr = schedule_reminder(
                db, patient_id=patient_id,
                scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
                message=f"Please upload the following required documents: "
                        f"{', '.join(docs['missing'])}.",
                reminder_type=ReminderType.DOCUMENT_REQUEST, workflow_run_id=run_id,
            )
            if dr.ok:
                reminder_ids.append(dr.data["reminder_id"])
                actions.append("document request reminder")

        data = {"reminder_ids": reminder_ids, "notification_ids": notifications,
                "actions": actions}
        message = ("Scheduled: " + ", ".join(actions)) if actions else \
            "No reminders required for this workflow."

        write_audit(db, action="followup.scheduled", entity_type="workflow_run", entity_id=run_id,
                    actor=AGENT, workflow_run_id=run_id, meta={"actions": actions})
        step = record_step(db, run_id=run_id, agent=AGENT, action="schedule_followup",
                           message=message, data=data)
        persist_run_state(db, run_id=run_id, state_patch={"followup": data},
                          current_step="finalize", status=WorkflowStatus.RUNNING)
        db.commit()

    return {"followup": data, "current_step": "finalize", "trace": [step]}

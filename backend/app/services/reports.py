"""Generate a self-contained HTML report for a workflow run, from persisted data only.

The report is downloadable and printable (Ctrl-P → Save as PDF). It never fabricates content —
every value is read from the database records produced by the agent workflow.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AppointmentSlot,
    AuditEvent,
    Doctor,
    PatientProfile,
    Reminder,
    User,
    WorkflowRun,
)


def _esc(value: object) -> str:
    return html.escape(str(value if value is not None else "—"))


def _fmt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%a %d %b %Y, %H:%M UTC")


def render_workflow_report(db: Session, run: WorkflowRun) -> str:
    """Return a complete HTML document summarizing a workflow run."""
    state = run.state or {}
    patient = db.get(PatientProfile, run.patient_id) if run.patient_id else None
    user = db.get(User, patient.user_id) if patient else None

    # Appointment (if any) from persisted state.
    appt_html = "<p class='muted'>No appointment was created in this workflow.</p>"
    appt_id = state.get("appointment", {}).get("appointment_id")
    if appt_id:
        appt = db.get(Appointment, appt_id)
        if appt:
            doctor = db.get(Doctor, appt.doctor_id)
            slot = db.get(AppointmentSlot, appt.slot_id) if appt.slot_id else None
            appt_html = f"""
            <table>
              <tr><th>Confirmation</th><td>{_esc(appt.confirmation_code)}</td></tr>
              <tr><th>Status</th><td>{_esc(appt.status.value)}</td></tr>
              <tr><th>Doctor</th><td>{_esc(doctor.name if doctor else '—')}</td></tr>
              <tr><th>When</th><td>{_fmt(slot.start_time) if slot else '—'}</td></tr>
              <tr><th>Reason</th><td>{_esc(appt.reason)}</td></tr>
            </table>"""

    # Documents.
    docs = state.get("documents", {})
    docs_html = (
        f"<p>Attached: <b>{_esc(docs.get('attached', 0))}</b> · "
        f"Duplicates flagged: <b>{_esc(docs.get('duplicates', 0))}</b> · "
        f"Missing required: <b>{_esc(', '.join(docs.get('missing', [])) or 'none')}</b></p>"
    )

    # Reminders.
    reminder_ids = set(state.get("followup", {}).get("reminder_ids", []))
    reminders = (
        db.scalars(select(Reminder).where(Reminder.patient_id == run.patient_id)).all()
        if run.patient_id else []
    )
    made = [r for r in reminders if r.id in reminder_ids]
    reminders_rows = "".join(
        f"<tr><td>{_esc(r.reminder_type.value)}</td><td>{_fmt(r.scheduled_at)}</td>"
        f"<td>{_esc(r.status.value)}</td></tr>"
        for r in made
    ) or "<tr><td colspan='3' class='muted'>No reminders scheduled.</td></tr>"

    # Agent trace.
    trace_rows = "".join(
        f"<tr><td>{s.sequence}</td><td>{_esc(s.agent)}</td><td>{_esc(s.action)}</td>"
        f"<td>{_esc(s.status)}</td><td>{_esc(s.message)}</td></tr>"
        for s in run.steps
    )

    # Escalations.
    esc_rows = "".join(
        f"<tr><td>{_esc(e.category)}</td><td>{_esc(e.severity)}</td><td>{_esc(e.status.value)}</td>"
        f"<td>{_esc(e.reason)}</td></tr>"
        for e in run.escalations
    ) or "<tr><td colspan='4' class='muted'>No escalations.</td></tr>"

    # Audit trail for this run.
    audit = db.scalars(
        select(AuditEvent).where(AuditEvent.workflow_run_id == run.id).order_by(AuditEvent.id)
    ).all()
    audit_rows = "".join(
        f"<tr><td>{_esc(a.action)}</td><td>{_esc(a.actor)}</td>"
        f"<td>{_esc(a.entity_type)}{('#' + a.entity_id) if a.entity_id else ''}</td>"
        f"<td>{_fmt(a.created_at)}</td></tr>"
        for a in audit
    )

    summary_html = _esc(run.summary).replace("\n", "<br>")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>AgentCare Report — Run #{run.id}</title>
<style>
  body {{ font-family: system-ui, sans-serif; color: #1e293b; max-width: 860px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ color: #1d4ed8; margin-bottom: 0; }}
  .sub {{ color: #64748b; margin-top: .25rem; }}
  .badge {{ display:inline-block; padding:2px 10px; border-radius:999px; background:#dbeafe; color:#1e40af; font-size:.8rem; font-weight:600; }}
  h2 {{ border-bottom: 2px solid #e2e8f0; padding-bottom:.3rem; margin-top:2rem; font-size:1.1rem; }}
  table {{ width:100%; border-collapse: collapse; font-size:.9rem; margin-top:.5rem; }}
  th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid #eef2f7; vertical-align:top; }}
  th {{ color:#475569; width: 160px; }}
  thead th {{ width:auto; background:#f8fafc; }}
  .muted {{ color:#94a3b8; }}
  .box {{ background:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; padding:.75rem 1rem; }}
  .safety {{ background:#fff7ed; border-color:#fed7aa; }}
  footer {{ margin-top:2.5rem; color:#94a3b8; font-size:.8rem; border-top:1px solid #e2e8f0; padding-top:.75rem; }}
  @media print {{ body {{ margin:0; }} }}
</style></head>
<body>
  <h1>AgentCare — Care Coordination Report</h1>
  <p class="sub">Run #{run.id} · <span class="badge">{_esc(run.status.value)}</span> · generated {_fmt(datetime.now(timezone.utc))}</p>

  <h2>Patient</h2>
  <table>
    <tr><th>Name</th><td>{_esc(user.name if user else '—')}</td></tr>
    <tr><th>MRN</th><td>{_esc(patient.mrn if patient else '—')}</td></tr>
    <tr><th>Preferred language</th><td>{_esc(patient.preferred_language if patient else '—')}</td></tr>
  </table>

  <h2>Request</h2>
  <div class="box">“{_esc(run.request_text)}”</div>

  <h2>Outcome summary</h2>
  <div class="box">{summary_html or '<span class="muted">No summary.</span>'}</div>

  <h2>Routing</h2>
  <p>Department: <b>{_esc(state.get('routing', {}).get('department_name'))}</b>
     (confidence {_esc(round(float(state.get('routing', {}).get('confidence', 0)) * 100))}%)</p>

  <h2>Appointment</h2>
  {appt_html}

  <h2>Documents</h2>
  {docs_html}

  <h2>Reminders</h2>
  <table><thead><tr><th>Type</th><th>Scheduled</th><th>Status</th></tr></thead>
  <tbody>{reminders_rows}</tbody></table>

  <h2>Escalations &amp; human oversight</h2>
  <table><thead><tr><th>Category</th><th>Severity</th><th>Status</th><th>Reason</th></tr></thead>
  <tbody>{esc_rows}</tbody></table>

  <h2>Agent trace</h2>
  <table><thead><tr><th>#</th><th>Agent</th><th>Action</th><th>Status</th><th>Message</th></tr></thead>
  <tbody>{trace_rows}</tbody></table>

  <h2>Audit trail</h2>
  <table><thead><tr><th>Action</th><th>Actor</th><th>Entity</th><th>Time</th></tr></thead>
  <tbody>{audit_rows}</tbody></table>

  <footer>
    AgentCare is an administrative coordination system. It does not diagnose, prescribe, or replace a
    clinician. All data shown is drawn from persisted workflow records. Sample data is synthetic.
  </footer>
</body></html>"""

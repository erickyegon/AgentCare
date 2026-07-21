# AgentCare — User Guide

A practical walkthrough of the patient portal and staff console. The same content is available
in-app at **`/help`**.

Demo accounts (password `AgentCare!2026`, all synthetic): `patient@agentcare.io`,
`staff@agentcare.io`, `admin@agentcare.io`. The login screen has one-click demo-fill buttons.

---

## For patients

1. **Sign in / register.** Use the demo **Patient** button, or register — a patient profile with an
   MRN is created automatically.
2. **Upload documents (optional).** From **New request** or **Documents**, upload files such as an
   ECG, blood report, or referral. Each upload is classified by type and checked for duplicates via
   a SHA-256 checksum.
3. **Submit a request in plain language**, e.g.
   *"I need a cardiology follow-up next week and want to attach my old ECG."* Tick any documents to
   attach, then **Submit to AgentCare**.
4. **Watch the live agent trace.** Six agents coordinate in sequence — Coordinator → Safety →
   Routing → Appointment → Document → Follow-up — streamed live as each step completes.
5. **Review the result.** A confirmation is composed from real records: appointment code and time,
   any missing required documents, and scheduled reminders.
6. **Manage your care.** Use **Appointments** (cancel if needed — late cancellations go to staff for
   approval), **Documents**, and **Reminders**.
7. **Download a report.** Open any request → **Report** to save a printable HTML summary (open it and
   use *Print → Save as PDF* for a PDF).

## For staff & administrators

1. **Sign in** with the demo **Staff**/**Admin** button or your account. Staff-only routes are
   enforced in the backend, not just hidden in the UI.
2. **Overview & Analytics.** Live totals and charts (workflows, appointments, escalations, reminders,
   department load) computed directly from the database.
3. **Review escalations.** Emergencies, clinical questions, uncertain routing, and late cancellations
   arrive in **Escalations**. **Approve**/**Reject** with a note — the decision is persisted with
   your identity.
4. **Approve gated actions.** Approving a late-cancellation *performs* the cancellation; rejecting
   *restores* the appointment.
5. **Inspect workflows.** Open any run to see the full agent trace, escalations, and audit trail;
   download a report for records.
6. **Manage the catalog.** Add **Departments** (routing can only target departments that exist),
   doctors, and slots.
7. **Audit log.** Every agent and human action is recorded immutably and can be filtered per run.

## Safety boundary (important)

AgentCare handles **administration and coordination only**. It never diagnoses, interprets results,
prescribes, changes dosages, or claims to replace a clinician.

- **Emergencies** (e.g. chest pain, difficulty breathing): the Safety agent **halts** the automated
  workflow, advises contacting emergency services, and raises a critical escalation.
- **Clinical questions** (diagnosis, medication, dosage, result interpretation): refused and
  escalated to a clinician; administrative parts (like booking) still proceed.
- **Sensitive actions** (e.g. late cancellations): require staff approval before taking effect.
- **Privacy:** patients can only see/act on their own records; all sample data is synthetic; secrets
  live only in a local, gitignored `.env`.

> If you are experiencing a medical emergency, contact your local emergency number or go to the
> nearest emergency department immediately.

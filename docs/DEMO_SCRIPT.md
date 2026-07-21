# AgentCare — Demo Script (≈ 4 minutes)

A tight, judge-friendly walkthrough that shows every scored capability: multi-agent
orchestration, safety & human oversight, document coordination, persistence, and auditability.

**Setup:** app running (Docker Compose or the deployed URLs). Have the login page open.
Demo accounts (password `AgentCare!2026`): `patient@agentcare.io`, `staff@agentcare.io`.

---

### 0 · Framing (15s)
> "AgentCare turns a plain-language administrative request into a fully-coordinated, persisted
> workflow — booking, documents, reminders, follow-up — while keeping every medical decision with a
> human. It's six distinct agents on a LangGraph state machine, wired end-to-end to a SQL database."

### 1 · Patient: the happy path (75s)
1. Sign in with **Patient** (one-click demo fill) → you land on **New request**.
2. Click the example chip **"I need a cardiology follow-up next week and want to attach my old ECG."**
   *(Optional: upload a file named `ecg.pdf` and tick it to attach.)*
3. Click **Submit to AgentCare**. Narrate the **live trace** as each agent streams in:
   - 🧭 **Coordinator** identifies the patient + intent
   - 🛡️ **Safety** clears it (administrative)
   - 🔀 **Routing** → Cardiology (90%)
   - 📅 **Appointment** books a real slot with conflict-checking → confirmation code
   - 📄 **Document** flags the missing/attached ECG (checksum de-dup)
   - 🔔 **Follow-up** schedules reminders + a confirmation email
4. Point at the **Result** card: "This confirmation is composed from persisted DB records, not the
   LLM." Click **Report** → a downloadable HTML summary. Show **Appointments** + **Reminders** tabs.

### 2 · Safety boundary + emergency (45s)
1. Back to **New request**, submit **"I have severe chest pain and cannot breathe right now."**
2. The **Safety agent halts** the workflow — no booking — status **escalated**, with a calm
   "contact emergency services" message.
> "The system never diagnoses or treats. Emergencies stop automation and go to a human."

### 3 · Staff: human oversight (60s)
1. Sign out → sign in with **Staff**.
2. **Overview / Analytics** — live metrics computed from the DB (workflows, appointments by
   department, escalations, reminders).
3. **Escalations** — open the emergency, add a note, click **Approve** → the decision is persisted
   with your identity. *(Mention: approving a late-cancellation actually performs the cancellation —
   a gated action.)*
4. **Workflows → open one** — show the full agent trace, and the **Audit log**: every agent and
   human action recorded immutably. Click **Report** for the run.

### 4 · Under the hood (30s)
> "Python/FastAPI backend, SQLAlchemy + Alembic, six agents with distinct prompts and eight real
> tools on a LangGraph graph, workflow state persisted after every hop, RBAC enforced in code,
> Anthropic Claude with a deterministic offline fallback, 23 passing tests, and a one-command Docker
> stack. Everything you saw is genuinely wired: route → agent → tool → database → persisted result."

---

### Talking points if asked
- **Three+ distinct agents?** Six — each with its own system prompt and tools/responsibility.
- **Not just a chatbot?** It plans, calls tools, and mutates persistent state; the chat box takes
  real actions.
- **Where's the state?** `WorkflowRun.state` (JSON) + per-node `WorkflowStep` rows; survives restart.
- **Safety in code?** `app/agents/nodes/safety.py` + hard heuristics; emergencies hard-stop.
- **Auth?** JWT + backend `require_role` + ownership checks (a patient can't see others' data).

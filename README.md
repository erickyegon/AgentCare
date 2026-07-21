# AgentCare — Agentic AI for Patient Administration & Care Coordination

AgentCare turns a plain-language administrative request — *"I need a cardiology follow-up next
week and want to attach my old ECG"* — into a fully-coordinated, **persisted** workflow: it
identifies the patient, understands the intent, routes to the right department, checks real
availability and books an appointment, coordinates documents, schedules reminders and follow-ups,
and **hands anything clinical or urgent to a human** — with a complete audit trail.

It is **not** a diagnosis or treatment system. The agents never diagnose, prescribe, change
dosages, or claim to replace a clinician. They handle administration and coordination only; the
safety agent actively blocks clinical requests and escalates emergencies to staff.

> Built for the **AgentCare Build Challenge 2026**. Every layer is genuinely wired end-to-end:
> **route → service → agent → tool → database → persisted result.**

---

## ✨ Highlights

| Requirement | How AgentCare delivers |
|---|---|
| **Python backend** | FastAPI + SQLAlchemy 2.0 + Alembic |
| **Agentic, multi-step, tool-using** | **6 distinct agents** orchestrated by a **LangGraph** state machine |
| **≥ 3 distinct agents** | Coordinator · Safety · Routing · Appointment · Document · Follow-up (each has its own system prompt + tools/responsibility) |
| **≥ 3 real tools** | **8 tools**: patient record, department lookup, slot availability, appointment booking, document classify/store, reminder/notification, escalation/approval, audit |
| **Persistent SQL DB** | SQLite (zero-config) or PostgreSQL (Docker) — same models & migrations |
| **Persistent workflow state** | `WorkflowRun.state` (JSON) + per-node `WorkflowStep` trace, updated after every agent hop |
| **User interface** | **Next.js 15 / React** patient portal + staff console (live SSE agent trace) |
| **RBAC in the backend** | JWT + `require_role` dependencies + resource-ownership checks |
| **Human escalation & approval** | `Escalation` records; staff approve/reject; agent actions **gated** on the persisted decision |
| **Audit logging** | Immutable `AuditEvent` on every agent & human action |
| **Error handling / retry** | `tenacity` retries on LLM calls; graph error paths; failed-run status; resumable runs |
| **Env config & secrets** | `pydantic-settings`; secrets only in gitignored `.env`; `.env.example` shipped |
| **Synthetic data** | Idempotent seed: 10 departments, 18 doctors, 720 slots, demo users |
| **Tests** | 19 pytest tests: RBAC, tools, safety boundary, end-to-end workflow |

---

## 🧠 Architecture at a glance

```
                Next.js UI  (patient portal · staff console · live SSE trace)
                     │  REST + Server-Sent Events
                     ▼
        FastAPI  (JWT auth · backend RBAC · audit · error handling)
                     │  creates + drives
                     ▼
        LangGraph StateGraph  ── persists WorkflowRun.state + WorkflowStep after every node
                     │
   ┌────────────┬────┴─────┬──────────────┬───────────────┬───────────────┐
   ▼            ▼          ▼              ▼               ▼               ▼
Coordinator  Safety &   Department    Appointment      Document       Follow-up
  Agent      Escalation   Routing        Agent           Agent          Agent
             (guardrail)   Agent
   │            │          │              │               │               │
   └────────────┴──────────┴──── 8 tools ─┴───────────────┴───────────────┘
                     │  real reads/writes
                     ▼
        SQL database (SQLite / PostgreSQL) — patients, appointments, slots,
        documents, reminders, escalations, workflow runs, audit events
```

**Control flow.** `START → Coordinator → Safety →`
- if the request is an **emergency / self-harm** → Safety **halts** the flow, raises a critical
  `Escalation`, and finalizes with safety guidance (no automated actions).
- otherwise → **Routing** (validated against real departments; low-confidence → escalate) →
  **Appointment** (availability, conflict detection, book/reschedule/cancel) → **Document**
  (classify, de-duplicate, missing-doc check) → **Follow-up** (reminders + notifications) →
  **Finalize** (confirmation composed **only from persisted records**).

Full detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

### The six agents

| Agent | Own responsibility & prompt | Tools it invokes |
|---|---|---|
| **Coordinator** | Identify/create the patient, understand intent, drive the graph, compose the final confirmation from the database | patient record, audit |
| **Safety & Escalation** | Guardrail: block diagnosis/prescription/dosage, detect emergencies & self-harm, raise escalations | escalation/approval, audit |
| **Department Routing** | Classify the administrative request to a real, active department; escalate uncertainty | department lookup, escalation, audit |
| **Appointment** | Retrieve slots, detect conflicts, book/reschedule/cancel, persist state; gate late cancellations for approval | slot availability, appointment booking, escalation, audit |
| **Document** | Confirm classification, map to patient, detect duplicates, flag missing required documents | document classify/store, audit |
| **Follow-up** | Schedule reminders & post-visit follow-ups, send notifications | reminder, notification, audit |

Each agent uses an LLM through a **provider abstraction** (`app/agents/llm.py`): real **Anthropic
Claude** when a key is present, or a **deterministic, input-driven mock** for offline runs, CI, and
tests. The mock is genuine logic over the request (not a fixed response) and also acts as the
graceful-degradation fallback if a live LLM call fails after retries.

---

## 🚀 Quick start

### Option A — Docker Compose (full stack: Postgres + API + Web)

```bash
cp .env.example .env            # optionally set ANTHROPIC_API_KEY and LLM_PROVIDER=anthropic
docker compose up --build
```

- Web UI → http://localhost:3000
- API docs → http://localhost:8000/docs
- Postgres → localhost:5432

The API container migrates the schema (Alembic) and seeds synthetic data on first boot.

### Option B — Local dev (SQLite, zero external services)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                       # defaults work out of the box (SQLite + mock LLM)
python -m app.db.seed                                      # optional; the app also auto-seeds on startup
uvicorn app.main:app --reload --port 8000
```

**Frontend** (in a second terminal)
```bash
cd frontend
npm install
cp .env.example .env.local                                # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000.

### Using real Claude

Set in `backend/.env` (or the root `.env` for compose):
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-5
```
Without a key the app runs fully on the deterministic mock provider — nothing crashes.

---

## 🔐 Demo accounts

Seeded with the password from `SEED_DEFAULT_PASSWORD` (default `AgentCare!2026`). All synthetic.

| Role | Email |
|---|---|
| Patient | `patient@agentcare.io` |
| Staff | `staff@agentcare.io` |
| Admin | `admin@agentcare.io` |

Patients can also self-register from the UI. The login screen has one-click demo fill buttons.

---

## 🧪 Try the core journey

1. Sign in as the **patient** → paste *"I need a cardiology follow-up next week and want to attach
   my old ECG."* (optionally upload a file named like `ecg.pdf`).
2. Watch the **live agent trace** stream each agent's action, then the confirmation built from the
   database (appointment code, missing-document check, reminders).
3. Submit *"I have severe chest pain and cannot breathe right now."* → the **Safety agent halts**
   the workflow and raises a **critical escalation** (no automated booking).
4. Sign in as **staff** → **Escalations** → review the emergency, **Approve/Reject** with a note →
   the decision is persisted with your identity. Inspect the **Workflow** trace and **Audit log**.

---

## 🗄️ Data model (SQLAlchemy)

`User`, `PatientProfile`, `Department`, `Doctor`, `AppointmentSlot`, `Appointment`,
`PatientDocument`, `WorkflowRun`, `WorkflowStep`, `Escalation`, `Reminder`, `Notification`,
`AuditEvent`. Migrations live in [`backend/alembic/`](backend/alembic); the schema is also
described in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 🧩 Project layout

```
AgentCare/
├── backend/
│   ├── app/
│   │   ├── agents/        # LangGraph graph, state, nodes (6 agents), LLM abstraction, heuristics
│   │   ├── api/           # FastAPI routes + RBAC dependencies + error handling
│   │   ├── core/          # config, db engine/session, JWT security
│   │   ├── db/            # init + synthetic seed
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── tools/         # 8 agent tools (real DB logic)
│   ├── alembic/           # migrations
│   ├── tests/             # pytest (rbac, tools, safety, e2e)
│   └── Dockerfile
├── frontend/              # Next.js 15 app (patient portal + staff console)
├── docker-compose.yml
├── docs/ARCHITECTURE.md
└── .github/workflows/agentcare-checks.yml
```

---

## ✅ Tests & checks

```bash
cd backend
export LLM_PROVIDER=mock        # tests never need a network or API key
python -m pytest -q             # 19 tests: rbac, tools, safety boundary, end-to-end workflow
```

The CI workflow ([`.github/workflows/agentcare-checks.yml`](.github/workflows/agentcare-checks.yml))
runs the hackathon's critical checks (Python compiles; an LLM client is declared) on every push.
Add your `SUBMISSION_TOKEN` as a repository secret to enable them.

---

## 🛡️ Safety, security & privacy

- **No clinical autonomy.** The Safety agent (`app/agents/nodes/safety.py`) classifies every request
  and blocks diagnosis/prescription/dosage; emergencies and self-harm halt the automated flow and
  escalate to humans. Confirmations are composed only from persisted administrative records.
- **RBAC in code.** Roles are enforced by FastAPI dependencies (`app/api/deps.py`) and ownership
  checks — patients can only read/act on their own records. Not UI-only hiding.
- **Human-in-the-loop.** Sensitive actions (e.g. late cancellations) create pending `Escalation`s;
  the action only proceeds once staff approve, and the decision is persisted with the reviewer.
- **Secrets & data.** No real patient data or secrets in the repo. All sample data is synthetic;
  secrets live only in a gitignored `.env`; `.env.example` ships without values.

---

## 📦 Submission notes

- Primary backend: **Python** (FastAPI). LLM client declared in `backend/requirements.txt`
  (`anthropic`, `langchain-anthropic`, `langgraph`).
- Default evaluation branch: **`main`**.
- Optional deployment URL / demo video can be added here.

## License

MIT — see the challenge rules for usage. Third-party libraries retain their own licenses.

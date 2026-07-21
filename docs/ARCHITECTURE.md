# AgentCare — Architecture

This document explains how AgentCare is wired end-to-end: the agent orchestration, the tools, the
data model, state persistence, safety, and access control.

## 1. Design goals

1. **Genuine end-to-end wiring** — every request travels *route → service → agent → tool → database
   → persisted result*. No fixed responses; no in-memory-only state.
2. **Distinct, cooperating agents** — six agents, each with its own system prompt and its own
   responsibility/tools, coordinated by a real orchestrator that hands state between them.
3. **Safety first** — administration only; clinical requests are blocked and emergencies escalated.
4. **Human oversight** — sensitive actions require a persisted human approval before they take effect.
5. **Auditable** — every consequential action writes an immutable audit event.

## 2. Technology

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI | Async-capable, typed, auto-docs |
| ORM / DB | SQLAlchemy 2.0 (sync) + Alembic | Reliable, migration-managed; sync pairs cleanly with LangGraph's sync tools |
| Database | SQLite / PostgreSQL | One `DATABASE_URL`; zero-config locally, robust in production |
| Agents | LangGraph `StateGraph` | Explicit nodes/edges, conditional routing, inspectable state |
| LLM | Anthropic Claude via `langchain-anthropic` (+ deterministic mock) | Best tool-use reasoning; mock keeps CI/offline runs green |
| Auth | JWT (`python-jose`) + `passlib[bcrypt]` | Stateless, role-carrying tokens |
| Reliability | `tenacity` | Retry/backoff around LLM calls |
| UI | Next.js 15 / React / Tailwind / TanStack Query | Real SPA; live SSE agent trace |

**Why synchronous SQLAlchemy?** The agent tools and the LangGraph nodes execute synchronously.
Mixing sync DB/tool code inside async request handlers is a common source of subtle bugs, so the
data layer is sync and FastAPI runs path operations in its threadpool — fully concurrent, far
simpler to reason about.

## 3. Orchestration (LangGraph)

The graph is defined in [`backend/app/agents/graph.py`](../backend/app/agents/graph.py) over a
typed `WorkflowState` ([`state.py`](../backend/app/agents/state.py)) — a JSON-serializable
"blackboard" carrying `patient_id`, `intent`, `safety`, `routing`, `appointment`, `documents`,
`followup`, `escalation_ids`, control flags (`halted`, `status`, `current_step`), and an appended
`trace`.

```
START → coordinator ──► safety ──(safe)──► routing ──(resolved)──► appointment
                          │                    │                        │
                    (emergency/               (low                      ▼
                     self-harm →              confidence →           document
                     halt)                    escalate)                 │
                          ▼                    ▼                        ▼
                       finalize ◄──────────────┴──────────────────► followup → finalize → END
```

Conditional edges (`add_conditional_edges`) implement:
- **Safety hard-stop** — `requires_stop` categories (emergency, self-harm) route straight to
  `finalize` after creating a critical escalation; no booking/documents/followup run.
- **Routing uncertainty** — unsupported department or confidence `< 0.4` routes to `finalize` with
  an escalation instead of guessing.

**Nodes never hold a DB session in state.** Each node opens its own session
([`nodes/_common.py`](../backend/app/agents/nodes/_common.py)), does real work, records a
`WorkflowStep`, merges its output into `WorkflowRun.state`, commits, and returns a partial state
that LangGraph reduces into the shared state (the `trace` list uses an `operator.add` reducer).

## 4. State persistence & resumability

After **every** node:
- `WorkflowRun.state` (JSON) is updated with the merged blackboard, plus `current_step` and
  `status` — this is the authoritative, restart-surviving workflow state.
- A `WorkflowStep` row is appended — the visible, ordered agent trace surfaced in the UI and API.

Because the full state is persisted, a run is inspectable at any time (`GET /workflows/{id}`) and
can be re-executed from its stored inputs. Runs are keyed by a stable `thread_id` (also usable as a
LangGraph checkpoint thread id).

## 5. The six agents

Each lives in [`backend/app/agents/nodes/`](../backend/app/agents/nodes) with a dedicated system
prompt in [`prompts.py`](../backend/app/agents/prompts.py).

1. **Coordinator** (`coordinator.py`) — entry: `get_or_create_patient` tool + intent extraction
   (`IntentDecision`). Exit (`finalize`): composes the patient-facing confirmation strictly from
   persisted `Appointment`/`Reminder`/`Document`/`Escalation` records and sets the terminal status.
2. **Safety & Escalation** (`safety.py`) — classifies into `SafetyDecision` (emergency, self-harm,
   clinical_advice, sensitive, none). Emergencies/self-harm **halt**; clinical questions are refused
   and escalated while administrative parts proceed. Never emits clinical content.
3. **Department Routing** (`routing.py`) — proposes a department (`RoutingDecision`), then
   **validates it against the DB** via the `department_lookup` tool so agents can only route to real,
   active departments. Low confidence → escalate.
4. **Appointment** (`appointment.py`) — book/reschedule/cancel through the `slot_availability` and
   `appointment_booking` tools with **conflict detection** (slot-taken and patient double-booking).
   Late cancellations (<24h) are **not** performed autonomously — they create an approval escalation.
5. **Document** (`document.py`) — reviews attached documents, summarizes types, counts duplicates
   (checksum-based), maps them to the patient, and flags **missing required documents** for the
   routed department (e.g. Cardiology requires an ECG).
6. **Follow-up** (`followup.py`) — schedules an appointment reminder (24h prior), a confirmation
   notification, a post-visit follow-up task, and a document-request reminder when documents are
   missing.

### LLM provider abstraction

[`llm.py`](../backend/app/agents/llm.py) exposes one method, `structured(system, user, schema,
mock)`, returning a validated Pydantic object:
- **AnthropicLLM** — `ChatAnthropic(...).with_structured_output(schema)` wrapped in `tenacity`
  retry/backoff. On terminal failure it degrades to the supplied `mock` closure (logged in the
  trace as `mock-fallback`) so a run never dies mid-flight.
- **MockLLM** — evaluates the deterministic closure built from the request in
  [`heuristics.py`](../backend/app/agents/heuristics.py). This is real logic over the input (regex
  intent/safety/specialty detection), used for tests, CI, and offline demos.

## 6. Tools (8)

In [`backend/app/tools/`](../backend/app/tools); every tool performs real DB logic and returns a
uniform `ToolResult`.

| Tool | File | What it does |
|---|---|---|
| Patient record | `patient_record.py` | Find/create patient, allocate MRN |
| Department lookup | `department_lookup.py` | Validate a label against active departments (exact/substring/keyword scoring) |
| Slot availability | `slot_availability.py` | Query real available future slots in a department/timeframe |
| Appointment booking | `appointment_booking.py` | Book/reschedule/cancel with conflict detection; mutate slot status |
| Document classify/store | `document_tools.py` | SHA-256 checksum, duplicate detection, type classification, missing-doc check |
| Reminder / notification | `reminder_notification.py` | Persist reminders; simulate + persist notifications |
| Escalation / approval | `escalation.py` | Create escalations; resolve (approve/reject) with reviewer identity |
| Audit | `audit_tool.py` | Append immutable audit events |

## 7. Data model

See [`backend/app/models/`](../backend/app/models). Timezone handling uses a custom `UtcDateTime`
type so SQLite and PostgreSQL both return aware-UTC datetimes.

```
User(id, name, email, password_hash, role, is_active, created_at)
PatientProfile(id, user_id→User, dob, phone, preferred_language, emergency_contact, mrn)
Department(id, name, slug, description, keywords, active)
Doctor(id, department_id→Department, name, specialty, active)
AppointmentSlot(id, doctor_id→Doctor, start_time, end_time, status)
Appointment(id, patient_id→PatientProfile, doctor_id, slot_id, status, reason, confirmation_code)
PatientDocument(id, patient_id, original_filename, document_type, confidence, checksum,
                storage_reference, is_duplicate, ...)
WorkflowRun(id, thread_id, patient_id, requested_by_user_id, request_text, current_step,
            status, state JSON, summary, error)
WorkflowStep(id, run_id→WorkflowRun, sequence, agent, action, status, message, data JSON)
Escalation(id, run_id→WorkflowRun, category, reason, severity, status, requires_approval,
           reviewed_by→User, resolution_note, payload JSON)
Reminder(id, patient_id, appointment_id, reminder_type, message, scheduled_at, status, channel)
Notification(id, patient_id, reminder_id, channel, recipient, subject, body, status)
AuditEvent(id, actor_id→User, actor, action, entity_type, entity_id, workflow_run_id, meta JSON)
```

## 8. API surface (selected)

Prefix `/api/v1`. Full interactive docs at `/docs`.

| Method & path | Role | Purpose |
|---|---|---|
| `POST /auth/register`, `POST /auth/login` | public | Patient self-registration / login (JWT) |
| `GET /auth/me`, `PATCH /auth/me/profile` | auth | Profile |
| `POST /workflows` | patient | Create a workflow run from a request |
| `POST /workflows/{id}/stream` | owner/staff | Execute + **stream** agent trace (SSE) |
| `POST /workflows/{id}/run` | owner/staff | Execute (non-streaming) |
| `GET /workflows/{id}` | owner/staff | Full run detail incl. state, steps, escalations |
| `POST /me/documents` | patient | Upload a document (classified + de-duplicated) |
| `GET /me/appointments \| /documents \| /reminders` | patient | Own records |
| `GET /staff/escalations` | staff | Pending/all escalations |
| `POST /staff/escalations/{id}/decision` | staff | Approve/reject; executes gated actions |
| `GET /staff/workflows \| /audit \| /patients` | staff | Oversight |
| `POST /departments \| /doctors \| /slots` | staff | Manage catalog |

## 9. Security & access control

- **JWT** carries `sub` (user id) and `role`. Verified in `app/api/deps.py`.
- **`require_role` / `require_staff`** dependencies gate staff routes; patient routes resolve the
  caller's own profile and filter by ownership — a patient can never read or mutate another
  patient's data. Enforced server-side (tested in `tests/test_auth_rbac.py`).
- **Approval gating** — `POST /staff/escalations/{id}/decision` persists the decision and, for a
  `sensitive_action` escalation, performs the held action (e.g. the late cancellation) only on
  approval, or restores prior state on rejection.

## 10. Error handling & recovery

- LLM calls retry with exponential backoff (`tenacity`); terminal failures fall back to the
  deterministic provider so the workflow completes.
- Node failures set `WorkflowRun.status = failed` with the error captured; the runner marks crashed
  runs failed defensively.
- Because state is fully persisted, a run can be re-executed from its stored inputs.

## 11. Testing

`backend/tests/` (run with `LLM_PROVIDER=mock`, no network):
- `test_auth_rbac.py` — registration/login and server-side role enforcement.
- `test_tools.py` — department lookup, document classification, checksum de-duplication,
  missing-document logic.
- `test_safety.py` — emergency halt + escalation, clinical-advice refusal (admin still proceeds),
  no-diagnosis output, cancellation handling.
- `test_workflow_e2e.py` — full route→agents→tools→DB→result: booking, attached documents, audit
  trail, and state persistence across requests.

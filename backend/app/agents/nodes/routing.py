"""Department Routing Agent — classify the request to a real, active department."""

from __future__ import annotations

from sqlalchemy import select

from app.agents.heuristics import route_department
from app.agents.llm import get_llm
from app.agents.prompts import ROUTING_PROMPT
from app.agents.schemas import RoutingDecision
from app.agents.state import WorkflowState
from app.core.db import session_scope
from app.models import Department, WorkflowStatus
from app.agents.nodes._common import persist_run_state, record_step
from app.tools import create_escalation, lookup_department, write_audit

AGENT = "routing_agent"
MIN_CONFIDENCE = 0.4


def routing_node(state: WorkflowState) -> dict:
    run_id = state["run_id"]
    text = state["request_text"]

    with session_scope() as db:
        catalog = [
            {"id": d.id, "name": d.name, "slug": d.slug, "keywords": d.keywords}
            for d in db.scalars(select(Department).where(Department.active.is_(True)))
        ]
        catalog_str = "\n".join(f"- {d['name']} (slug: {d['slug']})" for d in catalog)

        llm = get_llm()
        decision, provider = llm.structured(
            system=ROUTING_PROMPT,
            user=f"Departments available:\n{catalog_str}\n\nPatient request:\n{text}",
            schema=RoutingDecision,
            mock=lambda: route_department(text, catalog),
        )

        # Validate the proposed label against the DB (agents may only route to real departments).
        lookup = lookup_department(db, label=decision.department_label)
        escalation_ids = list(state.get("escalation_ids", []))

        unsupported = (not decision.is_supported) or (not lookup.ok) or (
            decision.confidence < MIN_CONFIDENCE
        )

        if unsupported:
            esc = create_escalation(
                db, run_id=run_id, category="routing",
                reason=(
                    f"Routing uncertain for request (confidence {decision.confidence:.2f}). "
                    f"Proposed: '{decision.department_label}'. {lookup.message}"
                ),
                severity="medium", requires_approval=False,
                payload={"proposed": decision.model_dump(), "request_text": text}, actor=AGENT,
            )
            if esc.ok:
                escalation_ids.append(esc.data["escalation_id"])
            write_audit(db, action="routing.escalated", entity_type="workflow_run", entity_id=run_id,
                        actor=AGENT, workflow_run_id=run_id, meta={"provider": provider})
            step = record_step(
                db, run_id=run_id, agent=AGENT, action="route_department",
                message="Could not confidently route the request; escalated to staff.",
                data={"routing": decision.model_dump(), "llm_provider": provider}, status="escalated",
            )
            persist_run_state(
                db, run_id=run_id,
                state_patch={"routing": {**decision.model_dump(), "resolved": False},
                             "escalation_ids": escalation_ids, "halted": True},
                current_step="finalize", status=WorkflowStatus.ESCALATED,
            )
            db.commit()
            return {"routing": {**decision.model_dump(), "resolved": False},
                    "escalation_ids": escalation_ids, "halted": True,
                    "current_step": "finalize", "trace": [step]}

        routing = {
            "resolved": True,
            "department_id": lookup.data["department_id"],
            "department_name": lookup.data["department_name"],
            "confidence": decision.confidence,
            "rationale": decision.rationale,
        }
        write_audit(db, action="routing.resolved", entity_type="department",
                    entity_id=routing["department_id"], actor=AGENT, workflow_run_id=run_id,
                    meta={"confidence": decision.confidence, "provider": provider})
        step = record_step(
            db, run_id=run_id, agent=AGENT, action="route_department",
            message=f"Routed to {routing['department_name']} "
                    f"(confidence {decision.confidence:.0%}). {decision.rationale}",
            data={"routing": routing, "llm_provider": provider},
        )
        persist_run_state(db, run_id=run_id, state_patch={"routing": routing},
                          current_step="appointment", status=WorkflowStatus.RUNNING)
        db.commit()

    return {"routing": routing, "current_step": "appointment", "trace": [step]}

"""Safety & Escalation Agent — the guardrail that runs before any administrative action."""

from __future__ import annotations

from app.agents.heuristics import assess_safety
from app.agents.llm import get_llm
from app.agents.prompts import SAFETY_PROMPT
from app.agents.schemas import SafetyDecision
from app.agents.state import WorkflowState
from app.core.db import session_scope
from app.models import WorkflowStatus
from app.agents.nodes._common import persist_run_state, record_step
from app.tools import create_escalation, write_audit

AGENT = "safety_agent"


def safety_node(state: WorkflowState) -> dict:
    run_id = state["run_id"]
    text = state["request_text"]

    with session_scope() as db:
        llm = get_llm()
        decision, provider = llm.structured(
            system=SAFETY_PROMPT,
            user=f"Classify this administrative request for safety:\n{text}",
            schema=SafetyDecision,
            mock=lambda: assess_safety(text),
        )

        escalation_ids: list[int] = list(state.get("escalation_ids", []))
        halted = decision.requires_stop

        # Raise an escalation for anything that needs human eyes.
        if decision.requires_human or decision.requires_stop or decision.category != "none":
            requires_approval = decision.category in ("emergency", "self_harm")
            esc = create_escalation(
                db, run_id=run_id, category=decision.category,
                reason=decision.reason, severity=decision.severity,
                requires_approval=requires_approval,
                payload={"request_text": text, "patient_message": decision.patient_message},
                actor=AGENT,
            )
            if esc.ok:
                escalation_ids.append(esc.data["escalation_id"])

        write_audit(db, action="safety.assessed", entity_type="workflow_run", entity_id=run_id,
                    actor=AGENT, workflow_run_id=run_id,
                    meta={"category": decision.category, "requires_stop": decision.requires_stop,
                          "provider": provider})

        action_msg = decision.reason
        if halted:
            action_msg += " Automated administrative actions halted pending human review."

        step = record_step(
            db, run_id=run_id, agent=AGENT, action="safety_check",
            message=action_msg,
            data={"safety": decision.model_dump(), "llm_provider": provider,
                  "escalation_ids": escalation_ids},
            status="halted" if halted else "completed",
        )

        next_step = "finalize" if halted else "routing"
        persist_run_state(
            db, run_id=run_id,
            state_patch={"safety": decision.model_dump(), "escalation_ids": escalation_ids,
                         "halted": halted},
            current_step=next_step,
            status=WorkflowStatus.ESCALATED if halted else WorkflowStatus.RUNNING,
        )
        db.commit()

    return {
        "safety": decision.model_dump(),
        "escalation_ids": escalation_ids,
        "halted": halted,
        "current_step": next_step,
        "trace": [step],
    }


def safety_router(state: WorkflowState) -> str:
    """Conditional edge: stop the automated flow on hard-stop safety categories."""
    return "finalize" if state.get("halted") else "routing"

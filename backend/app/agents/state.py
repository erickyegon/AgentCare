"""The shared workflow state (the agent 'blackboard').

Every field is JSON-serializable so the full state can be persisted to
``WorkflowRun.state`` after each node and handed between agents. Database handles are
never placed in state — each node opens its own session.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class WorkflowState(TypedDict, total=False):
    # Identity / bookkeeping
    run_id: int
    thread_id: str
    user_id: int
    patient_id: int | None
    request_text: str
    document_ids: list[int]

    # Per-agent outputs
    patient: dict[str, Any]
    intent: dict[str, Any]
    safety: dict[str, Any]
    routing: dict[str, Any]
    appointment: dict[str, Any]
    documents: dict[str, Any]
    followup: dict[str, Any]

    # Control flow
    status: str
    current_step: str
    halted: bool
    escalation_ids: list[int]
    summary: str
    error: str | None

    # Visible agent trace — appended to by every node (reducer merges lists).
    trace: Annotated[list[dict[str, Any]], operator.add]


def new_state(
    *, run_id: int, thread_id: str, user_id: int, request_text: str, document_ids: list[int]
) -> WorkflowState:
    return WorkflowState(
        run_id=run_id,
        thread_id=thread_id,
        user_id=user_id,
        patient_id=None,
        request_text=request_text,
        document_ids=document_ids,
        status="running",
        current_step="coordinator",
        halted=False,
        escalation_ids=[],
        summary="",
        error=None,
        trace=[],
    )

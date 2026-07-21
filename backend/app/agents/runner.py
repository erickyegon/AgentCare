"""Runner — create, execute, stream, and resume workflow runs.

The runner is the seam between the API layer and the LangGraph state machine. It creates the
persistent ``WorkflowRun``, drives the graph, and (for the live UI) streams per-node trace
events as they happen.
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.agents.graph import get_graph
from app.agents.state import WorkflowState, new_state
from app.models import User, WorkflowRun, WorkflowStatus
from app.tools import write_audit

logger = logging.getLogger("agentcare.runner")


def create_run(
    db: Session, *, user: User, request_text: str, document_ids: list[int] | None = None
) -> WorkflowRun:
    """Persist a new WorkflowRun in PENDING state and return it."""
    thread_id = "wf_" + secrets.token_hex(8)
    run = WorkflowRun(
        thread_id=thread_id,
        requested_by_user_id=user.id,
        request_text=request_text,
        current_step="coordinator",
        status=WorkflowStatus.PENDING,
        # Persist the attached document ids so the (separate) execute/stream request can use them.
        state={"document_ids": document_ids or []},
    )
    db.add(run)
    db.flush()
    write_audit(db, action="workflow.created", entity_type="workflow_run", entity_id=run.id,
                actor="patient", actor_id=user.id, workflow_run_id=run.id,
                meta={"document_ids": document_ids or []})
    db.commit()
    db.refresh(run)
    return run


def _initial_state(run: WorkflowRun, document_ids: list[int] | None) -> WorkflowState:
    if document_ids is None:
        document_ids = (run.state or {}).get("document_ids", [])
    return new_state(
        run_id=run.id,
        thread_id=run.thread_id,
        user_id=run.requested_by_user_id,
        request_text=run.request_text,
        document_ids=document_ids,
    )


def _config(run: WorkflowRun) -> dict:
    return {"configurable": {"thread_id": run.thread_id}, "recursion_limit": 25}


def run_workflow(run: WorkflowRun, document_ids: list[int] | None = None) -> dict[str, Any]:
    """Execute the graph to completion and return the final state (blocking)."""
    graph = get_graph()
    initial = _initial_state(run, document_ids)
    try:
        final = graph.invoke(initial, config=_config(run))
        return dict(final)
    except Exception as exc:  # pragma: no cover - defensive; nodes handle their own errors
        logger.exception("Workflow %s crashed", run.id)
        _mark_failed(run.id, str(exc))
        return {"status": "failed", "error": str(exc)}


def stream_workflow(run: WorkflowRun, document_ids: list[int] | None = None) -> Iterator[dict]:
    """Yield trace events as each agent node completes — used by the SSE endpoint."""
    graph = get_graph()
    initial = _initial_state(run, document_ids)
    try:
        for update in graph.stream(initial, config=_config(run), stream_mode="updates"):
            # ``update`` maps node_name -> partial state returned by that node.
            for node_name, patch in update.items():
                for event in patch.get("trace", []) if isinstance(patch, dict) else []:
                    yield {"type": "step", "node": node_name, "event": event}
        yield {"type": "done"}
    except Exception as exc:  # pragma: no cover
        logger.exception("Workflow %s stream crashed", run.id)
        _mark_failed(run.id, str(exc))
        yield {"type": "error", "message": str(exc)}


def _mark_failed(run_id: int, error: str) -> None:
    from app.core.db import session_scope

    with session_scope() as db:
        run = db.get(WorkflowRun, run_id)
        if run is not None:
            run.status = WorkflowStatus.FAILED
            run.error = error
            db.commit()

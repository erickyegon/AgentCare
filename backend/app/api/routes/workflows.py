"""Workflow routes — submit an administrative request and run the agent graph.

``POST /workflows`` creates the persistent run; ``POST /workflows/{id}/stream`` executes the
agent graph and streams each agent's trace event over Server-Sent Events for the live UI.
``POST /workflows/{id}/run`` is the non-streaming equivalent.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user
from app.api.errors import AppError, ForbiddenError, NotFoundError
from app.core.db import get_db, session_scope
from app.agents.runner import create_run, run_workflow, stream_workflow
from app.models import (
    Escalation,
    PatientDocument,
    PatientProfile,
    User,
    UserRole,
    WorkflowRun,
    WorkflowStatus,
    WorkflowStep,
)
from app.schemas.clinical import (
    EscalationOut,
    SubmitRequest,
    WorkflowRunDetail,
    WorkflowRunOut,
    WorkflowStepOut,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _owns_or_staff(db: Session, user: User, run: WorkflowRun) -> None:
    if user.role in (UserRole.STAFF, UserRole.ADMIN):
        return
    if run.requested_by_user_id == user.id:
        return
    raise ForbiddenError("You cannot access this workflow run.")


def _validate_documents(db: Session, profile: PatientProfile, document_ids: list[int]) -> None:
    if not document_ids:
        return
    owned = set(
        db.scalars(
            select(PatientDocument.id).where(
                PatientDocument.id.in_(document_ids),
                PatientDocument.patient_id == profile.id,
            )
        )
    )
    missing = set(document_ids) - owned
    if missing:
        raise AppError(f"Documents not found or not yours: {sorted(missing)}")


@router.post("", response_model=WorkflowRunOut, status_code=201)
def submit_request(
    payload: SubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkflowRun:
    """Patients submit a free-text administrative request; creates a PENDING run."""
    if user.role != UserRole.PATIENT:
        raise ForbiddenError("Only patients can submit requests.")
    profile = db.scalar(select(PatientProfile).where(PatientProfile.user_id == user.id))
    if profile is None:
        profile = PatientProfile(user_id=user.id)
        db.add(profile)
        db.commit()
    _validate_documents(db, profile, payload.document_ids)
    run = create_run(db, user=user, request_text=payload.message, document_ids=payload.document_ids)
    return run


@router.post("/{run_id}/run", response_model=WorkflowRunDetail)
def execute_run(
    run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> WorkflowRun:
    """Execute a pending run to completion (non-streaming) and return the full detail."""
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise NotFoundError("Workflow run not found")
    _owns_or_staff(db, user, run)
    if run.status not in (WorkflowStatus.PENDING,):
        # Idempotent: return current state if already executed.
        db.refresh(run)
        return run
    run_workflow(run)
    db.expire_all()
    return db.get(WorkflowRun, run_id)


@router.post("/{run_id}/stream")
def stream_run(
    run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Execute the run and stream agent trace events via SSE."""
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise NotFoundError("Workflow run not found")
    _owns_or_staff(db, user, run)
    thread_id = run.thread_id

    def event_generator():
        # Re-load the run inside a fresh session bound to the generator's lifetime.
        with session_scope() as gen_db:
            fresh = gen_db.scalar(select(WorkflowRun).where(WorkflowRun.thread_id == thread_id))
            if fresh is None:
                yield {"event": "error", "data": json.dumps({"message": "run vanished"})}
                return
            if fresh.status != WorkflowStatus.PENDING:
                yield {"event": "info",
                       "data": json.dumps({"message": f"already {fresh.status.value}"})}
        for evt in stream_workflow(fresh):
            yield {"event": evt.get("type", "step"), "data": json.dumps(evt)}

    return EventSourceResponse(event_generator())


@router.get("", response_model=list[WorkflowRunOut])
def list_my_runs(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[WorkflowRun]:
    stmt = select(WorkflowRun).order_by(WorkflowRun.id.desc())
    if user.role == UserRole.PATIENT:
        stmt = stmt.where(WorkflowRun.requested_by_user_id == user.id)
    return list(db.scalars(stmt.limit(100)))


@router.get("/{run_id}", response_model=WorkflowRunDetail)
def get_run(
    run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> WorkflowRun:
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise NotFoundError("Workflow run not found")
    _owns_or_staff(db, user, run)
    return run


@router.get("/{run_id}/steps", response_model=list[WorkflowStepOut])
def get_steps(
    run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[WorkflowStep]:
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise NotFoundError("Workflow run not found")
    _owns_or_staff(db, user, run)
    return list(
        db.scalars(
            select(WorkflowStep).where(WorkflowStep.run_id == run_id)
            .order_by(WorkflowStep.sequence)
        )
    )


@router.get("/{run_id}/escalations", response_model=list[EscalationOut])
def get_run_escalations(
    run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Escalation]:
    run = db.get(WorkflowRun, run_id)
    if run is None:
        raise NotFoundError("Workflow run not found")
    _owns_or_staff(db, user, run)
    return list(db.scalars(select(Escalation).where(Escalation.run_id == run_id)))

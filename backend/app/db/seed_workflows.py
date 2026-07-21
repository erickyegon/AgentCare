"""Seed a handful of *genuine* demo workflow runs.

These are produced by executing the real agent graph — not inserted as fake rows — so the
Analytics dashboard, staff queues, and audit trail have realistic content on first load.
Idempotent: does nothing if any workflow run already exists.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.agents.runner import create_run, run_workflow
from app.core.db import session_scope
from app.models import User, WorkflowRun

logger = logging.getLogger("agentcare.seed")

# (account email, request) — a varied mix: bookings, a document flow, and an emergency
# that produces a pending escalation for the staff demo.
# Timeframes are spread so the same patient's bookings don't overlap (which would correctly
# trigger conflict detection) — this keeps the demo data rich across several departments.
DEMO_REQUESTS: list[tuple[str, str]] = [
    ("patient@agentcare.io", "I need a cardiology follow-up next week and want to attach my old ECG."),
    ("carlos@agentcare.io", "Please book a dermatology appointment this week for a skin check."),
    ("mei@agentcare.io", "I have severe chest pain and cannot breathe right now."),
    ("patient@agentcare.io", "Book a neurology appointment next month for recurring migraines."),
    ("carlos@agentcare.io", "I'd like to book an orthopedics appointment next week for my knee."),
]


def seed_demo_workflows() -> int:
    """Run the demo requests through the agent graph. Returns number of runs created."""
    with session_scope() as db:
        existing = db.scalar(select(func.count(WorkflowRun.id))) or 0
    if existing:
        return 0

    created = 0
    for email, message in DEMO_REQUESTS:
        with session_scope() as db:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                continue
            run = create_run(db, user=user, request_text=message, document_ids=[])
            run_id = run.id
        with session_scope() as db:
            run = db.get(WorkflowRun, run_id)
            run_workflow(run)
        created += 1

    logger.info("Seeded %d demo workflow runs.", created)
    return created

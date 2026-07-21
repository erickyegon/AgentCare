"""Persistent workflow state: runs, per-node steps, and human escalations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import EscalationStatus, WorkflowStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import PatientProfile


class WorkflowRun(Base, TimestampMixin):
    """One end-to-end run of the agent graph for a single patient request.

    ``state`` holds the serialized ``WorkflowState`` (the shared blackboard passed
    between agents) so the run is fully inspectable and resumable after a restart.
    """

    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable, human-friendly identifier also used as the LangGraph checkpointer thread id.
    thread_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True, nullable=True
    )
    requested_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    request_text: Mapped[str] = mapped_column(Text, nullable=False)
    current_step: Mapped[str] = mapped_column(String(64), default="coordinator", nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, native_enum=False, length=24),
        default=WorkflowStatus.PENDING,
        nullable=False,
    )
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped["PatientProfile | None"] = relationship(back_populates="workflow_runs")
    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="WorkflowStep.id"
    )
    escalations: Mapped[list["Escalation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class WorkflowStep(Base, TimestampMixin):
    """A single agent-node execution within a run — the visible agent trace."""

    __tablename__ = "workflow_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="completed", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped["WorkflowRun"] = relationship(back_populates="steps")


class Escalation(Base, TimestampMixin):
    """A human-review / approval record raised by the safety or routing agents."""

    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(48), nullable=False)  # emergency|clinical|routing|...
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    status: Mapped[EscalationStatus] = mapped_column(
        Enum(EscalationStatus, native_enum=False, length=16),
        default=EscalationStatus.PENDING,
        nullable=False,
    )
    requires_approval: Mapped[bool] = mapped_column(default=False, nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    run: Mapped["WorkflowRun"] = relationship(back_populates="escalations")

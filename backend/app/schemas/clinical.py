"""Appointment, document, reminder, escalation, workflow, and audit schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AppointmentStatus,
    DocumentType,
    EscalationStatus,
    ReminderStatus,
    ReminderType,
    WorkflowStatus,
)


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    slot_id: int | None
    status: AppointmentStatus
    reason: str
    confirmation_code: str | None
    created_at: datetime
    updated_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    original_filename: str
    document_type: DocumentType
    classification_confidence: float
    content_type: str
    size_bytes: int
    checksum: str
    document_date: date | None
    is_duplicate: bool
    notes: str
    created_at: datetime


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    appointment_id: int | None
    reminder_type: ReminderType
    message: str
    scheduled_at: datetime
    status: ReminderStatus
    channel: str


class EscalationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    category: str
    reason: str
    severity: str
    status: EscalationStatus
    requires_approval: bool
    reviewed_by: int | None
    resolution_note: str
    created_at: datetime


class EscalationDecision(BaseModel):
    approve: bool
    note: str = Field(default="", max_length=2000)


class WorkflowStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sequence: int
    agent: str
    action: str
    status: str
    message: str
    data: dict
    created_at: datetime


class WorkflowRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: str
    patient_id: int | None
    request_text: str
    current_step: str
    status: WorkflowStatus
    summary: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowRunDetail(WorkflowRunOut):
    state: dict
    steps: list[WorkflowStepOut] = []
    escalations: list[EscalationOut] = []


class SubmitRequest(BaseModel):
    """A free-text administrative request from a patient."""

    message: str = Field(min_length=3, max_length=4000)
    # Optional: ids of already-uploaded documents to attach to this workflow.
    document_ids: list[int] = []


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    actor: str
    action: str
    entity_type: str
    entity_id: str | None
    workflow_run_id: int | None
    meta: dict
    created_at: datetime

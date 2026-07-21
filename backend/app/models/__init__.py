"""SQLAlchemy ORM models for AgentCare.

Importing this package registers every model on the shared ``Base.metadata`` so that
Alembic autogeneration and ``Base.metadata.create_all`` see the full schema.
"""

from app.models.appointment import Appointment, AppointmentSlot
from app.models.audit import AuditEvent
from app.models.catalog import Department, Doctor
from app.models.document import PatientDocument
from app.models.enums import (
    AppointmentStatus,
    DocumentType,
    EscalationStatus,
    NotificationChannel,
    NotificationStatus,
    ReminderStatus,
    ReminderType,
    SlotStatus,
    UserRole,
    WorkflowStatus,
)
from app.models.notification import Notification
from app.models.reminder import Reminder
from app.models.user import PatientProfile, User
from app.models.workflow import Escalation, WorkflowRun, WorkflowStep

__all__ = [
    "Appointment",
    "AppointmentSlot",
    "AuditEvent",
    "Department",
    "Doctor",
    "PatientDocument",
    "AppointmentStatus",
    "DocumentType",
    "EscalationStatus",
    "NotificationChannel",
    "NotificationStatus",
    "ReminderStatus",
    "ReminderType",
    "SlotStatus",
    "UserRole",
    "WorkflowStatus",
    "Notification",
    "Reminder",
    "PatientProfile",
    "User",
    "Escalation",
    "WorkflowRun",
    "WorkflowStep",
]

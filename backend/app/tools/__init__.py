"""Agent tools — each performs real logic against the database or workflow state.

A tool is the unit of action an agent can invoke. Every tool returns a ``ToolResult``
and (where consequential) writes an ``AuditEvent`` so the full action trail is persisted.
"""

from app.tools.appointment_booking import (
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
)
from app.tools.audit_tool import write_audit
from app.tools.base import ToolResult
from app.tools.department_lookup import lookup_department
from app.tools.document_tools import classify_document, store_document
from app.tools.escalation import create_escalation, resolve_escalation
from app.tools.patient_record import get_or_create_patient, get_patient
from app.tools.reminder_notification import schedule_reminder, send_notification
from app.tools.slot_availability import find_available_slots

__all__ = [
    "ToolResult",
    "book_appointment",
    "cancel_appointment",
    "reschedule_appointment",
    "write_audit",
    "lookup_department",
    "classify_document",
    "store_document",
    "create_escalation",
    "resolve_escalation",
    "get_or_create_patient",
    "get_patient",
    "schedule_reminder",
    "send_notification",
    "find_available_slots",
]

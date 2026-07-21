"""Reminder + notification tools.

``schedule_reminder`` persists a Reminder row. ``send_notification`` simulates delivery by
persisting a Notification (status SENT) and logging it — genuine, auditable state changes
without depending on an external email/SMS provider.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    PatientProfile,
    Reminder,
    ReminderStatus,
    ReminderType,
    User,
)
from app.tools.audit_tool import write_audit
from app.tools.base import ToolResult

logger = logging.getLogger("agentcare.notifications")


def schedule_reminder(
    db: Session,
    *,
    patient_id: int,
    scheduled_at: datetime,
    message: str,
    reminder_type: ReminderType = ReminderType.APPOINTMENT,
    appointment_id: int | None = None,
    channel: str = "email",
    workflow_run_id: int | None = None,
) -> ToolResult:
    """Create a scheduled reminder for a patient."""
    if db.get(PatientProfile, patient_id) is None:
        return ToolResult(ok=False, message=f"No patient with id {patient_id}.")

    reminder = Reminder(
        patient_id=patient_id,
        appointment_id=appointment_id,
        reminder_type=reminder_type,
        message=message,
        scheduled_at=scheduled_at,
        status=ReminderStatus.SCHEDULED,
        channel=channel,
    )
    db.add(reminder)
    db.flush()
    write_audit(
        db,
        action="reminder.scheduled",
        entity_type="reminder",
        entity_id=reminder.id,
        actor="followup_agent",
        workflow_run_id=workflow_run_id,
        meta={"type": reminder_type.value, "scheduled_at": scheduled_at.isoformat()},
    )
    return ToolResult(
        ok=True,
        message=f"{reminder_type.value.replace('_', ' ').title()} reminder scheduled for "
        f"{scheduled_at.isoformat()}.",
        data={"reminder_id": reminder.id, "scheduled_at": scheduled_at.isoformat()},
    )


def send_notification(
    db: Session,
    *,
    patient_id: int | None,
    subject: str,
    body: str,
    channel: NotificationChannel = NotificationChannel.EMAIL,
    reminder_id: int | None = None,
    recipient: str | None = None,
    workflow_run_id: int | None = None,
) -> ToolResult:
    """Simulate sending a notification and persist it as SENT."""
    if recipient is None and patient_id is not None:
        profile = db.get(PatientProfile, patient_id)
        if profile is not None:
            user = db.get(User, profile.user_id)
            recipient = user.email if user else "unknown@example.com"
    recipient = recipient or "unknown@example.com"

    notification = Notification(
        patient_id=patient_id,
        reminder_id=reminder_id,
        channel=channel,
        recipient=recipient,
        subject=subject,
        body=body,
        status=NotificationStatus.SENT,
    )
    db.add(notification)
    db.flush()
    logger.info("NOTIFY[%s] -> %s | %s", channel.value, recipient, subject)
    write_audit(
        db,
        action="notification.sent",
        entity_type="notification",
        entity_id=notification.id,
        actor="followup_agent",
        workflow_run_id=workflow_run_id,
        meta={"channel": channel.value, "recipient": recipient},
    )
    return ToolResult(
        ok=True,
        message=f"Notification sent to {recipient} via {channel.value}.",
        data={"notification_id": notification.id, "recipient": recipient},
    )

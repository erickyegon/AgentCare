"""Enumerations used across models. Stored as strings for readability + portability."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    STAFF = "staff"
    ADMIN = "admin"


class SlotStatus(str, enum.Enum):
    AVAILABLE = "available"
    HELD = "held"
    BOOKED = "booked"
    CANCELLED = "cancelled"


class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    AWAITING_APPROVAL = "awaiting_approval"


class DocumentType(str, enum.Enum):
    ECG = "ecg"
    BLOOD_REPORT = "blood_report"
    IMAGING = "imaging"           # X-ray / MRI / CT / ultrasound
    PRESCRIPTION = "prescription"
    REFERRAL_LETTER = "referral_letter"
    INSURANCE = "insurance"
    IDENTIFICATION = "identification"
    DISCHARGE_SUMMARY = "discharge_summary"
    OTHER = "other"


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


class EscalationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class ReminderType(str, enum.Enum):
    APPOINTMENT = "appointment"
    DOCUMENT_REQUEST = "document_request"
    FOLLOW_UP = "follow_up"


class ReminderStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELLED = "cancelled"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"


class NotificationStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"

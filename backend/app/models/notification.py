"""Notifications — a persisted, auditable simulation of email/SMS/in-app delivery.

Delivery is simulated (written to the DB and logged) rather than sending real messages,
so the workflow is fully testable without external providers while remaining genuine,
stateful application logic.
"""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.mixins import TimestampMixin


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True, nullable=True
    )
    reminder_id: Mapped[int | None] = mapped_column(
        ForeignKey("reminders.id", ondelete="SET NULL"), nullable=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, native_enum=False, length=16),
        default=NotificationChannel.EMAIL,
        nullable=False,
    )
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, native_enum=False, length=16),
        default=NotificationStatus.QUEUED,
        nullable=False,
    )

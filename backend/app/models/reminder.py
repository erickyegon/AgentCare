"""Reminders and follow-up tasks."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import ReminderStatus, ReminderType
from app.models.mixins import TimestampMixin
from app.models.types import UtcDateTime

if TYPE_CHECKING:
    from app.models.user import PatientProfile


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    reminder_type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType, native_enum=False, length=24),
        default=ReminderType.APPOINTMENT,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, native_enum=False, length=16),
        default=ReminderStatus.SCHEDULED,
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(16), default="email", nullable=False)

    patient: Mapped["PatientProfile"] = relationship(back_populates="reminders")

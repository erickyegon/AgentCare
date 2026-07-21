"""Appointment slots and appointments."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import AppointmentStatus, SlotStatus
from app.models.mixins import TimestampMixin
from app.models.types import UtcDateTime

if TYPE_CHECKING:
    from app.models.catalog import Doctor
    from app.models.user import PatientProfile


class AppointmentSlot(Base, TimestampMixin):
    __tablename__ = "appointment_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="CASCADE"), index=True, nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(UtcDateTime, index=True, nullable=False)
    end_time: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    status: Mapped[SlotStatus] = mapped_column(
        Enum(SlotStatus, native_enum=False, length=20), default=SlotStatus.AVAILABLE, nullable=False
    )

    doctor: Mapped["Doctor"] = relationship(back_populates="slots")
    appointment: Mapped["Appointment | None"] = relationship(
        back_populates="slot", uselist=False
    )


class Appointment(Base, TimestampMixin):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    doctor_id: Mapped[int] = mapped_column(
        ForeignKey("doctors.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    slot_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointment_slots.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, native_enum=False, length=24),
        default=AppointmentStatus.PENDING,
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confirmation_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True)

    patient: Mapped["PatientProfile"] = relationship(back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship()
    slot: Mapped["AppointmentSlot | None"] = relationship(back_populates="appointment")

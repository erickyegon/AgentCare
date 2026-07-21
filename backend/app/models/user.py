"""User accounts and patient profiles."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.document import PatientDocument
    from app.models.reminder import Reminder
    from app.models.workflow import WorkflowRun


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), default=UserRole.PATIENT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    profile: Mapped["PatientProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class PatientProfile(Base, TimestampMixin):
    __tablename__ = "patient_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(40), default="English", nullable=False)
    emergency_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mrn: Mapped[str | None] = mapped_column(  # Medical Record Number (synthetic)
        String(32), unique=True, index=True, nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="profile")
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    documents: Mapped[list["PatientDocument"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    workflow_runs: Mapped[list["WorkflowRun"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )

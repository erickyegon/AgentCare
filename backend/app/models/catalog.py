"""Hospital catalog: departments and doctors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.appointment import AppointmentSlot


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Comma-separated administrative keywords used by the routing agent's tool lookup.
    keywords: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    doctors: Mapped[list["Doctor"]] = relationship(
        back_populates="department", cascade="all, delete-orphan"
    )


class Doctor(Base, TimestampMixin):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department: Mapped["Department"] = relationship(back_populates="doctors")
    slots: Mapped[list["AppointmentSlot"]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )

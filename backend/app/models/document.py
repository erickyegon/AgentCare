"""Patient documents with checksum-based deduplication metadata."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import DocumentType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import PatientProfile


class PatientDocument(Base, TimestampMixin):
    __tablename__ = "patient_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, native_enum=False, length=24),
        default=DocumentType.OTHER,
        nullable=False,
    )
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_reference: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # sha256 hex
    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(default=False, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    patient: Mapped["PatientProfile"] = relationship(back_populates="documents")

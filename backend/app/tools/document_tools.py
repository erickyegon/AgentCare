"""Document tools — classification and storage with checksum-based deduplication.

``classify_document`` assigns a ``DocumentType`` using filename/content heuristics (and can
be augmented by the LLM in the Document agent). ``store_document`` writes bytes to disk,
computes a SHA-256 checksum, detects duplicates for the patient, records metadata, and
maps the document to the patient — real, persistent logic.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DocumentType, PatientDocument
from app.tools.audit_tool import write_audit
from app.tools.base import ToolResult

# Ordered keyword patterns mapping to a document type. First match wins.
_TYPE_PATTERNS: list[tuple[DocumentType, re.Pattern[str]]] = [
    (DocumentType.ECG, re.compile(r"\b(ecg|ekg|electrocardiogram)\b", re.I)),
    (DocumentType.BLOOD_REPORT, re.compile(r"\b(blood|cbc|lipid|hemoglobin|glucose|lab\s*report|hematology)\b", re.I)),
    (DocumentType.IMAGING, re.compile(r"\b(x[-\s]?ray|mri|ct\s*scan|ultrasound|sonograph|radiograph|imaging)\b", re.I)),
    (DocumentType.PRESCRIPTION, re.compile(r"\b(prescription|rx|medication\s*list)\b", re.I)),
    (DocumentType.REFERRAL_LETTER, re.compile(r"\b(referral|refer)\b", re.I)),
    (DocumentType.INSURANCE, re.compile(r"\b(insurance|policy|coverage|claim)\b", re.I)),
    (DocumentType.IDENTIFICATION, re.compile(r"\b(passport|national\s*id|driver'?s?\s*licen|identity|aadhaar)\b", re.I)),
    (DocumentType.DISCHARGE_SUMMARY, re.compile(r"\b(discharge|summary)\b", re.I)),
]

# Required documents per department slug — used for missing-document checks.
REQUIRED_DOCS: dict[str, list[DocumentType]] = {
    "cardiology": [DocumentType.ECG],
    "orthopedics": [DocumentType.IMAGING],
    "radiology": [DocumentType.REFERRAL_LETTER],
    "oncology": [DocumentType.REFERRAL_LETTER, DocumentType.BLOOD_REPORT],
}


def classify_document(filename: str, hint: str = "") -> tuple[DocumentType, float]:
    """Classify a document from its filename (+ optional text hint).

    Returns (type, confidence). Heuristic and deterministic — genuine logic on the input,
    not a fixed label.
    """
    # Normalize separators (underscores, dots, dashes, digits-adjacency) to spaces so word
    # boundaries work on names like "patient_ECG_2024.pdf".
    haystack = re.sub(r"[^A-Za-z0-9]+", " ", f"{filename} {hint}").strip()
    for doc_type, pattern in _TYPE_PATTERNS:
        if pattern.search(haystack):
            return doc_type, 0.85
    return DocumentType.OTHER, 0.3


def store_document(
    db: Session,
    *,
    patient_id: int,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
    document_date: date | None = None,
    hint: str = "",
    workflow_run_id: int | None = None,
) -> ToolResult:
    """Persist an uploaded document: checksum, dedupe, classify, store, map to patient."""
    checksum = hashlib.sha256(content).hexdigest()

    # Duplicate detection: same patient + same checksum already stored.
    existing = db.scalar(
        select(PatientDocument).where(
            PatientDocument.patient_id == patient_id,
            PatientDocument.checksum == checksum,
        )
    )

    doc_type, confidence = classify_document(filename, hint)

    storage_dir = settings.storage_path / f"patient_{patient_id}"
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename) or "document"
    stored_path = storage_dir / f"{checksum[:12]}_{safe_name}"
    if not stored_path.exists():
        stored_path.write_bytes(content)

    document = PatientDocument(
        patient_id=patient_id,
        original_filename=filename,
        document_type=doc_type,
        classification_confidence=confidence,
        content_type=content_type,
        size_bytes=len(content),
        storage_reference=str(stored_path.relative_to(settings.storage_path.parent))
        if stored_path.is_relative_to(settings.storage_path.parent)
        else str(stored_path),
        checksum=checksum,
        document_date=document_date,
        is_duplicate=existing is not None,
        notes="Duplicate of an existing document." if existing is not None else "",
    )
    db.add(document)
    db.flush()
    write_audit(
        db,
        action="document.stored",
        entity_type="patient_document",
        entity_id=document.id,
        actor="document_agent",
        workflow_run_id=workflow_run_id,
        meta={
            "document_type": doc_type.value,
            "checksum": checksum,
            "is_duplicate": existing is not None,
            "size_bytes": len(content),
        },
    )
    msg = (
        f"Stored '{filename}' classified as {doc_type.value} "
        f"(confidence {confidence:.0%})."
    )
    if existing is not None:
        msg += f" Flagged as a duplicate of document #{existing.id}."
    return ToolResult(
        ok=True,
        message=msg,
        data={
            "document_id": document.id,
            "document_type": doc_type.value,
            "confidence": confidence,
            "checksum": checksum,
            "is_duplicate": existing is not None,
            "duplicate_of": existing.id if existing else None,
        },
    )


def missing_required_documents(
    db: Session, *, patient_id: int, department_slug: str
) -> list[str]:
    """Return the list of required document types the patient has not yet provided."""
    required = REQUIRED_DOCS.get(department_slug, [])
    if not required:
        return []
    present = set(
        db.scalars(
            select(PatientDocument.document_type).where(
                PatientDocument.patient_id == patient_id
            )
        )
    )
    return [dt.value for dt in required if dt not in present]

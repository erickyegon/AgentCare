"""Unit tests for tools — each must perform real logic, not return fixed responses."""

from __future__ import annotations

from app.core.db import session_scope
from app.models import DocumentType
from app.tools import lookup_department
from app.tools.document_tools import classify_document, missing_required_documents, store_document


def test_department_lookup_matches_real_department():
    with session_scope() as db:
        res = lookup_department(db, label="Cardiology")
        assert res.ok
        assert res.data["department_name"] == "Cardiology"
        assert res.data["confidence"] >= 0.8


def test_department_lookup_rejects_unknown():
    with session_scope() as db:
        res = lookup_department(db, label="Teleportation")
        assert not res.ok
        assert res.data["confidence"] == 0.0


def test_classify_document_is_input_driven():
    # Different inputs -> different classifications (not a fixed label).
    assert classify_document("patient_ECG_2024.pdf")[0] == DocumentType.ECG
    assert classify_document("blood_report.pdf")[0] == DocumentType.BLOOD_REPORT
    assert classify_document("chest_xray.png")[0] == DocumentType.IMAGING
    assert classify_document("random.bin")[0] == DocumentType.OTHER


def test_store_document_dedupes_by_checksum(client):
    # Use the seeded patient's profile id (1).
    with session_scope() as db:
        first = store_document(db, patient_id=1, filename="ecg.pdf", content=b"ECG-BYTES")
        db.commit()
        assert first.ok
        assert not first.data["is_duplicate"]

        dup = store_document(db, patient_id=1, filename="ecg_copy.pdf", content=b"ECG-BYTES")
        db.commit()
        assert dup.data["is_duplicate"] is True
        assert dup.data["duplicate_of"] == first.data["document_id"]


def test_missing_required_documents_for_cardiology(client):
    with session_scope() as db:
        # Patient 2 has no documents -> cardiology requires an ECG.
        missing = missing_required_documents(db, patient_id=2, department_slug="cardiology")
        assert "ecg" in missing

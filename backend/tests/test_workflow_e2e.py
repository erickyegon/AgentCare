"""End-to-end workflow tests through the API — route → agents → tools → DB → result."""

from __future__ import annotations


def _run(client, headers, message: str, document_ids=None) -> dict:
    r = client.post("/api/v1/workflows",
                    json={"message": message, "document_ids": document_ids or []}, headers=headers)
    assert r.status_code == 201, r.text
    run_id = r.json()["id"]
    r = client.post(f"/api/v1/workflows/{run_id}/run", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_cardiology_booking_end_to_end(client, fresh_patient_headers):
    detail = _run(client, fresh_patient_headers,
                  "I need a cardiology follow-up next week and want to attach my old ECG.")

    assert detail["status"] == "completed"
    # All six agent roles + finalize produced trace steps.
    agents = {s["agent"] for s in detail["steps"]}
    assert {"coordinator_agent", "safety_agent", "routing_agent",
            "appointment_agent", "document_agent", "followup_agent"} <= agents

    # Routing persisted to Cardiology.
    assert detail["state"]["routing"]["department_name"] == "Cardiology"

    # An appointment was actually persisted and is retrievable.
    appts = client.get("/api/v1/me/appointments", headers=fresh_patient_headers).json()
    assert any(a["status"] in ("confirmed", "rescheduled") for a in appts)

    # The confirmation summary is composed from the persisted appointment (run linked to patient).
    assert detail["patient_id"] is not None
    code = next(a["confirmation_code"] for a in appts if a["confirmation_code"])
    assert code in detail["summary"]

    # Reminders were scheduled.
    reminders = client.get("/api/v1/me/reminders", headers=fresh_patient_headers).json()
    assert len(reminders) >= 1

    # Missing-document check flagged the ECG (cardiology requirement).
    assert "ecg" in detail["state"]["documents"]["missing"]


def test_workflow_with_attached_document(client, fresh_patient_headers):
    # Upload an ECG first, then reference it in the request.
    files = {"file": ("my_ecg.pdf", b"ECG-DATA-UNIQUE-123", "application/pdf")}
    up = client.post("/api/v1/me/documents", files=files, headers=fresh_patient_headers)
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]
    assert up.json()["document_type"] == "ecg"

    detail = _run(client, fresh_patient_headers,
                  "Book a cardiology appointment next week; attaching my ECG.",
                  document_ids=[doc_id])
    assert detail["status"] == "completed"
    docs_state = detail["state"]["documents"]
    assert docs_state["attached"] == 1
    # ECG now present -> not in missing list.
    assert "ecg" not in docs_state["missing"]


def test_audit_trail_written(client, fresh_patient_headers, staff_headers):
    detail = _run(client, fresh_patient_headers, "I want to book a dermatology appointment.")
    run_id = detail["id"]
    audit = client.get(f"/api/v1/staff/audit?workflow_run_id={run_id}", headers=staff_headers).json()
    actions = {a["action"] for a in audit}
    assert "workflow.created" in actions
    assert any(a.startswith("appointment.") for a in actions)
    assert "workflow.completed" in actions


def test_workflow_state_is_persisted(client, fresh_patient_headers):
    detail = _run(client, fresh_patient_headers, "Book a neurology appointment next week.")
    run_id = detail["id"]
    # Re-fetch from a fresh request: state survived (persisted, not in-memory).
    again = client.get(f"/api/v1/workflows/{run_id}", headers=fresh_patient_headers).json()
    assert again["status"] == "completed"
    assert again["state"]["routing"]["department_name"] == "Neurology"

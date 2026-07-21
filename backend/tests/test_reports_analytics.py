"""Tests for analytics aggregation and downloadable workflow reports."""

from __future__ import annotations


def _run(client, headers, message: str) -> dict:
    r = client.post("/api/v1/workflows", json={"message": message, "document_ids": []}, headers=headers)
    assert r.status_code == 201
    run_id = r.json()["id"]
    client.post(f"/api/v1/workflows/{run_id}/run", headers=headers)
    return run_id


def test_analytics_requires_staff(client, patient_headers):
    assert client.get("/api/v1/staff/analytics", headers=patient_headers).status_code == 403


def test_analytics_reflects_real_data(client, fresh_patient_headers, staff_headers):
    _run(client, fresh_patient_headers, "Book a cardiology follow-up next week.")
    data = client.get("/api/v1/staff/analytics", headers=staff_headers).json()

    assert data["totals"]["workflows"] >= 1
    assert data["totals"]["appointments"] >= 1
    # Aggregations are real dicts keyed by status/type.
    assert isinstance(data["workflows_by_status"], dict)
    assert sum(data["workflows_by_status"].values()) == data["totals"]["workflows"]
    assert isinstance(data["appointments_by_department"], list)


def test_report_download_contains_persisted_data(client, fresh_patient_headers):
    run_id = _run(client, fresh_patient_headers, "Book a cardiology follow-up next week.")
    detail = client.get(f"/api/v1/workflows/{run_id}", headers=fresh_patient_headers).json()

    r = client.get(f"/api/v1/workflows/{run_id}/report", headers=fresh_patient_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "attachment" in r.headers.get("content-disposition", "")
    html = r.text
    # The report is built from persisted records: it contains the run id and the routed department.
    assert f"Run #{run_id}" in html
    assert "Cardiology" in html
    # And the confirmation code from the persisted appointment appears in the report.
    appts = client.get("/api/v1/me/appointments", headers=fresh_patient_headers).json()
    code = next((a["confirmation_code"] for a in appts if a["confirmation_code"]), None)
    if code:
        assert code in html


def test_report_ownership_enforced(client, fresh_patient_headers, patient_headers):
    # A run created by one patient cannot be reported by another patient.
    run_id = _run(client, fresh_patient_headers, "Book a dermatology appointment.")
    r = client.get(f"/api/v1/workflows/{run_id}/report", headers=patient_headers)
    assert r.status_code == 403

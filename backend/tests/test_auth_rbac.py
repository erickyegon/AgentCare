"""Auth and role-based access control — enforced in the backend, not the UI."""

from __future__ import annotations


def test_register_and_login(client):
    r = client.post("/api/v1/auth/register",
                    json={"name": "New Patient", "email": "new@example.com", "password": "password123"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "patient"
    assert body["access_token"]

    r = client.post("/api/v1/auth/login",
                    json={"email": "new@example.com", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_rejects_bad_password(client):
    r = client.post("/api/v1/auth/login",
                    json={"email": "patient@agentcare.io", "password": "wrong"})
    assert r.status_code == 401


def test_unauthenticated_is_rejected(client):
    assert client.get("/api/v1/me/appointments").status_code == 401
    assert client.get("/api/v1/staff/audit").status_code == 401


def test_patient_cannot_access_staff_routes(client, patient_headers):
    # RBAC enforced server-side: a patient token must be forbidden on staff endpoints.
    assert client.get("/api/v1/staff/audit", headers=patient_headers).status_code == 403
    assert client.get("/api/v1/staff/escalations", headers=patient_headers).status_code == 403
    assert client.get("/api/v1/staff/patients", headers=patient_headers).status_code == 403


def test_staff_can_access_staff_routes(client, staff_headers):
    assert client.get("/api/v1/staff/audit", headers=staff_headers).status_code == 200
    assert client.get("/api/v1/staff/patients", headers=staff_headers).status_code == 200


def test_patient_cannot_create_department(client, patient_headers):
    r = client.post("/api/v1/departments",
                    json={"name": "Hacker Dept", "description": "", "keywords": ""},
                    headers=patient_headers)
    assert r.status_code == 403

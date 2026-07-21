"""Pytest fixtures.

A throwaway SQLite database is configured via environment BEFORE the app is imported, so the
engine binds to it. The app runs with the deterministic mock LLM provider so tests never need
network access or an API key.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Configure the environment before importing any app module.
_TMP_DB = Path(tempfile.gettempdir()) / "agentcare_test.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["AUTO_INIT_DB"] = "true"
os.environ["AUTO_SEED"] = "true"
os.environ["SEED_DEMO_WORKFLOWS"] = "false"  # deterministic tests: no pre-seeded runs
os.environ["SEED_DEFAULT_PASSWORD"] = "TestPass!123"
os.environ["SECRET_KEY"] = "test-secret-key"

import uuid  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

SEED_PASSWORD = "TestPass!123"


@pytest.fixture(scope="session")
def client():
    get_settings.cache_clear()
    with TestClient(app) as c:  # triggers lifespan → create tables + seed
        yield c
    # Dispose the engine so the SQLite file handle is released before deletion (Windows).
    from app.core.db import engine

    engine.dispose()
    if _TMP_DB.exists():
        try:
            _TMP_DB.unlink()
        except PermissionError:
            pass


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patient_headers(client) -> dict:
    r = client.post("/api/v1/auth/login",
                    json={"email": "patient@agentcare.io", "password": SEED_PASSWORD})
    assert r.status_code == 200, r.text
    return _auth_header(r.json()["access_token"])


@pytest.fixture
def staff_headers(client) -> dict:
    r = client.post("/api/v1/auth/login",
                    json={"email": "staff@agentcare.io", "password": SEED_PASSWORD})
    assert r.status_code == 200, r.text
    return _auth_header(r.json()["access_token"])


@pytest.fixture
def fresh_patient_headers(client) -> dict:
    """A brand-new, isolated patient so document/appointment state doesn't bleed across tests."""
    email = f"p_{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/v1/auth/register",
                    json={"name": "Fresh Patient", "email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return _auth_header(r.json()["access_token"])

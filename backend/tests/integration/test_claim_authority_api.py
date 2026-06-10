"""Integration test: Claim authority API routes."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_API_KEY", "test-key")


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "claim_api.db")
    monkeypatch.setenv("SQLITE_PATH", db_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VECTOR_DIR", str(tmp_path / "vectors"))

    from app.store.database import Database
    Database._instance = None

    from app.main import app
    return TestClient(app)


def test_ratify_claim_via_api(client):
    from app.core.runtime.kernel_instance import kernel

    kernel.emit_event(
        "BeliefFormed",
        "memory",
        "blf-api",
        {"category": "belief", "content": "API测试推断", "confidence": 0.6},
        actor="kernel",
    )

    r = client.post("/api/memory/memories/blf-api/ratify")
    assert r.status_code == 200
    assert r.json()["action"] == "ratify"

    row = kernel.query_state("memories", id="blf-api")[0]
    assert row["claim_status"] == "ratified"


def test_ratify_self_report_fails(client):
    from app.core.runtime.kernel_instance import kernel

    kernel.emit_event(
        "MemoryDerived",
        "memory",
        "m-self-api",
        {"category": "fact", "content": "用户自述", "confidence": 0.9},
        actor="user",
    )

    r = client.post("/api/memory/memories/m-self-api/ratify")
    assert r.status_code == 400

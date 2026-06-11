"""Trajectory suggester — keyword proposals."""

import os
import uuid

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.runtime.kernel import Kernel
from app.core.runtime.trajectory.engine import query_trajectory
from app.core.runtime.trajectory.suggester import (
    match_trajectory_ids,
    propose_links_for_memory,
)
from app.store.database import Database


@pytest.fixture(autouse=True)
def _restore():
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    saved_k, saved_d = ki.kernel, db_mod.db
    yield
    ki.kernel, db_mod.db = saved_k, saved_d


def test_match_entrepreneurship_keywords():
    ids = match_trajectory_ids("我想辞职创业")
    assert "career-entrepreneurship-2026" in ids


def test_propose_links_after_memory(tmp_path):
    k = Kernel(db=Database(db_path=str(tmp_path / "sug.db")))
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = k
    db_mod.db = k._db

    mid = str(uuid.uuid4())
    k.emit_event(
        "MemoryDerived",
        "memory",
        mid,
        payload={"category": "fact", "content": "想辞职创业", "confidence": 0.8},
        actor="extractor",
    )
    links = propose_links_for_memory(k, mid, "想辞职创业")
    assert links
    data = query_trajectory(k, "career-entrepreneurship-2026")
    assert data and len(data["links"]) >= 1
    assert data["links"][0]["claim_status"] == "proposed"

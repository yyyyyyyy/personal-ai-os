"""Trajectory layer — TrajectoryLinked, query_trajectory, link authority."""

import os
from pathlib import Path

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.runtime import kernel_instance
from app.core.runtime.kernel import Kernel
from app.core.runtime.trajectory import link_authority
from app.core.runtime.trajectory.engine import (
    link_event,
    load_merged_registry,
    query_trajectory,
    verify_competing_symmetry,
)
from app.core.runtime.trajectory.registry import load_yaml_registry
from app.store.database import Database

_REGISTRY = Path(__file__).resolve().parents[2] / "trajectory_registry.yaml"


@pytest.fixture(autouse=True)
def _restore_global_runtime():
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    saved_kernel = ki.kernel
    saved_db = db_mod.db
    yield
    ki.kernel = saved_kernel
    db_mod.db = saved_db


def _kernel(tmp_path):
    return Kernel(db=Database(db_path=str(tmp_path / "traj.db")))


def _patch(k):
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = k
    db_mod.db = k._db


class TestTrajectoryRegistry:
    def test_yaml_competing_symmetry(self):
        reg = load_yaml_registry(_REGISTRY)
        violations = verify_competing_symmetry(reg)
        assert violations == [], violations

    def test_merged_registry_includes_yaml(self, tmp_path):
        k = _kernel(tmp_path)
        _patch(k)
        reg = load_merged_registry(k)
        assert "career-entrepreneurship-2026" in reg
        assert "career-corporate-stability-2026" in reg["career-entrepreneurship-2026"]["competing_with"]


class TestTrajectoryLinks:
    def test_link_and_query(self, tmp_path):
        k = _kernel(tmp_path)
        _patch(k)
        src = k.emit_event(
            "MemoryDerived", "memory", "mem-1",
            payload={"content": "我想辞职创业", "category": "career"},
            actor="user",
        )
        link_event(
            k, "career-entrepreneurship-2026", src.seq,
            actor="system", rationale="entrepreneurship mention",
        )
        data = query_trajectory(k, "career-entrepreneurship-2026")
        assert data is not None
        assert len(data["links"]) == 1
        assert data["links"][0]["event_seq"] == src.seq
        assert len(data["events"]) == 1
        assert data["events"][0]["seq"] == src.seq

    def test_many_to_many_same_event(self, tmp_path):
        k = _kernel(tmp_path)
        _patch(k)
        src = k.emit_event(
            "MemoryDerived", "memory", "mem-2",
            payload={"content": "我想辞职创业", "category": "career"},
            actor="user",
        )
        link_event(k, "career-entrepreneurship-2026", src.seq)
        link_event(k, "career-corporate-stability-2026", src.seq)
        a = query_trajectory(k, "career-entrepreneurship-2026")
        b = query_trajectory(k, "career-corporate-stability-2026")
        assert a and b
        assert a["links"][0]["event_seq"] == b["links"][0]["event_seq"]

    def test_link_ratify_status(self, tmp_path):
        k = _kernel(tmp_path)
        _patch(k)
        src = k.emit_event("MemoryDerived", "memory", "m3", payload={"content": "x"}, actor="user")
        ev = link_event(k, "career-entrepreneurship-2026", src.seq)
        link_id = ev.payload["link_id"]
        link_authority.ratify(link_id)
        data = query_trajectory(k, "career-entrepreneurship-2026")
        assert data["links"][0]["claim_status"] == "ratified"

    def test_kernel_query_trajectory(self, tmp_path):
        k = _kernel(tmp_path)
        _patch(k)
        assert k.query_trajectory("missing-id") is None
        assert k.list_trajectories()

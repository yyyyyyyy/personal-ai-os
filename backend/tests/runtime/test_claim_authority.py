"""Meaning Boundary G1 — claim authority state machine and Agency gate."""

import os

os.environ.setdefault("LLM_API_KEY", "test-key")

import pytest

from app.core.agents.memory_engine import memory_engine
from app.core.runtime import claim_authority
from app.core.runtime.kernel import Kernel
from app.core.runtime.kernel.projectors import initial_claim_status
from app.product.claim_suggestions import notify_ratified_claim_insights
from app.store.database import Database


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
    return Kernel(db=Database(db_path=str(tmp_path / "claim_auth.db")))


def _patch_runtime(k):
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = k
    db_mod.db = k._db
    return k._db


class TestClaimStatusProjection:
    def test_initial_claim_status_mapping(self):
        assert initial_claim_status("claim") == "proposed"
        assert initial_claim_status("self_report") is None

    def test_belief_formed_starts_proposed(self, tmp_path):
        k = _kernel(tmp_path)
        k.emit_event(
            "BeliefFormed", "memory", "blf-1",
            {"category": "belief", "content": "推断", "confidence": 0.6},
            actor="kernel",
        )
        row = k.query_state("memories", id="blf-1")[0]
        assert row["origin"] == "claim"
        assert row["claim_status"] == "proposed"

    def test_self_report_has_null_claim_status(self, tmp_path):
        k = _kernel(tmp_path)
        k.emit_event(
            "MemoryDerived", "memory", "m-user",
            {"category": "fact", "content": "自述", "confidence": 0.9},
            actor="user",
        )
        row = k.query_state("memories", id="m-user")[0]
        assert row["origin"] == "self_report"
        assert row.get("claim_status") is None

    def test_ratify_reject_transitions(self, tmp_path):
        k = _kernel(tmp_path)
        _patch_runtime(k)
        k.emit_event(
            "BeliefFormed", "memory", "blf-2",
            {"category": "belief", "content": "测试", "confidence": 0.5},
            actor="kernel",
        )
        claim_authority.ratify("blf-2")
        assert k.query_state("memories", id="blf-2")[0]["claim_status"] == "ratified"
        claim_authority.reject("blf-2")
        assert k.query_state("memories", id="blf-2")[0]["claim_status"] == "rejected"

    def test_self_report_cannot_ratify(self, tmp_path):
        k = _kernel(tmp_path)
        _patch_runtime(k)
        k.emit_event(
            "MemoryDerived", "memory", "m-self",
            {"category": "fact", "content": "自述", "confidence": 0.9},
            actor="user",
        )
        with pytest.raises(ValueError, match="not a system claim"):
            claim_authority.ratify("m-self")

    def test_claim_status_survives_rebuild(self, tmp_path):
        k = _kernel(tmp_path)
        _patch_runtime(k)
        k.emit_event(
            "BeliefFormed", "memory", "blf-3",
            {"category": "belief", "content": "持久", "confidence": 0.7},
            actor="kernel",
        )
        claim_authority.ratify("blf-3")
        before = k.query_state("memories", id="blf-3")[0]["claim_status"]
        k.rebuild("memory")
        after = k.query_state("memories", id="blf-3")[0]["claim_status"]
        assert before == after == "ratified"


class TestAuthorityMapping:
    def test_can_present_and_drive_agency(self):
        proposed = {"origin": "claim", "claim_status": "proposed", "confidence": 0.5}
        contested = {"origin": "claim", "claim_status": "contested", "confidence": 0.5}
        ratified = {"origin": "claim", "claim_status": "ratified", "confidence": 0.8}
        rejected = {"origin": "claim", "claim_status": "rejected", "confidence": 0.8}
        released = {"origin": "claim", "claim_status": "released", "confidence": 0.8}
        self_report = {"origin": "self_report", "claim_status": None, "confidence": 0.9}

        assert claim_authority.can_present(proposed)
        assert claim_authority.can_present(contested)
        assert claim_authority.can_present(ratified)
        assert not claim_authority.can_present(rejected)
        assert not claim_authority.can_present(released)
        assert claim_authority.can_present(self_report)

        assert not claim_authority.can_drive_agency(proposed)
        assert not claim_authority.can_drive_agency(contested)
        assert claim_authority.can_drive_agency(ratified)
        assert not claim_authority.can_drive_agency(rejected)
        assert not claim_authority.can_drive_agency(self_report)


class TestAgencyNotifyPath:
    def test_only_ratified_claims_notify(self, tmp_path):
        k = _kernel(tmp_path)
        db = _patch_runtime(k)
        k.emit_event(
            "BeliefFormed", "memory", "blf-n1",
            {"category": "belief", "content": "未署名", "confidence": 0.6},
            actor="kernel",
        )
        assert notify_ratified_claim_insights() == 0

        claim_authority.ratify("blf-n1")
        assert notify_ratified_claim_insights() == 1

        with db.get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS c FROM notifications WHERE type = 'claim_insight'"
            ).fetchone()["c"]
        assert count == 1

        claim_authority.reject("blf-n1")
        assert notify_ratified_claim_insights() == 0


class TestPresentationG1:
    def test_rejected_claim_excluded_from_context(self):
        rendered = memory_engine.format_memory_context([
            {
                "id": "c1",
                "content": "被拒绝的推断",
                "confidence": 0.5,
                "origin": "claim",
                "claim_status": "rejected",
            },
            {
                "id": "c2",
                "content": "待确认推断",
                "confidence": 0.6,
                "origin": "claim",
                "claim_status": "proposed",
            },
        ])
        assert "被拒绝的推断" not in rendered
        assert "待确认推断" in rendered
        assert "[待你确认]" in rendered

    def test_ratified_claim_shows_signed_label(self):
        rendered = memory_engine.format_memory_context([
            {
                "id": "c3",
                "content": "已署名推断",
                "confidence": 0.8,
                "origin": "claim",
                "claim_status": "ratified",
            },
        ])
        assert "[已署名]" in rendered
        assert "已署名推断" in rendered

"""Identity RFC I-F1–F3 fixture lint (Trajectory §1.7 trace)."""

import os

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.review_engine import ReviewEngine
from app.core.runtime.kernel import Kernel
from app.core.runtime.projection.identity_lint import (
    lint_identity_hard_failures,
    lint_review_content,
)
from app.core.runtime.trajectory.engine import link_event, list_trajectories
from app.store.database import Database

_COMPETING_TRAJECTORIES = [
    {
        "id": "career-entrepreneurship-2026",
        "description": "entrepreneurship impulse",
        "competing_with": ["career-corporate-stability-2026"],
        "status": "active",
    },
    {
        "id": "career-corporate-stability-2026",
        "description": "corporate stability",
        "competing_with": ["career-entrepreneurship-2026"],
        "status": "active",
    },
]


class TestIdentityFixtureLint:
    def test_i_f1_single_outcome_evidence_fails(self):
        meta = {
            "outcome_event_seqs": [500],
            "identity_claims": [
                {"text": "你是冒险型", "evidence_event_seqs": [500], "evidence_types": ["outcome"]},
            ],
        }
        fails = lint_identity_hard_failures("", narrative_meta=meta)
        assert any("I-F1" in f for f in fails)

    def test_i_f1_multi_evidence_passes(self):
        meta = {
            "outcome_event_seqs": [500],
            "identity_claims": [
                {"text": "倾向探索", "evidence_event_seqs": [100, 500]},
            ],
        }
        fails = lint_identity_hard_failures("", narrative_meta=meta)
        assert not any("I-F1" in f for f in fails)

    def test_i_f2_one_competitor_missing_fails(self):
        content = "career-entrepreneurship-2026: entrepreneurship impulse"
        fails = lint_identity_hard_failures(
            content, trajectories=_COMPETING_TRAJECTORIES
        )
        assert any("I-F2" in f for f in fails)

    def test_i_f2_both_competitors_visible_passes(self):
        content = (
            "## 轨迹视角\n"
            "- career-entrepreneurship-2026: entrepreneurship （竞争轨迹: career-corporate-stability-2026）\n"
            "- career-corporate-stability-2026: corporate stability\n"
        )
        fails = lint_identity_hard_failures(
            content, trajectories=_COMPETING_TRAJECTORIES
        )
        assert not any("I-F2" in f for f in fails)

    def test_i_f3_proposed_belief_destiny_fails(self):
        meta = {
            "cited_beliefs": [
                {
                    "memory_id": "blf-1",
                    "claim_status": "proposed",
                    "excerpt": "你是天生的创业者",
                },
            ],
        }
        fails = lint_identity_hard_failures("x", narrative_meta=meta)
        assert any("I-F3" in f for f in fails)

    def test_i_f3_ratified_belief_not_checked_by_i_f3(self):
        meta = {
            "cited_beliefs": [
                {
                    "memory_id": "blf-2",
                    "claim_status": "ratified",
                    "excerpt": "你是天生的创业者",
                },
            ],
        }
        fails = lint_identity_hard_failures("x", narrative_meta=meta)
        assert not any("I-F3" in f for f in fails)


@pytest.fixture(autouse=True)
def _restore():
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    saved_k, saved_d = ki.kernel, db_mod.db
    yield
    ki.kernel, db_mod.db = saved_k, saved_d


def test_trajectory_rfc_trace_review_passes_i_f(tmp_path):
    """Trajectory RFC §1.7 — generated review passes I-F* on fixture db."""
    k = Kernel(db=Database(db_path=str(tmp_path / "id_trace.db")))
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = k
    db_mod.db = k._db

    src = k.emit_event(
        "MemoryDerived",
        "memory",
        "trace-mem",
        payload={"content": "我想辞职创业"},
        actor="user",
    )
    link_event(k, "career-entrepreneurship-2026", src.seq, actor="system")
    link_event(k, "career-corporate-stability-2026", src.seq, actor="system")

    engine = ReviewEngine()
    rid = engine.generate_daily_review(date="2099-03-01")
    review = engine.get_review(rid)
    assert review

    trajectories = list_trajectories(k)
    parsed = review["key_insights_parsed"]
    meta = parsed.get("narrative_audit") or {}

    fails = [
        i
        for i in lint_review_content(
            review["content"],
            trajectories=trajectories,
            narrative_meta=meta,
        )
        if i.startswith("FAIL:")
    ]
    assert fails == []

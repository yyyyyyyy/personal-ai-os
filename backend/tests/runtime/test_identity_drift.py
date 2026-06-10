"""Identity drift — Meaning Boundary scale verification (pytest mirror)."""

import os

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.agents.memory_engine import memory_engine
from app.core.runtime import claim_authority
from app.core.runtime.kernel import Kernel
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


def _setup(tmp_path):
    db = Database(db_path=str(tmp_path / "drift.db"))
    k = Kernel(db=db)
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = k
    db_mod.db = db
    return k, db


def _emit_claim(k, cid: str, content: str) -> None:
    k.emit_event(
        "BeliefFormed", "memory", cid,
        {"category": "belief", "content": content, "confidence": 0.6, "source": "reflection"},
        actor="kernel",
    )


class TestIdentityDriftPresentation:
    def test_proposed_never_shows_ratified_tag(self):
        rendered = memory_engine.format_memory_context([{
            "id": "x1",
            "content": "测试推断",
            "confidence": 0.5,
            "origin": "claim",
            "claim_status": "proposed",
        }])
        assert "[待你确认]" in rendered
        assert "[已署名]" not in rendered

    def test_released_excluded_from_context(self):
        rendered = memory_engine.format_memory_context([{
            "id": "x2",
            "content": "已释放推断",
            "confidence": 0.7,
            "origin": "claim",
            "claim_status": "released",
        }])
        assert "已释放推断" not in rendered


class TestIdentityDriftAgency:
    def test_many_proposed_zero_notifications(self, tmp_path):
        k, db = _setup(tmp_path)
        for i in range(20):
            _emit_claim(k, f"p-{i}", f"proposed {i}")

        with db.get_db() as conn:
            before = conn.execute(
                "SELECT COUNT(*) AS c FROM notifications WHERE type='claim_insight'"
            ).fetchone()["c"]

        notify_ratified_claim_insights()

        with db.get_db() as conn:
            after = conn.execute(
                "SELECT COUNT(*) AS c FROM notifications WHERE type='claim_insight'"
            ).fetchone()["c"]
        assert after == before

    def test_only_ratified_notified(self, tmp_path):
        k, db = _setup(tmp_path)
        _emit_claim(k, "r-1", "ratified one")
        _emit_claim(k, "r-2", "ratified two")
        _emit_claim(k, "p-1", "proposed one")

        claim_authority.ratify("r-1")
        claim_authority.ratify("r-2")

        created = 0
        for _ in range(2):
            created += notify_ratified_claim_insights()
        assert created == 2

        with db.get_db() as conn:
            rows = conn.execute(
                "SELECT content FROM notifications WHERE type='claim_insight'"
            ).fetchall()
        contents = " ".join(r["content"] for r in rows)
        assert "memory_id:r-1" in contents
        assert "memory_id:r-2" in contents
        assert "memory_id:p-1" not in contents

    def test_release_stops_agency(self, tmp_path):
        k, db = _setup(tmp_path)
        _emit_claim(k, "rel-1", "release me")
        claim_authority.ratify("rel-1")
        assert notify_ratified_claim_insights() == 1

        claim_authority.release("rel-1")
        assert notify_ratified_claim_insights() == 0

        events = k.read_events(aggregate_id="rel-1")
        types = {e.type for e in events}
        assert "ClaimRatified" in types
        assert "ClaimReleased" in types

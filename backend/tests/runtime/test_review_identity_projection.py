"""Identity RFC N5 — review projection metadata."""

import json
import os

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.review_engine import REVIEW_PROJECTION_META, ReviewEngine
from app.core.runtime.kernel import Kernel
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


def _patch(k):
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = k
    db_mod.db = k._db


class TestReviewIdentityProjection:
    def test_daily_review_has_projection_meta(self, tmp_path):
        k = Kernel(db=Database(db_path=str(tmp_path / "rev.db")))
        _patch(k)
        engine = ReviewEngine()
        rid = engine.generate_daily_review(date="2099-06-01")
        review = engine.get_review(rid)
        assert review is not None
        parsed = review["key_insights_parsed"]
        assert parsed.get("projection") is True
        assert parsed.get("not_ratified") is True
        assert parsed.get("surface") == "daily_review"
        assert "轨迹视角" in review["content"]
        assert "系统投影" in review["content"]
        audit = parsed.get("narrative_audit") or {}
        assert "cited_trajectory_ids" in audit
        assert "identity_claims" in audit
        assert "cited_beliefs" in audit

    def test_parse_key_insights_legacy_list(self):
        parsed = ReviewEngine.parse_key_insights(json.dumps(["a", "b"]))
        assert parsed.get("legacy") is True
        assert parsed["insights"] == ["a", "b"]

    def test_projection_meta_constants(self):
        assert REVIEW_PROJECTION_META["interpretive_plurality"] is True

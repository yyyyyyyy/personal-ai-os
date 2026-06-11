"""Trajectory Identity opt-in — Identity RFC P4."""

import os

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.runtime.kernel import Kernel
from app.core.runtime.trajectory.engine import list_trajectories
from app.core.runtime.trajectory.identity_authority import (
    is_identity_opted_in,
    list_identity_opted_in,
    opt_in,
    opt_out,
)
from app.store.database import Database


@pytest.fixture(autouse=True)
def _restore():
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    saved_k, saved_d = ki.kernel, db_mod.db
    yield
    ki.kernel, db_mod.db = saved_k, saved_d


def test_identity_opt_in_default_false(tmp_path):
    k = Kernel(db=Database(db_path=str(tmp_path / "tid.db")))
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = k
    db_mod.db = k._db

    assert is_identity_opted_in("career-entrepreneurship-2026") is False


def test_identity_opt_in_toggle(tmp_path):
    k = Kernel(db=Database(db_path=str(tmp_path / "tid2.db")))
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = k
    db_mod.db = k._db

    tid = "career-entrepreneurship-2026"
    opt_in(tid)
    assert is_identity_opted_in(tid) is True
    assert tid in list_identity_opted_in()

    opt_out(tid)
    assert is_identity_opted_in(tid) is False

    listed = list_trajectories(k)
    ent = next(t for t in listed if t["id"] == tid)
    assert ent["identity_narrative_opt_in"] is False

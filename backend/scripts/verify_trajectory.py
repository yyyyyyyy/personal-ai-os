#!/usr/bin/env python
"""Trajectory Integrity verification — registry symmetry + link fixture.

See docs/rfc/TRAJECTORY_RFC.md §1.6 (V1–V5).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.runtime.kernel import Kernel
from app.core.runtime.trajectory.engine import (
    link_event,
    load_merged_registry,
    query_trajectory,
    verify_competing_symmetry,
)
from app.core.runtime.trajectory.registry import load_yaml_registry
from app.store.database import Database


def main() -> int:
    violations: list[str] = []

    registry_path = _BACKEND_ROOT / "trajectory_registry.yaml"
    yaml_reg = load_yaml_registry(registry_path)
    violations.extend(verify_competing_symmetry(yaml_reg))

    db_path = _BACKEND_ROOT / "data" / "verify_trajectory.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(db_path=str(db_path))
    k = Kernel(db=db)

    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = k
    db_mod.db = db

    reg = load_merged_registry(k)
    violations.extend(verify_competing_symmetry(reg))

    # Fixture: entrepreneurship trace (TRAJECTORY_RFC §1.7)
    src = k.emit_event(
        "MemoryDerived", "memory", "verify-mem",
        payload={"content": "我想辞职创业，但还没决定"},
        actor="user",
    )
    assert src.seq is not None
    link_event(k, "career-entrepreneurship-2026", src.seq, actor="system")
    link_event(k, "career-corporate-stability-2026", src.seq, actor="system")

    conv = k.emit_event(
        "ConversationRecorded",
        "conversation",
        "verify-conv",
        payload={"user_message": "还在纠结创业", "assistant_message": "可以列 pros/cons"},
        actor="user",
        correlation_id="conv-turn-verify-1",
    )
    assert conv.seq is not None
    link_event(k, "career-entrepreneurship-2026", conv.seq, actor="system")

    ent = query_trajectory(k, "career-entrepreneurship-2026")
    corp = query_trajectory(k, "career-corporate-stability-2026")
    if not ent or not corp:
        violations.append("fixture: expected registry trajectories missing")
    else:
        if len(ent["links"]) < 2 or len(corp["links"]) < 1:
            violations.append("fixture: expected links on competing trajectories")
        conv_seqs = {e["seq"] for e in ent.get("events", [])}
        if conv.seq not in conv_seqs:
            violations.append("fixture: ConversationRecorded not in trajectory events")
        if not ent.get("competing_with") or "career-corporate-stability-2026" not in ent["competing_with"]:
            violations.append("fixture: entrepreneurship trajectory missing competing_with")

    # V2: invalid event_seq reference
    bad = k.emit_event(
        "TrajectoryLinked", "trajectory", "career-entrepreneurship-2026",
        payload={"link_id": "bad_link", "event_seq": 999999, "claim_status": "proposed"},
        actor="system",
    )
    _ = bad
    with k._db.get_db() as conn:
        row = conn.execute("SELECT 1 FROM event_log WHERE seq = ?", (999999,)).fetchone()
    if row:
        violations.append("V2.setup: unexpected seq 999999 exists")
    else:
        data = query_trajectory(k, "career-entrepreneurship-2026")
        if data is None:
            violations.append("V2: trajectory query returned None")
        else:
            bad_links = [lnk for lnk in data["links"] if lnk.get("link_id") == "bad_link"]
            if bad_links and data["events"]:
                seqs = {e["seq"] for e in data["events"]}
                if 999999 in seqs:
                    violations.append("V2: query included missing event_seq 999999")

    if violations:
        print("TRAJECTORY VERIFICATION FAILED", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print("TRAJECTORY VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

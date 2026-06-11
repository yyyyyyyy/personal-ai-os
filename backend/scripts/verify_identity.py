#!/usr/bin/env python
"""Identity integrity verification — surfaces registry + N1–N4 + I-F1–F3 lint.

See docs/rfc/IDENTITY_RFC.md §1–§3.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.review_engine import ReviewEngine
from app.core.runtime.kernel import Kernel
from app.core.runtime.projection.identity_lint import (
    lint_identity_hard_failures,
    lint_review_content,
)
from app.core.runtime.projection.surfaces import (
    identity_surface_ids,
    load_agency_surfaces,
    load_identity_surfaces,
)
from app.core.runtime.trajectory.engine import link_event, list_trajectories
from app.store.database import Database

_COMPETING_FIXTURE_TRAJECTORIES = [
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


def _patch_runtime(db: Database, kernel: Kernel) -> None:
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = kernel
    db_mod.db = db


def _check_surfaces_registry(violations: list[str]) -> None:
    identity = load_identity_surfaces()
    agency = load_agency_surfaces()
    if not identity:
        violations.append("identity_surfaces.yaml has no surfaces")
    if not agency:
        violations.append("agency_surfaces.yaml has no surfaces")
    ids = identity_surface_ids()
    for required in ("daily_review", "weekly_review", "monthly_review"):
        if required not in ids:
            violations.append(f"missing identity surface id {required!r}")
    for s in agency:
        if not s.get("rank_inputs_forbidden"):
            violations.append(f"agency surface {s.get('id')} missing rank_inputs_forbidden")


def _check_i_f_fixture_lint(violations: list[str]) -> None:
    """Synthetic I-F1–F3 fixtures must fail/succeed as specified."""
    i_f1 = lint_identity_hard_failures(
        "",
        narrative_meta={
            "outcome_event_seqs": [500],
            "identity_claims": [
                {"text": "x", "evidence_event_seqs": [500], "evidence_types": ["outcome"]},
            ],
        },
    )
    if not any("I-F1" in v for v in i_f1):
        violations.append("I-F1 fixture: expected outcome monoculture failure")

    i_f2_bad = lint_identity_hard_failures(
        "only career-entrepreneurship-2026 here",
        trajectories=_COMPETING_FIXTURE_TRAJECTORIES,
    )
    if not any("I-F2" in v for v in i_f2_bad):
        violations.append("I-F2 fixture: expected competing visibility failure")

    i_f2_good = lint_identity_hard_failures(
        "career-entrepreneurship-2026 and career-corporate-stability-2026 both visible",
        trajectories=_COMPETING_FIXTURE_TRAJECTORIES,
    )
    if any("I-F2" in v for v in i_f2_good):
        violations.append("I-F2 fixture: both competitors should pass")

    i_f3 = lint_identity_hard_failures(
        "n/a",
        narrative_meta={
            "cited_beliefs": [
                {
                    "memory_id": "b1",
                    "claim_status": "proposed",
                    "excerpt": "你是天生的创业者",
                },
            ],
        },
    )
    if not any("I-F3" in v for v in i_f3):
        violations.append("I-F3 fixture: expected proposed belief destiny failure")


def _check_review_narrative(
    engine: ReviewEngine, kernel: Kernel, db: Database, violations: list[str]
) -> None:
    fixture_date = "2099-02-01"
    with db.get_db() as conn:
        conn.execute(
            "DELETE FROM reviews WHERE type = 'daily' AND period_start = ?",
            (fixture_date,),
        )

    src = kernel.emit_event(
        "MemoryDerived",
        "memory",
        "verify-id-mem",
        payload={"content": "创业冲动与稳健留任并存"},
        actor="user",
    )
    assert src.seq is not None
    link_event(kernel, "career-entrepreneurship-2026", src.seq, actor="system")
    link_event(kernel, "career-corporate-stability-2026", src.seq, actor="system")

    rid = engine.generate_daily_review(date=fixture_date)
    review = engine.get_review(rid)
    if not review:
        violations.append("failed to generate review fixture")
        return

    parsed = review.get("key_insights_parsed") or {}
    if not parsed.get("projection"):
        violations.append("N5: missing projection meta")
    if not parsed.get("narrative_audit"):
        violations.append("N5: missing narrative_audit in key_insights")

    trajectories = list_trajectories(kernel)
    meta = parsed.get("narrative_audit") or {}
    issues = lint_review_content(
        review.get("content") or "",
        trajectories=trajectories,
        narrative_meta=meta,
    )
    for issue in issues:
        if issue.startswith("FAIL:"):
            violations.append(issue)
        elif issue.startswith("WARN:"):
            print(f"  note: {issue}", file=sys.stderr)


def main() -> int:
    violations: list[str] = []
    _check_surfaces_registry(violations)
    _check_i_f_fixture_lint(violations)

    db_path = _BACKEND_ROOT / "data" / "verify_identity.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(db_path=str(db_path))
    k = Kernel(db=db)
    _patch_runtime(db, k)

    _check_review_narrative(ReviewEngine(), k, db, violations)

    if violations:
        print("IDENTITY VERIFICATION FAILED", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print("IDENTITY VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

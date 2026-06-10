#!/usr/bin/env python
"""Meaning Boundary G1 verification — claim authority and Agency gate.

Validates HUMAN_RUNTIME_CONSTITUTION.md G1:
  - Proposed claims cannot drive Agency (notifications).
  - Ratified claims can drive Agency.
  - Rejected claims stop driving Agency.
  - claim_status survives memory rebuild.
"""

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.runtime import claim_authority
from app.core.runtime.kernel import Kernel
from app.product.claim_suggestions import notify_ratified_claim_insights
from app.store.database import Database


def _count_claim_insights(db: Database) -> int:
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM notifications WHERE type = 'claim_insight'"
        ).fetchone()
    return int(row["c"]) if row else 0


def _patch_runtime(db: Database, kernel: Kernel) -> None:
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = kernel
    db_mod.db = db


def main() -> int:
    db_path = _BACKEND_ROOT / "data" / "verify_claim_authority.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(db_path=str(db_path))
    k = Kernel(db=db)
    _patch_runtime(db, k)

    violations: list[str] = []
    claim_id = "blf-verify-g1"

    k.emit_event(
        "BeliefFormed",
        "memory",
        claim_id,
        payload={
            "category": "belief",
            "content": "你倾向在困难时放弃项目",
            "confidence": 0.73,
            "source": "reflection",
        },
        actor="kernel",
    )

    row = k.query_state("memories", id=claim_id)[0]
    if row.get("claim_status") != "proposed":
        violations.append(
            f"G1.setup: expected claim_status=proposed, got {row.get('claim_status')!r}"
        )

    # G1.a — proposed must not drive Agency
    before_proposed = _count_claim_insights(db)
    notify_ratified_claim_insights()
    after_proposed = _count_claim_insights(db)
    if after_proposed != before_proposed:
        violations.append(
            f"G1.a: proposed claim created notification "
            f"({before_proposed} -> {after_proposed})"
        )

    claim_authority.ratify(claim_id)
    if k.query_state("memories", id=claim_id)[0].get("claim_status") != "ratified":
        violations.append("G1.setup: ratify did not set claim_status=ratified")

    # G1.b — ratified must drive Agency
    before_ratified = _count_claim_insights(db)
    created = notify_ratified_claim_insights()
    after_ratified = _count_claim_insights(db)
    if created < 1 or after_ratified <= before_ratified:
        violations.append(
            f"G1.b: ratified claim did not create notification "
            f"(created={created}, count {before_ratified}->{after_ratified})"
        )

    # G1.c — rejected must not drive further Agency
    claim_authority.reject(claim_id)
    before_reject = _count_claim_insights(db)
    notify_ratified_claim_insights()
    after_reject = _count_claim_insights(db)
    if after_reject != before_reject:
        violations.append(
            f"G1.c: rejected claim still created notification "
            f"({before_reject} -> {after_reject})"
        )

    # G1.d — rebuild preserves claim_status
    status_before_rebuild = k.query_state("memories", id=claim_id)[0].get("claim_status")
    k.rebuild("memory")
    status_after_rebuild = k.query_state("memories", id=claim_id)[0].get("claim_status")
    if status_before_rebuild != status_after_rebuild:
        violations.append(
            f"G1.d: claim_status changed after rebuild "
            f"({status_before_rebuild!r} -> {status_after_rebuild!r})"
        )

    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass

    if violations:
        print("CLAIM AUTHORITY G1 VERIFICATION FAILED", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print("CLAIM AUTHORITY G1 VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

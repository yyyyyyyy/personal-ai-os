#!/usr/bin/env python
"""Identity Drift verification — Meaning Boundary at scale.

Proves G1/G2 jointly prevent ungoverned claims from influencing Agency or
presentation as ratified identity facts.

Experiments:
  A'  Many proposed claims → zero Agency leak; presentation never shows [已署名].
  B'  Mixed ratified/proposed → notifications only reference ratified claim ids.
  C'  Ratify → Release → influence gone; events preserved; rebuild consistent.
"""

import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.agents.memory_engine import memory_engine
from app.core.runtime import claim_authority
from app.core.runtime.kernel import Kernel
from app.product.claim_suggestions import notify_ratified_claim_insights
from app.store.database import Database

PROPOSED_BATCH = 100
RATIFY_COUNT = 10
TOTAL_MIXED = 20


def _patch_runtime(db: Database, kernel: Kernel) -> None:
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = kernel
    db_mod.db = db


def _count_claim_insights(db: Database) -> int:
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM notifications WHERE type = 'claim_insight'"
        ).fetchone()
    return int(row["c"]) if row else 0


def _notification_memory_ids(db: Database) -> list[str]:
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT content FROM notifications WHERE type = 'claim_insight'"
        ).fetchall()
    ids: list[str] = []
    for row in rows:
        for line in (row["content"] or "").splitlines():
            if line.startswith("memory_id:"):
                ids.append(line.split(":", 1)[1].strip())
    return ids


def _emit_proposed_claim(kernel: Kernel, claim_id: str, content: str) -> None:
    kernel.emit_event(
        "BeliefFormed",
        "memory",
        claim_id,
        payload={
            "category": "belief",
            "content": content,
            "confidence": 0.6,
            "source": "reflection",
        },
        actor="kernel",
    )


def experiment_a(kernel: Kernel, db: Database, violations: list[str]) -> list[str]:
    """A': N proposed claims must not drive Agency or show as ratified in context."""
    proposed_ids: list[str] = []
    for i in range(PROPOSED_BATCH):
        cid = f"blf-drift-a-{i:03d}"
        _emit_proposed_claim(kernel, cid, f"未署名推断 #{i}")
        proposed_ids.append(cid)

    rows = kernel.query_state("memories", origin="claim", limit=PROPOSED_BATCH + 10)
    proposed_rows = [r for r in rows if r.get("claim_status") == "proposed"]
    if len(proposed_rows) < PROPOSED_BATCH:
        violations.append(
            f"A'.setup: expected >={PROPOSED_BATCH} proposed claims, got {len(proposed_rows)}"
        )

    before = _count_claim_insights(db)
    notify_ratified_claim_insights()
    after = _count_claim_insights(db)
    if after != before:
        violations.append(
            f"A'.agency: {PROPOSED_BATCH} proposed claims leaked notification "
            f"({before} -> {after})"
        )

    sample = [
        {
            "id": proposed_ids[0],
            "content": "未署名推断 #0",
            "confidence": 0.6,
            "origin": "claim",
            "claim_status": "proposed",
        },
        {
            "id": proposed_ids[50],
            "content": "未署名推断 #50",
            "confidence": 0.6,
            "origin": "claim",
            "claim_status": "proposed",
        },
    ]
    rendered = memory_engine.format_memory_context(sample)
    if "[已署名]" in rendered:
        violations.append("A'.presentation: proposed claims rendered with [已署名] tag")
    if "[待你确认]" not in rendered:
        violations.append("A'.presentation: proposed claims missing [待你确认] tag")

    return proposed_ids


def experiment_b(
    kernel: Kernel, db: Database, violations: list[str], proposed_ids: list[str],
) -> None:
    """B': Only ratified subset may appear in claim_insight notifications."""
    mixed_ids: list[str] = []
    for i in range(TOTAL_MIXED):
        cid = f"blf-drift-b-{i:02d}"
        _emit_proposed_claim(kernel, cid, f"混合推断 #{i}")
        mixed_ids.append(cid)

    ratified_ids = mixed_ids[:RATIFY_COUNT]
    for cid in ratified_ids:
        claim_authority.ratify(cid)

    total_created = 0
    for _ in range(3):
        total_created += notify_ratified_claim_insights()

    if total_created != RATIFY_COUNT:
        violations.append(
            f"B'.agency: expected {RATIFY_COUNT} notifications, created {total_created}"
        )

    notified_ids = set(_notification_memory_ids(db))
    ratified_set = set(ratified_ids)
    proposed_set = set(mixed_ids[RATIFY_COUNT:])

    if not ratified_set.issubset(notified_ids):
        missing = ratified_set - notified_ids
        violations.append(f"B'.agency: ratified claims missing from notifications: {missing}")

    leaked = notified_ids & proposed_set
    if leaked:
        violations.append(f"B'.agency: proposed claims in notifications: {leaked}")

    extra_from_a = notified_ids & set(proposed_ids)
    if extra_from_a:
        violations.append(f"B'.agency: experiment A proposed ids leaked: {extra_from_a}")


def experiment_c(kernel: Kernel, db: Database, violations: list[str]) -> None:
    """C': Ratify → notify → release; influence ends; events survive rebuild."""
    claim_id = "blf-drift-c"
    _emit_proposed_claim(kernel, claim_id, "可释放的推断")

    claim_authority.ratify(claim_id)
    created = notify_ratified_claim_insights()
    if created < 1:
        violations.append("C'.setup: ratified claim did not create notification")

    claim_authority.release(claim_id)
    row = kernel.query_state("memories", id=claim_id)[0]
    if row.get("claim_status") != "released":
        violations.append(
            f"C'.release: expected claim_status=released, got {row.get('claim_status')!r}"
        )

    before_release_notify = _count_claim_insights(db)
    notify_ratified_claim_insights()
    after_release_notify = _count_claim_insights(db)
    if after_release_notify != before_release_notify:
        violations.append(
            f"C'.agency: released claim still created notification "
            f"({before_release_notify} -> {after_release_notify})"
        )

    rendered = memory_engine.format_memory_context([{
        "id": claim_id,
        "content": row["content"],
        "confidence": float(row.get("confidence") or 0.6),
        "origin": "claim",
        "claim_status": "released",
    }])
    if "可释放的推断" in rendered:
        violations.append("C'.presentation: released claim still in memory context")

    events_before = kernel.read_events(aggregate_id=claim_id, types=[
        "BeliefFormed", "ClaimRatified", "ClaimReleased",
    ])
    types_before = {e.type for e in events_before}
    if "ClaimRatified" not in types_before or "ClaimReleased" not in types_before:
        violations.append(f"C'.events: missing ratify/release events, got {types_before}")

    status_before_rebuild = row.get("claim_status")
    kernel.rebuild("memory")
    row_after = kernel.query_state("memories", id=claim_id)[0]
    if row_after.get("claim_status") != status_before_rebuild:
        violations.append(
            f"C'.rebuild: claim_status changed "
            f"({status_before_rebuild!r} -> {row_after.get('claim_status')!r})"
        )

    events_after = kernel.read_events(aggregate_id=claim_id, types=[
        "BeliefFormed", "ClaimRatified", "ClaimReleased",
    ])
    if len(events_after) < len(events_before):
        violations.append("C'.rebuild: event log lost claim lifecycle events")


def main() -> int:
    db_path = _BACKEND_ROOT / "data" / "verify_identity_drift.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(db_path=str(db_path))
    k = Kernel(db=db)
    _patch_runtime(db, k)

    violations: list[str] = []

    proposed_ids = experiment_a(k, db, violations)
    experiment_b(k, db, violations, proposed_ids)
    experiment_c(k, db, violations)

    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass

    if violations:
        print("IDENTITY DRIFT VERIFICATION FAILED", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print("IDENTITY DRIFT VERIFICATION PASSED")
    print(f"  A': {PROPOSED_BATCH} proposed → zero Agency leak, presentation OK")
    print(f"  B': {RATIFY_COUNT}/{TOTAL_MIXED} ratified → notifications attributed correctly")
    print("  C': ratify → release → influence gone, events + rebuild OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

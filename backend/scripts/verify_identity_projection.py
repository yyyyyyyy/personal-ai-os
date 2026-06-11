#!/usr/bin/env python
"""Identity Projection verification — Identity RFC N5 on review surfaces.

Validates that generated reviews carry projection metadata and preamble,
not presentable as ratified identity.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.review_engine import REVIEW_PROJECTION_META, ReviewEngine
from app.core.runtime.kernel import Kernel
from app.store.database import Database


def _patch_runtime(db: Database, kernel: Kernel) -> None:
    import app.core.runtime.kernel_instance as ki
    import app.store.database as db_mod

    ki.kernel = kernel
    db_mod.db = db


def _validate_review_meta(review: dict, violations: list[str], label: str) -> None:
    parsed = ReviewEngine.parse_key_insights(review.get("key_insights"))
    if not parsed.get("projection"):
        violations.append(f"{label}: key_insights missing projection=true")
    if parsed.get("not_ratified") is not True:
        violations.append(f"{label}: key_insights must set not_ratified=true")
    if not parsed.get("surface"):
        violations.append(f"{label}: key_insights missing surface")
    content = review.get("content") or ""
    if "Identity Projection" not in content and "系统投影" not in content:
        violations.append(f"{label}: content missing projection preamble")
    if "轨迹视角" not in content:
        violations.append(f"{label}: content missing trajectory plurality section")


def main() -> int:
    violations: list[str] = []

    db_path = _BACKEND_ROOT / "data" / "verify_identity_projection.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(db_path=str(db_path))
    k = Kernel(db=db)
    _patch_runtime(db, k)

    engine = ReviewEngine()
    rid = engine.generate_daily_review(date="2099-01-01")
    review = engine.get_review(rid)
    if not review:
        violations.append("failed to generate daily review fixture")
    else:
        _validate_review_meta(review, violations, "daily")

    # Static meta contract
    for key in ("projection", "projection_type", "interpretive_plurality", "not_ratified"):
        if key not in REVIEW_PROJECTION_META:
            violations.append(f"REVIEW_PROJECTION_META missing {key!r}")

    sample = json.dumps({"projection": True, "not_ratified": True, "insights": []})
    legacy = ReviewEngine.parse_key_insights('["legacy insight"]')
    if legacy.get("legacy") is not True:
        violations.append("parse_key_insights should detect legacy list format")

    if violations:
        print("IDENTITY PROJECTION VERIFICATION FAILED", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print("IDENTITY PROJECTION VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

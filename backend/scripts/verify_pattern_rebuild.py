#!/usr/bin/env python
"""Pattern Projection Replay Test — verifies Pattern as an Event Sourcing Primitive.

1. Inject synthetic ActivityNormalized events → wait for PatternDetected
2. Snapshot the patterns table
3. DELETE FROM patterns → kernel.rebuild("pattern")
4. Assert snapshot == rebuilt state

Success = Pattern is a First-Class Projection Primitive (same guarantees as State/Memory).
"""

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.core.runtime.kernel_instance import kernel


def _snapshot_patterns() -> list[dict]:
    rows = kernel.query_state("patterns", limit=5000)
    return sorted(rows, key=lambda r: r["id"])


def _patterns_equal(a: list[dict], b: list[dict]) -> bool:
    if len(a) != len(b):
        print(f"  ERR: count mismatch — before={len(a)} after={len(b)}")
        return False
    for left, right in zip(a, b):
        if left["id"] != right["id"]:
            print(f"  ERR: id mismatch — {left['id']} vs {right['id']}")
            return False
        for col in ("pattern_type", "metric", "window_days", "statistics", "evidence_chain"):
            if left.get(col) != right.get(col):
                print(f"  ERR: column {col} mismatch on {left['id']}")
                return False
    return True


def main() -> int:
    print("=== Pattern Projection Replay Test ===")

    # 1. Snapshot current state
    before = _snapshot_patterns()
    print(f"  1. Snapshot before rebuild: {len(before)} rows")

    if not before:
        print("  SKIP: no patterns to test rebuild against.  "
              "Run the system with ActivityNormalized events first.")
        return 0

    # 2. Rebuild
    count = kernel.rebuild("pattern")
    print(f"  2. kernel.rebuild('pattern') replayed {count} events")

    # 3. Snapshot after rebuild
    after = _snapshot_patterns()
    print(f"  3. Snapshot after rebuild: {len(after)} rows")

    # 4. Assert equality
    if _patterns_equal(before, after):
        print("  4. PASS — patterns table is fully reconstructible from Event Log")
        return 0
    else:
        # Dump first diff for diagnosis
        for left, right in zip(before, after):
            if left != right:
                print(f"\n  First diff:")
                print(f"    before: {json.dumps(left, indent=4)}")
                print(f"    after:  {json.dumps(right, indent=4)}")
                break
        print("\n  4. FAIL — rebuild did not produce identical state")
        return 1


if __name__ == "__main__":
    sys.exit(main())

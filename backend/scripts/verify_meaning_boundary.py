#!/usr/bin/env python
"""Meaning Boundary G2 verification — authorship-aware memory presentation.

Validates docs/HUMAN_RUNTIME_CONSTITUTION.md G2:
  - System inferences appear as hypotheses with confidence, never bare assertions.
  - User self-reports appear without hypothesis framing.
  - origin projection survives memory rebuild.
"""

import os
import re
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("LLM_API_KEY", "test-key")

from app.core.agents.memory_engine import memory_engine
from app.core.runtime.kernel import Kernel
from app.store.database import Database

BARE_ASSERTION = re.compile(r"你是[^，。；\n]*")


def main() -> int:
    db_path = _BACKEND_ROOT / "data" / "verify_meaning_boundary.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(db_path=str(db_path))
    k = Kernel(db=db)

    violations: list[str] = []

    # --- G2.c: origin projection from actor ---
    k.emit_event(
        "MemoryDerived",
        "memory",
        "m-self",
        {
            "category": "fact",
            "content": "我更重视家庭而非事业",
            "confidence": 0.9,
        },
        actor="user",
    )
    k.emit_event(
        "BeliefFormed",
        "memory",
        "m-claim",
        {
            "category": "belief",
            "content": "你倾向在困难时放弃项目",
            "confidence": 0.73,
            "source": "reflection",
        },
        actor="kernel",
    )

    self_row = k.query_state("memories", id="m-self")[0]
    claim_row = k.query_state("memories", id="m-claim")[0]
    if self_row.get("origin") != "self_report":
        violations.append(
            f"G2.c: expected origin=self_report for actor=user, got {self_row.get('origin')!r}"
        )
    if claim_row.get("origin") != "claim":
        violations.append(
            f"G2.c: expected origin=claim for actor=kernel, got {claim_row.get('origin')!r}"
        )

    before = {
        "m-self": dict(self_row),
        "m-claim": dict(claim_row),
    }
    k.rebuild("memory")
    after_self = k.query_state("memories", id="m-self")[0]
    after_claim = k.query_state("memories", id="m-claim")[0]
    if after_self.get("origin") != "self_report" or after_claim.get("origin") != "claim":
        violations.append("G2.c: origin lost after rebuild('memory')")

    # --- G2.a / G2.b: authorship-aware rendering ---
    rendered = memory_engine.format_memory_context([
        {
            "id": "m-self",
            "content": self_row["content"],
            "confidence": float(self_row.get("confidence") or 0.9),
            "origin": "self_report",
        },
        {
            "id": "m-claim",
            "content": claim_row["content"],
            "confidence": float(claim_row.get("confidence") or 0.73),
            "origin": "claim",
        },
    ])

    if "你告诉过我的（你的自述）" not in rendered:
        violations.append("G2.b: missing self-report section header")
    if self_row["content"] not in rendered:
        violations.append("G2.b: self-report content missing from render")
    if "[推测" not in rendered or "置信度" not in rendered:
        violations.append("G2.a: claim missing hypothesis/confidence framing")
    if "系统认为可能" not in rendered:
        violations.append("G2.a: claim missing '系统认为可能' qualifier")
    if BARE_ASSERTION.search(rendered):
        violations.append("G2.a: bare '你是…' assertion found in rendered context")

    # Self-report line must not carry hypothesis prefix on the same numbered item
    for line in rendered.splitlines():
        if self_row["content"] in line and "[推测" in line:
            violations.append("G2.b: self-report incorrectly wrapped as hypothesis")

    # Self-report section must appear before claim section
    self_idx = rendered.find("你告诉过我的")
    claim_idx = rendered.find("系统推测")
    if self_idx == -1 or claim_idx == -1 or self_idx > claim_idx:
        violations.append("G2.b: self-report section must precede system hypothesis section")

    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass

    if violations:
        print("MEANING BOUNDARY G2 VERIFICATION FAILED", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print("MEANING BOUNDARY G2 VERIFICATION PASSED")
    print(f"  origin before rebuild: self={before['m-self'].get('origin')}, claim={before['m-claim'].get('origin')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""Agency surface lint — G5 static check on registered agency projection modules."""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.core.runtime.projection.agency_lint import lint_all_agency_surfaces


def main() -> int:
    issues = lint_all_agency_surfaces()
    failures = [i for i in issues if i.startswith("FAIL:")]
    warnings = [i for i in issues if i.startswith("WARN:")]

    for w in warnings:
        print(f"  note: {w}", file=sys.stderr)

    if failures:
        print("AGENCY SURFACE VERIFICATION FAILED", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("AGENCY SURFACE VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Replay the routing fallback (prereg Amendment 11; DELTA_value_in_quote_motion.md §4 ruling 6)
over every recorded motion draw. No model calls.

For each draw whose raw status is ``extracted``, the production post-check is applied to the raw value
and raw quote; when it ROUTES a structured-noise tool, ``listed_package_in_quote`` is applied to the
same quote. Counts per run and paper: routed draws, and of those how many fall back to which package.
Also counted, for every other extracted draw: whether its quote names exactly one listed package --
the fallback does not apply there (nothing is routed), and this shows where it would be reachable.
**Prints no quote text.** The only content-derived strings are the structured-noise tool id and the
package token the fallback would return.

Usage:
    python scripts/motion_fallback_replay.py
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from extractor_mvp.motion_guard import (  # noqa: E402
    MOTION_VALUE_ROUTED,
    listed_package_in_quote,
    motion_post_check,
)

_RESULTS = _HERE.parent / "results"
_RUNS: tuple[tuple[str, Path], ...] = (
    ("v1 56bc 2026-10-21", _RESULTS / "motion_probe"),
    ("v2 378a 2026-10-22", _RESULTS / "motion_probe_v2" / "motion_probe"),
    ("ab 56bc 2026-10-25", _RESULTS / "motion_probe_ab_2026-10-25" / "56bc" / "motion_probe"),
    ("ab 378a 2026-10-25", _RESULTS / "motion_probe_ab_2026-10-25" / "378a" / "motion_probe"),
    ("ciric 56bc 2026-10-26", _RESULTS / "motion_probe_ciric_2026-10-26" / "motion_probe"),
    ("v3 ea7b 2026-10-26", _RESULTS / "motion_probe_v3" / "motion_probe"),
    ("v4 b009 2026-10-26", _RESULTS / "motion_probe_v4" / "motion_probe"),
    ("ab v4 b009 2026-10-26", _RESULTS / "motion_probe_ab_2026-10-26_v4v5" / "v4" / "motion_probe"),
    ("ab v5 fb57 2026-10-26", _RESULTS / "motion_probe_ab_2026-10-26_v4v5" / "v5" / "motion_probe"),
    ("v6 8df0 2026-10-27", _RESULTS / "motion_probe_v6" / "motion_probe"),
)


def main() -> int:
    total = extracted = 0
    routed: collections.Counter = collections.Counter()
    fallback: collections.Counter = collections.Counter()
    reachable_elsewhere: collections.Counter = collections.Counter()
    for run, path in _RUNS:
        if not path.is_dir():
            raise SystemExit(f"run directory missing: {path}")
        for f in sorted(path.glob("*.jsonl")):
            for line in f.open(encoding="utf-8"):
                if not line.strip():
                    continue
                rec = json.loads(line)
                total += 1
                if rec["raw_status"] != "extracted":
                    continue
                extracted += 1
                verdict = motion_post_check(rec["raw_value"], rec["raw_verbatim_quote"])
                if verdict is not None and verdict.startswith(MOTION_VALUE_ROUTED):
                    tool = verdict.split(":", 1)[1]
                    routed[(run, f.stem, tool)] += 1
                    pkg = listed_package_in_quote(rec["raw_verbatim_quote"])
                    fallback[(run, f.stem, tool, pkg or "<none>")] += 1
                elif listed_package_in_quote(rec["raw_verbatim_quote"]) is not None:
                    reachable_elsewhere[(run, f.stem)] += 1
    print(f"draws replayed: {total}; extracted: {extracted}")
    print(
        "\n== routed draws, and the package the fallback yields (run / paper / tool -> package: n)"
    )
    for (run, paper, tool, pkg), n in sorted(fallback.items()):
        print(f"   {run:22s} {paper:15s} {tool:10s} -> {pkg:8s} x{n}")
    print(
        f"\n== totals: routed {sum(routed.values())}; fallback fires on "
        f"{sum(n for (r, p, t, g), n in fallback.items() if g != '<none>')}; "
        f"papers with a fallback: {sorted({p for (r, p, t, g) in fallback if g != '<none>'})}"
    )
    print(
        "\n== extracted, NOT routed, quote naming exactly one listed package (the fallback does not "
        "apply; shown so 'fires nowhere else' is checkable)"
    )
    for (run, paper), n in sorted(reachable_elsewhere.items()):
        print(f"   {run:22s} {paper:15s} x{n}")
    print(f"   total {sum(reachable_elsewhere.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

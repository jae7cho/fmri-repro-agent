#!/usr/bin/env python3
"""Replay the motion value-in-quote post-check over every recorded probe draw. No model calls.

Acceptance for DELTA_value_in_quote_motion.md §4 (rulings 2-3), run over the four recorded runs:
v1 (2026-10-21, 60 draws), v2 (2026-10-22, 70), the same-day A/B (2026-10-25, 40) and ciric under
the restored stanza (2026-10-26, 10) -- 180 draws. For each draw the production path is mirrored:

* raw ``status`` not ``extracted``           -> untouched (the post-check never sees it)
* quote did not resolve (``span_start`` None) -> untouched (already MissingFromPaper upstream)
* otherwise ``motion_post_check(raw_value, raw_verbatim_quote)`` -> keep / unsupported / routed

**Prints no quote text and no value text.** Draws are identified by run, paper and draw id; the
only content-derived column is the frozen heuristic's class of the value. The runs live under
``extractor_mvp/results/`` (gitignored); the counts this prints are the record.

Usage:
    python scripts/motion_guard_replay.py            # all four runs, from the default locations
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))
sys.path.insert(0, str(_HERE))

from motion_value_kind import value_kind  # noqa: E402

from extractor_mvp.motion_guard import MOTION_VALUE_UNSUPPORTED, motion_post_check  # noqa: E402

_RESULTS = _HERE.parent / "results"
_RUNS: tuple[tuple[str, Path], ...] = (
    ("v1 56bc 2026-10-21", _RESULTS / "motion_probe"),
    ("v2 378a 2026-10-22", _RESULTS / "motion_probe_v2" / "motion_probe"),
    ("ab 56bc 2026-10-25", _RESULTS / "motion_probe_ab_2026-10-25" / "56bc" / "motion_probe"),
    ("ab 378a 2026-10-25", _RESULTS / "motion_probe_ab_2026-10-25" / "378a" / "motion_probe"),
    ("ciric 56bc 2026-10-26", _RESULTS / "motion_probe_ciric_2026-10-26" / "motion_probe"),
)


def verdict_for(rec: dict) -> str:
    if rec["raw_status"] != "extracted":
        return "untouched:not_extracted"
    if rec["span_start"] is None:
        return "untouched:span_unresolved"
    v = motion_post_check(rec["raw_value"], rec["raw_verbatim_quote"])
    if v is None:
        return "keep"
    if v == MOTION_VALUE_UNSUPPORTED:
        return "unsupported"
    return "routed:" + v.split(":", 1)[1]


def main() -> int:
    total = 0
    per_run: dict[str, collections.Counter] = {}
    listing: list[tuple[str, str, int, str, str]] = []
    for run, path in _RUNS:
        if not path.is_dir():
            raise SystemExit(f"run directory missing: {path}")
        c: collections.Counter = collections.Counter()
        for f in sorted(path.glob("*.jsonl")):
            for line in f.open(encoding="utf-8"):
                if not line.strip():
                    continue
                rec = json.loads(line)
                total += 1
                v = verdict_for(rec)
                kind = value_kind(rec["raw_value"]) if rec["raw_status"] == "extracted" else "-"
                c[(f.stem, v)] += 1
                if v != "keep":
                    listing.append((run, f.stem, rec["draw"], v, kind))
        per_run[run] = c

    print(f"draws replayed: {total}")
    for run, c in per_run.items():
        print(f"\n== {run}")
        for (paper, v), n in sorted(c.items()):
            print(f"   {paper:15s} {v:28s} x{n}")

    print("\n== every draw the post-check changes or does not see, by run / paper / draw (class)")
    by_v: collections.Counter = collections.Counter(v for _, _, _, v, _ in listing)
    for run, paper, draw, v, kind in listing:
        print(f"   {run:22s} {paper:15s} draw {draw:2d}  {v:28s} {kind}")
    print("\n== totals over 180")
    for v, n in sorted(by_v.items()):
        print(f"   {v:28s} {n}")
    print(f"   {'keep':28s} {total - sum(by_v.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

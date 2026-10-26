#!/usr/bin/env python3
"""Replay the step-field quote-support check over the 19 stored results. No model calls.

Applies ``quote_support.step_value_supported`` — the production function — to every EXTRACTED value of
the seven ``_FIELD_SPECS`` fields in ``results/<batch>/papers/*.json``, using the stored
``resolutions`` record's raw value (the model's own) and the stored span's text (what the resolver
located). Reports every cell the check would DEMOTE, by paper, field and span offsets; for the
held-out papers (liu_2005, tang_2025, wheaton_2004) counts only. Prints no quote or value text.

Usage:
    python scripts/step_field_support_replay.py --results-dir results/batch_a1_acceptance
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from extractor_mvp.extractor import _FIELD_SPECS
from extractor_mvp.quote_support import NUMERIC_FIELDS, step_value_supported

_HELD_OUT = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--results-dir", required=True, type=Path)
    args = ap.parse_args(argv)
    specs = [dotted for (_a, _f, dotted, _l, _t) in _FIELD_SPECS]
    per_field: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    held: collections.Counter = collections.Counter()
    demoted: list[tuple[str, str, int, int]] = []
    n_papers = 0
    for f in sorted((args.results_dir / "papers").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        pid = d["paper_id"]
        n_papers += 1
        raw_by_field = {r["field"]: r for r in d.get("resolutions", [])}
        for step in d["preprocessing"]["steps"]:
            for dotted in specs:
                kind, fname = dotted.split(".", 1)
                if step["kind"] != kind or fname not in step:
                    continue
                ex = step[fname]["extraction"]
                if ex.get("status") != "EXTRACTED":
                    continue
                span = ex["spans"][0]
                val = ex["value"]
                if dotted in NUMERIC_FIELDS:
                    value: object = float(val)
                else:
                    rec = raw_by_field.get(dotted)
                    verbatim = (
                        str(rec["raw_value"])
                        if rec and rec.get("raw_value") is not None
                        else val["verbatim"]
                    )
                    value = SimpleNamespace(
                        verbatim=verbatim,
                        resolved=val.get("resolved"),
                        resolution=val.get("resolution"),
                    )
                ok = step_value_supported(dotted, value, span["text"])
                if pid in _HELD_OUT:
                    held["pass" if ok else "DEMOTE"] += 1
                    continue
                per_field[dotted]["pass" if ok else "DEMOTE"] += 1
                if not ok:
                    demoted.append((pid, dotted, span["start"], span["end"]))
    print(f"papers: {n_papers}")
    print("\n== per field, non-held-out papers: pass / demote")
    for dotted in specs:
        c = per_field.get(dotted, collections.Counter())
        print(f"   {dotted:42s} pass {c['pass']:2d}   demote {c['DEMOTE']:2d}")
    print("\n== cells the check would demote (paper, field, span offsets)")
    for pid, dotted, a, b in demoted:
        print(f"   {pid:15s} {dotted:42s} {a}-{b}")
    if not demoted:
        print("   (none)")
    print(f"\n== held-out papers, counts only: pass {held['pass']}, demote {held['DEMOTE']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

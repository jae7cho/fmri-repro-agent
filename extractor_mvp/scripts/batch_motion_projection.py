#!/usr/bin/env python3
"""Projection of the motion field from a batch run's stored results -- the PROCESSED layer, one draw
per paper. No model calls. Reads ``<results-dir>/papers/<id>.json`` and emits, per paper: the
contamination class, ``likely_multi_acquisition``, the motion step's extraction status, its gap
reason base, span offsets, the heuristic's class of the processed value (``value_kind``), the
derived attribution level (``motion_guard.attribution_from_quote`` on the span's text; ``package``
when the routing fallback fired) and the base of any motion diagnostic. **No quote or value text.**
Rows for every paper are emitted by this script in the same format; the clean three are read by
nobody as anything but states and counts (prereg Amendment 13).

Usage:
    python scripts/batch_motion_projection.py --results-dir results/batch_motion_corpus_v1 \\
        --out ../ground_truth/batch_motion_corpus_v1_projection.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from motion_value_kind import value_kind

from extractor_mvp.motion_guard import (
    MOTION_VALUE_ROUTED_FALLBACK,
    attribution_from_quote,
)

#: DESIGN_motion_full_corpus.md §2.5, with cole and gordon in the probe set from Amendment 10.
_CLASS = {
    **{
        p: "probe"
        for p in (
            "power_2014",
            "binder_1999",
            "liu_2013",
            "derosa_2025",
            "agtzidis_2020",
            "poldrack_2015",
            "ciric_2017",
            "braun_2015",
            "viduarre_2017",
            "vanderwal_2016",
            "cole_2013",
            "gordon_2014",
            "mueller_2021",
        )
    },
    **{p: "co-adjudicated, not probed" for p in ("chen_2015", "oconnor_2017", "weber_2024")},
    **{p: "clean" for p in ("liu_2005", "tang_2025", "wheaton_2004")},
}
_ORDER = list(_CLASS)
_COLUMNS = (
    "paper_id",
    "class",
    "likely_multi_acquisition",
    "motion_status",
    "reason_base",
    "span_start",
    "span_end",
    "heuristic_class",
    "attribution",
    "diagnostic_base",
)


def _row(doc: dict[str, Any]) -> dict[str, Any]:
    pid = doc["paper_id"]
    step = next(
        (s for s in doc["preprocessing"]["steps"] if s.get("kind") == "motion_correction"), None
    )
    field = (step or {}).get("method") or {}
    ext = field.get("extraction") or {}
    status = ext.get("status", "")
    reason = (field.get("inference") or {}).get("reason") or ""
    span = (ext.get("spans") or [{}])[0] if status == "EXTRACTED" else {}
    verbatim = (
        (ext.get("value") or {}).get("verbatim") if isinstance(ext.get("value"), dict) else None
    )
    diags = [d for d in doc.get("diagnostics", []) if d.get("field") == "motion_correction.method"]
    dbase = diags[0]["failure_reason"].split(":")[0] if diags else ""
    kind = value_kind(verbatim) if status == "EXTRACTED" and verbatim else ""
    if status == "EXTRACTED" and kind == "tool_name" and span:
        level = (
            "package"
            if dbase == MOTION_VALUE_ROUTED_FALLBACK
            else attribution_from_quote(span.get("text"), verbatim)  # ruling 1 of 2026-10-28
        )
    else:
        level = ""
    return {
        "paper_id": pid,
        "class": _CLASS.get(pid, "unlisted"),
        "likely_multi_acquisition": "yes" if doc.get("likely_multi_acquisition") else "no",
        "motion_status": status,
        "reason_base": reason.split(":")[0],
        "span_start": span.get("start", ""),
        "span_end": span.get("end", ""),
        "heuristic_class": kind,
        "attribution": level,
        "diagnostic_base": dbase,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--results-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    papers = args.results_dir / "papers"
    present = {p.stem for p in papers.glob("*.json")}
    unlisted = sorted(present - set(_ORDER))
    if unlisted:
        raise SystemExit(f"results for papers outside the corpus partition: {unlisted}")
    manifest = args.results_dir / "launcher_manifest.json"
    head = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
    rows = [
        _row(json.loads((papers / f"{pid}.json").read_text(encoding="utf-8")))
        for pid in _ORDER
        if pid in present
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        f.write(
            "# PROJECTION of the motion field from a BATCH run (the processed layer, one draw per paper).\n"
            "# Emitted by extractor_mvp/scripts/batch_motion_projection.py -- do not hand-edit. No quote or\n"
            "# value text: status, reason base, span OFFSETS, heuristic class, derived attribution.\n"
            "# DIAGNOSTIC, NOT EVALUATIVE. Counts only; no rate may be computed from this file.\n"
            f"# vintage                    : {head.get('vintage', 'unknown')}\n"
            f"# motion_method_prompt_sha256: {head.get('motion_method_prompt_sha256', 'unknown')}\n"
            f"# head                       : {head.get('head', 'unknown')}\n"
            f"# model                      : {head.get('model', 'unknown')}\n"
            f"# projection generated_utc   : {datetime.now(UTC).isoformat(timespec='seconds')}\n#\n"
        )
        w = csv.DictWriter(f, fieldnames=_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} papers -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

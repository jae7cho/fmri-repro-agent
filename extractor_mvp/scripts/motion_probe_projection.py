#!/usr/bin/env python3
"""Emit the tracked PROJECTION of a motion_correction.method reachability-probe run.

The per-draw records a probe run writes (``results/<run>/motion_probe/*.jsonl``) carry the model's
returned value and quote, which are sentences from the papers. The corpus is not in this repository
for licensing reasons, so those strings may not be tracked. This script projects a run down to what
MAY be tracked -- status, the derived heuristic class, the state-map row, span OFFSETS, and the
per-draw bookkeeping -- and writes it as a CSV under ``ground_truth/``.

**It prints and writes no quote text and no value text.** The value is consumed by
``motion_value_kind.value_kind`` and only the class it returns is emitted. Keep it that way.

Counts only, no rate: the probe tests reachability (prereg ``:9-10``, ``:158-159``). The state map is
prereg Amendment 1's six rows; the heuristic is Amendment 2 ruling 5's implementation.

The 2026-10-21 projection (``ground_truth/motion_probe_v1_projection.csv``) was emitted by an ad-hoc
script that was not kept. This script was written on 2026-10-22 and VALIDATED by regenerating that
file from ``results/motion_probe/`` and comparing every data row -- identical -- before it was used
for the second run. The header comment differs only where it names the run.

Usage:
    python scripts/motion_probe_projection.py \
        --results-dir results/motion_probe_v2 --run-date 2026-10-22 \
        --out ../ground_truth/motion_probe_v2_projection.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion_value_kind import value_kind

_REPO = Path(__file__).resolve().parents[2]
_RESOLVER = "extractor_mvp/src/extractor_mvp/span_resolver.py"

#: The prereg's own order (:5-7), then the Amendment 4 addition. Papers absent from a run are skipped,
#: so the same order serves the six-paper and seven-paper runs.
_ORDER = (
    "power_2014",
    "binder_1999",
    "liu_2013",
    "derosa_2025",
    "agtzidis_2020",
    "poldrack_2015",
    "ciric_2017",
    # Amendment 8 (2026-10-26): the three deferral-shape papers, after the seven.
    "braun_2015",
    "viduarre_2017",
    "vanderwal_2016",
)

#: Added for version-3 runs (Amendment 7): the binding the MODEL stated, and whether it agrees with
#: the frozen heuristic's class. Emitted only when the run's records carry ``raw_binding``, so the
#: v1/v2/A-B/ciric projections regenerate byte-for-byte as before.
_V3_COLUMNS = ("model_state", "model_vs_heuristic")

_COLUMNS = (
    "paper_id",
    "draw",
    "raw_status",
    "heuristic_class",
    "state_map_row",
    "predicted_label_state",
    "span_resolved",
    "span_start",
    "span_end",
    "left_missing_reason",
    "deferral_target_kind",
    "completion_attempts",
    "reask_occurred",
    "wall_seconds",
)

#: Prereg Amendment 1, the state map. Rows 4 and 5 are decided on the ORIGINAL target_kind (the one
#: before the extractor narrows "supplement" -> "paper"), because row 5 is unobservable otherwise.
_DEFERRED_ROWS = {"paper": 4, "pipeline": 4, "dataset_doc": 4, "supplement": 5}


def _row(rec: dict[str, Any]) -> dict[str, Any]:
    status = rec["raw_status"]
    heuristic = ""
    row: int | str = ""
    state = ""
    if status == "extracted":
        heuristic = value_kind(rec["raw_value"])
        row, state = {
            "operation_phrase": (1, "described_only"),
            "tool_name": (2, "named_tool"),
            "undecided": (3, "undecided"),
        }[heuristic]
    elif status == "deferred":
        kind = rec.get("deferral_target_kind_original") or ""
        row = _DEFERRED_ROWS.get(kind, "")
        state = {4: "deferred", 5: "unread"}.get(row, "")  # type: ignore[arg-type]
    elif status == "missing":
        row, state = 6, "absent"
    resolved = rec["span_start"] is not None
    model_state = rec.get("raw_binding")
    if status == "extracted" and model_state is not None:
        expected = {"operation_phrase": "described_only", "tool_name": "named_tool"}.get(heuristic)
        agreement = (
            "undecided"
            if expected is None
            else ("agree" if expected == model_state else "disagree")
        )
    else:
        agreement = ""
    return {
        "paper_id": rec["paper_id"],
        "draw": rec["draw"],
        "raw_status": status or "",
        "heuristic_class": heuristic,
        "state_map_row": row,
        "predicted_label_state": state,
        "span_resolved": "yes" if resolved else "no",
        "span_start": "" if rec["span_start"] is None else rec["span_start"],
        "span_end": "" if rec["span_end"] is None else rec["span_end"],
        "left_missing_reason": rec.get("left_missing_reason") or "",
        "deferral_target_kind": rec.get("deferral_target_kind_original") or "",
        "completion_attempts": rec["completion_attempts"],
        "reask_occurred": "yes" if rec["reask_occurred"] else "no",
        "wall_seconds": rec["wall_seconds"],
        "model_state": model_state or "",
        "model_vs_heuristic": agreement,
    }


def _resolver_vintage() -> str:
    """Last commit to touch the span resolver, plus whether the working tree differs from it.

    The v1 projection recorded the stanza hash but not the resolver commit; the glyph-leak DELTA
    (§4) asks for one, because the prereg's correctness rule depends on span resolution even though
    reachability does not. Emitted, not typed.
    """
    try:
        sha = subprocess.run(
            ["git", "-C", str(_REPO), "log", "-1", "--format=%h %cs", "--", _RESOLVER],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(_REPO), "diff", "--quiet", "HEAD", "--", _RESOLVER],
            capture_output=True,
        ).returncode
    except (OSError, subprocess.CalledProcessError):
        return "unknown (git unavailable)"
    return f"{sha}{' + UNCOMMITTED working-tree changes' if dirty else ', working tree clean'}"


def _header(manifest: dict[str, Any], run_date: str, n_papers: int, n_draws: int) -> str:
    k = manifest["k"]
    return f"""# PROJECTION of the motion_correction.method reachability probe, run {run_date}.
# Emitted by extractor_mvp/scripts/motion_probe_projection.py -- do not hand-edit. Regenerate from the
# run's results/<run>/motion_probe/*.jsonl.
#
# WHY A PROJECTION AND NOT THE RUN. The per-draw records under extractor_mvp/results/ carry the
# model's returned value and quote, which are SENTENCES FROM THE PAPERS. The corpus is not in this
# repository for licensing reasons, so tracking those strings would redistribute what the corpus
# deliberately withholds. This projection therefore carries NO quote text and NO value text: only the
# status, the derived heuristic class, the state-map row, and the span OFFSETS. Anyone holding the
# corpus can recover the text from the offsets; anyone who does not, cannot.
#
# DIAGNOSTIC, NOT EVALUATIVE. No rate, fraction or accuracy figure is computed here or may be
# computed from it (prereg :9-10, :158-159). The probe tests whether a state is EXPRESSIBLE.
# Counts only. See the matching docs/findings/motion-probe-*-results.md for the outcome against the
# pre-declared readings, and the pre-registration for what may and may not be concluded.
#
# model                      : {manifest["model"]}, temperature 0.0, max_retries 2
# K                          : {k} per paper, {n_papers} papers, {n_draws} draws
# motion_method_prompt_sha256: {manifest["motion_method_prompt_sha256"]}
# span_resolver vintage      : {_resolver_vintage()}
# heuristic                  : extractor_mvp/scripts/motion_value_kind.py (prereg Amendment 2 ruling 5)
# state map                  : prereg Amendment 1, six rows
# run generated_utc          : {manifest["generated_utc"]}
# projection generated_utc   : {datetime.now(UTC).isoformat(timespec="seconds")}
#
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--results-dir", required=True, type=Path, help="the --results-dir the probe ran with"
    )
    ap.add_argument("--run-date", required=True, help="YYYY-MM-DD of the run, for the header")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    run_dir = args.results_dir / "motion_probe"
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []
    papers: list[str] = []
    for paper_id in _ORDER:
        src = run_dir / f"{paper_id}.jsonl"
        if not src.is_file():
            continue
        papers.append(paper_id)
        with src.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    raw_records.append(rec)
                    rows.append(_row(rec))
    unordered = sorted(set(manifest["papers"]) - set(papers))
    if unordered:
        raise SystemExit(f"papers in the manifest but not in _ORDER or on disk: {unordered}")

    v3 = any("raw_binding" in r for r in raw_records)
    columns = _COLUMNS + _V3_COLUMNS if v3 else _COLUMNS
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        f.write(_header(manifest, args.run_date, len(papers), len(rows)))
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")  # CRLF rows, as v1
        w.writeheader()
        w.writerows(rows)
    if v3:
        n = sum(1 for r in rows if r["model_vs_heuristic"] == "disagree")
        u = sum(1 for r in rows if r["model_vs_heuristic"] == "undecided")
        print(
            f"model vs heuristic: {n} disagree, {u} heuristic-undecided, over the extracted draws"
        )
    print(f"{len(rows)} draws over {len(papers)} papers -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

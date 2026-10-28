#!/usr/bin/env python3
"""Apply the motion method's inference arm to a stored batch vintage, as a PROCESSED vintage.
No model call. (``docs/design/DESIGN_motion_inference_arm.md`` §5; the author's rulings of 2026-10-28.)

For every ``<results-dir>/papers/<id>.json``: parse the stored preprocessing, run
``infer_motion_method`` (the same code the extractor runs after extraction), and write
``<out>/papers/<id>.json`` with the filled preprocessing and the ``motion_inference`` record, plus
``<id>.md`` re-rendered through ``to_report`` with the record. A ``manifest.json`` beside the output
names the source vintage, HEAD and the live stanza hash. The projection it emits carries, per
paper, the contamination class, the path (arm / diagnostic / none / never), basis name and type,
confidence, the number of alternatives and the inferred program -- **for the clean three, the path
only** (filled-or-not), every other column blank. No paper text anywhere.

Usage:
    python scripts/apply_motion_inference.py --results-dir results/batch_motion_corpus_v1 \\
        --out results/batch_motion_corpus_v1_inferred --projection ../ground_truth/x.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from batch_motion_projection import _CLASS, _ORDER
from fmri_repro.spec.migrations import parse_any_version

from extractor_mvp.extractor import MOTION_METHOD_PROMPT
from extractor_mvp.motion_inference import infer_motion_method
from extractor_mvp.render import to_report

_HELD_OUT = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})
_COLUMNS = (
    "paper_id",
    "class",
    "path",
    "basis_name",
    "basis_type",
    "confidence",
    "n_alternatives",
    "program",
    "reason_base",
)


def _row(pid: str, rec: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "paper_id": pid,
        "class": _CLASS.get(pid, "unlisted"),
        "path": rec["path"],
    }
    if pid in _HELD_OUT:
        return {**{c: "" for c in _COLUMNS}, **row}  # filled-or-not only
    row.update(
        basis_name=rec.get("basis_name") or "",
        basis_type=rec.get("basis_type") or "",
        confidence="" if rec.get("confidence") is None else rec["confidence"],
        n_alternatives=len(rec.get("alternatives") or []),
        program=rec.get("program") or "",
        reason_base=(rec.get("reason") or "").split(":")[0],
    )
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--results-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--projection", required=True, type=Path)
    args = ap.parse_args(argv)
    src = args.results_dir / "papers"
    if not src.is_dir():
        raise SystemExit(f"no papers/ under {args.results_dir}")
    if args.out.resolve() == args.results_dir.resolve():
        raise SystemExit(
            "--out must differ from --results-dir: a processed vintage is a NEW vintage"
        )
    dst = args.out / "papers"
    dst.mkdir(parents=True, exist_ok=True)
    present = {p.stem for p in src.glob("*.json")}
    unlisted = sorted(present - set(_ORDER))
    if unlisted:
        raise SystemExit(f"results for papers outside the corpus partition: {unlisted}")
    rows: list[dict[str, Any]] = []
    started = datetime.now(UTC).isoformat(timespec="seconds")
    for pid in (p for p in _ORDER if p in present):
        doc = json.loads((src / f"{pid}.json").read_text(encoding="utf-8"))
        preprocessing = parse_any_version(doc["preprocessing"])
        preprocessing, record = infer_motion_method(preprocessing)
        rec = record.as_dict()
        doc["preprocessing"] = preprocessing.model_dump(mode="json")
        doc["motion_inference"] = rec
        doc["processed_vintage"] = {
            "name": args.out.name,
            "source_vintage": args.results_dir.name,
            "applied": "extractor_mvp.motion_inference.infer_motion_method",
            "model_call": False,
        }
        (dst / f"{pid}.json").write_text(
            json.dumps(doc, indent=2, default=str) + "\n", encoding="utf-8"
        )
        (dst / f"{pid}.md").write_text(
            to_report(preprocessing, source=pid, motion_inference=record), encoding="utf-8"
        )
        rows.append(_row(pid, rec))
    head = subprocess.run(
        ["git", "-C", str(Path(__file__).resolve().parents[2]), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = {
        "artifact": "a PROCESSED vintage: the motion method's inference arm applied to a stored batch",
        "vintage": args.out.name,
        "source_vintage": args.results_dir.name,
        "head": head,
        "motion_method_prompt_sha256": hashlib.sha256(
            MOTION_METHOD_PROMPT.encode("utf-8")
        ).hexdigest(),
        "model_call": False,
        "papers": [r["paper_id"] for r in rows],
        "started_utc": started,
        "ended_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    args.projection.parent.mkdir(parents=True, exist_ok=True)
    with args.projection.open("w", encoding="utf-8", newline="") as f:
        f.write(
            "# PROJECTION of the motion method's inference arm applied to a stored batch (a processed\n"
            "# vintage, no model call). Emitted by extractor_mvp/scripts/apply_motion_inference.py -- do not\n"
            "# hand-edit. Per paper: the path (arm / diagnostic / none / never), basis name and type,\n"
            "# confidence, alternatives, the inferred program (a knowledge-base value, not paper text). For\n"
            "# the clean three: the path only. DIAGNOSTIC, NOT EVALUATIVE: counts of papers filled per\n"
            "# basis; no accuracy figure may be computed from this file.\n"
            f"# vintage                    : {manifest['vintage']} (from {manifest['source_vintage']})\n"
            f"# head                       : {head}\n"
            f"# motion_method_prompt_sha256: {manifest['motion_method_prompt_sha256']}\n"
            f"# projection generated_utc   : {manifest['ended_utc']}\n#\n"
        )
        w = csv.DictWriter(f, fieldnames=_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    counts: dict[str, int] = {}
    for r in rows:
        key = f"{r['path']}" + (f"/{r['basis_name']}" if r.get("basis_name") else "")
        counts[key] = counts.get(key, 0) + 1
    print(f"{len(rows)} papers -> {args.out}; counts by path/basis: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

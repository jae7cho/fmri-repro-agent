#!/usr/bin/env python3
"""Score stored records against the author's motion correction labels, bullet 1 (``method``)
(``ground_truth/motion_correction_labels_v1.xlsx``, sheet ``Labels``). The PROCESSED layer, one draw
per paper, no model calls. Counts only; no rates.

Bullet 1 is the only bullet the workbook labels at full rigour for extraction and scoring (its
"Start here" sheet); bullets 2-7 are attestation only and are not scored here.

The record's state comes from the pre-registered state map
(``docs/findings/motion-method-reachability-prereg.md``, "The state map"), applied to the stored
``motion_correction.method`` field:
- EXTRACTED: the operation-phrase heuristic (``scripts/motion_value_kind.py``) on the value's verbatim
  words: ``operation_phrase`` -> described_only, ``tool_name`` -> named_tool, ``undecided`` ->
  undecided (row 3: never defaulted).
- DEFERRED_TO_CITATION -> deferred. Row 5 (a supplement target is ``unread``) is not observable in a
  stored record, which keeps only the narrowed target kind.
- MISSING_FROM_PAPER -> absent (row 6), except when the record's diagnostics say the method's quote
  did not resolve: then ``unverifiable``, the report's own word, since the paper may state it.
- any other status -> ``other: <status>``.

Value: for a paper whose label and record are both named_tool, the tools agree when their names are
equal once case, spaces, hyphens and periods are set aside ("SPM12" = "SPM 12"; "FSL" != "MCFLIRT").

Rows for liu_2005, tang_2025 and wheaton_2004 print states and agree/disagree only, never a value
(the standing held-out rule, as in ``score_smoothing_filtering.py``).

Usage (openpyxl reads the workbook; it is not a dependency of this package):
    uv run --with openpyxl python scripts/score_motion.py --results-dir results/corpus_grobid_v1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion_value_kind import value_kind

REPO = Path(__file__).resolve().parents[2]
LABELS = REPO / "ground_truth" / "motion_correction_labels_v1.xlsx"

#: The workbook's method states (its Glossary sheet).
LABEL_STATES = ("named_tool", "described_only", "deferred", "absent", "stated_not_performed")

#: Papers whose label and record values are never printed.
VALUES_WITHHELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})

_KIND_TO_STATE = {
    "operation_phrase": "described_only",
    "tool_name": "named_tool",
    "undecided": "undecided",
}


@dataclass(frozen=True)
class MotionLabel:
    paper_id: str
    state: str
    value: str


def load_labels(path: Path = LABELS) -> list[MotionLabel]:
    """The Labels sheet's paper rows (a row whose paper_id has a space is the sheet's note)."""
    import openpyxl

    rows = list(openpyxl.load_workbook(path, data_only=True)["Labels"].iter_rows(values_only=True))
    head = [str(h) for h in rows[0]]
    out: list[MotionLabel] = []
    for r in rows[1:]:
        d = dict(zip(head, r, strict=False))
        pid = str(d.get("paper_id") or "").strip()
        if not pid or " " in pid:
            continue
        out.append(
            MotionLabel(
                pid,
                str(d.get("method_state") or "").strip(),
                str(d.get("method_value") or "").strip(),
            )
        )
    return out


@dataclass(frozen=True)
class MotionRecord:
    state: str
    value: str  # the extracted verbatim words, "" when none


def record_method(record: dict[str, Any]) -> MotionRecord:
    """The stored ``motion_correction.method`` under the pre-registered state map."""
    doc = record.get("extraction_json", record)
    step = next(
        (s for s in doc["preprocessing"]["steps"] if s.get("kind") == "motion_correction"), None
    )
    ext = ((step or {}).get("method") or {}).get("extraction") or {}
    status = ext.get("status") or "MISSING_FROM_PAPER"
    if status == "EXTRACTED":
        value = ext.get("value")
        verbatim = str(value.get("verbatim") or "") if isinstance(value, dict) else str(value or "")
        return MotionRecord(_KIND_TO_STATE[value_kind(verbatim)], verbatim)
    if status == "DEFERRED_TO_CITATION":
        return MotionRecord("deferred", "")
    if status == "MISSING_FROM_PAPER":
        unresolved = any(
            d.get("field") == "motion_correction.method"
            and "quote" in str(d.get("failure_reason") or "")
            for d in doc.get("diagnostics") or []
        )
        return MotionRecord("unverifiable" if unresolved else "absent", "")
    return MotionRecord(f"other: {status}", "")


def _tool(name: str) -> str:
    return re.sub(r"[\s\-.]", "", name).lower()


def compare_value(label: MotionLabel, rec: MotionRecord) -> str:
    if label.state != "named_tool" or rec.state != "named_tool":
        return ""
    if not label.value:
        return "not labelled"
    return "agree" if _tool(label.value) == _tool(rec.value) else "disagree"


@dataclass(frozen=True)
class Scored:
    label: MotionLabel
    record: MotionRecord | None  # None: no record for the paper

    @property
    def state_agrees(self) -> bool | None:
        return None if self.record is None else self.record.state == self.label.state

    @property
    def value(self) -> str:
        return "" if self.record is None else compare_value(self.label, self.record)


def load_records(*results_dirs: Path) -> dict[str, MotionRecord]:
    """Every ``<dir>/papers/<id>.json``; a paper in two directories is an error."""
    out: dict[str, MotionRecord] = {}
    for d in results_dirs:
        for f in sorted((d / "papers").glob("*.json")):
            if f.stem in out:
                raise SystemExit(f"{f.stem} has a record in more than one results directory")
            out[f.stem] = record_method(json.loads(f.read_text()))
    return out


def score(labels: list[MotionLabel], records: dict[str, MotionRecord]) -> list[Scored]:
    return [Scored(lab, records.get(lab.paper_id)) for lab in labels]


def _value_shown(pid: str, v: str) -> str:
    if pid in VALUES_WITHHELD:
        return "match" if v == "agree" else ("no match" if v == "disagree" else v)
    return v


def render(results: list[Scored], results_dirs: list[str]) -> str:
    lines = [
        "# Motion correction, bullet 1 (method): stored records vs the author's labels",
        "",
        f"Records: {', '.join(f'`{d}`' for d in results_dirs)}, read with the current code. Labels: "
        "`ground_truth/motion_correction_labels_v1.xlsx`. Counts only; no rates.",
        "",
        "| paper | label state | record state | state | tool |",
        "|---|---|---|---|---|",
    ]
    for s in sorted(results, key=lambda s: s.label.paper_id):
        pid = s.label.paper_id
        if s.record is None:
            lines.append(f"| {pid} | {s.label.state} | no record | | |")
            continue
        agree = "agree" if s.state_agrees else "disagree"
        lines.append(
            f"| {pid} | {s.label.state} | {s.record.state} | {agree} | "
            f"{_value_shown(pid, s.value)} |"
        )
    c = Counter(
        "no record" if s.record is None else ("agree" if s.state_agrees else "disagree")
        for s in results
    )
    lines += [
        "",
        f"State: {c['agree']} agree, {c['disagree']} disagree, {c['no record']} no record.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--labels", type=Path, default=LABELS)
    ap.add_argument("--results-dir", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, help="write the report here (default: stdout)")
    args = ap.parse_args(argv)
    labels = load_labels(args.labels)
    bad = [lab.paper_id for lab in labels if lab.state not in LABEL_STATES]
    if bad:
        print(f"label state not in vocabulary: {bad}", file=sys.stderr)
        return 1
    text = render(
        score(labels, load_records(*args.results_dir)), [str(d) for d in args.results_dir]
    )
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

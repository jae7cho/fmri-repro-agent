"""Score the resolved realignment tool against the motion labels' resolved_tool (2026-11-09).

Per labelled paper: the record's resolution (``resolution.realignment_tool``: package and program)
against the label's ``resolved_tool`` ("fsl MCFLIRT"): agree / disagree / label blank (the author
has not set one) / no record / no resolution. Split by the record's provenance: KB-confirmed
(EXTRACTED, from the paper or a cited paper, or INFERRED_DEFAULT) against model-only
(INFERRED_MODEL, UNKNOWN). Counts only; no rates. The three held-out papers show their outcome, not
their tools.

    uv run --with openpyxl python scripts/score_motion_resolved.py --results-dir results/corpus_full_v2_reresolved
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
LABELS = REPO / "ground_truth" / "motion_correction_labels_v1.xlsx"
HELD_OUT = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})
KB_CONFIRMED = frozenset({"EXTRACTED", "INFERRED_DEFAULT"})


def load_labels(path: Path = LABELS) -> dict[str, str | None]:
    """``{paper_id: resolved_tool or None}`` for every paper row of the Labels sheet."""
    import openpyxl

    rows = list(openpyxl.load_workbook(path, data_only=True)["Labels"].iter_rows(values_only=True))
    head = [str(h) for h in rows[0]]
    out: dict[str, str | None] = {}
    for r in rows[1:]:
        d = dict(zip(head, r, strict=False))
        pid = str(d.get("paper_id") or "").strip()
        if pid and " " not in pid:
            v = d.get("resolved_tool")
            out[pid] = str(v).strip() if v not in (None, "") else None
    return out


def record_parts(record: dict[str, Any]) -> tuple[str | None, str | None, str]:
    """``(package, program, provenance)`` of a record's resolution; the provenance is "no
    resolution" when the record has none."""
    res = record.get("resolution")
    if not isinstance(res, dict) or res.get("status") != "ok":
        return None, None, "no resolution"
    t = res.get("realignment_tool") or {}
    conf = t.get("kb_confirmation") or {}
    package = t.get("value") if t.get("kb", True) else None
    program = t.get("program") or conf.get("program")
    return (package or None), (program or None), str(t.get("provenance") or "UNKNOWN")


def record_tool(record: dict[str, Any]) -> tuple[str | None, str]:
    """``(package program, provenance)`` of a record's resolution; (None, state) when it has none."""
    package, program, prov = record_parts(record)
    if not package or not program:
        return None, prov
    return f"{package} {program}", prov


def group_of(prov: str) -> str:
    if prov in KB_CONFIRMED:
        return "KB-confirmed"
    return "unknown" if prov == "UNKNOWN" else "model-only"


def compare(label: str, package: str | None, program: str | None) -> str:
    """agree / disagree for a set label (the label forms in the module docstring)."""
    words = _norm(label).split()
    if words == ["unknown"]:
        return "agree" if not package else "disagree"
    if len(words) == 1:
        same = bool(package) and _norm(package or "") == words[0]
        return "agree" if same and not program else "disagree"
    if not package or not program:
        return "disagree"  # the label names a tool; the record resolves none
    return "agree" if _norm(f"{package} {program}") == _norm(label) else "disagree"


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def score(
    labels: dict[str, str | None], records: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    rows = []
    for pid, label in sorted(labels.items()):
        rec = records.get(pid)
        if rec is None:
            rows.append(
                {
                    "paper": pid,
                    "outcome": "no record",
                    "group": "",
                    "label": label or "",
                    "record": "",
                }
            )
            continue
        package, program, prov = record_parts(rec)
        tool = " ".join(x for x in (package, program) if x) or None
        group = group_of(prov)
        if prov == "no resolution":
            outcome, group = "no resolution", ""
        elif label is None:
            outcome = "label blank"
        else:
            outcome = compare(label, package, program)
        rows.append(
            {
                "paper": pid,
                "outcome": outcome,
                "group": group,
                "label": label or "",
                "record": tool or "",
                "provenance": prov,
            }
        )
    return rows


def render(rows: list[dict[str, str]], results_dir: str) -> str:
    lines = [
        "# Motion correction: the resolved tool against the labels' resolved_tool",
        "",
        f"Records: `{results_dir}`. Labels: `ground_truth/motion_correction_labels_v1.xlsx` (resolved_tool, "
        "filled by code where the label names a program or package). Counts only; no rates.",
        "",
        "| paper | outcome | provenance group | label | record |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        held = r["paper"] in HELD_OUT
        lines.append(
            f"| {r['paper']} | {r['outcome']} | {r['group']} | "
            f"{'(held out)' if held and r['label'] else r['label']} | {'(held out)' if held and r['record'] else r['record']} |"
        )
    c = Counter((r["group"], r["outcome"]) for r in rows)
    lines += ["", "| group | agree | disagree | label blank |", "|---|---|---|---|"]
    for g in ("KB-confirmed", "model-only", "unknown"):
        lines.append(
            f"| {g} | {c[(g, 'agree')]} | {c[(g, 'disagree')]} | {c[(g, 'label blank')]} |"
        )
    other = {
        k: v
        for k, v in Counter(r["outcome"] for r in rows).items()
        if k in ("no record", "no resolution")
    }
    if other:
        lines.append(f"\nNot scored: {', '.join(f'{k} {v}' for k, v in other.items())}.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--labels", type=Path, default=LABELS)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    records = {
        f.stem: json.loads(f.read_text())
        for f in sorted((args.results_dir / "papers").glob("*.json"))
    }
    text = render(score(load_labels(args.labels), records), str(args.results_dir))
    if args.out:
        args.out.write_text(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

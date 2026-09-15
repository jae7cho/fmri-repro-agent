#!/usr/bin/env python3
"""Corpus tallies for target_space, written to a FILE so no number is hand-transcribed.

Usage (from extractor_mvp/):
    python tally_target_space.py --out ../ground_truth/target_space_tally.md
    python tally_target_space.py --vintage v050          # stdout, one vintage

Three things this emits that report-only scoring did not.

**1. The label distribution, regenerated.** `TRACK_A_SCOPE.md` recorded that no committed code
tallies `target_space_state` and that the published volumetric distribution existed "only as
inline prose" in the protocol and DEVLOG. It is computed here from the CSV.

**2. Per-label state counts — the reason this file exists.** The headline totals are INVARIANT
across the two prediction vintages: both score 11 correct / 8 error over 19 and both partition
5 / 2 / 1, while the blind rate moves six points. Anyone checking "did anything change?" against
the totals sees nothing, because braun went correct->error and mueller error->correct and they
cancel. A per-label breakdown does not cancel: it shows `deferred` losing its one correct grade
and `study_specific` gaining one, which is what actually happened.

**3. Every rate with its vintage on its face**, per the same TRACK_A_SCOPE trap.

Reachable-only is not emitted, in any form. It is a post-hoc exclusion, retired from
`target_space_README.md`; the scorers keep printing it as a working diagnostic, labelled, and
this file is the publication-facing one.

**Two readers, one rule.** Everything goes through :func:`read_rows`, which strips `#` lines.
Both prediction CSVs carry provenance headers and a bare ``csv.DictReader`` parses those comment
lines as data — 32 rows instead of 19, no error raised. ``tests/test_tally_target_space.py``
asserts that no other ``csv.DictReader`` exists in this module, so adding an unstripped one fails
the suite rather than silently producing garbage.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from score_target_space import NON_BLIND, apply_map, load_member_tier, wilson

REPO = Path(__file__).resolve().parents[1]
GT = REPO / "ground_truth"

#: The 19-row derived CSV, NEVER target_space_labels_v1.xlsx. The workbook's Labels sheet holds
#: 22 data rows: the 19 real ones, two "(EXAMPLE)" rows duplicating oconnor and mueller, and a
#: legend row. Reading it would inflate canonical to 2 and study_specific to 3.
#: derive_target_space_csv.py:54-58 is what strips them.
LABELS = GT / "target_space_labels_v1.csv"

VINTAGES = {
    "v040_frozen": GT / "target_space_predictions_v040_frozen.csv",
    "v050": GT / "target_space_predictions_v050.csv",
}

VINTAGE_NOTE = {
    "v040_frozen": "frozen pre-0.5.0 output, translated into the v3 map's shape by reconstruct_struct",
    "v050": "real 0.5.0 extractor output, K=3, batch_v050_labelset draws 1/2/3",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    """THE reader. Strips `#` provenance headers; nothing else in this module opens a CSV.

    Omitting the strip does not raise — it yields ~32 rows of comment text parsed as data, which
    then tallies cleanly into nonsense. That is why the strip lives in one function with a test
    forbidding any other DictReader here, rather than being repeated at each call site and
    eventually forgotten at one of them.
    """
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(ln for ln in f if not ln.startswith("#")))


def load_labels() -> dict[str, str]:
    """The 19 ground-truth labels, with the XLSX trap asserted rather than trusted."""
    rows = read_rows(LABELS)
    labels = {r["paper_id"]: r["target_space_state"] for r in rows}
    if len(labels) != 19:
        raise SystemExit(f"expected 19 labels in {LABELS.name}, got {len(labels)}")
    leaked = sorted(p for p in labels if "EXAMPLE" in p.upper())
    if leaked:
        raise SystemExit(f"worked-example rows reached the labels: {leaked} — the XLSX was read")
    return labels


def graded_predictions(vintage: str) -> dict[str, str]:
    """Map paper_id -> graded state for one vintage.

    The two vintages are graded differently because the files are different artifacts. The v050
    CSV already carries `v3_grade`, computed and provenance-checked by its own generator, so it is
    read rather than recomputed. The frozen CSV carries raw extractor fields only, so the
    committed v3 map is applied to it here via score_target_space.apply_map.
    """
    rows = read_rows(VINTAGES[vintage])
    if vintage == "v050":
        return {r["paper_id"]: r["v3_grade"] for r in rows}
    member_tier = load_member_tier()
    return {
        r["paper_id"]: apply_map(
            r["extractor_status"],
            r["extractor_value"],
            r["failure_reason"],
            r["raw_diagnostic"],
            member_tier,
        )
        for r in rows
    }


def per_label_states(labels: dict[str, str], graded: dict[str, str]) -> dict[str, Counter[str]]:
    """For each ground-truth label, how the graded predictions fall across states."""
    out: dict[str, Counter[str]] = {}
    for paper, label in labels.items():
        out.setdefault(label, Counter())[graded[paper]] += 1
    return out


def blind_rate(
    labels: dict[str, str], graded: dict[str, str]
) -> tuple[int, int, float, float, float]:
    blind = [p for p in labels if p not in NON_BLIND]
    hits = [p for p in blind if graded[p] == labels[p]]
    return (len(hits), len(blind), *wilson(len(hits), len(blind)))


def _distribution_section(labels: dict[str, str]) -> list[str]:
    dist = Counter(labels.values())
    lines = [
        "## Label distribution (ground truth, vintage-independent)",
        "",
        f"Regenerated from `{LABELS.name}` — {len(labels)} papers. Vintage-independent: these are",
        "the labels, not predictions, and they do not move when the extractor does.",
        "",
        "| target_space_state | n |",
        "|---|---|",
    ]
    lines += [
        f"| {state} | {n} |" for state, n in sorted(dist.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    lines += [f"| **total** | **{sum(dist.values())}** |", ""]
    return lines


def _vintage_section(vintage: str, labels: dict[str, str]) -> list[str]:
    graded = graded_predictions(vintage)
    missing = sorted(set(labels) - set(graded))
    if missing:
        raise SystemExit(f"{vintage}: no prediction for {missing}")
    k, n, p, lo, hi = blind_rate(labels, graded)
    states = sorted({s for c in per_label_states(labels, graded).values() for s in c})
    matrix = per_label_states(labels, graded)

    lines = [
        f"## Vintage `{vintage}`",
        "",
        f"Source: `{VINTAGES[vintage].name}` — {VINTAGE_NOTE[vintage]}.",
        "",
        f"**Blind correct-rate: {k}/{n} = {p:.1%} [{lo:.0%}, {hi:.0%}]**, vintage `{vintage}`.",
        f"Denominator is the {len(labels)} scored papers minus the {len(NON_BLIND)} non-blind",
        f"({', '.join(sorted(NON_BLIND))}), who appear as worked-example rows as well as their own.",
        "",
        "### Per-label state counts",
        "",
        "Rows are ground-truth labels, columns are graded predictions; the diagonal is correct.",
        "This table is here because the totals are invariant across vintages and this is not.",
        "",
        "| label \\ graded | " + " | ".join(f"`{s}`" for s in states) + " | correct / n |",
        "|---" * (len(states) + 2) + "|",
    ]
    for label in sorted(matrix):
        row = matrix[label]
        total = sum(row.values())
        cells = " | ".join(str(row.get(s, 0)) if row.get(s, 0) else "·" for s in states)
        lines.append(f"| `{label}` | {cells} | {row.get(label, 0)} / {total} |")
    lines.append("")
    return lines


def render(vintages: list[str]) -> str:
    labels = load_labels()
    out = [
        "# target_space corpus tally",
        "",
        "GENERATED by `extractor_mvp/tally_target_space.py`. Do NOT hand-edit: a re-run rewrites",
        "this file, so anything added here is silently lost. Regenerate with",
        "`python tally_target_space.py --out <this file>` from `extractor_mvp/`.",
        "",
        f"Labels: `{LABELS.name}` (19 rows — the derived CSV, never the 22-data-row workbook).",
        "",
        "Reachable-only is not reported here in any form: it is a post-hoc exclusion, retired from",
        "`target_space_README.md`. The scorers still print it, labelled, as a working diagnostic.",
        "",
    ]
    out += _distribution_section(labels)
    for vintage in vintages:
        out += _vintage_section(vintage, labels)
    if len(vintages) > 1:
        out += _comparison_section(labels, vintages)
    return "\n".join(out).rstrip() + "\n"


def _comparison_section(labels: dict[str, str], vintages: list[str]) -> list[str]:
    graded = {v: graded_predictions(v) for v in vintages}
    lines = [
        "## What moved between vintages",
        "",
        "The totals do not answer this. Both vintages score the same number correct over the same",
        "19 papers; the papers are different ones.",
        "",
        "| paper | label | " + " | ".join(f"`{v}`" for v in vintages) + " |",
        "|---" * (len(vintages) + 2) + "|",
    ]
    moved = [
        p
        for p in sorted(labels)
        if len({graded[v][p] == labels[p] for v in vintages}) > 1
        or len({graded[v][p] for v in vintages}) > 1
    ]
    for paper in moved:
        cells = " | ".join(
            f"{graded[v][paper]} {'✓' if graded[v][paper] == labels[paper] else '✗'}"
            for v in vintages
        )
        blind = "" if paper in NON_BLIND else " (blind)"
        lines.append(f"| {paper}{blind} | `{labels[paper]}` | {cells} |")
    if not moved:
        lines.append("| — | — | " + " | ".join("—" for _ in vintages) + " |")
    lines += [
        "",
        f"{len(moved)} of {len(labels)} papers differ. Totals identical; the rate is not, because",
        "whether a mover is blind decides whether it reaches the denominator.",
        "",
    ]
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="tally_target_space",
        description="Corpus tallies for target_space, with per-label state counts and vintage labels.",
    )
    ap.add_argument(
        "--vintage",
        choices=[*VINTAGES, "both"],
        default="both",
        help="which prediction vintage to tally (default: both, side by side)",
    )
    ap.add_argument("--out", type=Path, help="write here instead of stdout; parents are created")
    args = ap.parse_args(argv)

    vintages = list(VINTAGES) if args.vintage == "both" else [args.vintage]
    # Rendered in full BEFORE any file is opened. open("w") truncates on entry, so a failure
    # raised mid-render would otherwise destroy the artifact it was regenerating — the bug that
    # cost the v050 CSV once already (score_v050_reextraction.py:229).
    text = render(vintages)

    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

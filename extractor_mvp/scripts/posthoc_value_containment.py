#!/usr/bin/env python3
"""A post-hoc value column beside the pre-registered row scorers (the author's ruling of 2026-11-24).

NOT pre-registered. Written 2026-11-24, after the stored records were scored, because exact matching
"as stated" scored correct values as disagreements (ladouceur_2023 coregistration: four values
right, none agreeing, against labels such as "bbregister (FreeSurfer v6.0.1)"). The pinned scorers
(``preproc_rows_scoring.py``, ``preproc_rows_scoring_v2.py`` and the per-sheet scripts) are imported
and never changed. Their state, part matching and "as stated" value results stand. This script adds
one column.

**contained:** a value the as-stated rule calls "disagree" agrees when one of the record's forms
(its verbatim words or its resolved member, normalized as the scorers normalize them: case, spaces,
"_" and "-") is a whole-word phrase of the label, or the label is a whole-word phrase of that form.
A list agrees when every record item does. Numbers, yes/no fields and forms shorter than three
characters keep the as-stated result. Every value it turns into an agreement is listed for review.

Rows of liu_2005, tang_2025 and wheaton_2004 are left out entirely (the standing held-out rule).
Counts only; no rates. No model calls.

Usage:
    uv run --with openpyxl python scripts/posthoc_value_containment.py --arm S=DIR --arm B=DIR [--out FILE]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import preproc_rows_scoring as base
import preproc_rows_scoring_v2 as v2

HELD_OUT = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})
MIN_FORM = 3


def _phrase_in(needle: str, hay: str) -> bool:
    return len(needle) >= MIN_FORM and bool(
        re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", hay)
    )


def _one_contained(label: str, item: Any) -> bool:
    lab = base._norm(label)
    return any(_phrase_in(f, lab) or _phrase_in(lab, f) for f in base._forms(item))


def contained(label: str, rec: Any) -> bool:
    """True when ``rec`` agrees with ``label`` by whole-word containment (module docstring)."""
    if isinstance(rec, tuple) and len(rec) == 2 and rec[0] == "any of":
        return any(contained(label, x) for x in rec[1])
    if isinstance(rec, bool | int | float) or rec in (None, "", []):
        return False
    if isinstance(rec, list | tuple):
        if all(isinstance(x, int | float) or x is None for x in rec):
            return False
        return all(_one_contained(label, x) for x in rec)
    return _one_contained(label, rec)


def _module(sheet: str) -> Any:
    return v2 if sheet in v2.VIEWS else base


def views_scored(sheet: str, results_dir: Path) -> list[tuple[base.RowLabel, Any, dict[str, str]]]:
    """(label row, the record view or part it was scored against, the as-stated value results) for
    every row the pinned scorer scored, held-out rows dropped."""
    mod = _module(sheet)
    labels = mod.load_labels(sheet)
    records = mod.load_records(results_dir, sheet)
    out = []
    by_paper: dict[str, list[base.RowLabel]] = {}
    for r in labels:
        by_paper.setdefault(r.paper_id, []).append(r)
    for s in mod.score(labels, records):
        r = s.row
        if r.paper_id in HELD_OUT or s.outcome != "scored":
            continue
        view = records[r.paper_id]
        if s.scope is None:
            target = view
        else:
            parts = list((view.streams or {}).values()) or [view]
            target = parts[s.scope.matches[by_paper[r.paper_id].index(r)]]
        out.append((r, target, s.values))
    return out


def run(arms: dict[str, Path]) -> str:
    sheets = [s for s in base.SHEETS if s != "software"] + [
        s for s in v2.VIEWS if s != "resting_state_feature"
    ]
    lines = [
        "# Post-hoc value column: whole-word containment (NOT pre-registered, 2026-11-24)",
        "",
        "Arms: " + ", ".join(f"`{n}` = `{d}`" for n, d in arms.items()),
        "Held-out papers left out. Counts only.",
        "",
        "| sheet | arm | as stated: agree | disagree | contained adds | agree with contained |",
        "|---|---|---|---|---|---|",
    ]
    added: list[str] = []
    totals: Counter[tuple[str, str]] = Counter()
    for sheet in sheets:
        for name, d in arms.items():
            c: Counter[str] = Counter()
            for r, target, results in views_scored(sheet, d):
                for f, outcome in results.items():
                    c[outcome] += 1
                    if outcome != "disagree":
                        continue
                    rec = target.values.get(f)
                    label = str(r.values.get(f) or "")
                    if contained(label, rec):
                        c["added"] += 1
                        added.append(
                            f"| {sheet} | {name} | {r.paper_id} | {r.applies_to} | {f} | "
                            f"{label} | {base._plain(rec) if not isinstance(rec, tuple) else rec} |"
                        )
            for k in ("agree", "disagree", "added"):
                totals[(name, k)] += c[k]
            lines.append(
                f"| {sheet} | {name} | {c['agree']} | {c['disagree']} | {c['added']} | "
                f"{c['agree'] + c['added']} |"
            )
    lines += ["", "Totals:", ""]
    for name in arms:
        a, dis, add = (totals[(name, k)] for k in ("agree", "disagree", "added"))
        lines.append(
            f"- {name}: as stated {a} agree / {dis} disagree; contained adds {add} "
            f"(agree {a + add}, disagree {dis - add})"
        )
    lines += [
        "",
        "## Every value the contained column turns into an agreement",
        "",
        "| sheet | arm | paper | applies_to | field | label | record |",
        "|---|---|---|---|---|---|---|",
        *added,
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--arm", action="append", required=True, help="NAME=DIR")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    arms = {}
    for a in args.arm:
        name, _, d = a.partition("=")
        if not name or not (Path(d) / "papers").is_dir():
            ap.error(f"--arm {a!r}: want NAME=DIR with DIR/papers/")
        arms[name] = Path(d)
    text = run(arms)
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

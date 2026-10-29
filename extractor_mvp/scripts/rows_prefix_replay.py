"""Replay item 6 (the author's order of 2026-10-28) over the stored coverage_v1 reports. No model
calls, no text printed: re-render each stored record with the current renderer and compare its
``### Rows`` lines with the stored report's -- a row whose line changed is one the kind prefix moved.
Contaminated papers are listed by paper and row; the three held-out papers are counts only.

Usage:
    python scripts/rows_prefix_replay.py [results/batch_coverage_v1]
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from types import SimpleNamespace

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))
sys.path.insert(0, str(_HERE.parent.parent / "src"))

from fmri_repro.spec.migrations import parse_any_version  # noqa: E402

from extractor_mvp.methods_finder import MethodsSlice  # noqa: E402
from extractor_mvp.render import to_report  # noqa: E402

_HELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})


def _rows_lines(report: str) -> dict[str, str]:
    out: dict[str, str] = {}
    section = report.split("### Rows", 1)
    if len(section) < 2:
        return out
    for line in section[1].splitlines()[1:]:
        if not line.startswith("- "):
            break
        aspect = line[2:].split(" [", 1)[0]
        out[aspect] = line
    return out


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    results = Path(args[0]) if args else _HERE.parent / "results" / "batch_coverage_v1"
    changed: list[tuple[str, str]] = []
    held_changed = collections.Counter()
    same = 0
    other_lines_changed: list[str] = []
    for f in sorted((results / "papers").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        pid = d["paper_id"]
        stored = (results / "papers" / f"{pid}.md").read_text(encoding="utf-8")
        methods = MethodsSlice(text="", **d["methods"])
        prep = parse_any_version(d["preprocessing"])
        # the motion inference record travels as a side channel of the stored JSON (batch.py);
        # the renderer reads it by attribute, so the dict is wrapped
        record = d.get("motion_inference")
        motion = SimpleNamespace(**record) if isinstance(record, dict) else None
        new = to_report(prep, source=pid, methods_slice=methods, motion_inference=motion)
        old_rows, new_rows = _rows_lines(stored), _rows_lines(new)
        for aspect, line in new_rows.items():
            if old_rows.get(aspect) == line:
                same += 1
            elif pid in _HELD:
                held_changed[aspect] += 1
            else:
                changed.append((pid, aspect))
        # everything outside the Rows section must be byte-identical
        if stored.split("### Rows")[0] != new.split("### Rows")[0]:
            other_lines_changed.append(pid if pid not in _HELD else "held-out")
    print(f"== Rows lines unchanged: {same}")
    print(f"== Rows lines changed on the contaminated papers (paper, row): {len(changed)}")
    for row in changed:
        print("  ", *row)
    print("== changed on the held-out three, counts by row:", dict(held_changed) or 0)
    print("== papers whose report changed OUTSIDE the Rows section:", other_lines_changed or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

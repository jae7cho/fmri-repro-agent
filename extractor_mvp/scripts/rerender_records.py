#!/usr/bin/env python3
"""Re-render stored records with the current code, no model call (Stage 2c, 2026-11-11).

Copies each ``<results-dir>/papers/<id>.json`` to ``<out>/papers/<id>.json`` with its
``part_joins`` entry recomputed (part_names.record_entry, the entry batch.py now writes), and writes
``<out>/<id>.md`` (full_report.render_record) and ``<out>/<id>.preproc.txt``
(pseudocode.render_pseudocode). Never writes into ``<results-dir>``: the stored draw stays as it was
read, so the two directories diff.

    extractor_mvp/.venv/bin/python extractor_mvp/scripts/rerender_records.py \\
        --results-dir extractor_mvp/results/applies_to_v2 --out extractor_mvp/results/applies_to_v2c
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def rerender(src: Path, out: Path, papers: list[str] | None = None) -> list[str]:
    from fmri_repro.spec.migrations import parse_any_version

    from extractor_mvp.full_report import render_record
    from extractor_mvp.part_names import record_entry
    from extractor_mvp.pseudocode import render_pseudocode
    from extractor_mvp.render import flatten

    if out.resolve() == src.resolve():
        raise SystemExit("--out must differ from --results-dir")
    (out / "papers").mkdir(parents=True, exist_ok=True)
    done = []
    for f in sorted((src / "papers").glob("*.json")):
        if papers and f.stem not in papers:
            continue
        record = json.loads(f.read_text(encoding="utf-8"))
        if "preprocessing" in record:
            prep = parse_any_version(record["preprocessing"])
            record["part_joins"] = record_entry(flatten(prep), prep)
        (out / "papers" / f.name).write_text(
            json.dumps(record, indent=1, default=str), encoding="utf-8"
        )
        (out / f"{f.stem}.md").write_text(render_record(record), encoding="utf-8")
        code = render_pseudocode(record)
        if code is not None:
            (out / f"{f.stem}.preproc.txt").write_text(code, encoding="utf-8")
        done.append(f.stem)
    return done


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--results-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--paper", action="append", help="only these paper ids (repeatable)")
    args = ap.parse_args(argv)
    for pid in rerender(args.results_dir, args.out, args.paper):
        print(f"rendered {pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Re-check and re-render stored records with the 2026-11-09 rules, no model call (items 2 and 3).

For each record in ``--in`` (a results folder with ``papers/<id>.json``): the paper's text is read
again (``batch.load_text`` + ``reflow_one_word_lines``; the record's ``text_source`` must match, else
the record is copied unchanged and said so), ``rechecks.recheck_record`` re-runs the value check and
the span resolver on every quote-failed field, and the report is re-rendered
(``full_report.render_record``, which adds checker-supplied values). Writes ``--out/papers/<id>.json``
and ``--out/<id>.md`` and prints, per record, the unverifiable field counts before and after.
Counts only: no values or quotes are printed.

    uv run python scripts/recheck_records.py --in results/corpus_full_v1 --out results/corpus_full_v1_rechecked
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from extractor_mvp.batch import load_text
from extractor_mvp.full_report import render_record
from extractor_mvp.pdf_loader import reflow_one_word_lines
from extractor_mvp.rechecks import (
    _fields,
    _unverifiable_reason,
    checker_supplied,
    recheck_record,
    unverifiable_fields,
)


def before_count(record: dict) -> int:
    """The stored count: every MISSING field with an unverifiable reason (no checker-supplied rule)."""
    return sum(_unverifiable_reason(pf) is not None for _p, pf in _fields(record))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in", dest="src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists() and any(args.out.iterdir()):
        print(f"refusing to write into a non-empty folder: {args.out}", file=sys.stderr)
        return 2
    (args.out / "papers").mkdir(parents=True, exist_ok=True)
    rows = []
    for f in sorted((args.src / "papers").glob("*.json")):
        rec = json.loads(f.read_text())
        pid = rec["paper_id"]
        row = {"paper": pid, "status": rec.get("status")}
        if "preprocessing" not in rec:
            new, note = rec, "no extraction (copied)"
        else:
            text, _parser, source = load_text(Path(rec["path"]))
            stored = (rec.get("text_source") or {}).get("text_source")
            if source.get("text_source") != stored:
                new, note = (
                    rec,
                    f"text source now {source.get('text_source')}, stored {stored} (copied)",
                )
            else:
                text, _ = reflow_one_word_lines(text)
                new, summary = recheck_record(rec, text)
                note = (
                    f"rechecked {len(summary['rechecked'])}, now extracted "
                    f"{len(summary['now_extracted'])}"
                )
            row.update(
                before=before_count(rec),
                after_rechecks=before_count(new),
                checker_supplied=len(checker_supplied(new)),
                after=len(unverifiable_fields(new)),
            )
        row["note"] = note
        (args.out / "papers" / f"{pid}.json").write_text(json.dumps(new, indent=2))
        (args.out / f"{pid}.md").write_text(render_record(new))
        rows.append(row)
        print(
            "\t".join(
                str(row.get(k, ""))
                for k in (
                    "paper",
                    "status",
                    "before",
                    "after_rechecks",
                    "checker_supplied",
                    "after",
                    "note",
                )
            ),
            flush=True,
        )
    (args.out / "recheck_summary.json").write_text(json.dumps(rows, indent=2))
    t = {
        k: sum(r.get(k, 0) for r in rows)
        for k in ("before", "after_rechecks", "checker_supplied", "after")
    }
    print(f"TOTAL\t{len(rows)} records\t" + "\t".join(f"{k} {v}" for k, v in t.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

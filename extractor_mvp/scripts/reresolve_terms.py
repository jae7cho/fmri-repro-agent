#!/usr/bin/env python3
"""Re-resolve the vocabulary terms of stored records with the current resolver, no model call
(2026-11-24, the resolver audit).

A stored record keeps the member its term was resolved to when it was extracted. After a resolver
change (the whole-word alias rule, the field rules in ``coverage_fields.TERM_RULES``) the stored
member and the current code disagree. For every coverage-call term field (single terms and term
lists, extracted or varied), this re-runs ``extractor._resolve_term`` on the stored paper's words
and writes the record, otherwise unchanged, to ``--out``. The paper's words are never changed;
only ``resolved`` and ``resolution`` are. A term stored as ``other`` is left as stored (its
"other (phrase)" wrapper is not in the record). Never writes into ``--in``.

Prints counts of changed values per field. Counts only: no values or quotes.

    uv run python scripts/reresolve_terms.py --in results/arms_2026-11-15/B --out results/arms_2026-11-15/B_reresolved
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extractor_mvp.coverage_fields import COVERAGE_SPECS
from extractor_mvp.extractor import _resolve_term

TERM_SPECS = {
    (s.kind, s.field_id): s for s in COVERAGE_SPECS if s.value_kind in ("term", "term_list")
}


def _reresolve_value(value: Any, spec: Any) -> tuple[Any, int]:
    """The value with every term re-resolved, and how many terms changed."""
    syn = (spec.synonyms, spec.underspecified) if spec.synonyms else None
    items = value if isinstance(value, list) else [value]
    changed = 0
    out = []
    for it in items:
        if not isinstance(it, dict) or "verbatim" not in it or it.get("resolved") == "other":
            # "other (phrase)" was stored as resolved other with only the phrase kept; the phrase
            # alone cannot show the resolver that the model said "other", so it is left as stored.
            out.append(it)
            continue
        t = _resolve_term(str(it["verbatim"]), spec.literal_type, syn, spec.dotted)
        new = {**it, "resolved": t.resolved, "resolution": t.resolution}
        changed += (new["resolved"], new["resolution"]) != (
            it.get("resolved"),
            it.get("resolution"),
        )
        out.append(new)
    return (out if isinstance(value, list) else out[0]), changed


def reresolve_record(record: dict[str, Any]) -> Counter[str]:
    """Re-resolve one record in place; the per-field counts of changed terms."""
    counts: Counter[str] = Counter()
    holder = record if "preprocessing" in record else record.get("extraction_json") or {}
    prep = holder.get("preprocessing") or {}
    for step in prep.get("steps") or []:
        kind = step.get("kind")
        for field_id, pf in step.items():
            spec = TERM_SPECS.get((kind, field_id))
            if spec is None or not isinstance(pf, dict):
                continue
            ext = pf.get("extraction") or {}
            if ext.get("status") == "EXTRACTED" and ext.get("value") is not None:
                ext["value"], n = _reresolve_value(ext["value"], spec)
                counts[spec.dotted] += n
            for var in ext.get("variants") or []:
                if var.get("value") is not None:
                    var["value"], n = _reresolve_value(var["value"], spec)
                    counts[spec.dotted] += n
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--in", dest="src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.resolve() == args.src.resolve():
        raise SystemExit("--out must differ from --in")
    (args.out / "papers").mkdir(parents=True, exist_ok=True)
    total: Counter[str] = Counter()
    n = 0
    for f in sorted((args.src / "papers").glob("*.json")):
        record = json.loads(f.read_text(encoding="utf-8"))
        total.update(reresolve_record(record))
        (args.out / "papers" / f.name).write_text(
            json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        n += 1
    print(f"{n} records re-resolved into {args.out}")
    for field, c in sorted(total.items()):
        if c:
            print(f"  {field}: {c} terms changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

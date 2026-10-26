#!/usr/bin/env python3
"""Read-only survey: would the base_pipeline value-support guard pass the seven step fields?

Runs ``span_resolver.quote_supports_value`` over every EXTRACTED value of the seven ``_FIELD_SPECS``
fields in a stored batch (the 19 ``results/<batch>/papers/*.json``), comparing the model's OWN raw
value (from the stored ``resolutions`` record, falling back to the SpecifiedTerm's ``verbatim`` or
the number as written) against the resolved span's text. No model calls. Nothing is written.

**Prints no quote text and no value text** -- paper, field, span offsets, verdict and, for a
failure, a classification:

* ``synonym_in_quote``   the value is a resolver synonym/canonical form and an alias of the same
                         canonical value (``synonym_resolver.SYNONYMS_BY_FIELD``) IS in the quote
* ``number_form``        a numeric field whose number is in the quote in another surface form
* ``absent``             nothing of the value's family is in the quote

For the held-out papers (liu_2005, tang_2025, wheaton_2004 -- prereg C11/C26) only pass/fail
COUNTS are printed, never a field, an offset or a classification.

Usage:
    python scripts/value_support_survey.py --results-dir results/batch_a1_acceptance
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from extractor_mvp.extractor import _FIELD_SPECS
from extractor_mvp.span_resolver import quote_supports_value
from extractor_mvp.synonym_resolver import SYNONYMS_BY_FIELD

_HELD_OUT = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})


def _num_in(value: str, quote: str) -> bool:
    try:
        x = float(value)
    except ValueError:
        return False
    for tok in re.findall(r"\d+(?:\.\d+)?", quote):
        try:
            if abs(float(tok) - x) < 1e-9:
                return True
        except ValueError:
            continue
    return False


def _synonym_in(field_id: str, resolved: object, quote: str) -> bool:
    entry = SYNONYMS_BY_FIELD.get(field_id)
    if not entry or resolved is None:
        return False
    table = entry[0]
    for alias in table.get(str(resolved), []):
        if quote_supports_value(alias, quote):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--results-dir", required=True, type=Path)
    args = ap.parse_args(argv)
    papers_dir = args.results_dir / "papers"
    specs = {dotted: (field_id, lit) for (_attr, field_id, dotted, lit, _t) in _FIELD_SPECS}

    per_field: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    held: collections.Counter = collections.Counter()
    failures: list[tuple[str, str, int, int, str]] = []
    n_papers = 0
    for f in sorted(papers_dir.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        pid = d["paper_id"]
        n_papers += 1
        raw_by_field = {r["field"]: r for r in d.get("resolutions", [])}
        for step in d["preprocessing"]["steps"]:
            for dotted, (field_id, _lit) in specs.items():
                kind, fname = dotted.split(".", 1)
                if step["kind"] != kind or fname not in step:
                    continue
                ex = step[fname]["extraction"]
                if ex.get("status") != "EXTRACTED":
                    continue
                span = ex["spans"][0]
                quote = span["text"]
                res = raw_by_field.get(dotted)
                val = ex["value"]
                if res is not None and res.get("raw_value") is not None:
                    value = str(res["raw_value"])
                elif isinstance(val, dict) and "verbatim" in val:
                    value = str(val["verbatim"])
                else:
                    value = str(val)
                resolved = val.get("resolved") if isinstance(val, dict) else val
                ok = quote_supports_value(value, quote)
                if pid in _HELD_OUT:
                    held["pass" if ok else "fail"] += 1
                    continue
                per_field[dotted]["pass" if ok else "fail"] += 1
                if not ok:
                    if _synonym_in(field_id, resolved, quote):
                        cls = "synonym_in_quote"
                    elif _num_in(value, quote):
                        cls = "number_form"
                    else:
                        cls = "absent"
                    failures.append((pid, dotted, span["start"], span["end"], cls))

    print(f"papers: {n_papers} (held-out counted but not listed: {sorted(_HELD_OUT)})")
    print(
        "\n== per field, the 16 non-held-out papers: EXTRACTED values the guard would pass / fail"
    )
    for dotted in specs:
        c = per_field.get(dotted, collections.Counter())
        print(f"   {dotted:42s} pass {c['pass']:2d}   fail {c['fail']:2d}")
    print("\n== failures (paper, field, span offsets, class) -- no quote text")
    for pid, dotted, a, b, cls in failures:
        print(f"   {pid:15s} {dotted:42s} {a}-{b}  {cls}")
    print(f"\n== held-out papers, counts only: pass {held['pass']}, fail {held['fail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

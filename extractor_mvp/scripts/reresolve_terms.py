#!/usr/bin/env python3
"""Re-resolve the vocabulary terms of stored records with the current resolver, no model call
(2026-11-24, the resolver audit; widened by D2b, 2026-11-25).

A stored record keeps the member its term was resolved to when it was extracted. After a resolver
change (the whole-word alias rule, the field rules in ``coverage_fields.TERM_RULES``, the longer
alias winning) the stored member and the current code disagree. For every vocabulary field (the 35
coverage fields and, since D2b, the 4 fields of the shared call; single terms and term lists,
extracted or varied), this re-runs the resolver on the stored paper's words and writes the record,
otherwise unchanged, to ``--out``. The paper's words are never changed; only ``resolved`` and
``resolution`` are. A term stored as ``other`` is left as stored (its "other (phrase)" wrapper is
not in the record). Never writes into ``--in``.

A list is re-resolved as ``extractor._resolve_term_list`` resolves it: each stored item alone,
then a coordination that shares its head noun ("white" beside "gray matter"). The stored items are
NOT split again: a list the older splitter cut ("blip-up/blip-down" stored as two items, "FD > 0,5
mm" as "FD > 0" and "5 mm") stays cut, so the splitter fixes of D2b show only in new extractions.

Prints counts of changed terms per field, over the papers that are not held out. ``--show`` also
lists each changed term (paper, field, the paper's words, member before and after). Held-out
papers get one total: no field of theirs is printed, in the counts or in the list.

The detrend field is re-resolved as the extractor resolves it: ``_resolve_term``, then the
highest order its quote names (coverage_extractor's rule of 2026-10-28), for a value the coverage
call extracted. A part of a varied value and a value the checking pass supplied do not go through
that rule in the extractor, and do not here. Until D2b this script re-ran only ``_resolve_term``
and wrote such a value back unresolved.

    uv run python scripts/reresolve_terms.py --in results/arms_2026-11-15/B --out results/arms_2026-11-15/B_reresolved --show
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import term_audit as ta

#: (step kind, field id) -> the vocabulary field. Kept under its 2026-11-24 name.
TERM_SPECS = ta.vocabulary()
#: (dotted field, the paper's words, member before, member after)
Change = tuple[str, str, str | None, str | None]


def _reresolve_value(
    value: Any, field: ta.Field, context: float | None, rule_quote: str | None = None
) -> tuple[Any, list[Change]]:
    """The value with every term re-resolved, and the terms that changed. ``rule_quote``: see
    ``term_audit.resolve`` (the detrend field's highest-order rule reads the quote)."""
    items = value if isinstance(value, list) else [value]
    # "other (phrase)" was stored as resolved other with only the phrase kept; the phrase alone
    # cannot show the resolver that the model said "other", so it is left as stored.
    # kept as stored: "other" (the model's own statement), and a member that is the model's
    # reading of the term (``model_mapped``, schema 0.8.0), also where today's table gives the
    # words a member: the audit lists that disagreement, and what to do with it is not this
    # script's to decide. A term marked model_mapped that holds no member is an unresolved term
    # like any other, here and in the audit.
    kept = [
        not isinstance(it, dict)
        or "verbatim" not in it
        or it.get("resolved") == "other"
        or (it.get("resolution") == "model_mapped" and it.get("resolved") is not None)
        for it in items
    ]
    words = [
        str(it["verbatim"]) if isinstance(it, dict) and "verbatim" in it else "" for it in items
    ]
    if context is None and field.shared and isinstance(items[0], dict):
        context = ta.gated_value(field, items[0].get("resolved"))
    now = ta.resolve(field, words, context, rule_quote)
    changes: list[Change] = []
    out = []
    for it, keep, word, (member, resolution) in zip(items, kept, words, now, strict=True):
        if keep:
            out.append(it)
            continue
        new = {**it, "resolved": member, "resolution": resolution}
        if (new["resolved"], new["resolution"]) != (it.get("resolved"), it.get("resolution")):
            changes.append((field.dotted, word, it.get("resolved"), member))
        out.append(new)
    return (out if isinstance(value, list) else out[0]), changes


def reresolve_record(record: dict[str, Any], changes: list[Change] | None = None) -> Counter[str]:
    """Re-resolve one record in place; the per-field counts of changed terms. ``changes``, when
    given, receives each changed term."""
    counts: Counter[str] = Counter()
    holder = record if "preprocessing" in record else record.get("extraction_json") or {}
    prep = holder.get("preprocessing") or {}
    for step in prep.get("steps") or []:
        kind = step.get("kind")
        context = None
        if kind == "intensity_normalization":
            number = ((step.get("value") or {}).get("extraction") or {}).get("value")
            context = float(number) if isinstance(number, (int, float)) else None
        for field_id, pf in step.items():
            field = TERM_SPECS.get((kind, field_id))
            if field is None or not isinstance(pf, dict):
                continue
            ext = pf.get("extraction") or {}
            # each holder of a value with the quote the detrend rule reads: the extraction's own
            # spans as the extractor joins them; none for a part of a varied value, and none for a
            # value the checking pass supplied, which the extractor promotes after the rule has run
            holders: list[tuple[dict[str, Any], str | None]] = []
            if ext.get("status") == "EXTRACTED":
                quote = " ".join(str(s.get("text", "")) for s in ext.get("spans") or [])
                holders.append((ext, None if ext.get("checker_supplied") else quote))
            holders += [(v, None) for v in ext.get("variants") or [] if isinstance(v, dict)]
            for h, rule_quote in holders:
                if h.get("value") is None:
                    continue
                h["value"], changed = _reresolve_value(h["value"], field, context, rule_quote)
                counts[field.dotted] += len(changed)
                if changes is not None:
                    changes.extend(changed)
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--in", dest="src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--show", action="store_true", help="list each changed term (not held-out)")
    args = ap.parse_args(argv)
    if args.out.resolve() == args.src.resolve():
        raise SystemExit("--out must differ from --in")
    (args.out / "papers").mkdir(parents=True, exist_ok=True)
    total: Counter[str] = Counter()
    shown: list[tuple[str, Change]] = []
    held_out = 0
    n = 0
    for f in sorted((args.src / "papers").glob("*.json")):
        record = json.loads(f.read_text(encoding="utf-8"))
        changes: list[Change] = []
        counts = reresolve_record(record, changes)
        if ta.is_held_out(f.stem):
            held_out += len(changes)  # one number: no field of a held-out paper is printed
        else:
            total.update(counts)
            shown += [(f.stem, c) for c in changes]
        (args.out / "papers" / f.name).write_text(
            json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        n += 1
    print(f"{n} records re-resolved into {args.out}")
    for field, c in sorted(total.items()):
        if c:
            print(f"  {field}: {c} terms changed")
    if args.show:
        for paper, (dotted, words, before, after) in shown:
            print(f"  {paper} | {dotted} | {words!r}: {before} -> {after}")
    print(f"  held-out papers: {held_out} terms changed (counted, never listed by field)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

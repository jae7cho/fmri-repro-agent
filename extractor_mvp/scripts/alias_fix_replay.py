"""Replay item 3 (the author's order of 2026-10-28) over the stored records. No model calls.

Two checks, on every EXTRACTED term field whose value is a ``SpecifiedTerm`` with a verbatim:

* re-resolve the verbatim under the current alias tables and matcher (the coverage fields through
  their own dotted-id tables, the seven shared fields through ``SYNONYMS_BY_FIELD``) and compare with
  the stored ``resolved`` -- a difference is a cell that MOVES; the count of unchanged cells is the
  "nothing resolved before changes" line;
* for ``nuisance_regression.detrend``, the highest order the located quote names against the stored
  resolved member -- a higher named order is a cell the new rule MOVES.

**Prints no quote text.** Contaminated papers are listed by paper and field with old -> new; the
three held-out papers are counts only.

Usage:
    python scripts/alias_fix_replay.py
"""

from __future__ import annotations

import collections
import json
import sys
import typing
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))

from extractor_mvp.coverage_extractor import _DETREND_ORDER  # noqa: E402
from extractor_mvp.coverage_fields import COVERAGE_SPECS, DETREND  # noqa: E402
from extractor_mvp.extractor import _FIELD_SPECS  # noqa: E402
from extractor_mvp.quote_support import phrase_in_quote  # noqa: E402
from extractor_mvp.synonym_resolver import SYNONYMS_BY_FIELD, resolve_to_literal  # noqa: E402

_RESULTS = _HERE.parent / "results"
_HELD = frozenset({"liu_2005", "tang_2025", "wheaton_2004"})
_VINTAGES = (
    "batch_a1_acceptance",
    "batch_motion_corpus_v1",
    "batch_motion_corpus_v1_inferred",
    "batch_coverage_v1",
)
_SPEC_BY_DOTTED = {s.dotted: s for s in COVERAGE_SPECS}


_SHARED_LITERAL = {field_id: literal for _a, field_id, _d, literal, _t in _FIELD_SPECS}


def _re_resolve(
    dotted: str, field_id: str, verbatim: str, value_context: float | None
) -> str | None:
    """Mirror the production resolution: the field's alias table first, then exact membership
    of the Literal (extractor._resolve_term / _process_field), with the intensity convention's
    sibling value as context."""
    spec = _SPEC_BY_DOTTED.get(dotted)
    if spec is not None and spec.synonyms is not None:
        res = resolve_to_literal(verbatim, spec.synonyms, spec.underspecified, None)
        if res.status == "resolved":
            return res.resolved
        return verbatim if verbatim in typing.get_args(spec.literal_type) else None
    entry = SYNONYMS_BY_FIELD.get(field_id)
    literal = _SHARED_LITERAL.get(field_id)
    if entry is not None:
        syns, under = entry
        res = resolve_to_literal(verbatim, syns, under, value_context)
        if res.status == "resolved":
            return res.resolved
        return verbatim if literal is not None and verbatim in typing.get_args(literal) else None
    if literal is not None:
        return verbatim if verbatim in typing.get_args(literal) else None
    return "(no table)"


def main() -> int:
    unchanged = collections.Counter()
    moves: list[tuple[str, str, str, str, str]] = []
    held_moves = collections.Counter()
    detrend_moves: list[tuple[str, str, str, str]] = []
    held_detrend = 0
    for vint in _VINTAGES:
        papers = _RESULTS / vint / "papers"
        if not papers.is_dir():
            continue
        for f in sorted(papers.glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            pid = d["paper_id"]
            for step in d["preprocessing"].get("steps", []):
                kind = step.get("kind")
                context: float | None = None
                if kind == "intensity_normalization":
                    v_ext = (step.get("value") or {}).get("extraction") or {}
                    if v_ext.get("status") == "EXTRACTED":
                        context = float(v_ext["value"])
                for name, value in step.items():
                    if not isinstance(value, dict):
                        continue
                    ext = value.get("extraction")
                    if not isinstance(ext, dict) or ext.get("status") != "EXTRACTED":
                        continue
                    val = ext.get("value")
                    items = val if isinstance(val, list) else [val]
                    dotted = f"{kind}.{name}"
                    for item in items:
                        if not isinstance(item, dict) or "verbatim" not in item:
                            continue
                        verbatim = item.get("verbatim")
                        if verbatim is None:
                            continue
                        new = _re_resolve(dotted, name, str(verbatim), context)
                        if new == "(no table)":
                            continue
                        old = item.get("resolved")
                        if new == old:
                            unchanged[vint] += 1
                        elif pid in _HELD:
                            held_moves[vint] += 1
                        else:
                            moves.append((vint, pid, dotted, str(old), str(new)))
                    if dotted == "nuisance_regression.detrend" and isinstance(val, dict):
                        quote = ext["spans"][0]["text"]
                        named = [
                            m
                            for m in _DETREND_ORDER
                            if any(phrase_in_quote(a, quote) for a in DETREND.get(m, ()))
                        ]
                        if named:
                            highest = max(named, key=_DETREND_ORDER.index)
                            cur = val.get("resolved")
                            if cur is None or _DETREND_ORDER.index(cur) < _DETREND_ORDER.index(
                                highest
                            ):
                                if pid in _HELD:
                                    held_detrend += 1
                                else:
                                    detrend_moves.append((vint, pid, str(cur), highest))
    print("== term cells re-resolved to the SAME member, per vintage")
    for k, v in sorted(unchanged.items()):
        print(f"  {k:<36} {v}")
    print(f"== term cells whose resolution MOVES (contaminated, listed): {len(moves)}")
    for row in moves:
        print("  ", *row)
    print("== the same on the held-out three, counts only:", dict(held_moves) or 0)
    print(f"== detrend cells the highest-order rule MOVES (contaminated): {len(detrend_moves)}")
    for row in detrend_moves:
        print("  ", *row)
    print("== the same on the held-out three, count only:", held_detrend)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

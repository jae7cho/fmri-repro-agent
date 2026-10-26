#!/usr/bin/env python
"""Predict, per paper/field, whether a one-character glyph wildcard would recover a failed quote.

**This script prints BOOLEANS ONLY. It never prints, logs or returns paper text, a model quote,
a span, an offset or a character.** That is not a style choice: the only cell whose prediction is
wanted lives in ``liu_2005``, which prereg C11/C26 holds out, and deriving the prediction requires
reading its text while the operator must not see it. Every output line is ``key: True`` or
``key: False``. If you extend this script, keep it that way.

What it answers, for one (paper, field) pair whose stored diagnostic is a quote-resolution failure:

  quote_located_in_store            the stored diagnostic carries a quote to test at all
  text_carries_glyph_leak           the source text contains a ``/C<digit>`` run
  quote_crosses_leak                the quote's longest matching prefix ends at a leak -- i.e.
                                    the leak is what breaks the match, not something else
  recovered_by_one_char_wildcard    THE PREDICTION: the quote matches when each ``/C<digit>`` run
                                    in the SOURCE is allowed to stand for exactly one character of
                                    the quote, and nothing else is relaxed

``recovered_by_one_char_wildcard`` implements the rule proposed in
``docs/design/DELTA_glyph_leak_span_recovery.md`` §1, composed with tier 5's whitespace-deletion
tolerance (both sides are whitespace-stripped first, because the same clause is mangled twice --
see that DELTA §4a). It asserts no glyph identity: a leak stands for *one character*, never for a
*named* character.

Usage:
    python scripts/glyph_leak_prediction.py --paper liu_2005 --field resolution_mm
    python scripts/glyph_leak_prediction.py --paper agtzidis_2020 --field resolution_mm   # control
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_RESULTS = Path(__file__).resolve().parents[1] / "results"
_LEAK = re.compile(r"/C\d+")

#: Papers whose text does not come from a corpus PDF. liu_2005 is fed the de-interleaved slice
#: directly (scripts/run_pending_target_space.py:31), so a prediction for it must read the same
#: input the extraction read, or it predicts the wrong thing.
_TEXT_OVERRIDE = {"liu_2005": _REPO / "ground_truth" / "liu_2005_deinterleaved_methods.txt"}

_CORPUS = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch")
_PDF = {
    "agtzidis_2020": "Agtzidis_2020.pdf",
    "poldrack_2015": "Poldrack_2015.pdf",
    "chen_2015": "Chen_2015.pdf",
}


#: Stands in for one leaked glyph while matching. Chosen because it cannot occur in PDF-extracted
#: text or a model quote, so it can never collide with real content.
_HOLE = "\x00"


def _strip_ws(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _mark_leaks(text: str) -> str:
    r"""Replace each ``/C<digit>`` run with a single-character hole, BEFORE whitespace is stripped.

    Order matters and a positive control caught it. Stripping whitespace first merges a leak with
    whatever follows it: ``"3 /C2 3"`` becomes ``"3/C23"``, where a greedy ``\d+`` reads the code as
    ``/C23`` and swallows the ``3`` that belongs to the measurement. The wildcard then consumes real
    content and the match fails. Leaks are therefore identified in the original text, where the
    whitespace that delimits them still exists, and only then is whitespace removed.
    """
    return _LEAK.sub(_HOLE, text)


def _wildcard_match(text: str, quote: str) -> bool:
    """True iff ``quote`` occurs in ``text`` when each leaked glyph matches ONE character.

    Exact everywhere else: no edit distance, no partial credit, no skipping. A quote that differs
    from the source anywhere other than at a leak position cannot match. Takes ORIGINAL text and
    quote and does its own marking/stripping, so callers cannot get the order wrong.
    """
    t, q = _strip_ws(_mark_leaks(text)), _strip_ws(quote)
    n, m = len(t), len(q)
    for start in range(n):
        i, j = start, 0
        while j < m:
            if i < n and t[i] == _HOLE:
                i += 1
                j += 1  # the hole stands for exactly one quote character, unknown which
            elif i < n and t[i] == q[j]:
                i += 1
                j += 1
            else:
                break
        if j == m:
            return True
    return False


def _longest_prefix_end(text: str, quote: str) -> int | None:
    """Index in ``text`` just past the longest prefix of ``quote`` that occurs in it."""
    lo, hi = 0, len(quote)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if quote[:mid] in text:
            lo = mid
        else:
            hi = mid - 1
    if lo == 0:
        return None
    return text.index(quote[:lo]) + lo


def _stored_quote(paper: str, field: str) -> str | None:
    """The model quote from the first stored quote-unresolved diagnostic for this paper/field."""
    found: list[str] = []
    for path in sorted(_RESULTS.glob(f"**/papers/{paper}*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        def walk(node: object) -> None:
            if isinstance(node, dict):
                reason = node.get("failure_reason")
                fid = str(node.get("field", ""))
                if (
                    isinstance(reason, str)
                    and "quote_unresolved" in reason
                    and fid.endswith(field)
                    and isinstance(node.get("raw_quote"), str)
                ):
                    found.append(node["raw_quote"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(doc)
        if found:
            break
    return found[0] if found else None


def _source_text(paper: str) -> str | None:
    override = _TEXT_OVERRIDE.get(paper)
    if override is not None:
        return override.read_text(encoding="utf-8") if override.is_file() else None
    name = _PDF.get(paper)
    if name is None or not (_CORPUS / name).is_file():
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from extractor_mvp.methods_finder import find_methods_section
    from extractor_mvp.pdf_loader import load_pdf_text

    return find_methods_section(load_pdf_text(_CORPUS / name)[0]).text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Booleans only. Never prints paper text.")
    ap.add_argument("--paper", required=True)
    ap.add_argument("--field", required=True)
    args = ap.parse_args(argv)

    quote = _stored_quote(args.paper, args.field)
    text = _source_text(args.paper)
    print(f"quote_located_in_store: {quote is not None}")
    print(f"source_text_available: {text is not None}")
    if quote is None or text is None:
        return 1

    nt, nq = _strip_ws(text), _strip_ws(quote)
    print(f"text_carries_glyph_leak: {bool(_LEAK.search(text))}")
    print(f"resolves_without_any_change: {nq in nt}")

    marked = _strip_ws(_mark_leaks(text))
    end = _longest_prefix_end(marked, nq)
    crosses = end is not None and _HOLE in marked[end : end + 2]
    print(f"quote_crosses_leak: {crosses}")
    print(f"recovered_by_one_char_wildcard: {_wildcard_match(text, quote)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

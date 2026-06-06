"""Resolve an LLM-quoted string to a character-offset ``Span`` in the paper text.

Conservative by design: a failed resolution is a flag, not a fabrication. Beyond
the one whitespace-collapsing heuristic (PDF text extraction commonly inserts
line breaks mid-sentence), there is no fuzzy / edit-distance / partial matching —
those would introduce silent mis-attributions and defeat the point of grounding.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from fmri_repro.spec.provenance import Span

# Characters NFKD doesn't fold to an ASCII-friendly form. Each entry is motivated
# by an observed PDF artifact, not preemptive coverage.
_EXPLICIT_NORMALIZATIONS: dict[str, str] = {
    "×": "x",  # × MULTIPLICATION SIGN (observed: liu_2013 "2×2×2mm")
    "÷": "/",  # ÷ DIVISION SIGN
    "·": "*",  # · MIDDLE DOT
    "–": "-",  # – EN DASH
    "—": "-",  # — EM DASH
    "−": "-",  # − MINUS SIGN
    "‘": "'",  # ' LEFT SINGLE QUOTATION MARK
    "’": "'",  # ' RIGHT SINGLE QUOTATION MARK
    "“": '"',  # " LEFT DOUBLE QUOTATION MARK
    "”": '"',  # " RIGHT DOUBLE QUOTATION MARK
    " ": " ",  # NO-BREAK SPACE
}


def normalize_with_offset_map(text: str) -> tuple[str, list[int]]:
    """NFKD-fold + strip combining marks + apply explicit mappings, tracking offsets.

    Returns ``(normalized, offset_map)`` where ``offset_map`` has length
    ``len(normalized) + 1``: ``offset_map[i]`` is the position in ``text`` that
    ``normalized[i]`` originates from, and ``offset_map[len(normalized)] == len(text)``
    (sentinel for terminal slicing). ASCII-only text round-trips unchanged with an
    identity map. A ligature like ﬂ at position k yields 'f','l' both mapped to k;
    combining marks contribute no normalized char and no offset entry.
    """
    out_chars: list[str] = []
    out_offsets: list[int] = []
    for orig_idx, ch in enumerate(text):
        if ch in _EXPLICIT_NORMALIZATIONS:
            for nc in _EXPLICIT_NORMALIZATIONS[ch]:
                out_chars.append(nc)
                out_offsets.append(orig_idx)
        else:
            for nc in unicodedata.normalize("NFKD", ch):
                if not unicodedata.combining(nc):
                    out_chars.append(nc)
                    out_offsets.append(orig_idx)
    out_offsets.append(len(text))  # sentinel
    return "".join(out_chars), out_offsets


@dataclass(frozen=True)
class SpanResolution:
    span: Span | None  # None if the quote couldn't be located
    failure_reason: str | None  # "quote_not_found" | "quote_ambiguous" | None on success


def _make_span(text: str, start: int, end: int) -> Span:
    return Span(start=start, end=end, text=text[start:end], section=None)


def _collapse_with_map(s: str) -> tuple[str, list[int]]:
    """Collapse each whitespace run to a single space.

    Returns ``(collapsed, index_map)`` where ``index_map[i]`` is the original
    offset of collapsed character ``i`` (a collapsed space maps to the first
    char of its original run), so a match in the collapsed string can be mapped
    back to original offsets.
    """
    out: list[str] = []
    index_map: list[int] = []
    i, n = 0, len(s)
    while i < n:
        if s[i].isspace():
            run_start = i
            while i < n and s[i].isspace():
                i += 1
            out.append(" ")
            index_map.append(run_start)
        else:
            out.append(s[i])
            index_map.append(i)
            i += 1
    return "".join(out), index_map


def resolve_quote(quote: str, text: str) -> SpanResolution:
    """Find ``quote`` in ``text`` and return a grounded ``Span``.

    1. exact substring (case-sensitive); exactly one match -> success
    2. else case-insensitive substring; exactly one -> success
    3. else Unicode-normalized (NFKD + explicit maps), exact-then-case-insensitive;
       exactly one -> success. Stricter than whitespace-collapse (character identity
       preserved up to compatibility variants), so it sits ahead of tier 4.
    4. else whitespace-collapsed on both sides; exactly one -> success
    5. multiple matches at any stage -> ``quote_ambiguous`` (LLM should quote more)
    6. never matched -> ``quote_not_found``
    """
    if not quote or not quote.strip():
        return SpanResolution(None, "quote_not_found")
    if len(quote) > len(text):
        return SpanResolution(None, "quote_not_found")

    # 1. exact
    count = text.count(quote)
    if count == 1:
        start = text.index(quote)
        return SpanResolution(_make_span(text, start, start + len(quote)), None)
    if count > 1:
        return SpanResolution(None, "quote_ambiguous")

    # 2. case-insensitive
    low_text, low_quote = text.lower(), quote.lower()
    ci_count = low_text.count(low_quote)
    if ci_count == 1:
        start = low_text.index(low_quote)
        return SpanResolution(_make_span(text, start, start + len(quote)), None)
    if ci_count > 1:
        return SpanResolution(None, "quote_ambiguous")

    # 3. Unicode-normalized (exact, then case-insensitive), mapped to original offsets.
    n_text, t_off = normalize_with_offset_map(text)
    n_quote, _ = normalize_with_offset_map(quote)
    if n_quote:
        for hay, needle in ((n_text, n_quote), (n_text.lower(), n_quote.lower())):
            nc = hay.count(needle)
            if nc == 1:
                ns = hay.index(needle)
                o_start, o_end = t_off[ns], t_off[ns + len(needle)]
                if o_end <= o_start:
                    return SpanResolution(None, "quote_not_found")
                # invariant: the original slice normalizes back to the matched region
                if (
                    normalize_with_offset_map(text[o_start:o_end])[0]
                    != n_text[ns : ns + len(needle)]
                ):
                    raise RuntimeError(
                        "span_resolver: Unicode offset-map inconsistency "
                        f"(quote={quote!r}, span=[{o_start},{o_end}])"
                    )
                return SpanResolution(_make_span(text, o_start, o_end), None)
            if nc > 1:
                return SpanResolution(None, "quote_ambiguous")

    # 4. whitespace-collapsed (case-insensitive), mapped back to original offsets
    collapsed_text, index_map = _collapse_with_map(low_text)
    collapsed_quote = " ".join(low_quote.split())
    if not collapsed_quote:
        return SpanResolution(None, "quote_not_found")
    wc_count = collapsed_text.count(collapsed_quote)
    if wc_count == 1:
        c_start = collapsed_text.index(collapsed_quote)
        c_end = c_start + len(collapsed_quote)
        orig_start = index_map[c_start]
        # original offset just past the last matched collapsed char
        orig_end = index_map[c_end - 1] + 1
        if orig_end <= orig_start:  # defensive; shouldn't happen
            return SpanResolution(None, "quote_not_found")
        return SpanResolution(_make_span(text, orig_start, orig_end), None)
    if wc_count > 1:
        return SpanResolution(None, "quote_ambiguous")

    return SpanResolution(None, "quote_not_found")

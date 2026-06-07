"""Resolve an LLM-quoted string to a character-offset ``Span`` in the paper text.

Conservative by design: a failed resolution is a flag, not a fabrication. Beyond
two whitespace heuristics (PDF text extraction commonly inserts line breaks
mid-sentence, and splits measurement tokens like ``3mm`` -> ``3m m``), there is
no fuzzy / edit-distance / partial matching — those would introduce silent
mis-attributions and defeat the point of grounding.
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


def _measurement_ws_drop_indices(text: str) -> set[int]:
    """Indices of whitespace chars that pypdf spuriously inserted inside a
    measurement token (e.g. ``3mm`` extracted as ``3m m`` or ``3mm³`` as
    ``3m m\\n3``), which should be removed so the quote can match.

    A whitespace run qualifies only when it is flanked by alphanumerics on both
    sides AND an immediately-flanking token is a single ASCII letter (a split
    unit fragment) AND a flanking token contains a digit. That conjunction fires
    on ``3m m`` / ``m\\n3`` but leaves real word boundaries intact —
    ``MNI152 space``, ``20 subjects``, ``Table 3 shows``, ``2 mm`` all have no
    single-letter flank and so are preserved.
    """
    n = len(text)
    drops: set[int] = set()
    i = 0
    while i < n:
        if not text[i].isspace():
            i += 1
            continue
        ws_start = i
        while i < n and text[i].isspace():
            i += 1
        ws_end = i  # exclusive
        if ws_start == 0 or ws_end >= n:
            continue
        if not (text[ws_start - 1].isalnum() and text[ws_end].isalnum()):
            continue
        left_start = ws_start - 1
        while left_start - 1 >= 0 and text[left_start - 1].isalnum():
            left_start -= 1
        left = text[left_start:ws_start]
        right_end = ws_end
        while right_end + 1 < n and text[right_end + 1].isalnum():
            right_end += 1
        right = text[ws_end : right_end + 1]
        has_single_letter = (len(left) == 1 and left.isalpha()) or (
            len(right) == 1 and right.isalpha()
        )
        has_digit = any(c.isdigit() for c in left) or any(c.isdigit() for c in right)
        if has_single_letter and has_digit:
            drops.update(range(ws_start, ws_end))
    return drops


def normalize_with_offset_map(text: str) -> tuple[str, list[int]]:
    """NFKD-fold + strip combining marks + apply explicit mappings, tracking offsets.

    Returns ``(normalized, offset_map)`` where ``offset_map`` has length
    ``len(normalized) + 1``: ``offset_map[i]`` is the position in ``text`` that
    ``normalized[i]`` originates from, and ``offset_map[len(normalized)] == len(text)``
    (sentinel for terminal slicing). ASCII-only text round-trips unchanged with an
    identity map. A ligature like ﬂ at position k yields 'f','l' both mapped to k;
    combining marks — and pypdf-split measurement whitespace (see
    :func:`_measurement_ws_drop_indices`) — contribute no normalized char and no
    offset entry.
    """
    drop_idx = _measurement_ws_drop_indices(text)
    out_chars: list[str] = []
    out_offsets: list[int] = []
    for orig_idx, ch in enumerate(text):
        if orig_idx in drop_idx:
            continue
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
                # Invariant: the original slice re-normalizes back to the matched
                # region. Measurement-whitespace dropping is context-sensitive (it
                # depends on flanking tokens), so a slice that begins or ends mid
                # measurement token can re-normalize differently than it did in full
                # context. Real sentence quotes never start mid-"3mm", but rather
                # than fabricate a span on the off chance, fail closed -> not_found.
                if (
                    normalize_with_offset_map(text[o_start:o_end])[0]
                    != n_text[ns : ns + len(needle)]
                ):
                    return SpanResolution(None, "quote_not_found")
                return SpanResolution(_make_span(text, o_start, o_end), None)
            if nc > 1:
                return SpanResolution(None, "quote_ambiguous")

    # 4. whitespace-collapsed (case-insensitive), mapped back to original offsets.
    #    Collapse runs on the NORMALIZED text so this tier composes with the
    #    Unicode + measurement-split normalization above (a quote can need both a
    #    line break collapsed AND a split unit rejoined). Two maps are composed:
    #    collapsed -> n_text index (n_index_map) -> original offset (t_off).
    collapsed_text, n_index_map = _collapse_with_map(n_text.lower())
    collapsed_quote = " ".join(n_quote.lower().split())
    if not collapsed_quote:
        return SpanResolution(None, "quote_not_found")
    wc_count = collapsed_text.count(collapsed_quote)
    if wc_count == 1:
        c_start = collapsed_text.index(collapsed_quote)
        c_end = c_start + len(collapsed_quote)
        n_start = n_index_map[c_start]  # index into n_text
        n_end = n_index_map[c_end - 1] + 1  # just past the last matched normalized char
        orig_start, orig_end = t_off[n_start], t_off[n_end]
        if orig_end <= orig_start:  # defensive; shouldn't happen
            return SpanResolution(None, "quote_not_found")
        return SpanResolution(_make_span(text, orig_start, orig_end), None)
    if wc_count > 1:
        return SpanResolution(None, "quote_ambiguous")

    return SpanResolution(None, "quote_not_found")

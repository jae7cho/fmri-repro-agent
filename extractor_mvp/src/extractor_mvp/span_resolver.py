"""Resolve an LLM-quoted string to a character-offset ``Span`` in the paper text.

Conservative by design: a failed resolution is a flag, not a fabrication. Beyond
two whitespace heuristics (PDF text extraction commonly inserts line breaks
mid-sentence, and splits measurement tokens like ``3mm`` -> ``3m m``), there is
no fuzzy / edit-distance / partial matching — those would introduce silent
mis-attributions and defeat the point of grounding.

Tier 5 (corrupted-source tolerant, added v0.4.0) recovers a model quote that the model
silently repaired from mangled pypdf text, using three GENERAL pypdf mangles only —
whitespace-DELETION, injected citation markers, line-break hyphenation — still substring-only
(never fuzzy), in original coordinates, re-verified to fail closed, and it fires ONLY after every
exact/near tier failed (so it can never move a currently-resolving span). A tier-5 match sets
``SpanResolution.recovered=True`` so the caller can mark the extraction honestly.

NOT handled by tier 5: the font-specific multiplication-sign (U+00D7) -> ``/C2`` glyph mangle seen
in a few papers (agtzidis/gordon/poldrack/wheaton). ``/C<digit>`` are font glyph codes that map to
DIFFERENT glyphs across papers, so treating ``/C2`` as that glyph globally risks a WRONG match --
which would violate the never-fuzzy invariant. It is deliberately excluded; those dimension-quote
drops stay unrecovered rather than risk a mis-attribution.
"""

from __future__ import annotations

import re
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


def _hyphenation_drop_indices(text: str) -> set[int]:
    """Indices to drop for a line-wrap soft-hyphen: a word-internal hyphen immediately
    followed (allowing spaces before the break) by a newline. PDF text extraction
    hard-wraps words at the hyphen (``normal-\\nized``); dropping the hyphen and the
    newline/space run rejoins the halves (``normalized``) so a quote carrying the intact
    word matches.

    Scoped conservatively — fires ONLY when the hyphen is (a) preceded by an
    alphanumeric (the left word-half), (b) followed by optional spaces, then a newline,
    then optional whitespace, and (c) that run is followed by an alphanumeric (the right
    word-half). So ``grand-mean`` / ``z-score`` / ``0.01-0.1`` (hyphen + non-newline) and
    ``word - \\nword`` (hyphen not attached to a word) are left untouched. Diagnosed on
    liu_2013 (``temporally normal-\\nized``).
    """
    n = len(text)
    drops: set[int] = set()
    i = 0
    while i < n:
        if text[i] != "-" or i == 0 or not text[i - 1].isalnum():
            i += 1
            continue
        j = i + 1
        while j < n and text[j] in " \t":  # optional spaces between hyphen and the break
            j += 1
        if j < n and text[j] == "\n":
            k = j + 1
            while k < n and text[k] in " \t\n":  # trailing whitespace after the break
                k += 1
            if k < n and text[k].isalnum():
                drops.update(range(i, k))  # hyphen through the newline/space run
                i = k
                continue
        i += 1
    return drops


def normalize_with_offset_map(text: str) -> tuple[str, list[int]]:
    """NFKD-fold + strip combining marks + apply explicit mappings, tracking offsets.

    Returns ``(normalized, offset_map)`` where ``offset_map`` has length
    ``len(normalized) + 1``: ``offset_map[i]`` is the position in ``text`` that
    ``normalized[i]`` originates from, and ``offset_map[len(normalized)] == len(text)``
    (sentinel for terminal slicing). ASCII-only text round-trips unchanged with an
    identity map. A ligature like ﬂ at position k yields 'f','l' both mapped to k;
    combining marks — pypdf-split measurement whitespace (see
    :func:`_measurement_ws_drop_indices`) — and line-wrap soft-hyphens (see
    :func:`_hyphenation_drop_indices`) contribute no normalized char and no offset entry.
    """
    drop_idx = _measurement_ws_drop_indices(text) | _hyphenation_drop_indices(text)
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
    recovered: bool = False  # True iff located ONLY by the corrupted-source tolerant tier (5)


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


_MARKER_RE = re.compile(r"\[\s*\d+(?:[-–]\d+)?\s*\]")


def _delete_with_map(s: str) -> tuple[str, list[int]]:
    """Delete whitespace, hyphens, and injected citation markers; keep an offset map into ``s``.

    Composes ON TOP of the Unicode-normalized text (tier 3's ``normalize_with_offset_map``), so
    ligatures (``ﬁ``->``fi``), curly quotes, and split measurement units are already folded before
    this runs — tier 5 only has to absorb the three GENERAL pypdf mangles: whitespace-DELETION
    (run-together words / shattered ``C-P A C``), all hyphens (line-break AND compound, since pypdf
    drops both unreliably), and injected markers ``[ 62]``. Returns ``(deleted, index_map)`` with
    ``index_map[i]`` = the offset in ``s`` of deleted-string char ``i`` (+ trailing sentinel). NOT
    handled: the font-specific multiplication-sign->/C2 glyph mangle (see module note)."""
    skip = bytearray(len(s))
    for m in _MARKER_RE.finditer(s):
        for i in range(m.start(), m.end()):
            skip[i] = 1
    out: list[str] = []
    idx: list[int] = []
    for i, c in enumerate(s):
        if skip[i] or c.isspace() or c == "-":
            continue
        out.append(c)
        idx.append(i)
    idx.append(len(s))  # sentinel so a match ending at the last char can map its end
    return "".join(out), idx


def _resolve_quote_once(quote: str, text: str) -> SpanResolution:
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

    # 5. Corrupted-source tolerant tier (LAST — reached only after every exact/near tier above
    #    failed, so a currently-resolving quote can NEVER enter here; this is what makes the
    #    corpus-wide arm-(ii) span-stability guarantee hold by construction). Handles the three
    #    GENERAL pypdf mangles observed across the corpus: whitespace-DELETION (run-together
    #    words / shattered "C-P A C"), injected citation markers ("[ 62]"), and line-break
    #    hyphenation ("us-\ning"). Substring-only after normalization -> never fuzzy/edit-distance;
    #    the recovered span is in ORIGINAL coordinates and is re-verified to fail closed. The
    #    font-specific "× -> /C2" glyph mangle is DELIBERATELY NOT handled (see module note).
    #    Composes with tiers 3-4: delete-normalize the ALREADY-Unicode-normalized text (n_text),
    #    then map agg-index -> n_text-index (a_map) -> original offset (t_off).
    agg_text, a_map = _delete_with_map(n_text.lower())
    agg_quote, _ = _delete_with_map(n_quote.lower())
    if not agg_quote:
        return SpanResolution(None, "quote_not_found")
    ac = agg_text.count(agg_quote)
    if ac == 1:
        a_start = agg_text.index(agg_quote)
        n_start = a_map[a_start]
        n_end = a_map[a_start + len(agg_quote) - 1] + 1
        orig_start, orig_end = t_off[n_start], t_off[n_end]
        if orig_end <= orig_start:
            return SpanResolution(None, "quote_not_found")
        # fail-closed re-verification: the recovered ORIGINAL slice, re-normalized the same way,
        # must equal the matched needle exactly (guards any offset-mapping error from producing a
        # wrong span). Only then is the recovery trustworthy.
        reslice_n, _ = normalize_with_offset_map(text[orig_start:orig_end])
        if _delete_with_map(reslice_n.lower())[0] != agg_quote:
            return SpanResolution(None, "quote_not_found")
        return SpanResolution(_make_span(text, orig_start, orig_end), None, recovered=True)
    if ac > 1:
        return SpanResolution(None, "quote_ambiguous")

    return SpanResolution(None, "quote_not_found")


_TRAILING_SENTENCE_PUNCT = ".!?"


def _strip_trailing_sentence_punct(quote: str) -> str:
    """Strip a trailing run of sentence punctuation + whitespace from the END of a quote.

    Only the tail is touched -- internal punctuation (and decimals like ``5.0``, which end
    in a digit, not punctuation) are left intact. ``"...surface. "`` -> ``"...surface"``;
    ``"...5.0."`` -> ``"...5.0"``; ``"...5.0"`` -> unchanged.
    """
    stripped = quote.rstrip()
    while stripped and stripped[-1] in _TRAILING_SENTENCE_PUNCT:
        stripped = stripped[:-1].rstrip()
    return stripped


def resolve_quote(quote: str, text: str) -> SpanResolution:
    """Resolve ``quote`` to a grounded ``Span`` (see :func:`_resolve_quote_once` for tiers).

    Adds ONE fallback, fired only after a primary ``quote_not_found`` (never after success
    or ``quote_ambiguous``): re-attempt the SAME pipeline with trailing sentence punctuation
    stripped from the quote. Motivating artifact (poldrack_2015 surface_registration): the
    LLM quotes ``"...fsaverage surface."`` but pypdf flattened a superscript citation into
    the parsed stream as ``"...fsaverage surface 51-54."``, separating the terminal period
    from the last word so the contiguous match fails on that one char (425/426). Stripping
    the trailing period lets ``"...fsaverage surface"`` ground. The rescue is accepted ONLY
    on a unique match (``failure_reason is None``); an ambiguous or still-absent retry falls
    through to the original ``quote_not_found``. Offset correctness is inherited from
    ``_resolve_quote_once`` -- the returned span covers the stripped-quote match (ending at
    the word), never the citation or the stripped punctuation. Deliberately narrow: it does
    NOT drop citation markers mid-quote (no observed instance; over-matching numeric prose
    like ``"version 5.0"`` would violate the fail-closed invariant).
    """
    primary = _resolve_quote_once(quote, text)
    if primary.failure_reason != "quote_not_found":
        return primary
    stripped = _strip_trailing_sentence_punct(quote)
    if stripped and stripped != quote:
        retry = _resolve_quote_once(stripped, text)
        if retry.failure_reason is None:
            return retry
    return primary


# --- Value-support check (v0.4.0 base_pipeline guard) ------------------------
# Used by the extractor to test whether a model's OWN value is actually present in its OWN
# quote — firewall-clean (no KB), so it does not couple the paper-only extractor to the KB.


def _first_use_variants(name: str) -> list[str]:
    """Split a 'Full Name (ACRONYM)' first-use form into {whole, pre-paren, parenthetical}.
    Pure lexical (no KB) — content-agnostic, so it does not couple the extractor to the KB."""
    variants = [name]
    m = re.match(r"^(.*\S)\s*\(([^()]+)\)\s*$", name)
    if m:
        variants.append(m.group(1))
        variants.append(m.group(2))
    return [v for v in variants if v.strip()]


def quote_supports_value(value: str, quote: str) -> bool:
    """True iff ``value`` (or a first-use variant) appears in ``quote`` as a run of WHOLE tokens.

    NFKD+lowercase normalization so surface mangling/spacing never causes a spurious 'unsupported';
    hyphen/space mangling that splits a name across adjacent tokens (``C-PAC`` ~ ``c pac``) is
    tolerated by allowing a contiguous token concatenation. Crucially the match is on TOKEN
    boundaries, NOT raw substring: a short value never matches inside a longer word -- ``ANTs`` is
    not supported by ``Avants``/``particip-ANTS``, ``FIX`` not by ``fixation`` -- which would
    otherwise let the value-support guard report a citation-only quote as 'supported' and emit a
    fabricated EXTRACTED (the guard's whole purpose). Never fuzzy.
    """
    q_tokens = re.findall(r"[a-z0-9]+", normalize_with_offset_map(quote.lower())[0])

    def _core(s: str) -> str:
        return "".join(re.findall(r"[a-z0-9]+", normalize_with_offset_map(s.lower())[0]))

    def _spans_whole_tokens(core: str) -> bool:
        # core == a contiguous concatenation of >=1 whole quote tokens (start at each token, grow
        # until the accumulation matches or overshoots core's length).
        for i in range(len(q_tokens)):
            acc = ""
            for j in range(i, len(q_tokens)):
                acc += q_tokens[j]
                if len(acc) > len(core):
                    break
                if acc == core:
                    return True
        return False

    return any(
        (c := _core(variant)) and _spans_whole_tokens(c) for variant in _first_use_variants(value)
    )

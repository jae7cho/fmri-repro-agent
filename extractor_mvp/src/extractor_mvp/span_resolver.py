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
which would violate the never-fuzzy invariant. Tier 5 still refuses it.

Tier 6 (the named source-text repair, added 2026-10-28 under the author's item 1 of
``DESIGN_coverage_expansion.md`` B14) answers that reason the way ``DELTA_glyph_leak_span_recovery.md``
proposed: a ``/C<digits>`` run in the SOURCE may match exactly one character of the quote with no
claim about which glyph it is; binder's ``ª`` may match the quote's ``fi``; and a SYMBOL in the quote
(``> < = ≤ ≥ ± ~ ≈ °``) may match a letter or digit in the source at that position (the text layer
printing ``>`` as ``4``). Bounded to :data:`_MAX_REPAIRS` substitutions per quote, substring-only
otherwise, unique or nothing, re-verified fail-closed, and reported: the span carries the
substitutions by name (``Span.repairs``) and ``recovered=True`` marks it "matched after source-text
repair". ``ﬁ``/``ﬂ`` keep folding silently at tier 3 (NFKD), as they always have.
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
    # 2026-11-09 (the author's item 3): the multiplication sign's other text-layer forms fold to the
    # same character on both quote and text -- U+2AFB and U+03EB (the Coptic letter a GROBID text
    # layer prints for x in some fonts; dimitrova). /C2 and the GROBID form of that glyph code (U+00C2)
    # fold only BETWEEN DIGITS, in _multiplication_marks, since alone they name other glyphs.
    "\u2afb": "x",
    "\u03eb": "x",
    # Ligatures fold explicitly (NFKD folds them too; written out so the rule is visible).
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
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


#: A multiplication sign between two digits, in any of its text-layer forms (the author's item 3,
#: 2026-11-09): the sign itself, U+2AFB, U+03EB, the leaked glyph code ``/C2`` (pypdf) and its GROBID
#: form U+00C2, and a plain ``x``, each with optional whitespace on either side.
_MULT_BETWEEN_DIGITS = re.compile(r"(?<=\d)(\s*)(\u00d7|\u2afb|\u03eb|\u00c2|/C2|[xX])(\s*)(?=\d)")


def _multiplication_marks(text: str) -> tuple[dict[int, str], set[int]]:
    """For every multiplication sign between digits: its first character maps to ``x``, the rest of
    a ``/C2`` code and the whitespace around the sign are dropped -- so "2 x-sign 2", "2U+03EB2", "2 /C2 2" and
    "2x2" all normalise to "2x2" on both quote and text. A sign anywhere else is left alone."""
    replace: dict[int, str] = {}
    drop: set[int] = set()
    for m in _MULT_BETWEEN_DIGITS.finditer(text):
        drop.update(range(m.start(1), m.end(1)))
        drop.update(range(m.start(3), m.end(3)))
        replace[m.start(2)] = "x"
        drop.update(range(m.start(2) + 1, m.end(2)))
    return replace, drop


def normalize_with_offset_map(text: str, keep_citations: bool = False) -> tuple[str, list[int]]:
    """NFKD-fold + strip combining marks + apply explicit mappings, tracking offsets.

    Returns ``(normalized, offset_map)`` where ``offset_map`` has length
    ``len(normalized) + 1``: ``offset_map[i]`` is the position in ``text`` that
    ``normalized[i]`` originates from, and ``offset_map[len(normalized)] == len(text)``
    (sentinel for terminal slicing). ASCII-only text round-trips unchanged with an
    identity map. A ligature like ﬂ at position k yields 'f','l' both mapped to k;
    combining marks — pypdf-split measurement whitespace (see
    :func:`_measurement_ws_drop_indices`) — and line-wrap soft-hyphens (see
    :func:`_hyphenation_drop_indices`) contribute no normalized char and no offset entry.
    The citation delimiters of GROBID text (:data:`CITATION_OPEN`, :data:`CITATION_CLOSE`) are
    dropped too, so tiers 3 to 6 read GROBID text as a reader does, citations inline; only tier 5b
    keeps them (``keep_citations=True``).
    """
    mult_replace, mult_drop = _multiplication_marks(text)
    drop_idx = _measurement_ws_drop_indices(text) | _hyphenation_drop_indices(text) | mult_drop
    out_chars: list[str] = []
    out_offsets: list[int] = []
    for orig_idx, ch in enumerate(text):
        if orig_idx in drop_idx:
            continue
        if not keep_citations and ch in (CITATION_OPEN, CITATION_CLOSE):
            continue
        if orig_idx in mult_replace:
            out_chars.append(mult_replace[orig_idx])
            out_offsets.append(orig_idx)
        elif ch in _EXPLICIT_NORMALIZATIONS:
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
    recovered: bool = False  # True iff located ONLY by a tolerant tier (5, or 6 with repairs)
    repairs: tuple[str, ...] = ()  # tier 6 only: the named substitutions, in quote order


def _make_span(text: str, start: int, end: int, repairs: tuple[str, ...] = ()) -> Span:
    return Span(start=start, end=end, text=text[start:end], section=None, repairs=list(repairs))


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

    # 5b. Citations as skippable regions (the author's ruling 2 of 2026-11-06). GROBID text carries
    #     every <ref type="bibr"> between CITATION_OPEN and CITATION_CLOSE; a quote may hold any text
    #     there, or none. Reached only after tier 5 failed, and only for text that carries regions.
    if CITATION_OPEN in text:
        across = _resolve_across_citations(text, n_quote)
        if across is not None:
            return across

    # 6. The named source-text repair (2026-10-28; module note). Reached only after tier 5 failed,
    #    on the same deletion-normalized strings, so a quote any earlier tier resolves never enters
    #    here. Each candidate start walks the quote with at most _MAX_REPAIRS substitution events;
    #    exactly one successful start is accepted, re-verified on the recovered original slice.
    q_a_text, q_a_map = _delete_with_map(n_quote.lower())
    _, q_off = normalize_with_offset_map(quote)
    quote_chars = [quote[q_off[q_a_map[j]]] for j in range(len(q_a_text))]
    marks = _repair_marks(text, n_text, t_off, a_map, len(agg_text))
    hits: list[tuple[int, int, tuple[str, ...]]] = []
    for i0 in _repair_candidate_starts(agg_text, agg_quote, marks):
        walked = _repair_walk(agg_text, i0, agg_quote, quote_chars, text, t_off, a_map, marks)
        if walked is not None:
            hits.append((i0, walked[0], walked[1]))
            if len(hits) > 1:
                return SpanResolution(None, "quote_ambiguous")
    if len(hits) == 1:
        i0, i_end, events = hits[0]
        n_start, n_end = a_map[i0], a_map[i_end - 1] + 1
        orig_start, orig_end = t_off[n_start], t_off[n_end]
        if orig_end <= orig_start:
            return SpanResolution(None, "quote_not_found")
        # fail-closed re-verification: the recovered original slice, prepared the same way, must
        # walk the whole quote from its first character to its last with the same events.
        reslice = text[orig_start:orig_end]
        re_n, re_off = normalize_with_offset_map(reslice)
        re_agg, re_map = _delete_with_map(re_n.lower())
        re_marks = _repair_marks(reslice, re_n, re_off, re_map, len(re_agg))
        re_walk = _repair_walk(re_agg, 0, agg_quote, quote_chars, reslice, re_off, re_map, re_marks)
        if re_walk is None or re_walk[0] != len(re_agg) or re_walk[1] != events:
            return SpanResolution(None, "quote_not_found")
        return SpanResolution(
            _make_span(text, orig_start, orig_end, events), None, recovered=True, repairs=events
        )

    return SpanResolution(None, "quote_not_found")


# --- Tier 5b: citations as skippable regions ---------------------------------------------------

#: The delimiters GROBID text puts around each citation (``grobid_source.flatten_tei``): Unicode's
#: interlinear annotation anchor and terminator, format characters no PDF text layer emits. The
#: model reads the citation between them; the matcher need not find it in the quote.
CITATION_OPEN = "\ufff9"
CITATION_CLOSE = "\ufffb"
_GROUP_SEP = re.compile(r"[\s,;]*")
_REGION_RE = re.compile(f"{CITATION_OPEN}[^{CITATION_OPEN}{CITATION_CLOSE}]*{CITATION_CLOSE}")
#: How much quote text a citation region may stand for: twice the region's own text (after
#: deletion-normalizing) plus this many characters. Bounded so a region is never a wildcard
#: for a sentence.
_REGION_SLACK = 20
#: The quote prefix that anchors a candidate start.
_ANCHOR = 12


@dataclass(frozen=True)
class _Gap:
    n_start: int  # the first region's start in the normalized text
    n_end: int  # the last region's end (exclusive)
    bound: int  # the most quote characters the gap may absorb
    digits: str  # the regions' digits, in order
    letters: str  # the regions' letters, in order


def _delete_with_regions(s: str) -> tuple[str, list[int], dict[int, _Gap]]:
    """Tier 5's deletion (whitespace, hyphens, bracketed markers) with every citation region taken
    out and remembered as a gap at the position it occupied; adjacent regions are one gap. Returns
    ``(deleted, index_map, gaps)``, ``index_map`` into ``s`` with a trailing sentinel."""
    skip = bytearray(len(s))
    for m in _MARKER_RE.finditer(s):
        for i in range(m.start(), m.end()):
            skip[i] = 1
    regions = {m.start(): m.end() for m in _REGION_RE.finditer(s)}
    out: list[str] = []
    idx: list[int] = []
    gaps: dict[int, _Gap] = {}
    i = 0
    while i < len(s):
        if i in regions:
            end = regions[i]
            own = s[i + 1 : end - 1]
            size = sum(1 for c in own if not c.isspace())
            digits = "".join(c for c in own if c.isdigit())
            letters = "".join(_LETTERS.findall(own))
            pos = len(out)
            prev = gaps.get(pos)
            if prev is None:
                gaps[pos] = _Gap(i, end, 2 * size + _REGION_SLACK, digits, letters)
            else:
                gaps[pos] = _Gap(
                    prev.n_start,
                    end,
                    prev.bound + 2 * size,
                    prev.digits + digits,
                    prev.letters + letters,
                )
            # a citation group: only whitespace and separators before the next citation, so the
            # separators belong to the gap ("[34] , [35]" is one place a quote may leave out)
            sep = _GROUP_SEP.match(s, end)
            i = sep.end() if sep and s.startswith(CITATION_OPEN, sep.end()) else end
            continue
        c = s[i]
        if not (skip[i] or c.isspace() or c == "-" or c in (CITATION_OPEN, CITATION_CLOSE)):
            out.append(c)
            idx.append(i)
        i += 1
    idx.append(len(s))
    return "".join(out), idx, gaps


_DIGITS = re.compile(r"\d+")
_LETTERS = re.compile(r"[^\W\d_]+")


def _drawn_from(x: str, gap: _Gap) -> bool:
    """The quote's text at a citation is drawn from that citation: every run of digits in it occurs
    in the citation's digits, and every run of letters in the citation's letters (both in order,
    whitespace and punctuation aside; tier 5 has already deleted the quote's whitespace and hyphens,
    so "3-5" arrives as "35"). Punctuation is free. So a quote may print a citation its own way
    (the paper's "(Author et al., 2019, 2020" where GROBID's refs read "(Author et al., 2019" and
    "(Author et al., , 2020") but never put a word or a number there that the citation lacks."""
    return all(d in gap.digits for d in _DIGITS.findall(x)) and all(
        w in gap.letters for w in _LETTERS.findall(x)
    )


def _walk_gapped(
    t: str, gaps: dict[int, _Gap], q: str, j: int, i: int, gap_done: bool, seen: set
) -> tuple[int, _Gap | None] | None:
    """Match ``q[i:]`` against ``t`` from ``j``; at a gap the quote may hold up to the gap's bound
    of any characters, or none. Returns ``(t end, the gap the quote ends inside, if any)``."""
    while True:
        if i == len(q):
            return j, None
        if j in gaps and not gap_done:
            key = (j, i)
            if key in seen:
                return None
            seen.add(key)
            g = gaps[j]
            for x in range(min(g.bound, len(q) - i) + 1):
                if x and not _drawn_from(q[i : i + x], g):
                    continue
                if i + x == len(q):
                    return (j, g) if x else (j, None)
                r = _walk_gapped(t, gaps, q, j, i + x, True, seen)
                if r is not None:
                    return r
            return None
        if j >= len(t) or t[j] != q[i]:
            return None
        i += 1
        j += 1
        gap_done = False


def _gapped_matches(t: str, gaps: dict[int, _Gap], q: str) -> set[tuple[int, int, int, int]]:
    """Every distinct match of ``q`` in ``t`` across gaps, as ``(start, lead_gap_start, end,
    tail_gap_end)`` with -1 for no leading or trailing citation text."""
    k = min(_ANCHOR, len(q))
    starts: set[tuple[int, int]] = set()  # (t start, quote start)
    p = t.find(q[:k])
    while p != -1:
        starts.add((p, 0))
        p = t.find(q[:k], p + 1)
    for g, gap in gaps.items():
        for n in range(1, k):  # the quote's first characters end right at a gap
            if g - n >= 0 and t[g - n : g] == q[:n]:
                starts.add((g - n, 0))
        for x in range(1, min(gap.bound, len(q) - 1) + 1):  # the quote opens with citation text
            kk = min(k, len(q) - x)
            if t[g : g + kk] == q[x : x + kk] and _drawn_from(q[:x], gap):
                starts.add((g, x))
    out: set[tuple[int, int, int, int]] = set()
    for p, x in starts:
        r = _walk_gapped(t, gaps, q, p, x, x > 0 or p in gaps, set())
        if r is None or r[0] <= p:
            continue
        lead = gaps[p].n_start if x > 0 else -1
        out.add((p, lead, r[0], r[1].n_end if r[1] is not None else -1))
    return out


def _resolve_across_citations(text: str, n_quote: str) -> SpanResolution | None:
    """Tier 5b. ``None`` when nothing matches (the caller goes on to tier 6)."""
    n_text, t_off = normalize_with_offset_map(text, keep_citations=True)
    s = n_text.lower()
    t, idx, gaps = _delete_with_regions(s)
    if not gaps:
        return None
    q = _delete_with_map(n_quote.lower())[0]
    q = q.replace(CITATION_OPEN, "").replace(CITATION_CLOSE, "")
    if not q:
        return None
    hits = _gapped_matches(t, gaps, q)
    spans = set()
    for p, lead, end, tail in hits:
        n_start = lead if lead >= 0 else idx[p]
        n_end = tail if tail >= 0 else idx[end - 1] + 1
        spans.add((t_off[n_start], t_off[n_end]))
    if not spans:
        return None
    if len(spans) > 1:
        return SpanResolution(None, "quote_ambiguous")
    o_start, o_end = spans.pop()
    if o_end <= o_start:
        return SpanResolution(None, "quote_not_found")
    # fail-closed re-verification: on the recovered slice alone the quote must match once, from
    # the slice's first character to its last
    re_n, _ = normalize_with_offset_map(text[o_start:o_end], keep_citations=True)
    re_t, _, re_gaps = _delete_with_regions(re_n.lower())
    whole = {
        (p, end)
        for p, lead, end, tail in _gapped_matches(re_t, re_gaps, q)
        if (p == 0 or lead >= 0) and end == len(re_t)
    }
    if len(whole) != 1:
        return SpanResolution(None, "quote_not_found")
    return SpanResolution(_make_span(text, o_start, o_end), None, recovered=True)


# --- Tier 6 helpers -----------------------------------------------------------------------------

#: Symbols a model writes where the text layer printed a letter or a digit (``>`` as ``4``, ``<``
#: as ``o``). A quote character in this set may stand for ONE alphanumeric source character.
_REPAIR_SYMBOLS: frozenset[str] = frozenset("<>=≤≥±~≈°")
#: The bound: a quote needing more substitutions than this is not recovered.
_MAX_REPAIRS = 3
#: A font glyph code pypdf leaks into the text layer (``/C2`` for ×, ``/C0`` ...), ONE glyph slot.
_GLYPH_CODE = re.compile(r"/C\d+")
#: The one ligature glyph the corpus leaks that NFKD folds to the wrong letter (binder: ``ª`` for fi).
_LIGATURE_GLYPHS: dict[str, str] = {"ª": "fi"}


def _repair_marks(
    text: str, n_text: str, t_off: list[int], a_map: list[int], agg_len: int
) -> tuple[dict[int, tuple[int, str]], dict[int, str]]:
    """In aggregated coordinates: ``runs[i] = (length, original run text)`` for every ``/C<digits>``
    run starting at ``i`` (marked on the NORMALIZED text, where the whitespace that delimits a code
    still exists -- the DELTA's ordering constraint), and ``ligs[i] = quote letters`` for every
    position whose original character is a leaked ligature glyph."""
    in_run: dict[int, int] = {}
    for rid, m in enumerate(_GLYPH_CODE.finditer(n_text)):
        for k in range(m.start(), m.end()):
            in_run[k] = rid
    runs: dict[int, tuple[int, str]] = {}
    ligs: dict[int, str] = {}
    i = 0
    while i < agg_len:
        ni = a_map[i]
        run_id = in_run.get(ni)
        if run_id is not None:
            j = i
            while j < agg_len and in_run.get(a_map[j]) == run_id:
                j += 1
            runs[i] = (j - i, text[t_off[a_map[i]] : t_off[a_map[j - 1]] + 1])
            i = j
            continue
        orig = text[t_off[ni]]
        if orig in _LIGATURE_GLYPHS:
            ligs[i] = _LIGATURE_GLYPHS[orig]
        i += 1
    return runs, ligs


def _repair_candidate_starts(
    agg_text: str, agg_quote: str, marks: tuple[dict[int, tuple[int, str]], dict[int, str]]
) -> list[int]:
    """Start positions at which a repaired match could begin: an exact first character, a glyph
    run, a ligature glyph the quote spells out, or an alphanumeric under a leading quote symbol."""
    runs, ligs = marks
    if not agg_quote:
        return []
    q0 = agg_quote[0]
    out: list[int] = []
    for i, ch in enumerate(agg_text):
        if (
            ch == q0
            or i in runs
            or (i in ligs and agg_quote.startswith(ligs[i]))
            or (q0 in _REPAIR_SYMBOLS and ch.isalnum())
        ):
            out.append(i)
    return out


def _repair_walk(
    agg_text: str,
    i0: int,
    agg_quote: str,
    quote_chars: list[str],
    text: str,
    t_off: list[int],
    a_map: list[int],
    marks: tuple[dict[int, tuple[int, str]], dict[int, str]],
) -> tuple[int, tuple[str, ...]] | None:
    """Walk the whole quote against ``agg_text`` from ``i0`` with at most ``_MAX_REPAIRS``
    substitution events. Returns ``(end index, events)`` or ``None``. Events are named as the
    quote's character(s) → the source's character(s), in quote order."""
    runs, ligs = marks
    i, j = i0, 0
    events: list[str] = []
    n_text, n_quote = len(agg_text), len(agg_quote)
    while j < n_quote:
        if i >= n_text:
            return None
        if i in runs:
            length, raw = runs[i]
            events.append(f"{quote_chars[j]}→{raw}")
            i += length
            j += 1
        elif i in ligs and agg_quote.startswith(ligs[i], j):
            letters = ligs[i]
            events.append(f"{letters}→{text[t_off[a_map[i]]]}")
            i += 1
            j += len(letters)
        elif agg_text[i] == agg_quote[j]:
            i += 1
            j += 1
        elif agg_quote[j] in _REPAIR_SYMBOLS and agg_text[i].isalnum():
            events.append(f"{quote_chars[j]}→{text[t_off[a_map[i]]]}")
            i += 1
            j += 1
        else:
            return None
        if len(events) > _MAX_REPAIRS:
            return None
    if not events:
        return None  # an exact match here would have resolved at tier 5
    return i, tuple(events)


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


#: The line ``batch.supplement_marker`` writes between the paper's text and its supplement's in the
#: text the model reads (fix 4, 2026-11-05). Kept here so the resolver can tell the two documents
#: apart; test_span_resolver checks the two agree.
SUPPLEMENT_MARKER_RE = re.compile(
    r"\n\n\[Supplementary material, read with the paper: [^\]\n]*\]\n"
)


def resolve_quote(quote: str, text: str) -> SpanResolution:
    """Resolve ``quote`` in ``text`` one document at a time (the author's list of 2026-11-05, third
    round, item 2).

    When ``text`` is a paper and its supplement joined by the supplement marker line, the quote is
    resolved in the paper first; a match there, or an ambiguity there, is the answer. Only a quote
    the paper does not hold is resolved in the supplement, and its span is shifted into ``text``.
    So identical text in both documents resolves to the paper's occurrence, and a quote is
    ambiguous only when it matches twice within one document. Any other text is one document.
    """
    marks = list(SUPPLEMENT_MARKER_RE.finditer(text))
    if len(marks) != 1:
        return _resolve_in_one_document(quote, text)
    m = marks[0]
    in_paper = _resolve_in_one_document(quote, text[: m.start()])
    if in_paper.failure_reason != "quote_not_found":
        return in_paper
    in_supp = _resolve_in_one_document(quote, text[m.end() :])
    if in_supp.span is None:
        return in_supp
    shifted = in_supp.span.model_copy(
        update={"start": in_supp.span.start + m.end(), "end": in_supp.span.end + m.end()}
    )
    return SpanResolution(shifted, None, recovered=in_supp.recovered, repairs=in_supp.repairs)


def _resolve_in_one_document(quote: str, text: str) -> SpanResolution:
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

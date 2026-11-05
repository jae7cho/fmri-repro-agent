"""Heuristic methods-section identification by header regex.

A heuristic, not a parser: when it misses it falls back to whole-paper text and
says so (``found_via='fallback_full_text'``) rather than fabricating a match.
``start_offset`` lets the caller translate slice-relative spans back to
full-paper offsets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

# The ``^...$`` line anchor is LOAD-BEARING: chen has a body line beginning "methods [22]
# are relatively less reliable ..." — an unanchored line-initial pattern would anchor the
# slice in the Introduction. Recall comes from VOCABULARY, not weaker anchoring.
# Every alternative below was verified against a real corpus PDF under tested_lit/ before
# encoding (see methods_finder before/after table); patterns no corpus paper exhibits are
# deliberately absent (STAR Methods — 0 hits). "Experimental Procedures" was added on 2026-11-05
# (fix 1a): Bakker_2012 (stress_v1) heads its methods so and fell back to the full text.
METHODS_HEADERS = [
    # Top-level methods section. "<X> and methods" / "methods and <X>" cover "Materials and
    # Methods", "Methods and Materials", and chen's "Methods and Analysis"; "online methods"
    # covers Cole 2013. GUARD: "Results and Discussion" matches none of these (neither side
    # is "methods") and is a NEXT header instead — tested explicitly.
    r"^\s*(?:\d+\.?\s+)?(?:\w+ and methods?|methods? and \w+|online methods?|methods?"
    r"|experimental procedures?)\s*$",
    # Common fMRI subsections
    r"^\s*(?:\d+\.\d+\.?\s+)?(?:fmri |mri |image |data )?(?:preprocessing|pre-?processing)\s*$",
    r"^\s*(?:\d+\.\d+\.?\s+)?(?:image|fmri|mri) (?:acquisition and )?analysis\s*$",
    r"^\s*(?:\d+\.\d+\.?\s+)?(?:data )?(?:analysis|processing)\s*$",
]
# Next-section terminators. Beyond the classic IMRaD headers, corpus-verified END-MATTER
# headers so a slice terminates before References (oconnor is a data descriptor with no
# Results/Discussion; its methods run into end-matter).
#
# "data records" is deliberately NOT a next-section header.
# OConnor_2017 (GigaScience Data Note) has a standalone "Data records" header at char 17806,
# but its C-PAC methods text continues to 27365 and the true terminator is
# "Availability of supporting data" at 37384. Including "data records" would truncate the
# methods slice before the pipeline is named.
# KNOWN LIMITATION: "Data Records" is a standard terminal section in data descriptors
# (Scientific Data, GigaScience). For a well-formed descriptor this exclusion will OVER-slice.
# This is corpus-specific tuning, not a general rule. Revisit with held-out data (NARPS).
#
# A bare "Supplementary" line is NOT a next-section header (2026-11-05, fix 1a): Cattarinussi_2026's
# text layer puts one word per line, so an in-sentence "see Supplementary Material" became a lone
# "Supplementary" line and ended its methods slice after 613 characters. The heading forms keep
# their second word ("Supplementary Material(s)", "... Information", "... Data", "... Methods").
NEXT_SECTION_HEADERS = [
    r"^\s*(?:\d+\.?\s+)?(?:"
    r"results? and discussion|results?|discussion|conclusions?|references?"
    r"|acknowledge?ments?|supplementary (?:materials?|information|data|methods)"
    r"|supporting information"
    r"|author contributions?|data availability|availability of supporting data"
    r"|competing interests?|declaration of competing interests?|funding"
    r")\s*$",
]

_METHODS_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in METHODS_HEADERS]
_NEXT_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in NEXT_SECTION_HEADERS]

_SUSPICIOUS_RATIO = 0.6
#: A header slice shorter than either floor is not a methods section (2026-11-05, fix 1a): the
#: paper is ``methods_not_found`` and extraction reads the full text, so a tiny slice can never
#: produce a page of "not reported". Floors set under every corpus slice on 2026-11-05: the
#: shortest real slice is 5,077 characters (Schwartz_2018) and the lowest ratio 0.117
#: (Mueller_2021); Cattarinussi_2026's cut slice was 613 characters, ratio 0.008.
MIN_SLICE_CHARS = 2000
MIN_SLICE_RATIO = 0.03
#: A text layer whose lines are nearly all one word cannot tell a heading from a word in a sentence
#: (2026-11-05, fix 1a; Claude's call beside the author's list): Cattarinussi_2026 has 99.1% one-word
#: lines, and with the bare "Supplementary" terminator gone its slice ended instead at an
#: in-sentence "reference". Such a paper is ``methods_not_found``. The highest share elsewhere in the
#: corpus on 2026-11-05 is 0.291 (Poldrack_2015).
MAX_ONE_WORD_LINE_SHARE = 0.8


@dataclass(frozen=True)
class MethodsSlice:
    text: str  # the sliced methods section (== full text on fallback)
    start_offset: int  # char offset in full paper text where the slice begins
    found_via: Literal["header_match", "fallback_full_text"]
    matched_header: str | None
    end_offset: int = 0  # char offset where the slice ends
    slice_ratio: float = 1.0  # len(text) / len(full text)
    ended_at: str = "end_of_text"  # the matched next-header text, or "end_of_text"
    #: A slice to distrust: whole-document fallback, a header slice that swallowed too much
    #: (> 0.6 of the paper), OR an EARLY header (start < 50% of the paper) that ran to
    #: end-of-text with no terminator (likely swallowed Results/Discussion). A LATE header
    #: running to end-of-text is NOT flagged — that is the normal shape of a terminal-Methods
    #: paper. NEVER auto-truncated — fabricating a boundary is worse than a bloated slice.
    suspicious: bool = True
    #: Why the slice is the full text although a header may have matched (2026-11-05, fix 1a):
    #: the header and the length of the slice it gave, or a text layer with one word per line.
    #: None for a header slice and for a paper with no methods header at all.
    fallback_reason: str | None = None


def find_methods_section(paper_text: str) -> MethodsSlice:
    """Slice the methods section by header regex, with diagnostics.

    Takes everything from the earliest-in-text methods header until the first subsequent
    next-section header (or end). No methods header -> whole document, ``fallback_full_text``.
    """
    n = len(paper_text)

    lines = [ln for ln in paper_text.splitlines() if ln.strip()]
    one_word = sum(1 for ln in lines if len(ln.split()) == 1) / len(lines) if lines else 0.0
    if len(lines) >= 50 and one_word > MAX_ONE_WORD_LINE_SHARE:
        return MethodsSlice(
            text=paper_text,
            start_offset=0,
            found_via="fallback_full_text",
            matched_header=None,
            end_offset=n,
            slice_ratio=1.0,
            ended_at="end_of_text",
            suspicious=True,
            fallback_reason=(
                f"the text layer puts one word per line ({one_word:.0%} of lines), so no heading "
                "can be told from a word in a sentence"
            ),
        )

    earliest: tuple[int, re.Match[str]] | None = None
    for rx in _METHODS_RE:
        m = rx.search(paper_text)
        if m is not None and (earliest is None or m.start() < earliest[0]):
            earliest = (m.start(), m)

    if earliest is None:
        return MethodsSlice(
            text=paper_text,
            start_offset=0,
            found_via="fallback_full_text",
            matched_header=None,
            end_offset=n,
            slice_ratio=1.0,
            ended_at="end_of_text",
            suspicious=True,
        )

    start_offset, match = earliest
    next_match: re.Match[str] | None = None
    for rx in _NEXT_RE:
        nm = rx.search(paper_text, match.end())
        if nm is not None and (next_match is None or nm.start() < next_match.start()):
            next_match = nm
    next_start = next_match.start() if next_match is not None else n
    ended_at = next_match.group(0).strip() if next_match is not None else "end_of_text"

    text = paper_text[start_offset:next_start]
    slice_ratio = (len(text) / n) if n else 0.0
    if len(text) < MIN_SLICE_CHARS or slice_ratio < MIN_SLICE_RATIO:
        header = " ".join(match.group(0).split())
        return MethodsSlice(
            text=paper_text,
            start_offset=0,
            found_via="fallback_full_text",
            matched_header=None,
            end_offset=n,
            slice_ratio=1.0,
            ended_at="end_of_text",
            suspicious=True,
            fallback_reason=(
                f"{header!r} gave {len(text)} characters ({slice_ratio:.1%} of the text), "
                f"ending at {ended_at!r}"
            ),
        )
    # A missing terminator only indicates swallowed Results/Discussion when the methods header
    # appears EARLY. A LATE header running to end-of-text is the normal shape of a
    # terminal-Methods paper (e.g. Braun_2015, Viduarre_2017: Methods at ~70-77%), not a defect.
    early_header = (start_offset / n) < 0.5 if n else False
    suspicious = slice_ratio > _SUSPICIOUS_RATIO or (ended_at == "end_of_text" and early_header)
    return MethodsSlice(
        text=text,
        start_offset=start_offset,
        found_via="header_match",
        matched_header=match.group(0).strip(),
        end_offset=next_start,
        slice_ratio=slice_ratio,
        ended_at=ended_at,
        suspicious=suspicious,
    )

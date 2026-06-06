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

METHODS_HEADERS = [
    # Top-level methods section
    r"^\s*(?:\d+\.?\s+)?(?:materials? and methods?|methods? and materials?|methods?)\s*$",
    # Common fMRI subsections
    r"^\s*(?:\d+\.\d+\.?\s+)?(?:fmri |mri |image |data )?(?:preprocessing|pre-?processing)\s*$",
    r"^\s*(?:\d+\.\d+\.?\s+)?(?:image|fmri|mri) (?:acquisition and )?analysis\s*$",
    r"^\s*(?:\d+\.\d+\.?\s+)?(?:data )?(?:analysis|processing)\s*$",
]
NEXT_SECTION_HEADERS = [
    r"^\s*(?:\d+\.?\s+)?(?:results?|discussion|conclusions?|references?"
    r"|acknowledgements?|supplementary)\s*$",
]

_METHODS_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in METHODS_HEADERS]
_NEXT_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in NEXT_SECTION_HEADERS]


@dataclass(frozen=True)
class MethodsSlice:
    text: str  # the sliced methods section (== full text on fallback)
    start_offset: int  # char offset in full paper text where the slice begins
    found_via: Literal["header_match", "fallback_full_text"]
    matched_header: str | None


def find_methods_section(paper_text: str) -> MethodsSlice:
    """Slice the methods section by header regex, with diagnostics.

    Takes everything from the earliest-in-text methods header until the first
    subsequent next-section header (or end). No match -> full text, fallback.
    """
    earliest: tuple[int, re.Match[str]] | None = None
    for rx in _METHODS_RE:
        m = rx.search(paper_text)
        if m is not None and (earliest is None or m.start() < earliest[0]):
            earliest = (m.start(), m)

    if earliest is None:
        return MethodsSlice(paper_text, 0, "fallback_full_text", None)

    start_offset, match = earliest
    next_start = len(paper_text)
    for rx in _NEXT_RE:
        nm = rx.search(paper_text, match.end())
        if nm is not None and nm.start() < next_start:
            next_start = nm.start()

    return MethodsSlice(
        text=paper_text[start_offset:next_start],
        start_offset=start_offset,
        found_via="header_match",
        matched_header=match.group(0).strip(),
    )

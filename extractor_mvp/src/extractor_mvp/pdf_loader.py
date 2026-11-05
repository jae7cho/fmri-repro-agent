"""PDF text extraction via pypdf. No OCR, no fallback — Marker is post-abstract."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Literal

# PDF /CreationDate is "D:YYYYMMDD..." (the "D:" prefix and trailing tz are optional).
_PDF_DATE_RE = re.compile(r"D?:?\s*(\d{4})(\d{2})(\d{2})")


def load_pdf_text(path: Path) -> tuple[str, Literal["pypdf", "failed"]]:
    """Extract text from a PDF with pypdf.

    Returns ``(text, "pypdf")`` on success, ``("", "failed")`` if pypdf errors or
    yields no text. Page texts are joined with a newline; trailing whitespace and
    stray form-feed characters are stripped, but the text is otherwise left close
    to pypdf's output (the methods heuristic + span resolver depend on that).
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception:  # corrupt/encrypted/unreadable -> caller logs pdf_parse_failed
        return "", "failed"

    text = "\n".join(pages).replace("\f", "").strip()
    if not text:
        return "", "failed"
    return text, "pypdf"


#: A text layer whose non-blank lines are more than this share one word each, over at least
#: ``REFLOW_MIN_LINES`` lines, is reflowed before slicing (the author's list of 2026-11-05, third
#: round, item 4). Same threshold as ``methods_finder.MAX_ONE_WORD_LINE_SHARE``, which stays as the
#: guard for a layer that reflow cannot rebuild.
REFLOW_ONE_WORD_SHARE = 0.8
REFLOW_MIN_LINES = 50


def _one_word_share(text: str) -> tuple[int, float]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0, 0.0
    return len(lines), sum(1 for ln in lines if len(ln.split()) == 1) / len(lines)


def reflow_one_word_lines(text: str) -> tuple[str, dict[str, object] | None]:
    """Rebuild the lines of a one-word-per-line text layer; any other text is returned unchanged.

    In such a layer (Cattarinussi_2026: 99.1% one-word lines) pypdf writes each word on its own
    line and marks a word that continues the printed line with a leading space; a word that starts
    a printed line has none, and a whitespace-only line separates blocks (a heading from its
    paragraph). A line with a leading space is joined to the line before it, as written (its own
    leading space is the separator); a whitespace-only line ends the current line. Only line breaks
    and whitespace-only lines are removed; every other character is kept in order. Returns the text and a record of the reflow
    (line counts and one-word shares before and after), or None when the text was not reflowed.
    """
    n_before, share_before = _one_word_share(text)
    if n_before < REFLOW_MIN_LINES or share_before <= REFLOW_ONE_WORD_SHARE:
        return text, None
    out: list[str] = []
    cur: str | None = None
    for ln in text.split("\n"):
        if not ln.strip():
            if cur is not None:
                out.append(cur)
                cur = None
            continue
        if ln[0].isspace() and cur is not None:
            cur += ln
        else:
            if cur is not None:
                out.append(cur)
            cur = ln
    if cur is not None:
        out.append(cur)
    reflowed = "\n".join(out)
    n_after, share_after = _one_word_share(reflowed)
    return reflowed, {
        "lines_before": n_before,
        "one_word_share_before": round(share_before, 3),
        "lines_after": n_after,
        "one_word_share_after": round(share_after, 3),
    }


def pdf_creation_date(path: Path) -> date | None:
    """Best-effort PDF publication date from the ``/CreationDate`` metadata.

    Parses the leading ``YYYYMMDD`` of a ``D:YYYYMMDDHHmmSS...`` string into a
    :class:`datetime.date`. Returns ``None`` if the metadata is absent or
    unparseable (missing/corrupt PDF, no CreationDate, malformed value, or an
    impossible date) — callers treat ``None`` as "date unknown".
    """
    try:
        from pypdf import PdfReader

        meta = PdfReader(str(path)).metadata
        raw = meta.get("/CreationDate") if meta else None
        if not raw:
            return None
        m = _PDF_DATE_RE.match(str(raw))
        if m is None:
            return None
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:  # unreadable PDF / impossible date / anything else -> unknown
        return None

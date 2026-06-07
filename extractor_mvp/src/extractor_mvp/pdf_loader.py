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

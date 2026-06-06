"""PDF text extraction via pypdf. No OCR, no fallback — Marker is post-abstract."""

from __future__ import annotations

from pathlib import Path
from typing import Literal


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

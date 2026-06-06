"""Canonical text representation of a paper. Extraction spans reference offsets
into ``ParsedPaper.text``."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PageSpan(BaseModel):
    """Maps a character range in ``ParsedPaper.text`` to a physical page number."""

    model_config = {"frozen": True}
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    page: int = Field(ge=1)


class ParsedPaper(BaseModel):
    """All extraction spans reference offsets into ``text``."""

    text: str
    source: str = Field(description="Filename or DOI for traceability")
    parser: Literal["pdftotext", "pypdf", "marker", "manual"] = "manual"
    pages: list[PageSpan] = Field(default_factory=list)  # optional; may be empty

    def page_for_offset(self, offset: int) -> int | None:
        """Return the 1-indexed page number containing ``offset``, or None."""
        for span in self.pages:
            if span.start <= offset < span.end:
                return span.page
        return None

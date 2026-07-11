"""Corpus-composition registry: papers deliberately excluded from AESPA statistics.

An exclusion is a RECORDED decision with its rationale, never a silent deletion — a
vanished paper is the same provenance failure AESPA exists to prevent. The PDF and any
prior result JSON are kept; this registry is the single source of truth that removes a
paper from analysis and forces every aggregate to state its denominator on its face
(``N PDFs present · M excluded · N-M analysed``).
"""

from __future__ import annotations

#: paper_id -> rationale. Excluded from every corpus statistic.
EXCLUDED_PAPERS: dict[str, str] = {
    "cabral_2017": (
        "Review / modelling paper (Cabral, Kringelbach & Deco 2017, NeuroImage, "
        "'Models and mechanisms'). No Methods section; no preprocessing performed. "
        "Its MISSING_FROM_PAPER fields are not-applicable, not underreporting. "
        "Excluded from all corpus statistics."
    ),
}


def is_excluded(paper_id: str) -> bool:
    """True iff ``paper_id`` is registered as excluded from corpus statistics."""
    return paper_id in EXCLUDED_PAPERS

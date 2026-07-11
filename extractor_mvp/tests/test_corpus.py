"""Corpus exclusion registry."""

from __future__ import annotations

from extractor_mvp.corpus import EXCLUDED_PAPERS, is_excluded


def test_cabral_is_excluded_with_rationale() -> None:
    assert is_excluded("cabral_2017") is True
    assert is_excluded("chen_2015") is False
    assert "cabral_2017" in EXCLUDED_PAPERS
    # the rationale is recorded, not a bare flag
    assert "Review" in EXCLUDED_PAPERS["cabral_2017"]
    assert "no preprocessing" in EXCLUDED_PAPERS["cabral_2017"].lower()

"""Tier-5 (corrupted-source tolerant) resolution tests — synthetic, offline.

Tier 5 recoveries are now CONSUMED by the builders (v0.4.0): a recovered span is kept and
marked ``Extracted.span_recovered=True`` (base_pipeline additionally runs the value-support
guard — see test_base_pipeline_extraction.py). These tests pin the resolver behavior directly,
including the two safety arms:
  - arm (ii): an EXACT/clean match is never touched by tier 5 (recovered stays False, span
    unchanged) — this is what guarantees no clean extraction moved when tier 5 was added.
  - arm (iii): a genuinely-absent quote still fails (the hallucination guard holds after tier 5).
Also pins ``quote_supports_value`` (the firewall-clean base_pipeline value-support helper).
"""

from __future__ import annotations

import pytest

from extractor_mvp.span_resolver import quote_supports_value, resolve_quote


def test_exact_match_not_recovered() -> None:
    """arm (ii): a quote that matches exactly resolves at tier 1 — tier 5 is unreachable."""
    text = "the data were processed with fMRIPrep version 20.2.3 and smoothed."
    r = resolve_quote("processed with fMRIPrep version 20.2.3", text)
    assert r.span is not None
    assert r.recovered is False
    assert r.span.text == "processed with fMRIPrep version 20.2.3"


# arm (ii), property form: a fixed fixture of clean-resolving (quote, text) pairs — NO live LLM
# run — each must resolve with recovered is False and a stable, identical (start, end, text) on
# repeat. Arm-(ii) holds by construction (tier 5 is appended AFTER tiers 1-4 and is unreachable
# once one matches), so any of these moving would be a real regression, not fixture drift.
_CLEAN_PAIRS = [
    ("processed with fMRIPrep version 20.2.3", "we then processed with fMRIPrep version 20.2.3."),
    ("the HCP minimal preprocessing pipeline", "using the HCP minimal preprocessing pipeline here"),
    ("registered to fsaverage", "surfaces were registered to fsaverage for analysis"),
    ("C-PAC (v1.8)", "ran with C-PAC (v1.8) on the cluster"),
]


@pytest.mark.parametrize("quote,text", _CLEAN_PAIRS)
def test_clean_resolutions_never_recovered_and_stable(quote: str, text: str) -> None:
    first = resolve_quote(quote, text)
    assert first.span is not None
    assert first.recovered is False
    assert first.span.text == quote  # exact tier-1 match: span covers the quote verbatim
    second = resolve_quote(quote, text)  # determinism: identical (start, end, text) on repeat
    assert second.span is not None
    assert (second.span.start, second.span.end, second.span.text) == (
        first.span.start,
        first.span.end,
        first.span.text,
    )


def test_quote_supports_value_present_and_absent() -> None:
    """arm (iii) helper: value-support is substring-after-normalization, never fuzzy."""
    # Value stated in the quote -> supported.
    assert quote_supports_value("fMRIPrep", "the data followed fMRIPrep (Esteban 2019)") is True
    # Acronym present via the 'Full Name (ACRONYM)' first-use form -> supported.
    assert (
        quote_supports_value(
            "C-PAC",
            "the Configurable Pipeline for the Analysis of Connectomes (C-PAC) was used",
        )
        is True
    )
    # viduarre: value INFERRED from a citation, not stated in the quote -> unsupported.
    assert (
        quote_supports_value(
            "HCP minimal preprocessing pipeline",
            "Spatial preprocessing was applied using the procedure described by Glasser et al.",
        )
        is False
    )


def test_whitespace_deletion_recovers() -> None:
    """Run-together words (pypdf dropped inter-word spaces) recover, flagged."""
    text = "preprocessing usingtheconfigurablepipeline for connectomes was applied."
    r = resolve_quote("using the configurable pipeline", text)
    assert r.span is not None
    assert r.recovered is True
    # recovered span points at the real (corrupted) source bytes
    assert "usingtheconfigurablepipeline" in r.span.text


def test_injected_marker_recovers() -> None:
    """An injected citation marker mid-quote ("[ 62]") is normalized away."""
    text = "we used the Analysis Pipeline [ 62] for connectomes here."
    r = resolve_quote("the Analysis Pipeline for connectomes", text)
    assert r.span is not None
    assert r.recovered is True


def test_linebreak_hyphenation_resolves() -> None:
    """Line-break hyphenation ("us-\\ning") already resolves at the existing tiers (not tier 5)."""
    text = "the signal was processed us-\ning a standard pipeline downstream."
    r = resolve_quote("processed using a standard pipeline", text)
    assert r.span is not None  # handled pre-tier-5; recovered flag not required


def test_ligature_resolves_via_unicode() -> None:
    """The ﬁ ligature folds via the existing Unicode tier; tier 5 also composes with it."""
    text = "with minor modiﬁcations described below in the methods."
    r = resolve_quote("with minor modifications described below", text)
    assert r.span is not None  # handled by the Unicode tier; recovered flag not required


def test_combined_mangle_needs_tier5() -> None:
    """A ligature AND whitespace-deletion together defeat the existing tiers -> tier 5 recovers."""
    text = "processed usingminormodiﬁcations here downstream."
    r = resolve_quote("processed using minor modifications", text)
    assert r.span is not None
    assert r.recovered is True


def test_hallucination_still_fails() -> None:
    """arm (iii) SYNTHETIC: a quote whose content is absent must still fail after tier 5.

    The corpus has no natural hallucination case (Phase-1 adjudication: all drops trace to real
    mangled source), so the guard can only be verified synthetically — this is that test."""
    text = "the data were processed with a standard pipeline and smoothed at 6mm."
    r = resolve_quote("registered to a bespoke quantum flux atlas", text)
    assert r.span is None
    assert r.recovered is False
    assert r.failure_reason == "quote_not_found"


def test_font_glyph_mangle_deliberately_not_recovered() -> None:
    """The font-specific multiplication-sign -> /C2 mangle is NOT folded (module note): unresolved.

    Recovering it would require treating '/C2' as that glyph, but '/C<digit>' are font glyph codes
    that map to different glyphs across papers -- a wrong-match risk that fails the never-fuzzy
    invariant.
    """
    text = "resampling them into 3 /C2 3 /C2 3m m 3 voxels finally."
    r = resolve_quote("resampling them into 3 \u00d7 3 \u00d7 3 mm3 voxels", text)
    assert r.span is None


def test_tolerant_match_still_requires_uniqueness() -> None:
    """Tier 5 is substring-exact after normalization, not fuzzy: two matches -> ambiguous."""
    text = "usingthepipeline here and also usingthepipeline there."
    r = resolve_quote("using the pipeline", text)
    assert r.span is None
    assert r.failure_reason == "quote_ambiguous"

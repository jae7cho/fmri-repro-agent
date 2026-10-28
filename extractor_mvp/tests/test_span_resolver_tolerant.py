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


def test_quote_supports_value_short_name_substring_hole() -> None:
    """Regression: a short value must NOT be reported 'supported' by matching inside a longer word.

    Before the token-boundary fix, ``ANTs`` matched ``Av-ANTS``/``particip-ANTS`` and ``FIX`` matched
    ``FIX-ation`` under whitespace-deleted substring, so a citation-only quote defeated the
    value-support guard by the author's own name -> fabricated EXTRACTED. This is the viduarre
    failure mode with a short pipeline name.
    """
    assert (
        quote_supports_value("ANTs", "normalization followed the method of Avants et al.") is False
    )
    assert quote_supports_value("ANTs", "after preprocessing, participants were scanned") is False
    assert quote_supports_value("FIX", "a fixation cross was presented at screen center") is False
    # But real token presence (incl. surface mangling that splits the token) still supports:
    assert quote_supports_value("ANTs", "registered with ANTs (Avants 2011)") is True
    assert quote_supports_value("fMRIPrep", "processed with fMRI Prep then analyzed") is True


# Blast-radius guard: quote_supports_value is called ONLY on tier-5-recovered base_pipeline spans,
# so its entire production population is v0.4.0's recovered base_pipeline keeps. These are the real
# (value, quote) pairs recorded across the dumps (HARD_DROP_AUDIT.jsonl for liu/oconnor/weber/
# viduarre; generalize_ab.jsonl for derosa — see the doc on the run disagreement). The token-boundary
# fix must not flip any keep True->False (that would silently regress a v0.4.0 EXTRACTED to a deferral).
_RECOVERED_BASE_PIPELINE = [
    (
        "FCP analysis scripts",
        "FCP analysis scripts (version 1.1-beta) were used to pre-process",
        True,
    ),
    (
        "Configurable Pipeline for the Analysis of Connectomes (C-PAC)",
        "Nipype-based [62] Configurable Pipeline for the Analysis of Connectomes [1] "
        "(C-PAC version 0.4.0 [63]).",
        True,
    ),
    (
        "C-PAC",
        "based on the configurable pipeline for the analysis of connectomes (C-PAC) (https://x) [83]",
        True,
    ),
    # derosa: the most exposed keep (parenthetical value -> 3 variants incl. dotted "version 5.0.10";
    # drop cause is the URL-adjacent "( http" spacing mangle). Matches via the "FSL suite" variant.
    (
        "FSL suite (version 5.0.10)",
        "carried out using the FSL suite (version 5.0.10) (http://fsl.fmrib.ox.ac.uk), "
        "including motion correction via ICA-AROMA",
        True,
    ),
    # viduarre: value INFERRED from a citation -> intended DEFERRAL, not a keep (must stay False).
    ("HCP minimal preprocessing pipeline", "the procedure described by Glasser et al. 40.", False),
]


@pytest.mark.parametrize("value,quote,expected", _RECOVERED_BASE_PIPELINE)
def test_recovered_base_pipeline_keeps_unregressed(value: str, quote: str, expected: bool) -> None:
    # KNOWN LIMITATION (documented in docs/findings/value-support-guard-substring-hole.md): a citation
    # marker interleaved INSIDE an acronym ("C-P [1] A C") would now flip True->False vs the old
    # marker-deleting matcher. It does not occur in the recorded population, and it errs toward
    # deferral (safe: a recall loss, never a fabrication). These recorded keeps are unaffected.
    assert quote_supports_value(value, quote) is expected


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


def test_font_glyph_mangle_recovered_by_tier6_without_naming_the_glyph() -> None:
    """UNTIL 2026-10-28 this test pinned the exclusion: the /C2 mangle was NOT folded, because
    '/C<digit>' are font glyph codes that map to different glyphs across papers. Tier 5 still does
    not fold it. Tier 6 (the author's item 1, DESIGN_coverage_expansion.md B14) answers the recorded
    reason as DELTA_glyph_leak_span_recovery.md proposed: the run matches exactly ONE quote
    character with no claim about which glyph it is, and the substitution is named on the span.
    """
    text = "resampling them into 3 /C2 3 /C2 3m m 3 voxels finally."
    r = resolve_quote("resampling them into 3 \u00d7 3 \u00d7 3 mm3 voxels", text)
    assert r.span is not None and r.recovered is True
    assert r.repairs == ("\u00d7→/C2", "\u00d7→/C2")
    # and a glyph code never matches MORE than one character: two quote characters for one run fail
    assert (
        resolve_quote("resampling them into 3 \u00d7\u00d7 3 \u00d7 3 mm3 voxels", text).span
        is None
    )


def test_tolerant_match_still_requires_uniqueness() -> None:
    """Tier 5 is substring-exact after normalization, not fuzzy: two matches -> ambiguous."""
    text = "usingthepipeline here and also usingthepipeline there."
    r = resolve_quote("using the pipeline", text)
    assert r.span is None
    assert r.failure_reason == "quote_ambiguous"


# ---------------------------------------------------------------------------
# Tier 6 — the named source-text repair (2026-10-28, DESIGN_coverage_expansion.md B14 item 1).
# The excerpts are REAL mangled clauses from contaminated corpus papers (one clause each, not the
# paper), because a synthetic glyph alone would not exercise the composition with tier 5's
# whitespace-deletion (DELTA_glyph_leak_span_recovery.md §4a).
# ---------------------------------------------------------------------------

_AGTZIDIS = (
    "with repetition time (TR) of 2 s and 3 /C2 3 /C2 3m m3 voxel size.\n2.2. Motion estimation"
)
_BINDER = (
    "problem-solving, and plan-\nning is consistent with several recent ªndings regarding\n"
    "cerebral lateralization."
)
_POLDRACK = "and spectral ﬁltering 45. Frames with framewise displacement 40.25 mm\nwere censored, as well as"


def test_tier6_glyph_code_matches_one_quote_character_named() -> None:
    """agtzidis: the text layer leaks ``\u00d7`` as ``/C2`` twice AND splits ``3 mm3`` as ``3m m3``; the
    repair composes with tier 5's whitespace deletion and names both substitutions."""
    r = resolve_quote("3 \u00d7 3 \u00d7 3 mm3 voxel size", _AGTZIDIS)
    assert r.failure_reason is None and r.recovered is True
    assert r.repairs == ("\u00d7→/C2", "\u00d7→/C2")
    assert r.span is not None
    assert r.span.text == "3 /C2 3 /C2 3m m3 voxel size"
    assert r.span.repairs == ["\u00d7→/C2", "\u00d7→/C2"]


def test_tier6_binder_ligature_glyph_matches_fi() -> None:
    r = resolve_quote(
        "consistent with several recent findings regarding cerebral lateralization", _BINDER
    )
    assert r.failure_reason is None and r.recovered is True
    assert r.repairs == ("fi→ª",)
    assert r.span is not None and "ªndings" in r.span.text


def test_tier6_quote_symbol_matches_a_source_digit() -> None:
    """poldrack: the text layer prints ``>`` as ``4`` (``FD 40.25 mm`` for ``FD >0.25 mm``)."""
    r = resolve_quote("Frames with framewise displacement >0.25 mm were censored", _POLDRACK)
    assert r.failure_reason is None and r.recovered is True
    assert r.repairs == (">→4",)
    assert r.span is not None and r.span.text.startswith("Frames with framewise displacement 40.25")


@pytest.mark.parametrize(
    ("quote", "text"),
    [
        ("3 \u00d7 3 \u00d7 4 mm3 voxel size", _AGTZIDIS),  # a digit changed
        ("3 \u00d7 3 \u00d7 3 mm3 voxel sizes are", _AGTZIDIS),  # a word changed
        ("Frames with framewise displacement >0.35 mm were censored", _POLDRACK),  # a digit changed
        ("Frames with framewise displacement >0.25 mm were kept", _POLDRACK),  # a word changed
        ("consistent with several recent findings regarding spinal lateralization", _BINDER),
    ],
)
def test_tier6_fails_closed_on_any_other_difference(quote: str, text: str) -> None:
    """The repair is substring-only: every character outside a named substitution must match."""
    r = resolve_quote(quote, text)
    assert r.span is None and r.failure_reason == "quote_not_found"


def test_tier6_is_bounded() -> None:
    """More than _MAX_REPAIRS substitutions is not a repair, it is a different sentence."""
    text = "values 4 a 4 b 4 c 4 d end"
    assert resolve_quote("values > a > b > c > d end", text).span is None
    assert resolve_quote("values > a > b > c 4 d end", text).repairs == (">→4", ">→4", ">→4")


def test_tier6_two_candidate_sites_are_ambiguous_not_guessed() -> None:
    text = "FD 40.2 mm here. FD 40.2 mm there."
    r = resolve_quote("FD >0.2 mm", text)
    assert r.span is None and r.failure_reason == "quote_ambiguous"


def test_tier6_never_touches_a_clean_or_tier5_match() -> None:
    """arm (ii) for tier 6: a quote any earlier tier resolves keeps its span, recovered flag and an
    empty repairs list. The ``ﬁ`` ligature keeps folding silently at tier 3."""
    for quote, text in _CLEAN_PAIRS:
        r = resolve_quote(quote, text)
        assert r.recovered is False and r.repairs == () and r.span.repairs == []
    r = resolve_quote("spectral filtering", "and spectral ﬁltering 45. Frames")
    assert r.span is not None and r.recovered is False and r.repairs == ()


def test_tier6_symbol_never_matches_a_symbol_or_a_space() -> None:
    """A quote symbol stands for a LETTER or DIGIT only: ``=`` for ``¼`` (symbol for symbol) and
    ``>`` for a space are not repairs."""
    assert resolve_quote("sigma = 2", "sigma ¼ 2 voxels").span is None
    assert resolve_quote("FD > 0.2", "FD   0.2").span is None

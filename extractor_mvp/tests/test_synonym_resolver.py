"""Synonym resolver — precision-only mapping, underspecification-preserving."""

from __future__ import annotations

from extractor_mvp.synonym_resolver import (
    INTENSITY_CONVENTION_SYNONYMS,
    SURFACE_REGISTRATION_SYNONYMS,
    SURFACE_REGISTRATION_UNDERSPECIFIED,
    TARGET_SPACE_SYNONYMS,
    TARGET_SPACE_UNDERSPECIFIED,
    resolve_to_literal,
)


def _ts(raw, value_context=None):
    return resolve_to_literal(raw, TARGET_SPACE_SYNONYMS, TARGET_SPACE_UNDERSPECIFIED)


# --- the load-bearing invariant: underspecified MNI stays unresolved --------


def test_mni_is_underspecified_not_coerced():
    for raw in ("MNI", "MNI152", "MNI standard space", "normalized to MNI space"):
        r = _ts(raw)
        assert r.status == "underspecified", raw
        assert r.resolved is None, raw


def test_specific_target_space_resolves():
    assert _ts("MNI152NLin6Asym").resolved == "MNI152NLin6Asym"
    assert _ts("MNI152NLin6Asym").status == "resolved"


def test_fsl_mni152_resolves_to_nlin6asym():
    # FSL ships NLin6Asym unambiguously -> more specific, allowed
    r = _ts("registered to the FSL MNI152 template")
    assert r.resolved == "MNI152NLin6Asym" and r.status == "resolved"


def test_fonov_2009c_resolves():
    assert _ts("the Fonov 2009c template").resolved == "MNI152NLin2009cAsym"


# --- intensity convention value-context -------------------------------------


def _conv(raw, value_context=None):
    return resolve_to_literal(raw, INTENSITY_CONVENTION_SYNONYMS, None, value_context)


def test_mode_with_value_1000_resolves():
    assert _conv("mode", 1000).resolved == "global_mode_1000"
    assert _conv("normalized to a mode of 1,000").resolved == "global_mode_1000"


def test_mode_with_wrong_or_no_value_does_not_resolve():
    assert _conv("mode", 10000).status == "no_match"  # FSL mode-default isn't a member
    assert _conv("mode", None).status == "no_match"


def test_median_value_context_disambiguates():
    assert _conv("median", 1000).resolved == "global_median_1000"
    assert _conv("median", 10000).resolved == "fsl_median_10000"


def test_zscore_resolves_without_value():
    assert _conv("z-score").resolved == "voxel_temporal_zscore"
    assert _conv("voxel-wise z-score").resolved == "voxel_temporal_zscore"


# --- surface registration underspecification --------------------------------


def test_freesurfer_alone_is_underspecified():
    r = resolve_to_literal(
        "FreeSurfer", SURFACE_REGISTRATION_SYNONYMS, SURFACE_REGISTRATION_UNDERSPECIFIED
    )
    assert r.status == "underspecified" and r.resolved is None


def test_folding_based_registration_resolves():
    r = resolve_to_literal(
        "folding-based registration",
        SURFACE_REGISTRATION_SYNONYMS,
        SURFACE_REGISTRATION_UNDERSPECIFIED,
    )
    assert r.resolved == "freesurfer_recon"


def test_no_match_and_empty():
    assert (
        resolve_to_literal("a bespoke in-house atlas", TARGET_SPACE_SYNONYMS).status == "no_match"
    )
    assert resolve_to_literal(None, TARGET_SPACE_SYNONYMS).status == "no_match"


def test_ambiguous_when_two_members_claim_term():
    syn = {"member_a": ["foo"], "member_b": ["foo bar"]}
    # "foo bar" contains both "foo" (a) and "foo bar" (b) -> ambiguous
    assert resolve_to_literal("foo bar baz", syn).status == "ambiguous"

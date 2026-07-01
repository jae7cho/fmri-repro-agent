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


# --- Tier-2 additions: target_surface typo + token-prefix containment collapse,
#     surface_registration sphere/recon-all, fsl grand-mean 10000 ---------------

from extractor_mvp.synonym_resolver import TARGET_SURFACE_SYNONYMS  # noqa: E402


def _tsurf(raw, value_context=None):
    return resolve_to_literal(raw, TARGET_SURFACE_SYNONYMS, None, value_context)


def _surf(raw, value_context=None):
    return resolve_to_literal(
        raw, SURFACE_REGISTRATION_SYNONYMS, SURFACE_REGISTRATION_UNDERSPECIFIED, value_context
    )


def test_fsaverge5_typo_resolves():
    r = _tsurf("down-sampled to the fsaverge5 surface grid")
    assert r.resolved == "fsaverage5" and r.status == "resolved"


def test_fsaverage5_correct_spelling_resolves():
    # The bug being fixed: "fsaverage5" also matched "fsaverage", going ambiguous.
    # Token-prefix containment collapse drops "fsaverage" (next char "5" is alnum).
    r = _tsurf("fsaverage5")
    assert r.resolved == "fsaverage5" and r.status == "resolved"


def test_fsaverage6_resolves():
    r = _tsurf("fsaverage6")
    assert r.resolved == "fsaverage6" and r.status == "resolved"


def test_both_fsaverage5_and_6_is_ambiguous():
    # Sanity: collapse drops the shared "fsaverage" prefix but the two distinct
    # specific members both remain -> ambiguous (not silently coerced).
    r = _tsurf("projected to fsaverage5 and later fsaverage6")
    assert r.status == "ambiguous" and r.resolved is None


def test_sphere_registration_underspecified():
    r = _surf("registration was performed via a sphere registration")
    assert r.status == "underspecified" and r.resolved is None


def test_recon_all_resolves_freesurfer():
    r = _surf("surfaces generated using FreeSurfer's default recon-all (version 5.0)")
    assert r.resolved == "freesurfer_recon" and r.status == "resolved"


_CHEN_GLOBAL_MEAN = "normalized the 4D global mean intensity to 10,000"


def test_chen_global_mean_10000_with_value_context():
    # value_context path: "global mean@10000" fires when the sibling numeric == 10000.
    r = _conv(_CHEN_GLOBAL_MEAN, 10000)
    assert r.resolved == "fsl_grand_mean_10000" and r.status == "resolved"


def test_chen_global_mean_10000_without_value_context():
    # direct-phrase fallback path: resolves even when no numeric context is supplied.
    r = _conv(_CHEN_GLOBAL_MEAN, None)
    assert r.resolved == "fsl_grand_mean_10000" and r.status == "resolved"

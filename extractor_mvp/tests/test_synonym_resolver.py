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
    """global_mode_1000 resolves on convention-bearing phrasing, not the bare word
    'mode'. Bare 'mode@1000' was removed because it false-fired on 'default mode' /
    'mode of covariation' (Marek false-fire probe); the term must denote the
    convention, with the number only disambiguating."""
    # positive: convention-bearing terms + value context, and direct phrase
    assert _conv("mode value", 1000).resolved == "global_mode_1000"
    assert _conv("mode scaling", 1000).resolved == "global_mode_1000"
    assert _conv("normalized to a mode of 1,000").resolved == "global_mode_1000"
    # negative: the bare word no longer resolves even with the number
    assert _conv("mode", 1000).status != "resolved"


def test_mode_with_wrong_or_no_value_does_not_resolve():
    assert _conv("mode", 10000).status == "no_match"  # FSL mode-default isn't a member
    assert _conv("mode", None).status == "no_match"


def test_poldrack_mode_1000_token_resolves_scoped():
    """Poldrack 2015: the LLM emits the abbreviated canonical token 'mode_1000'
    (drops the 'global_' prefix). The value-context-scoped 'mode_1000@1000' alias
    resolves it, WITHOUT reopening the Marek false-fires."""
    # positive: the emitted token + value 1000 -> global_mode_1000
    assert _conv("mode_1000", 1000).resolved == "global_mode_1000"
    # @1000 scoping: wrong / absent value context must NOT resolve via this alias
    assert _conv("mode_1000", 10000).status != "resolved"
    assert _conv("mode_1000", None).status != "resolved"
    # Marek-safety (adversarial, with the new alias present): the underscored token is
    # not a substring of the false-fire phrases, so "default mode ... " + value 1000
    # still does NOT resolve -- the regression the bare 'mode@1000' caused stays closed.
    assert _conv("A default mode of brain function", 1000).status != "resolved"
    assert _conv("the median study sample size is about 25", 1000).status != "resolved"


def test_median_value_context_disambiguates():
    """Value-context flips median between global_median_1000 (1000) and
    fsl_median_10000 (10000) — but only via convention-bearing phrasing. Bare
    'median@1000'/'median@10000' were removed because 'median' alone false-fired on
    statistics vocabulary (median sample size / effect size — Marek false-fire probe)."""
    # positive: convention-bearing term, value context flips the member
    assert _conv("median scaling", 1000).resolved == "global_median_1000"
    assert _conv("median scaling", 10000).resolved == "fsl_median_10000"
    assert _conv("median intensity", 1000).resolved == "global_median_1000"
    # negative: bare 'median' no longer resolves at either value context
    assert _conv("median", 1000).status != "resolved"
    assert _conv("median", 10000).status != "resolved"


def test_zscore_is_not_an_intensity_convention():
    """Per-voxel temporal z-scoring is NOT a magnitude-scaling convention (z-score
    category-error corpus finding), so it must not resolve in the intensity table.
    PATH 0: the Literal member + its no-magnitude validator remain in the schema
    (see tests/spec/test_intensity_zscore.py); only the resolver mapping was removed.
    Rewritten from the former test_zscore_resolves_without_value, which asserted the
    now-removed behavior."""
    assert _conv("z-score").status != "resolved"
    assert _conv("z-scored").status != "resolved"
    assert _conv("voxel-wise z-score").status != "resolved"
    assert (
        _conv("subtracting its mean and then dividing by its temporal standard deviation").status
        != "resolved"
    )


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


# --- v6 intensity pass: Marek false-fire regressions + true-positive preservation --
# Justification: numeric/value-context probe on Marek 2022 + 25-paper corpus grep.
# Bare-word value-context aliases (median@N, mode@1000, mean intensity@10000) and the
# z-score entry were removed; see the commit message for the probe details.


def test_intensity_false_fire_regressions_do_not_resolve():
    """Statistics/anatomy vocabulary + a magnitude number must NOT resolve to a
    convention (the core Marek false-fire risk)."""
    assert _conv("the median study sample size is about 25", 1000).status != "resolved"
    assert _conv("the median study sample size is about 25", 10000).status != "resolved"
    assert _conv("A default mode of brain function", 1000).status != "resolved"
    assert _conv("registering the mean intensity image", 10000).status != "resolved"


def test_intensity_true_positives_preserved():
    """Real corpus phrasings still resolve to the correct convention."""
    # Marek 2022: whole-brain-mode value of 1,000
    assert (
        _conv("intensity normalization to a whole-brain-mode value of 1,000", 1000).resolved
        == "global_mode_1000"
    )
    # Chen 2015: 4D global mean intensity to 10,000
    assert _conv("global mean intensity to 10,000", 10000).resolved == "fsl_grand_mean_10000"
    assert _conv("median scaling", 1000).resolved == "global_median_1000"
    assert _conv("median scaling", 10000).resolved == "fsl_median_10000"


def test_grand_mean_hyphen_and_space_both_resolve():
    """Hyphen false-negative fix: both spellings resolve at vc=10000 (previously only
    the hyphenated 'grand-mean scaling@10000' alias existed)."""
    assert _conv("grand mean scaling", 10000).resolved == "fsl_grand_mean_10000"
    assert _conv("grand-mean scaling", 10000).resolved == "fsl_grand_mean_10000"

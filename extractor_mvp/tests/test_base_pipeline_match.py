"""Pin the pre-registered Tier-A / Tier-B base_pipeline matching rules on the worked examples.

These are unit checks of the matcher, NOT a scoring run — no ground-truth labels are involved (there
are none yet). They lock the equivalence relation before any hallucination rate is ever computed.
"""

from __future__ import annotations

from extractor_mvp.base_pipeline_match import (
    matches_tier_a,
    matches_tier_b,
    normalize,
)


def test_normalize_worked_forms() -> None:
    assert normalize("SPM99") == "spm"  # fused version digit stripped
    assert normalize("SPM") == "spm"
    assert normalize("CPAC") == normalize("C-PAC") == "cpac"  # punctuation, whole-token
    assert normalize("FSL suite (version 5.0.10)") == "fsl"  # wrapper + version stripped
    assert normalize("FCP analysis scripts (version 1.1-beta)") == "fcpanalysisscripts"


def test_tier_a_strict_identity() -> None:
    # version-insensitive at the name level (version lives in its own field)
    assert matches_tier_a(["SPM99"], ["SPM"]) is True
    assert matches_tier_a(["CPAC"], ["C-PAC"]) is True
    assert matches_tier_a(["FSL"], ["FSL suite (version 5.0.10)"]) is True
    # set membership (D4): predicted subset of label
    assert matches_tier_a(["AFNI"], ["AFNI", "FreeSurfer"]) is True
    # genuine wrong pipeline does NOT match under strict identity
    assert matches_tier_a(["fMRIPrep"], ["C-PAC"]) is False
    # NO substring: a short name must not match inside a longer one
    assert matches_tier_a(["ANT"], ["Avants"]) is False
    assert matches_tier_a(["SPM"], ["SPMs were projected"]) is False  # 'spm' != 'spmswereprojected'
    assert matches_tier_a([], ["C-PAC"]) is False  # empty prediction never matches


def test_tier_b_alias_equivalent() -> None:
    # KB recognize(): full name ≡ acronym for the 4 KB pipelines
    assert (
        matches_tier_b(["Configurable Pipeline for the Analysis of Connectomes"], ["C-PAC"]) is True
    )
    assert (
        matches_tier_a(["Configurable Pipeline for the Analysis of Connectomes"], ["C-PAC"])
        is False
    )
    # pre-registered toolbox alias: full name ≡ acronym for non-KB toolboxes
    assert matches_tier_b(["Statistical Parametric Mapping 12"], ["SPM12"]) is True
    assert matches_tier_b(["FMRIB Software Library"], ["FSL"]) is True
    assert matches_tier_b(["Advanced Normalization Tools"], ["ANTs"]) is True
    # Tier B still rejects a genuinely different pipeline
    assert matches_tier_b(["fMRIPrep"], ["C-PAC"]) is False


def test_version_strip_is_boundary_aware() -> None:
    """The version-strip regex strips a version token WITHOUT eating an adjacent name.

    The old greedy `v?\\d+(\\.\\d+)*[a-z-]*` consumed trailing letters, so a name starting with a
    digit (`3dvolreg`) or a hyphen-suffixed word after a version vanished entirely.
    """
    # a name that starts with a digit must survive intact (was eaten -> "" before the fix)
    assert normalize("3dvolreg") == "3dvolreg"
    assert normalize("fsl6") == "fsl6"  # glued digit is not a version token
    # a real version, space- or paren-separated, is stripped; the name is kept
    assert normalize("ANTs 2.3.1") == "ants"
    assert normalize("fMRIPrep 20.2.1") == "fmriprep"
    assert normalize("FSL suite (version 5.0.10)") == "fsl"
    assert normalize("FCP analysis scripts (version 1.1-beta)") == "fcpanalysisscripts"
    # bare integer token (e.g. "… Mapping 12") is dropped as a version
    assert normalize("Mapping 12") == "mapping"
    # the pinned worked pair still holds after the change
    assert normalize("C-PAC") == normalize("CPAC") == "cpac"
    assert matches_tier_a(["FSL"], ["FSL suite (version 5.0.10)"]) is True

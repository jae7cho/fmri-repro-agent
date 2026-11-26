"""The resolver against the wordings the 2026-11-24 audit found in stored records (held-out papers
excluded). Each case is a real wording and the member it must resolve to (None: kept unresolved,
in the paper's words)."""

from __future__ import annotations

import pytest

from extractor_mvp.coverage_fields import COVERAGE_SPECS
from extractor_mvp.extractor import _resolve_term
from extractor_mvp.synonym_resolver import resolve_to_literal

_SPEC = {s.dotted: s for s in COVERAGE_SPECS}
MOTION = "nuisance_regression.motion_expansion"


def _resolved(dotted: str, verbatim: str) -> str | None:
    s = _SPEC[dotted]
    syn = (s.synonyms, s.underspecified) if s.synonyms else None
    return _resolve_term(verbatim, s.literal_type, syn, dotted).resolved


@pytest.mark.parametrize(
    ("verbatim", "want"),
    [
        # the six parameters alone
        ("6param", "6param"),
        ("6 motion parameters", "6param"),
        ("six realignment parameters", "6param"),
        # six, derivatives and squares (or quadratic terms): the project's friston24
        ("Resting-state fMRI: six parameters plus their derivatives and squares", "friston24"),
        (
            "6 motion parameters, their derivatives, quadratic terms, and squares of derivatives",
            "friston24",
        ),
        ("6 parameters with temporal, quadratic, and quadratic temporal derivatives", "friston24"),
        (
            "6 degrees of motion, with temporal, quadratic, and quadratic temporal derivatives",
            "friston24",
        ),
        ("24 motion parameters", "friston24"),
        ("friston24", "friston24"),
        ("volterra", "friston24"),  # item 3, 2026-10-28
        ("none", "none"),
        # derivatives without squares: 12param since schema 0.8.0 (2026-11-25). Until then no
        # member fitted and these kept their words.
        ("six motion parameters and their first-order derivatives", "12param"),
        ("6 parameters and their first order derivatives", "12param"),
        ("the 6 realignment parameters and their temporal derivatives", "12param"),
        ("12 parameters (6 motion parameters and their derivatives)", "12param"),
        ("R and R\u00b4 (12 motion related regressors)", "12param"),
        ("12param", "12param"),
        # no count is stated, so no member is claimed
        ("motion parameters and their derivatives", None),
        # D2c (2026-11-25, C13): an alias since then; the plural "24 regressors" did not read it
        ("24-regressor model of motion", "friston24"),
    ],
)
def test_motion_expansion_wordings(verbatim: str, want: str | None) -> None:
    assert _resolved(MOTION, verbatim) == want


def test_aliases_match_whole_words_only() -> None:
    assert _resolved("brain_extraction.method", "optiBET") is None  # was bet through "BET"
    assert _resolved("brain_extraction.method", "BET") == "bet"
    # a plural after a whole-word alias still matches
    assert _resolved("spatial_smoothing.space", "CIFTI grayordinates space") == "template_surface"


def test_an_exact_member_is_never_claimed_by_another_members_alias() -> None:
    syn = {"a": ["alpha"], "b": ["a"]}  # "a" is b's alias and a's exact name
    assert resolve_to_literal("a", syn).resolved == "b"  # the table alone hands it to b
    from typing import Literal

    t = _resolve_term("a", Literal["a", "b"], (syn, None), None)
    assert t.resolved == "a"


@pytest.mark.parametrize(
    ("dotted", "verbatim", "want"),
    [
        # correct partial matches the audit kept (no change by the 2026-11-24 rules)
        ("scrub.interpolation_method", "least squares spectral estimation", "spectral"),
        ("scrub.criterion", "volume-to-volume RMS displacement", "fd_jenkinson"),
        ("spatial_smoothing.space", "MNI normalized brain space", "mni_volume"),
        ("segmentation.tissue_classes", "cerebrospinal_fluid", "csf"),
        ("coregistration.cost_function", "bbr", "boundary_based"),
    ],
)
def test_audited_partial_matches_still_resolve(dotted: str, verbatim: str, want: str) -> None:
    assert _resolved(dotted, verbatim) == want

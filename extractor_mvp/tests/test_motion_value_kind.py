"""Calibration of the pre-registration's operation-phrase heuristic.

Every string here is from the pre-registration itself or from a probe paper's committed quote. No
text from any paper outside the six appears, and in particular none from liu_2005, tang_2025 or
wheaton_2004 — the three uncontaminated cells (prereg C11, C26).

These are not examples. The prereg says what each string must return, so each row is a pinned
expectation; the implementation was fixed until they all held, not the reverse.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from motion_value_kind import (
    _NOT_TOOL_INITIALISMS,
    is_operation_phrase,
    is_tool_shaped,
    value_kind,
)

#: binder_1999's committed quote, prereg :113-114. binder is a probe paper, so quoting it here is
#: within the iteration licence (C11); it is also already in the prereg verbatim.
BINDER_QUOTE = (
    "All EPI images were spatially coregistered using an iterative procedure that minimizes "
    "variance in voxel intensity differences between images (Cox, 1996b)."
)
#: The same sentence with the operation word removed — the prereg's "Known limitation" case:
#: "If the extractor's value is the algorithm description rather than the word 'coregistered'".
BINDER_ALGORITHM_ONLY = (
    "an iterative procedure that minimizes variance in voxel intensity differences between images"
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # prereg :110-111 names this as the case that MUST halt rather than resolve silently.
        ("motion correction via ICA-AROMA", "undecided"),
        # prereg :116 — the word itself is an operation phrase
        ("coregistered", "operation_phrase"),
        # prereg :113-118's known limitation: a closed vocabulary cannot recognise an algorithm
        # described in prose, and that is the honest outcome rather than a defect
        (BINDER_ALGORITHM_ONLY, "undecided"),
        # prereg :102-104's tool tokens and initialisms
        ("SPM12", "tool_name"),
        ("FSL", "tool_name"),
        ("ICA-AROMA", "tool_name"),
        ("applywarp", "tool_name"),
        # the probe's target shape, derosa reading 4 (prereg :18, :152)
        ("motion correction", "operation_phrase"),
    ],
    ids=[
        "both_lists_halts",
        "coregistered",
        "binder_algorithm_only",
        "SPM12",
        "FSL",
        "ICA-AROMA",
        "applywarp",
        "motion_correction",
    ],
)
def test_the_prereg_strings_land_where_the_prereg_says(value: str, expected: str) -> None:
    assert value_kind(value) == expected


def test_binders_full_committed_quote_is_an_operation_phrase() -> None:
    """Reported because it was NOT obvious, and it is the outcome the probe turns on.

    The full quote contains "coregistered", so it is an operation phrase. It is NOT tool-shaped,
    and both of ruling 5's fixes are load-bearing in reaching that:

    * "EPI" is an initialism of two or more capitals, so without the exclusion set the quote would
      be tool-shaped AND an operation phrase, and would halt as ``undecided`` — on the very paper
      the prereg designates as the test of whether ``undecided`` is rare. A heuristic that halts on
      its own test case cannot measure it.
    * "(Cox, 1996b)" contains a four-digit year. Under the prereg's prose pattern
      ``\\w+\\s*v?\\d+`` that year matched, because ``\\w`` includes digits. Restricted to letters
      then digits, the comma between "Cox" and "1996b" means there is no match.

    So the full quote maps to state-map row 1 -> ``described_only``, which is binder's committed
    label. The ``undecided`` branch the prereg anticipates needs the value to be the algorithm
    description WITHOUT the operation word, which is the row above.
    """
    assert is_operation_phrase(BINDER_QUOTE) is True
    assert is_tool_shaped(BINDER_QUOTE) is False
    assert value_kind(BINDER_QUOTE) == "operation_phrase"


def test_the_two_tests_are_independent_so_a_double_match_can_halt() -> None:
    """Ruling 5 defect 1. The prereg's prose made ``tool_name`` require "contains none of the
    above", which makes a both-lists match impossible — while the same section says a value
    matching both is ``undecided`` and gives a string that must halt. Under the prose as written
    that string resolved to ``operation_phrase`` and never halted."""
    both = "motion correction via ICA-AROMA"
    assert is_operation_phrase(both) is True
    assert is_tool_shaped(both) is True
    assert value_kind(both) == "undecided"


def test_a_bare_year_or_count_is_not_tool_shaped() -> None:
    """Ruling 5 defect 2, directly."""
    for v in ("1996", "(Cox, 1996b)", "24 regressors", "six parameters"):
        assert is_tool_shaped(v) is False, v
    # the positive control: a real versioned token still matches
    for v in ("SPM12", "FSL 5.0.10", "v0.3 beta", "AFNI 23.1"):
        assert is_tool_shaped(v) is True, v


def test_imaging_acronyms_are_not_tool_shaped() -> None:
    """Ruling 5 defect 3, and the exclusions are named rather than pattern-hidden."""
    for v in ("EPI", "BOLD", "the EPI volumes", "BOLD time series"):
        assert is_tool_shaped(v) is False, v
    # FD and RMS are CONSUME statistics per CALL 10 Axis 2, never the value
    for v in ("mean FD", "RMS displacement"):
        assert is_tool_shaped(v) is False, v
    # and the exclusion set is a declared list, so a reader can argue with it
    assert {"EPI", "BOLD", "FD", "RMS"} <= _NOT_TOOL_INITIALISMS
    # positive control: a tool initialism of the same shape IS matched
    for v in ("SPM", "AFNI", "FSL", "CCS", "CONN", "DPABI"):
        assert is_tool_shaped(v) is True, v


def test_none_is_undecided_not_silently_classified() -> None:
    assert value_kind(None) == "undecided"


# NOT a test: the C11/C26 containment guard was tried here and removed.
#
# A test can check that the three held-out ids do not appear in this file -- but this file names
# them in the module docstring precisely to record that they are excluded, so the check fails on
# correct code. And the property that actually matters is that no SENTENCE from those papers
# appears, which cannot be checked without reading them: the check would require the very access
# it exists to forbid.
#
# So the guarantee is procedural, not tested, and saying so is more honest than an assertion that
# looks like verification and is not. What IS enforced mechanically lives in
# scripts/motion_probe.py, which refuses those three paper ids before building a client -- that is
# the access path a test can close, and it is closed and mutation-checked.

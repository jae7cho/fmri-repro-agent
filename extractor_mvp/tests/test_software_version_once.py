"""The Software row gives a version once (fix 5, the author's list of 2026-11-05): Li_2024's mention
stored the name "Statistical Parametric Mapping (SPM) 12" with the version "12", rendered "12 12"."""

from __future__ import annotations

from extractor_mvp.render import _with_version


def test_a_name_ending_with_its_version_is_not_given_it_again() -> None:
    assert _with_version("Statistical Parametric Mapping (SPM) 12", "12") == (
        "Statistical Parametric Mapping (SPM) 12"
    )
    assert _with_version("SPM12", "12") == "SPM12"


def test_a_name_without_its_version_gets_it() -> None:
    assert _with_version("CONN toolbox", "v17c") == "CONN toolbox v17c"
    assert _with_version("FSL", "6.0.4") == "FSL 6.0.4"
    assert _with_version("FSL", None) == "FSL"


def test_a_longer_number_ending_in_the_same_digits_is_not_the_version() -> None:
    assert _with_version("Tool 1.12", "12") == "Tool 1.12 12"
    assert _with_version("Tool 112", "12") == "Tool 112 12"

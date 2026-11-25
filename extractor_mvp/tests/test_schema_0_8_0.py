"""Schema 0.8.0 on the extractor side (DESIGN_prompt_schema_2026-11 D3, 2026-11-25).

The spec's own tests (tests/spec) pin the models and the migration hop. These pin what the
extractor does with them: the 12-parameter motion model and the global-signal scrub criterion, each
resolved by a rule that reads the whole wording; the scrub threshold as a one-item list from the
model's string to the report; and what the code does with the two schema values nothing writes yet
(``model_mapped``, the inference statuses). No prompt and no request schema changed in this step.

Wordings marked with a review are ones an adversarial review found resolving to a wrong member,
or taking seconds to refuse, under an earlier build of the step. The first build used two loose
patterns with a block list, and aliases; the second added trailers and a reading in running text.
"""

from __future__ import annotations

import json
import sys
import typing
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fmri_repro.spec.migrations import parse_any_version
from fmri_repro.spec.preprocessing import SCHEMA_VERSION, Preprocessing

from conftest import stub_client
from extractor_mvp import extractor as ex
from extractor_mvp import pseudocode, render
from extractor_mvp.citation_hop import described_only
from extractor_mvp.coverage_extractor import TemporalVolumeExtraction
from extractor_mvp.coverage_fields import (
    COVERAGE_NUMBER_LIST_FIELDS,
    COVERAGE_NUMERIC_FIELDS,
    COVERAGE_SPECS,
    DISTORTION_METHOD,
    MOTION_EXPANSION,
    RULE_WORDS,
    SCRUB_CRITERION,
    TERM_RULES,
    DistortionFamily,
    TermRules,
    names_no_member,
    rules_resolve,
)
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import PreprocessingExtraction, extract_preprocessing
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.quote_support import (
    _term_supported,
    coverage_value_supported,
    literal_value_supported,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import reresolve_terms as rr
import term_audit as ta

_SPEC = {s.dotted: s for s in COVERAGE_SPECS}
_MOTION = "nuisance_regression.motion_expansion"
_CRITERION = "scrub.criterion"
_METHOD = "distortion_correction.method"
_THRESHOLD = "scrub.threshold"


def _resolved(dotted: str, raw: str) -> list[str | None]:
    """The members ``extractor._process_field`` resolves the value to (a list field is split)."""
    s = _SPEC[dotted]
    syn = (s.synonyms, s.underspecified) if s.synonyms else None
    if s.value_kind == "term_list":
        items = ex._split_terms(raw, ex._keep_whole(dotted, syn))
        return [t.resolved for t in ex._resolve_term_list(items, s.literal_type, syn, dotted)]
    return [ex._resolve_term(raw, s.literal_type, syn, dotted).resolved]


# --- 12param (B1): the whole wording ------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        # the wordings stored records hold (achuthan_2023, ciric_2017, li_2024, power_2014)
        "six head motion parameters and their first order derivatives",
        "the 6 realignment parameters and their temporal derivatives",
        "six motion parameters and their first-order derivatives",
        "6 parameters and their first order derivatives",
        "6 motion parameters and their temporal derivatives",
        "R and R\u00b4 (12 motion related regressors)",
        "12 parameters (6 motion parameters and their derivatives)",
        # the nouns, the connective and the derivative, each in another form
        "the six parameters of head motion and their derivatives",
        "six translation and rotation parameters, their derivatives",
        "six rigid-body parameters with first derivates",
        "6 motion parameters + 6 derivatives",
        "six motion parameters & their first-order temporal derivatives",
        "six motion parameters and the derivate of each",
        "six motion params plus derivs",
        "six motion parameters and their first-order derivative terms",
        "SIX REALIGNMENT PARAMETERS AND THEIR TEMPORAL DERIVATIVES",
        "six motion parameters and their deriva-\ntives",
        '"six motion parameters and their derivatives."',
        "(six motion regressors and their derivatives)",
        # each alternative of the closed lists (the third review: no test reached them alone)
        "six movement parameters and their derivatives",
        "six head regressors and their derivatives",
        "six headmotion parameters and their derivatives",
        "six translational and rotational motion parameters and their derivatives",
        "six params and their derivatives",
        "six parameters of head movement and their derivatives",
        "six motion parameters, and their derivatives",
        "six motion parameters as well as their derivatives",
        "six motion parameters along with their derivatives",
        "six motion parameters and its derivatives",
        "six motion parameters and their 1st-order derivatives",
        "six motion parameters and their 1st derivatives",
        "six motion parameters and their time derivatives",
        "six motion parameters and their derivations",
        "six motion parameters and their derivative regressors",
        # what may stand around the wording: spaces, quotes, a bracket, a full stop
        " six motion parameters and their derivatives",
        "six motion parameters and their derivatives\n",
        "'six motion parameters and their derivatives'",
        "[12 parameters]",
        # the count of twelve written out
        "12 motion parameters",
        "twelve motion regressors",
        "12 head-motion parameters",
        "12 realignment parameters",
        "12 movement parameters",
        "the 12 motion parameters",
        "R and R' (12 motion related regressors)",
        "R and R\u2032 (12 motion related regressors)",
        "twelve parameters (six motion parameters and their derivatives)",
        "12 parameters",
        "12-parameter motion model",
        "12P",
        "12param",
    ],
)
def test_six_with_derivatives_is_the_12_parameter_model(raw: str) -> None:
    assert _resolved(_MOTION, raw) == ["12param"]


_SIX = "six motion parameters"
_PLAIN = f"{_SIX} and their derivatives"


@pytest.mark.parametrize(
    ("raw", "twin"),
    [
        # Each wording says something the pattern has no place for, and keeps its words. The twin
        # beside it resolves, which shows the pair's difference is what the rule refused.
        # the count
        ("five motion parameters and their derivatives", _PLAIN),
        ("16 motion parameters and their derivatives", "6 motion parameters and their derivatives"),
        (
            "0.6 motion parameters and their derivatives",
            "6 motion parameters and their derivatives",
        ),
        # six of something else: "regressors" and "estimates" need a motion word
        ("six regressors and their derivatives", "six motion regressors and their derivatives"),
        ("six estimates and their derivatives", "six realignment estimates and their derivatives"),
        (
            "six nuisance regressors and their derivatives",
            "six motion regressors and their derivatives",
        ),
        ("six signals and their derivatives", "six parameters and their derivatives"),
        (
            "six physiological regressors and their derivatives",
            "six motion regressors and their derivatives",
        ),
        # "and" joins two motion words and is not one (the third review)
        ("six and regressors and derivatives", "six motion regressors and derivatives"),
        ("six motion and parameters and their derivatives", _PLAIN),
        ("the six and and parameters with derivatives", "the six parameters with derivatives"),
        ("6motion parameters and their derivatives", "6 motion parameters and their derivatives"),
        ("six runs of motion parameters and their derivatives", _PLAIN),
        # a connective: without one the wording is the derivatives alone
        ("six motion parameter derivatives", f"{_SIX}, derivatives"),
        (f"{_SIX} without their derivatives", f"{_SIX} with their derivatives"),
        (f"{_SIX} w/o derivatives", f"{_SIX} & derivatives"),
        (f"{_SIX} rather than their derivatives", f"{_SIX} together with their derivatives"),
        (f"{_SIX} (no derivatives)", f"{_SIX}, 6 derivatives"),
        (f"{_SIX} or their derivatives", f"{_SIX} and their derivatives"),
        (f"{_SIX} with no derivatives", f"{_SIX} with the derivatives"),
        (f"{_SIX}; their derivatives", f"{_SIX}, their derivatives"),
        (f"{_SIX} / their derivatives", f"{_SIX} + their derivatives"),
        # the derivative is the parameters' own, and a first one (the first review)
        (f"{_SIX} and the global signal derivative", f"{_SIX} and the first derivative"),
        (f"{_SIX} and CSF derivatives", _PLAIN),
        (f"{_SIX} and their second derivatives", f"{_SIX} and their first derivatives"),
        (f"{_SIX} and their higher-order derivatives", f"{_SIX} and their first-order derivatives"),
        (f"{_SIX} and their derivitives", _PLAIN),
        # nothing may follow the wording (both reviews): a further term, a count, a citation
        (f"{_SIX}, their derivatives and one-volume lagged versions", f"{_SIX}, their derivatives"),
        (f"{_SIX}, derivative terms dropped", f"{_SIX}, derivative terms"),
        (f"{_PLAIN} of the tissue signals", f"{_PLAIN} of each"),
        (f"{_PLAIN} (24 regressors)", _PLAIN),
        (f"{_PLAIN} (12 regressors)", _PLAIN),
        (f"{_PLAIN} (Satterthwaite et al., 2013)", _PLAIN),
        (f"{_PLAIN} [24]", _PLAIN),
        (f"{_PLAIN} \ufff9and their lagged copies\ufffb", _PLAIN),
        (f"{_PLAIN}?", f"{_PLAIN}."),
        # nothing may stand before it but a quote or a bracket (the second review)
        (f"not {_PLAIN}", _PLAIN),
        (f"\u2260{_PLAIN}", f"({_PLAIN})"),
        (f"<{_PLAIN}", f"({_PLAIN})"),
        (f"{_PLAIN};", f"{_PLAIN}."),
        # a word glued on by a line wrap is not the derivative (the second review)
        (f"{_PLAIN}-" + chr(10) + "lagged", f"{_SIX} and their deriva-" + chr(10) + "tives"),
        # the count of twelve, when more is said (both reviews)
        ("12 motion parameters and their derivatives", "12 motion parameters"),
        ("12 motion parameters (derivs)", "12 motion parameters"),
        ("12 parameters of the affine transformation", "12 parameters"),
        ("12 motion and physiological parameters", "12 motion parameters"),
        ("12 rigid-body parameters", "12 realignment parameters"),
        ("12 nuisance regressors", "12 motion regressors"),
        ("12 regressors", "12 motion regressors"),
        ("13 motion parameters", "12 motion parameters"),
        ("\u226512 parameters", "12 parameters"),
        ("12P+", "12P"),
        (
            "12 parameters (12 motion parameters)",
            "12 parameters (6 motion parameters and their derivatives)",
        ),
        # only the count of twelve wraps the six, and with a bracket
        (
            "24 parameters (6 motion parameters and their derivatives)",
            "12 parameters (6 motion parameters and their derivatives)",
        ),
        (
            "12 parameters 6 motion parameters and their derivatives",
            "12 parameters (6 motion parameters and their derivatives)",
        ),
        ("12 affine parameters", "12 motion parameters"),
        ("24P", "12P"),
    ],
)
def test_a_wording_that_says_anything_more_is_not_the_12_parameter_model(
    raw: str, twin: str
) -> None:
    assert rules_resolve(_MOTION, twin) == ["12param"]
    assert rules_resolve(_MOTION, raw) == []
    assert _resolved(_MOTION, raw) != ["12param"]


@pytest.mark.parametrize(
    "raw",
    [
        # a stray six beside a wording that states no count (the first review)
        "motion parameters and their derivatives (FD > 0.6 mm)",
        "motion parameters and their derivatives; FWHM 6 mm",
        "motion parameters and their derivatives, for each of six runs",
        # the derivative of something else, or before the count (the first review)
        "six motion parameters, and the white matter and CSF signals and their derivatives",
        "six motion parameters (DVARS = derivative of RMS variance)",
        "derivatives of the six motion parameters",
        # no count: the rule asks for the six
        "motion parameters and their derivatives",
    ],
)
def test_the_papers_words_are_kept_where_no_member_is_stated(raw: str) -> None:
    assert _resolved(_MOTION, raw) == [None]


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # six, derivatives AND squares is the 24-parameter model, as before 0.8.0
        ("six parameters, their derivatives and their squares", "friston24"),
        ("6 motion parameters with derivatives and quadratic terms", "friston24"),
        # a wording HEAD resolved keeps its member. As aliases of 12param, "12 motion" and
        # "12 parameters" had tied with the first four; a citation trailer had taken the last two
        # (the reviews)
        ("24 motion regressors (12 motion parameters plus their squares)", "friston24"),
        ("Friston 24 (12 motion parameters and squares)", "friston24"),
        ("12 motion parameters (Friston 1996)", "friston24"),
        ("none (12 motion parameters were not regressed)", "none"),
        ("12 motion parameters \ufff9(24 regressors)\ufffb", "friston24"),
        ("12 parameters \ufff9(24 regressors)\ufffb", "friston24"),
        ("six motion parameters", "6param"),
        ("24 motion parameters", "friston24"),
    ],
)
def test_the_other_motion_members_are_as_they_were(raw: str, want: str) -> None:
    assert _resolved(_MOTION, raw) == [want]


def test_the_new_members_have_no_alias() -> None:
    """Each is reached by its token and by its whole-wording rule only: an alias matches inside a
    longer wording, which is where the wrong members came from."""
    assert MOTION_EXPANSION["12param"] == []
    assert SCRUB_CRITERION["global_signal"] == []
    assert DISTORTION_METHOD["fieldmap_less"] == []
    assert set(TERM_RULES[_MOTION].require_all) == {"friston24", "12param"}
    assert set(TERM_RULES[_CRITERION].require_all) == {"global_signal"}
    assert set(TERM_RULES[_METHOD].require_all) == {"fieldmap_less"}
    assert "12param" not in TERM_RULES[_MOTION].block


def test_a_rule_does_not_hand_over_what_the_members_block_refuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``require_all`` and ``block`` of one member (coverage_fields.TermRules). No member has
    both today, so the mechanism is pinned on a rule made for the test."""
    rules = TermRules(require_all={"m": (r"alpha",)}, block={"m": (r"beta",)})
    monkeypatch.setitem(TERM_RULES, "a.field", rules)
    assert rules_resolve("a.field", "alpha") == ["m"]
    assert rules_resolve("a.field", "alpha and beta") == []


def test_rules_resolve_returns_nothing_for_a_field_without_rules() -> None:
    assert "scrub.remediation" not in TERM_RULES
    assert rules_resolve("scrub.remediation", "six parameters and their derivatives") == []
    assert rules_resolve("", "six parameters and their derivatives") == []
    assert rules_resolve(_MOTION, "six parameters and their derivatives") == ["12param"]  # control


def test_the_note_is_not_put_on_a_term_about_a_member_the_vocabulary_holds() -> None:
    """B11's note says the vocabulary holds no name for the words. The two members have no alias,
    so a term that says more than their rule allows is known by a word of the rule's own lists
    (coverage_fields.RULE_WORDS): a derivative, the count of twelve, the average signal."""
    for words in (
        "six regressors and their derivs (no GSR)",
        "six regressors and their derivates (no GSR)",
        "the derivate of the motion parameters",
        "6 head motion parameters and their derivations (Power et al., 2014)",
        "6 head motion params + deriv. (Power)",
        "motion parameters and their temporal derivatives",
        "six motion parameters, their derivatives and lagged copies",
        "twelve motion-related nuisance regressors",
        "12 motion confounds",
        "12 realignment parameters (Power et al., 2014)",
        "twelve head-motion parameters [12]",
        "12 movement parameters [12]",
        "12P (Satterthwaite et al., 2013)",
        "12-parameter model (6 + 6)",
    ):
        assert _resolved(_MOTION, words) == [None], words
        assert names_no_member(_MOTION, words) is False, words
    for words in ("average signal change", "global signal regression"):
        assert _resolved(_CRITERION, words) == [None], words
        assert names_no_member(_CRITERION, words) is False, words
    # a wording a rule resolves today is known too: a record stored before the rule holds such a
    # term unresolved, and it gets no note
    for words in ("12 parameters", "12P", "12-parameter motion model"):
        assert _resolved(_MOTION, words) == ["12param"], words
        assert names_no_member(_MOTION, words) is False, words
    # controls: nothing the vocabulary knows, among them a registration with twelve parameters
    assert names_no_member(_MOTION, "CONN's default denoising") is True
    assert names_no_member(_MOTION, "six nuisance regressors and their lagged copies") is True
    assert names_no_member(_MOTION, "12 affine parameters") is True
    assert names_no_member(_CRITERION, "whole-brain intensity > 3 SD") is True


def test_the_rule_words_are_the_words_of_the_two_rules_and_no_others() -> None:
    """The note cannot disagree with the rule. RULE_WORDS is written out here from the rules' own
    closed lists and compared whole, so a word the rule reads cannot be missing (the fourth
    review: "12 headmotion") and a broader one cannot be added ("twelve" alone would take the
    note off "twelve affine parameters"). A plural is read with its singular, so "derivs" is
    not listed beside "deriv"."""
    heads = ("motion", "head motion", "headmotion", "realignment", "movement", "parameter")
    twelve = [f"{count} {head}" for count in ("12", "twelve") for head in heads]
    assert set(RULE_WORDS) == {_MOTION, _CRITERION}
    assert sorted(RULE_WORDS[_MOTION]) == sorted(
        ["derivative", "derivate", "derivation", "deriv", *twelve, "12P"]
    )
    assert RULE_WORDS[_CRITERION] == ("average signal",)
    # each entry, in the plainest wording its rule reads, resolves to the rule's member
    for word in ("derivative", "derivate", "derivation", "deriv", "derivs"):
        assert _resolved(_MOTION, f"six motion parameters and their {word}") == ["12param"], word
    for word in [*twelve, "12P"]:
        wording = word if word.endswith(("parameter", "P")) else f"{word} parameters"
        assert _resolved(_MOTION, wording) == ["12param"], wording
    assert _resolved(_CRITERION, "3 SD of the average signal") == ["global_signal"]
    # and, in a term that says more, keeps the note off it
    for word in RULE_WORDS[_MOTION]:
        assert _resolved(_MOTION, f"{word} confounds (Power et al., 2014)") == [None], word
        assert names_no_member(_MOTION, f"{word} confounds (Power et al., 2014)") is False, word
    assert names_no_member(_MOTION, "six regressors and their derivs (Power)") is False
    # controls: a registration with twelve parameters is none of these
    assert names_no_member(_MOTION, "twelve affine parameters") is True
    assert names_no_member(_MOTION, "12 affine parameters") is True


def test_a_wording_a_rule_resolves_is_known_to_the_note(monkeypatch: pytest.MonkeyPatch) -> None:
    """names_no_member asks the rules too. Every rule of today's tables also leaves an alias, a
    token or a rule word in the wording it resolves, so the question is pinned on a rule made for
    the test."""
    assert names_no_member("scrub.remediation", "zzz") is True
    rules = TermRules(require_all={"censor": (r"\Azzz\Z",)})
    monkeypatch.setitem(TERM_RULES, "scrub.remediation", rules)
    assert names_no_member("scrub.remediation", "zzz") is False


def test_the_audit_does_not_find_a_member_without_an_alias_in_a_quote() -> None:
    """The token trace asks whether an alias of the member is in the quote. 12param has none, and
    its rule reads a whole wording, so a quote that states it names no member; the audit says so
    in its text. A quote that is the wording itself is read."""
    field = ta.vocabulary()[("nuisance_regression", "motion_expansion")]
    quote = "the six realignment estimates and their temporal derivatives were regressed out"
    assert ta.members_in_quote(field, quote, None) == set()
    assert ta.members_in_quote(field, "six motion parameters and their derivatives", None) == {
        "12param"
    }
    squares = quote.replace("were regressed", "and the squares of both were regressed")
    assert ta.members_in_quote(field, squares, None) == {"friston24"}  # control: the older rule


# --- global_signal (C9): a whole item with its threshold ----------------------------------------


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("> 3 standard deviations of average signal", ["global_signal"]),  # schwartz_2018
        ("3 SD of the average signal", ["global_signal"]),
        ("2.5 s.d. from the whole-brain global signal", ["global_signal"]),
        ("global signal > 3 SD", ["global_signal"]),
        ("global signal 3 SD", ["global_signal"]),  # the comparator may be left out
        # each comparator and preposition of the pattern (the third review)
        ("<= 3 SD of the average signal", ["global_signal"]),
        ("\u2265 3 SD of the global signal", ["global_signal"]),
        ("\u2264 3 SD of the global signal", ["global_signal"]),
        ("3 SD in the global signal", ["global_signal"]),
        ("global signal <= 3 SD", ["global_signal"]),
        ("global signal \u2264 3 SD", ["global_signal"]),
        ("the average signal \u2265 3 standard deviations", ["global_signal"]),
        ("global_signal", ["global_signal"]),
        ("FD > 0.5 mm and global signal > 3 SD", ["fd_power", "global_signal"]),
        ("framewise displacement, 3 SD of average signal", ["fd_power", "global_signal"]),
    ],
)
def test_the_global_signal_scrub_criterion(raw: str, want: list[str]) -> None:
    assert _resolved(_CRITERION, raw) == want


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # The signal named without a threshold is not read: each of these is what the code before
        # 0.8.0 gave. As aliases, and then as a pattern that read the bare name, "global signal"
        # and "average signal" took the first ten, and the DVARS and FD wordings lost their
        # member (the reviews).
        ("global signal", [None]),
        ("average signal", [None]),
        ("global signal regression", [None]),
        ("white-matter average signal", [None]),
        ("average signal to noise ratio", [None]),
        ("not global signal", [None]),
        ("DVARS, the global signal change", ["dvars", None]),
        ("average signal/noise ratio", [None, None]),
        ("average and peak percent BOLD signal change", [None, "bold_pct"]),
        ("white matter, CSF and global signal", [None, None, None]),
        ("DVARS (rate of change of the global signal)", ["dvars"]),
        ("DVARS > 0.5% of the global signal", ["dvars"]),
        ("FD > 0.5 mm (global signal regression was also performed)", ["fd_power"]),
        ("percent BOLD change in global signal", ["bold_pct"]),
        ("FD or global signal", ["fd_power"]),
        # a threshold that is not in standard deviations, or on another signal
        ("0.5% of the global signal", [None]),
        ("3 SD of the white matter signal", [None]),
        ("global signal > 3", [None]),
        ("global signal > 3 z", [None]),
        ("mean signal > 3 SD", [None]),
        # controls: the members that were there
        ("percent BOLD change", ["bold_pct"]),
        ("FD, DVARS", ["fd_power", "dvars"]),
    ],
)
def test_a_wording_that_only_mentions_the_global_signal_is_as_it_was(
    raw: str, want: list[str | None]
) -> None:
    assert _resolved(_CRITERION, raw) == want


# --- the two patterns refuse a long wording in one pass ------------------------------------------


def _fastest(dotted: str, raw: str, runs: int = 5) -> float:
    import time

    best = float("inf")
    for _ in range(runs):
        started = time.perf_counter()
        assert rules_resolve(dotted, raw) == []
        best = min(best, time.perf_counter() - started)
    return best


@pytest.mark.parametrize(
    ("dotted", "make"),
    [
        # A run that a pattern can split in more than one way costs the square or the cube of its
        # length. The step's second build did: the first three took seconds at 1,600 characters
        # and the first criterion row a second at 5,000 (the second review). Every repetition is
        # possessive now, and each of these is a run next to a piece that could have shared it.
        (_MOTION, lambda n: _PLAIN + " " * n + "x"),
        (_MOTION, lambda n: _PLAIN + chr(10) * n + "x"),
        (_MOTION, lambda n: "12 parameters" + " " * n + "x"),
        (_MOTION, lambda n: "six " + "motion " * (n // 7) + "x"),
        (_MOTION, lambda n: _PLAIN + " (12)" * (n // 5) + " x"),
        (_CRITERION, lambda n: "1" + " " * n + "x"),
        (_CRITERION, lambda n: "3 SD of " + "the " * (n // 4)),
        (_CRITERION, lambda n: "global signal > " + "9" * n),
        (_METHOD, lambda n: "fieldmap-less" + " " * n + "x"),
        (_METHOD, lambda n: "field" + " " * n + "map"),
    ],
)
def test_refusing_a_wording_costs_no_more_than_its_length(
    dotted: str, make: typing.Callable[[int], str]
) -> None:
    small = _fastest(dotted, make(2_000))
    assert small < 0.25  # first, so that a pattern that backtracks fails here and not after minutes
    large = _fastest(dotted, make(8_000))
    # four times the length: about four times the time, on any machine. The square would be 16.
    assert large < 10 * max(small, 2e-4)


# --- fieldmap_less, other (C9) and the Literals -------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "fieldmap-less",
        "field map-less",
        "field-map-less",
        "fieldmapless",
        "fieldmap less",
        "Fieldmap_Less",
        "fieldmap\u2010less",
        # with the registration it runs on, or the word for the step
        "fieldmap-less SyN",
        "fieldmap-less (SyN)",
        "field map-less SyN-SDC",
        "fieldmap-less SDC",
        "fieldmap-less distortion correction",
        "fieldmap-less susceptibility distortion correction",
        "fieldmap-less correction",
        "fieldmap-less approach",
        "fieldmap-less method",
    ],
)
def test_a_fieldmap_less_correction_on_the_method_field(raw: str) -> None:
    assert _resolved(_METHOD, raw) == ["fieldmap_less"]


def test_a_fieldmap_less_item_of_a_method_list() -> None:
    assert _resolved(_METHOD, "blip-up/blip-down, fieldmap-less") == [
        "reverse_phase_encoding",
        "fieldmap_less",
    ]


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # Each is what the code before 0.8.0 gave. As aliases of the method, the source field's
        # wordings resolved the first six to fieldmap_less: "less" as an ordinary word after a
        # field map (the fourth review), and a fieldmap named beside "fieldmapless" (the third).
        ("field map less than ideal", [None]),
        ("fieldmap less robust than topup", [None]),
        ("B0 field map less than 2 Hz", [None]),
        ("field map - less noise", [None]),
        ("fieldmap or fieldmapless", [None]),
        ("fieldmap (fieldmapless SyN as fallback)", [None]),
        # more than the item rule reads: the paper's words are kept
        ("fieldmap-less correction was not applied", [None]),
        ("fieldmap-less SyN-based SDC", [None]),
        ("sdc_fieldmapless", [None]),
        ("fieldmap-free", [None]),
        # controls: the other members are as they were
        ("fieldmap", ["fieldmap"]),
        ("reverse phase encoding", ["reverse_phase_encoding"]),
    ],
)
def test_a_wording_that_only_holds_fieldmap_less_is_as_it_was(
    raw: str, want: list[str | None]
) -> None:
    assert _resolved(_METHOD, raw) == want


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        # "SyN-based" is the source field's alias and not the method's: on the method it also met
        # SyN used for normalization, and these lost the member they had (the second review)
        ("fieldmap unwarping followed by SyN-based registration", ["fieldmap"]),
        ("reverse phase encoding with SyN-based registration", ["reverse_phase_encoding"]),
        ("SyN-based normalization", [None]),
        ("SyN-based distortion correction", [None]),
    ],
)
def test_syn_based_is_not_an_alias_of_the_method(raw: str, want: list[str | None]) -> None:
    assert _resolved("distortion_correction.method", raw) == want
    assert _resolved("distortion_correction.source", "SyN-based") == ["fieldmap_less"]  # control


def test_the_extractor_resolves_only_to_members_the_schema_holds() -> None:
    """The members added in 0.8.0 are in the Literal each table is checked against."""
    for dotted, member in (
        (_MOTION, "12param"),
        (_CRITERION, "global_signal"),
        ("distortion_correction.method", "fieldmap_less"),
        ("coregistration.cost_function", "other"),
    ):
        s = _SPEC[dotted]
        assert member in typing.get_args(s.literal_type), dotted
        assert member in (s.synonyms or {}), dotted
    assert "fieldmap_less" in typing.get_args(DistortionFamily)


# --- the scrub threshold, a list of one (C9) ----------------------------------------------------

_QUOTE = (
    "Volumes with framewise displacement above 0.5 mm or a change of more than 3 standard "
    "deviations of average signal were censored."
)


def _run(raw: str, quote: str = _QUOTE) -> Preprocessing:
    missing = FieldExtractionResult(status="missing")
    payload = PreprocessingExtraction(
        target_space=missing,
        resolution_mm=missing,
        surface_registration=missing,
        target_surface=missing,
        intensity_convention=missing,
        intensity_value=missing,
    )
    temporal = TemporalVolumeExtraction(
        scrub_threshold=FieldExtractionResult(status="extracted", value=raw, verbatim_quote=quote)
    )
    prep, _, _ = extract_preprocessing(
        ParsedPaper(text="Methods. " + quote, source="t", parser="manual"),
        "m",
        client=stub_client(payload, temporal=temporal),
    )
    return prep


def _threshold(prep: Preprocessing) -> Any:
    return next(s for s in prep.steps if s.kind == "scrub").threshold


@pytest.mark.parametrize(
    "raw",
    [
        "0.5",
        "0.5 mm",
        "3rd",
        "1,000",
        "5%",
        "2 SD",
        # One number is read however many the string holds: several need a format the prompt
        # states. Split on commas and "and", the last three stored a citation year and a count of
        # volumes as thresholds (the review).
        "3 SD, 0.5 mm",
        "0.5 mm and 3 SD",
        "0.5 mm (Power et al., 2012)",
        "0.5 mm, 1 volume before and 2 after",
        "0.5 mm and 5 volumes",
    ],
)
def test_one_number_is_read_as_it_was_before_the_field_was_a_list(raw: str) -> None:
    one = ex._parse_number(raw, integer=False)
    assert one is not None
    pf = _threshold(_run(raw, f"Volumes above {raw} were censored."))
    assert pf.extraction.status == "EXTRACTED"
    assert pf.extraction.value == [float(one)]


def test_the_threshold_is_the_one_number_list_field() -> None:
    assert COVERAGE_NUMBER_LIST_FIELDS == {_THRESHOLD}
    assert _THRESHOLD not in COVERAGE_NUMERIC_FIELDS
    assert _SPEC[_THRESHOLD].t == list[float]
    # the attribute the model fills is the one it filled before
    assert _SPEC[_THRESHOLD].attr == "scrub_threshold"


@pytest.mark.parametrize(
    ("value", "want"),
    [
        ([3.0, 0.5], True),
        ([0.5], True),
        ((3.0,), True),
        ([0.5, 0.2], False),  # every number must be in the quote
        ([0.2], False),
        ([], False),
        (["x"], False),
        (None, False),
        # a record written before 0.8.0 and read without migration holds the one number
        (0.5, True),
        (0.2, False),
    ],
)
def test_every_number_of_the_list_must_be_in_the_quote(value: Any, want: bool) -> None:
    assert coverage_value_supported(_THRESHOLD, value, _QUOTE) is want


def test_a_number_that_is_not_in_the_quote_fails_the_field() -> None:
    pf = _threshold(_run("0.7 mm"))
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason == "value_unsupported_by_quote"
    words = _threshold(_run("stringent"))
    assert words.inference.reason == "value_not_numeric"
    assert _threshold(_run("0.5")).extraction.value == [0.5]  # control


def _row_text(prep: Preprocessing) -> str:
    row = next(r for r in render.flatten(prep) if r.path == _THRESHOLD)
    return render._fmt_row_value(row)


def test_the_report_and_the_pseudocode_show_one_threshold_as_the_number() -> None:
    one = _run("0.5")
    assert _row_text(one) == "0.5"
    assert "- threshold = 0.5   [from paper]" in render.to_report(one, source="t")
    assert pseudocode._literal([0.5]) == "0.5" == pseudocode._literal(0.5)
    code = pseudocode.render_pseudocode({"preprocessing": one.model_dump(mode="json")})
    assert code is not None and "threshold=0.5" in code and "threshold=[0.5]" not in code
    # a list of two (a hand-built or a later document) keeps both numbers on each surface
    assert render._fmt_value([3.0, 0.5]) == "3.0, 0.5"
    assert pseudocode._literal([3.0, 0.5]) == "[3, 0.5]"
    # control: a band keeps its brackets (two numbers, never one)
    assert pseudocode._literal((0.01, 0.1)) == "[0.01, 0.1]"


def test_a_record_written_under_0_7_4_shows_its_threshold_as_it_did() -> None:
    """A stored record holds the one number. Read through the migration it is a one-item list, and
    every surface shows the same text the number gave."""
    doc = json.loads(render.to_json(_run("0.5")))
    assert doc["schema_version"] == SCHEMA_VERSION == "0.8.0"
    scrub = next(s for s in doc["steps"] if s["kind"] == "scrub")
    assert scrub["threshold"]["extraction"]["value"] == [0.5]
    # the same document as 0.7.4 wrote it
    doc["schema_version"] = "0.7.4"
    doc["written_under"] = "0.7.4"
    scrub["threshold"]["extraction"]["value"] = 0.5
    old = parse_any_version(doc)
    assert old.written_under == "0.7.4" and old.schema_version == "0.8.0"
    assert _threshold(old).extraction.value == [0.5]
    assert _row_text(old) == str(0.5) == "0.5"
    code = pseudocode.render_pseudocode({"preprocessing": doc})
    assert code is not None and f"threshold={0.5:g}" in code


# --- the schema values nothing writes yet -------------------------------------------------------

_BET = "brain_extraction.method"
_BET_QUOTE = "Skull stripping was performed with ROBEXBET on each T1 image."


def _term(verbatim: str, resolved: str | None, resolution: str) -> Any:
    return SimpleNamespace(verbatim=verbatim, resolved=resolved, resolution=resolution)


def test_a_model_mapped_term_is_checked_by_the_papers_words() -> None:
    """``model_mapped`` (C7): the member is the model's reading and no alias confirmed it, so the
    member's aliases prove nothing about the quote. Before the guard a term whose words were in
    the quote was demoted, and one whose words were not passed on an alias (the review)."""
    mapped = _term("ROBEXBET", "bet", "model_mapped")
    assert _term_supported(_BET, mapped, _BET_QUOTE) is True
    assert _term_supported(_BET, mapped, "Skull stripping was performed with BET.") is False
    # control: a member the table resolved is checked by its aliases, as before
    resolved = _term("BET", "bet", "resolved")
    assert _term_supported(_BET, resolved, _BET_QUOTE) is False
    assert _term_supported(_BET, resolved, "Skull stripping was performed with BET.") is True
    # the shared fields' check reads it the same way
    space = "spatial_normalization.target_space"
    said = "Images were warped to the Colin27 brain."
    assert literal_value_supported(space, "Colin27", "MNI152NLin6Asym", "model_mapped", said)
    assert not literal_value_supported(
        space, "Colin27", "MNI152NLin6Asym", "model_mapped", "Images were warped to MNI space."
    )


def test_a_model_mapped_tool_is_a_named_tool_and_survives_a_re_resolve() -> None:
    mapped = _term("the McFLIRT tool", "mcflirt", "model_mapped")
    assert described_only([mapped]) is False
    assert described_only([_term("corrected for motion", None, "unrecognized")]) is True  # control
    field = rr.TERM_SPECS[("coregistration", "cost_function")]
    stored = {"verbatim": "NMI", "resolved": "mutual_information", "resolution": "model_mapped"}
    assert rr._reresolve_value(dict(stored), field, None) == (stored, [])
    # control: the same words without the model's member are re-resolved by the table
    plain = {"verbatim": "NMI", "resolved": "mutual_information", "resolution": "resolved"}
    again, changes = rr._reresolve_value(dict(plain), field, None)
    assert again["resolved"] is None and len(changes) == 1
    # a term marked model_mapped that holds no member is an unresolved term like any other: the
    # audit grades it so, and a re-resolve writes the table's member (the fourth review)
    empty = {"verbatim": "mutual information", "resolved": None, "resolution": "model_mapped"}
    again, changes = rr._reresolve_value(dict(empty), field, None)
    assert again["resolved"] == "mutual_information" and again["resolution"] == "resolved"
    assert len(changes) == 1


def test_a_record_with_one_of_the_two_new_statuses_is_refused_by_the_report() -> None:
    """Schema 0.8.0 holds INFERRED_FROM_TEXT and INFERRED_FROM_CITATION; their display is the
    inference pass's step (D5). Until then the report refuses such a record. Without the guard it
    showed the field as "unspecified" and dropped the value (the review)."""
    prep = _run("0.5")
    step = next(s for s in prep.steps if s.kind == "temporal_filtering")
    field = type(step.relative_to_regression)
    for status, basis in (
        ("INFERRED_FROM_TEXT", {"basis_type": "derived", "source_field_ids": ["step_order"]}),
        ("INFERRED_FROM_CITATION", {"basis_type": "prior_publication", "citation": "A 2007"}),
    ):
        step.relative_to_regression = field.model_validate(
            {
                "field_id": "relative_to_regression",
                "extraction": step.relative_to_regression.extraction.model_dump(),
                "inference": {
                    "status": status,
                    "value": {"verbatim": None, "resolved": "before", "resolution": "resolved"},
                    "basis": basis,
                    "confidence": 0.5,
                    "alternative_inferences": [],
                },
            }
        )
        with pytest.raises(NotImplementedError, match=f"relative_to_regression: {status}"):
            render.flatten(prep)
    assert render.flatten(_run("0.5"))  # control: a record without them is shown

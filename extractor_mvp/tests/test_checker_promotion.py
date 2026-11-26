"""Pre-rerun item 2 (2026-11-11): checker-supplied values. A MISSED or WRONG verdict with a value and
a resolved sentence goes through the extraction's own checks; passing, it fills a field left without a
value (checker_supplied); failing, it stays a flag. The methods text is written for these tests."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from conftest import FULL_TEXT, _canned_payload, stub_client
from extractor_mvp.checker_promotion import parse_parts, promote
from extractor_mvp.extractor import extract
from extractor_mvp.parsed_paper import ParsedPaper

TEXT = (
    "Task data were censored at a framewise displacement above 0.9 mm. "
    "For rest data, frames with framewise displacement above 0.2 mm were removed. "
    "Images were smoothed with a 6 mm FWHM Gaussian kernel."
)
TASK = "Task data were censored at a framewise displacement above 0.9 mm."
REST = "For rest data, frames with framewise displacement above 0.2 mm were removed."

_PREP: Any = None


def _prep() -> Any:
    global _PREP
    if _PREP is None:
        _PREP, _, _ = extract(
            ParsedPaper(text=FULL_TEXT, source="p"), "m", client=stub_client(_canned_payload())
        )
    return copy.deepcopy(_PREP)


def _step(prep: Any, kind: str) -> Any:
    return next(s for s in prep.steps if s.kind == kind)


def _verifier(**fields: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "fields": {
            k.replace("__", "."): {"relied_on_resolved": True, **v} for k, v in fields.items()
        },
    }


def test_parse_parts() -> None:
    assert parse_parts("0.9 mm for task data; 0.2 mm for rest data") == [
        ("task data", "0.9 mm"),
        ("rest data", "0.2 mm"),
    ]
    assert parse_parts("0.9 [task]; 0.2 [rest]") == [("task", "0.9"), ("rest", "0.2")]
    assert parse_parts("task: 0.9; rest: 0.2") == [("task", "0.9"), ("rest", "0.2")]
    assert parse_parts("6") is None
    # one "<value> for <part>" is a part only when the part's words are in the text
    assert parse_parts("0.2 mm for rest data", TEXT) == [("rest data", "0.2 mm")]
    assert parse_parts("regression for motion and drift", TEXT) is None
    # a segment that is not a part makes the whole one value
    assert parse_parts("0.9 for task; and more") is None


def test_a_missing_field_is_filled_when_the_value_passes_the_checks() -> None:
    prep = _prep()
    assert _step(prep, "scrub").threshold.extraction.status == "MISSING_FROM_PAPER"
    log = promote(
        prep,
        _verifier(scrub__threshold={"verdict": "missed", "better_value": "0.9", "relied_on": TASK}),
        TEXT,
    )
    ext = _step(prep, "scrub").threshold.extraction
    # schema 0.8.0: the threshold is a list; one number is read into it
    assert ext.status == "EXTRACTED" and ext.checker_supplied and ext.value == [0.9]
    assert log[0]["outcome"] == "filled"


def test_a_value_not_in_its_sentence_stays_a_flag() -> None:
    prep = _prep()
    log = promote(
        prep,
        _verifier(scrub__threshold={"verdict": "missed", "better_value": "0.5", "relied_on": TASK}),
        TEXT,
    )
    assert _step(prep, "scrub").threshold.extraction.status == "MISSING_FROM_PAPER"
    assert log[0]["outcome"] == "flag: value_unsupported_by_quote"


def test_an_unresolved_sentence_or_no_value_does_nothing() -> None:
    prep = _prep()
    v = _verifier(scrub__threshold={"verdict": "missed", "better_value": "0.9", "relied_on": TASK})
    v["fields"]["scrub.threshold"]["relied_on_resolved"] = False
    assert promote(prep, v, TEXT)[0]["outcome"].startswith("flag: the checking pass's sentence")
    assert _step(prep, "scrub").threshold.extraction.status == "MISSING_FROM_PAPER"
    log = promote(
        prep,
        _verifier(
            scrub__threshold={"verdict": "wrong", "better_value": "not reported", "relied_on": TASK}
        ),
        TEXT,
    )
    assert log == []
    log = promote(
        prep,
        _verifier(
            scrub__threshold={"verdict": "supported", "better_value": "0.9", "relied_on": TASK}
        ),
        TEXT,
    )
    assert log == []


def test_a_value_the_extraction_produced_is_never_overridden() -> None:
    prep = _prep()
    promote(
        prep,
        _verifier(scrub__threshold={"verdict": "missed", "better_value": "0.9", "relied_on": TASK}),
        TEXT,
    )
    before = _step(prep, "scrub").threshold.model_dump()
    log = promote(
        prep,
        _verifier(
            scrub__threshold={
                "verdict": "wrong",
                "better_value": "0.2 mm for rest data",
                "relied_on": REST,
            }
        ),
        TEXT,
    )
    assert log[0]["outcome"] == "flag: the field is EXTRACTED, never overridden"
    assert _step(prep, "scrub").threshold.model_dump() == before


def test_a_verdict_naming_per_part_values_creates_parts() -> None:
    prep = _prep()
    log = promote(
        prep,
        _verifier(
            scrub__threshold={
                "verdict": "missed",
                "better_value": "0.9 for Task data; 0.2 for rest data",
                "relied_on": TASK + " " + REST,
            }
        ),
        TEXT,
    )
    ext = _step(prep, "scrub").threshold.extraction
    assert log[0]["outcome"] == "filled" and log[0]["parts"] is not None
    assert ext.status == "VARIED"
    assert [(v.applies_to, v.value, v.checker_supplied) for v in ext.variants] == [
        ("Task data", [0.9], True),
        ("rest data", [0.2], True),
    ]


def test_a_part_line_verdict_is_never_acted_on() -> None:
    prep = _prep()
    log = promote(
        prep,
        _verifier(
            **{
                "scrub__threshold[rest data]": {
                    "verdict": "missed",
                    "better_value": "0.2",
                    "relied_on": REST,
                }
            }
        ),
        TEXT,
    )
    assert log == []


def test_the_report_counts_a_supplied_value_and_the_pseudocode_tags_it() -> None:
    from extractor_mvp import render
    from extractor_mvp.pseudocode import render_pseudocode

    prep = _prep()
    v = _verifier(scrub__threshold={"verdict": "missed", "better_value": "0.9", "relied_on": TASK})
    promote(prep, v, TEXT)
    rows = render.flatten(prep)
    row = next(r for r in rows if r.path == "scrub.threshold")
    assert row.state == "EXTRACTED" and row.checker_supplied
    report = render.to_report(prep, source="t", verifier=v)
    assert "- threshold = 0.9   [checker-supplied]" in report
    line = next(ln for ln in report.splitlines() if ln.startswith("- threshold = 0.9"))
    assert "MISSED" not in line  # the verdict became the value; it is not shown against it
    code = render_pseudocode({"preprocessing": prep.model_dump(mode="json"), "verifier": v})
    assert code is not None and "threshold=0.9 [E†]" in code
    assert "[E†] the checking pass's value" in code
    # control: a record with no supplied value has no [E†] in its legend
    plain = render_pseudocode({"preprocessing": _prep().model_dump(mode="json")})
    assert plain is not None and "E†" not in plain


def test_the_old_beside_the_field_path_is_off_for_a_record_drawn_with_promotion() -> None:
    from extractor_mvp.rechecks import checker_supplied

    dump = _prep().model_dump(mode="json")
    step = next(s for s in dump["steps"] if s["kind"] == "scrub")
    step["threshold"]["inference"] = {
        "status": "LEFT_MISSING",
        "reason": "extraction_quote_unresolved:quote_not_found",
    }
    verdict = {"verdict": "wrong", "better_value": "0.9", "relied_on": TASK}
    rec = {
        "preprocessing": dump,
        "diagnostics": [{"field": "scrub.threshold", "raw_quote": TASK}],
        "verifier": {"status": "ok", "fields": {"scrub.threshold": verdict}},
    }
    # control: a stored record drawn before promotion keeps the 2026-11-09 entry
    assert [c["field"] for c in checker_supplied(rec)] == ["scrub.threshold"]
    rec["verifier"]["supplied"] = []
    assert checker_supplied(rec) == []


@pytest.mark.parametrize("verdict", ["missed", "wrong"])
def test_both_verdicts_fill(verdict: str) -> None:
    prep = _prep()
    promote(
        prep,
        _verifier(scrub__threshold={"verdict": verdict, "better_value": "0.9", "relied_on": TASK}),
        TEXT,
    )
    assert _step(prep, "scrub").threshold.extraction.status == "EXTRACTED"


# --- D2c (2026-11-25, the author's ruling C14): the detrend rule inside promote() ---------------

TRENDS_TEXT = (
    "Linear and quadratic trends were removed from each run. "
    "No detrending or linear trend removal was applied to the task data. "
    "Only a linear trend was removed from the rest data."
)
BOTH_ORDERS = "Linear and quadratic trends were removed from each run."
ONE_ORDER = "Only a linear trend was removed from the rest data."
RULED_OUT = "No detrending or linear trend removal was applied to the task data."


def _supplied_detrend(value: str, sentence: str) -> tuple[Any, dict[str, Any], list[Any]]:
    prep = _prep()
    assert _step(prep, "nuisance_regression").detrend.extraction.status == "MISSING_FROM_PAPER"
    diagnostics: list[Any] = []
    verdict = {"verdict": "missed", "better_value": value, "relied_on": sentence}
    (entry,) = promote(
        prep, _verifier(nuisance_regression__detrend=verdict), TRENDS_TEXT, diagnostics
    )
    return _step(prep, "nuisance_regression").detrend.extraction, entry, diagnostics


def test_a_supplied_detrend_value_takes_the_highest_order_its_sentence_names() -> None:
    """Until D2c promote() ran after the highest-order rule, and a supplied value never met it."""
    ext, entry, diagnostics = _supplied_detrend("linear", BOTH_ORDERS)
    assert ext.status == "EXTRACTED" and ext.checker_supplied is True
    assert (ext.value.verbatim, ext.value.resolved) == ("linear", "quadratic")
    assert [s.text for s in ext.spans] == [BOTH_ORDERS]
    moved = "detrend_highest_order_named:linear->quadratic"
    assert entry["outcome"] == "filled" and entry["rule"] == moved
    assert [(d.field, d.failure_reason) for d in diagnostics] == [
        ("nuisance_regression.detrend", moved)
    ]
    # the order is raised and never lowered
    ext, entry, diagnostics = _supplied_detrend("quadratic", ONE_ORDER)
    assert ext.value.resolved == "quadratic" and "rule" not in entry and diagnostics == []


def test_a_supplied_detrend_value_with_no_higher_order_named_is_as_supplied() -> None:
    ext, entry, diagnostics = _supplied_detrend("linear", ONE_ORDER)
    assert (ext.value.resolved, ext.checker_supplied) == ("linear", True)
    assert "rule" not in entry and diagnostics == []
    # without a list to receive it, the move is still made and logged
    prep = _prep()
    verdict = {"verdict": "missed", "better_value": "linear", "relied_on": BOTH_ORDERS}
    (entry,) = promote(prep, _verifier(nuisance_regression__detrend=verdict), TRENDS_TEXT)
    assert _step(prep, "nuisance_regression").detrend.extraction.value.resolved == "quadratic"
    assert entry["rule"] == "detrend_highest_order_named:linear->quadratic"


OMITTED = "Linear detrending was omitted for the task data."
NONE_OF = "None of the task runs were detrended beyond a linear fit."


@pytest.mark.parametrize(
    ("words", "sentence"),
    [
        ("No detrending", RULED_OUT),
        ("no detrending", RULED_OUT),
        ("omitted", OMITTED),  # the sentence rules the order out in a word no list holds
        ("detrended", NONE_OF),  # "none" in the sentence is not the member none
        ("detrended", BOTH_ORDERS),  # nor is an order handed to a term that names none
    ],
)
def test_a_supplied_term_that_resolved_to_nothing_is_given_no_member(
    words: str, sentence: str
) -> None:
    """promote() raises an order and does no more. The checking pass can say that no detrending
    was done only in words, since its "none" means no value; such a term resolves to nothing,
    and the rule would hand it the order its sentence rules out (the review of D2c)."""
    text = TRENDS_TEXT + " " + OMITTED + " " + NONE_OF
    prep = _prep()
    diagnostics: list[Any] = []
    verdict = {"verdict": "missed", "better_value": words, "relied_on": sentence}
    (entry,) = promote(prep, _verifier(nuisance_regression__detrend=verdict), text, diagnostics)
    ext = _step(prep, "nuisance_regression").detrend.extraction
    assert ext.status == "EXTRACTED" and ext.checker_supplied is True
    assert (ext.value.verbatim, ext.value.resolved) == (words, None)
    assert entry["outcome"] == "filled" and "rule" not in entry and diagnostics == []


def test_the_rule_in_promote_is_the_detrend_field_s_alone() -> None:
    """Another field's sentence may name a detrend order; the rule does not read it."""
    sentence = "After linear and quadratic detrending, frames above 0.9 mm were removed."
    prep = _prep()
    diagnostics: list[Any] = []
    verdict = {"verdict": "missed", "better_value": "0.9", "relied_on": sentence}
    (entry,) = promote(prep, _verifier(scrub__threshold=verdict), sentence, diagnostics)
    assert _step(prep, "scrub").threshold.extraction.value == [0.9]
    assert entry["outcome"] == "filled" and "rule" not in entry and diagnostics == []
    # a single term of another field, whose member is no detrend order
    sentence = "After quadratic detrending, a rigid-body transform aligned each run to the T1."
    prep = _prep()
    verdict = {"verdict": "missed", "better_value": "rigid-body", "relied_on": sentence}
    (entry,) = promote(prep, _verifier(coregistration__transform=verdict), sentence, diagnostics)
    assert _step(prep, "coregistration").transform.extraction.value.resolved == "rigid"
    assert entry["outcome"] == "filled" and "rule" not in entry and diagnostics == []

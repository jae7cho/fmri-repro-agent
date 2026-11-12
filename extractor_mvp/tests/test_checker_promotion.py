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
    assert ext.status == "EXTRACTED" and ext.checker_supplied and ext.value == 0.9
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
        ("Task data", 0.9, True),
        ("rest data", 0.2, True),
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

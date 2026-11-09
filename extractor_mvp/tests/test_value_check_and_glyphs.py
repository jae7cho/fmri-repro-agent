"""The author's items 2 and 3 of 2026-11-09. Synthetic strings and records only: no paper text."""

from __future__ import annotations

from typing import Any

import pytest
from fmri_repro.spec.preprocessing import SpecifiedTerm

from extractor_mvp.quote_support import (
    coverage_value_supported,
    is_tool_name,
    normalize_number_words,
    number_in_quote,
    step_value_supported,
)
from extractor_mvp.rechecks import (
    checker_supplied,
    recheck_record,
    same_quote,
    unverifiable_fields,
)
from extractor_mvp.span_resolver import normalize_with_offset_map, resolve_quote

# --- item 2: numbers and tool names literal; everything else to the checking pass --------------


def test_number_words_are_read_as_digits() -> None:
    assert normalize_number_words("the First four and Twenty") == "the 1 4 and 20"
    assert number_in_quote(4.0, "the first four volumes were discarded")
    assert number_in_quote(1.0, "the first volume was discarded")
    assert number_in_quote(20.0, "twenty components were kept")
    assert number_in_quote(10.0, "the tenth run")
    assert not number_in_quote(5.0, "the first four volumes were discarded")
    # whole words only: "someone" holds no 1, "fourteenth" is not a number word
    assert not number_in_quote(1.0, "someone ran it")
    assert not number_in_quote(14.0, "the fourteenth run")


def test_numbers_keep_the_literal_check() -> None:
    assert coverage_value_supported("spatial_smoothing.fwhm_mm", 6.0, "a 6 mm kernel") is True
    assert coverage_value_supported("spatial_smoothing.fwhm_mm", 8.0, "a 6 mm kernel") is False
    assert step_value_supported("spatial_normalization.resolution_mm", 2.0, "2 mm voxels") is True
    assert step_value_supported("spatial_normalization.resolution_mm", 3.0, "2 mm voxels") is False


def _term(verbatim: str, resolved: str | None = None) -> SpecifiedTerm[str]:
    return SpecifiedTerm[str](
        verbatim=verbatim,
        resolved=resolved,
        resolution="resolved" if resolved else "unrecognized",
    )


def test_a_tool_name_keeps_the_literal_check_and_a_category_does_not() -> None:
    assert is_tool_name("BET") and is_tool_name("SPM12") and not is_tool_name("gaussian")
    quote = "Skull stripping was applied to the anatomical image."
    # a tool-shaped term its quote does not hold is unsupported; one it holds is supported
    assert coverage_value_supported("brain_extraction.method", _term("BET"), quote) is False
    assert coverage_value_supported("brain_extraction.method", _term("BET"), "using BET") is True
    # a categorical term is left to the checking pass, whatever its quote
    assert (
        coverage_value_supported("spatial_smoothing.kernel_type", _term("gaussian"), quote) is None
    )
    # a Literal step field likewise
    term = _term("MNI")
    assert step_value_supported("spatial_normalization.target_space", term, quote) is None


def test_lists_booleans_and_orderings_go_to_the_checking_pass() -> None:
    quote = "Nothing relevant here."
    assert coverage_value_supported("spatial_smoothing.performed", True, quote) is None
    terms = [_term("white matter"), _term("CSF")]
    assert coverage_value_supported("nuisance_regression.tissue_regressors", terms, quote) is None
    order = _term("before")
    assert (
        coverage_value_supported("temporal_filtering.relative_to_regression", order, quote) is None
    )
    # a list with a tool-name item checks that item literally
    tools = [_term("topup"), _term("FSL FUGUE")]
    assert coverage_value_supported("distortion_correction.tool", tools, quote) is False
    assert (
        coverage_value_supported("distortion_correction.tool", tools, "corrected with FSL FUGUE")
        is True
    )


# --- item 3: one character for the multiplication sign; ligatures ------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "voxels of 2\u03eb2\u03eb3 mm were kept",  # the Coptic glyph a text layer prints
        "voxels of 2\u2afb2\u2afb3 mm were kept",
        "voxels of 2 /C2 2 /C2 3 mm were kept",  # pypdf's leaked glyph code
        "voxels of 2Â2Â3 mm were kept",  # the same code in a GROBID text layer
        "voxels of 2 x 2 x 3 mm were kept",
        "voxels of 2x2x3 mm were kept",
        "voxels of 2 \u00d7 2 \u00d7 3 mm were kept",
    ],
)
def test_every_multiplication_form_matches_every_other(source: str) -> None:
    for quote in (
        "voxels of 2 \u00d7 2 \u00d7 3 mm",
        "voxels of 2x2x3 mm",
        "voxels of 2\u03eb2\u03eb3 mm",
    ):
        r = resolve_quote(quote, source)
        assert r.span is not None, (quote, source)
        assert r.span.text.startswith("voxels of 2") and r.span.text.endswith("3 mm")


def test_glyph_codes_fold_only_between_digits() -> None:
    assert normalize_with_offset_map("see /C2 here")[0] == "see /C2 here"
    assert normalize_with_offset_map("3 /C2 3")[0] == "3x3"
    assert normalize_with_offset_map("a x b")[0] == "a x b"
    # offsets still point into the source
    text = "size 2 /C2 2 mm"
    norm, offsets = normalize_with_offset_map(text)
    assert norm == "size 2x2 mm"
    assert text[offsets[norm.index("x")]] == "/"


def test_ligatures_fold_on_both_sides() -> None:
    assert normalize_with_offset_map("ﬁltered ﬂow eﬀect")[0] == "filtered flow effect"
    r = resolve_quote("filtered with a band-pass", "data were ﬁltered with a band-pass filter")
    assert r.span is not None


# --- item 2b: the checking pass's value for an unverifiable field ------------------------------


def _missing(reason: str) -> dict[str, Any]:
    return {
        "field_id": "x",
        "extraction": {
            "status": "MISSING_FROM_PAPER",
            "searched_terms": [],
            "sections_searched": [],
        },
        "inference": {"status": "LEFT_MISSING", "reason": reason},
    }


def _record(verdict: dict[str, Any], reason: str = "value_unsupported_by_quote") -> dict[str, Any]:
    return {
        "preprocessing": {
            "steps": [{"kind": "nuisance_regression", "motion_expansion": _missing(reason)}]
        },
        "diagnostics": [
            {
                "field": "nuisance_regression.motion_expansion",
                "failure_reason": reason,
                "raw_value": "derivatives",
                "raw_quote": "six synthetic parameters and their derivatives",
            }
        ],
        "verifier": {"status": "ok", "fields": {"nuisance_regression.motion_expansion": verdict}},
    }


def test_a_wrong_verdict_with_a_value_on_the_same_quote_is_checker_supplied() -> None:
    rec = _record(
        {
            "verdict": "wrong",
            "better_value": "first-order derivatives",
            "relied_on": "We regressed six synthetic parameters and their derivatives.",
            "reason": "stated",
        }
    )
    [entry] = checker_supplied(rec)
    assert entry["field"] == "nuisance_regression.motion_expansion"
    assert entry["value"] == "first-order derivatives"
    assert entry["provenance"] == "checker-supplied"
    assert unverifiable_fields(rec) == []


@pytest.mark.parametrize(
    "verdict",
    [
        {"verdict": "wrong", "better_value": None, "relied_on": "six synthetic parameters"},
        {"verdict": "supported", "better_value": "x", "relied_on": "six synthetic parameters"},
        {"verdict": "wrong", "better_value": "x", "relied_on": "An unrelated sentence."},
    ],
)
def test_no_value_no_wrong_or_another_quote_is_not_checker_supplied(
    verdict: dict[str, Any],
) -> None:
    rec = _record(verdict)
    assert checker_supplied(rec) == []
    assert unverifiable_fields(rec) == ["nuisance_regression.motion_expansion"]


def test_a_field_that_is_not_unverifiable_is_never_checker_supplied() -> None:
    rec = _record(
        {"verdict": "wrong", "better_value": "x", "relied_on": "six synthetic parameters"},
        reason="not_stated_in_text",
    )
    assert checker_supplied(rec) == []
    assert unverifiable_fields(rec) == []


def test_same_quote_reads_through_glyphs_and_containment() -> None:
    assert same_quote("2 \u00d7 2 mm voxels", "2\u03eb2 mm voxels")
    assert same_quote("a clause", "A sentence with a clause in it.")
    assert not same_quote("", "anything") and not same_quote("one thing", "another")


def test_the_report_line_says_checker_supplied() -> None:
    import importlib.util
    from pathlib import Path

    from extractor_mvp import render
    from extractor_mvp.coverage_extractor import SpatialExtraction

    spec = importlib.util.spec_from_file_location(
        "_cov", Path(__file__).with_name("test_coverage_expansion.py")
    )
    assert spec and spec.loader
    cov = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cov)
    # a number its quote does not hold: unverifiable under item 2
    prep = cov._run(spatial=SpatialExtraction(smoothing_fwhm_mm=cov._ex("8", cov._S["smooth"])))
    fwhm = prep.steps[[s.kind for s in prep.steps].index("spatial_smoothing")].fwhm_mm
    assert fwhm.inference.reason == "value_unsupported_by_quote"
    entry = {
        "field": "spatial_smoothing.fwhm_mm",
        "value": "6",
        "quote": cov._S["smooth"],
        "provenance": "checker-supplied",
    }
    out = render.to_report(prep, checker_supplied=[entry])
    assert "- fwhm_mm = 6   [checker-supplied]" in out
    assert "[checker-supplied]" not in render.to_report(prep)


# --- the stored-record re-check (items 2 and 3, no model call) ---------------------------------


def test_recheck_turns_a_glyph_failed_number_into_an_extraction() -> None:
    text = "Intro. Methods: voxels were 2\u03eb2\u03eb2 mm and smoothed with a 6 mm kernel. End."
    quote = "voxels were 2 \u00d7 2 \u00d7 2 mm and smoothed with a 6 mm kernel"
    reason = "extraction_quote_unresolved:quote_not_found"
    rec = {
        "methods": {"start_offset": 0, "end_offset": len(text)},
        "preprocessing": {"steps": [{"kind": "spatial_smoothing", "fwhm_mm": _missing(reason)}]},
        "diagnostics": [
            {
                "field": "spatial_smoothing.fwhm_mm",
                "failure_reason": reason,
                "raw_value": "6",
                "raw_quote": quote,
            }
        ],
    }
    new, summary = recheck_record(rec, text)
    assert summary["now_extracted"] == ["spatial_smoothing.fwhm_mm"]
    pf = new["preprocessing"]["steps"][0]["fwhm_mm"]
    assert pf["extraction"]["status"] == "EXTRACTED" and pf["extraction"]["value"] == 6.0
    assert pf["extraction"]["spans"][0]["span_in_full_paper"]["start"] == text.index("voxels")
    assert new["diagnostics"] == []
    assert rec["preprocessing"]["steps"][0]["fwhm_mm"]["extraction"]["status"] != "EXTRACTED"
    # a number the quote does not hold stays as stored
    rec["diagnostics"][0]["raw_value"] = "8"
    new, summary = recheck_record(rec, text)
    assert summary["unchanged"] == ["spatial_smoothing.fwhm_mm"]
    assert new["preprocessing"]["steps"][0]["fwhm_mm"]["extraction"]["status"] != "EXTRACTED"


def _categorical_record(verdict: dict[str, Any] | None) -> tuple[dict[str, Any], str]:
    text = "Methods: the band-pass filter was applied before nuisance regression. End."
    quote = "the band-pass filter was applied before nuisance regression"
    reason = "value_unsupported_by_quote"
    rec: dict[str, Any] = {
        "methods": {"start_offset": 0, "end_offset": len(text)},
        "preprocessing": {
            "steps": [{"kind": "temporal_filtering", "relative_to_regression": _missing(reason)}]
        },
        "diagnostics": [
            {
                "field": "temporal_filtering.relative_to_regression",
                "failure_reason": reason,
                "raw_value": "before",
                "raw_quote": quote,
            }
        ],
    }
    if verdict is not None:
        rec["verifier"] = {
            "status": "ok",
            "fields": {"temporal_filtering.relative_to_regression": verdict},
        }
    return rec, text


def test_recheck_restores_a_categorical_value_only_where_the_checking_pass_did_not_judge_it() -> (
    None
):
    path = "temporal_filtering.relative_to_regression"
    rec, text = _categorical_record(None)
    assert recheck_record(rec, text)[1]["now_extracted"] == [path]
    rec, text = _categorical_record({"verdict": "wrong", "relied_on": "x", "better_value": None})
    assert recheck_record(rec, text)[1]["now_extracted"] == [path]
    for verdict in (
        {"verdict": "supported", "relied_on": "x"},
        {"verdict": "wrong", "relied_on": "x", "better_value": "after"},
    ):
        rec, text = _categorical_record(verdict)
        assert recheck_record(rec, text)[1]["unchanged"] == [path]


@pytest.mark.parametrize("glyph", ["\u03eb", "\u2afb", "\u00d7"])
def test_the_sign_folds_beside_a_unit_too(glyph: str) -> None:
    # not between digits: a unit sits between the sign and the number
    r = resolve_quote(
        "a 3 mm \u00d7 3 mm in-plane grid", f"with a 3 mm {glyph} 3 mm in-plane grid here"
    )
    assert r.span is not None

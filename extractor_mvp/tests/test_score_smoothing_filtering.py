"""scripts/score_smoothing_filtering.py (the author's request of 2026-11-05): the matching rule, the
values as stated, the classes, and that a withheld paper's values never reach the output. Offline:
labels are built in memory (openpyxl is not a dependency here), records from the canned extraction."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import score_smoothing_filtering as sf

from conftest import FULL_TEXT, _canned_payload, stub_client
from extractor_mvp.extractor import extract
from extractor_mvp.parsed_paper import ParsedPaper


def _row(sheet: str = "Smoothing", paper: str = "agtzidis_2020", **kw: Any) -> sf.LabelRow:
    d = {
        "paper_id": paper,
        "applies_to": "all",
        "state": "reported",
        "quote": "Data were smoothed with an 8 mm FWHM Gaussian kernel.",
        "adjudication": "agreed",
        **(
            {"kernel": "Gaussian", "width": 8, "width_measure": "FWHM"}
            if sheet == "Smoothing"
            else {"pass_type": "band-pass", "band_or_cutoff_as_stated": "0.01\u20130.1 Hz"}
        ),
    }
    d.update(kw)
    return sf.label_row(sheet, d)


def _views(sm_state: str = "reported", sm: dict[str, Any] | None = None, **kw: Any) -> Any:
    return {
        "spatial_smoothing": sf.StepView(sm_state, sm or {}, frozenset({"fwhm_mm", "kernel_type"})),
        "temporal_filtering": sf.StepView(
            kw.get("tf_state", "reported"),
            kw.get("tf", {}),
            frozenset({"effective_band_hz", "pass_type"}),
            kw.get("streams"),
        ),
    }


# --- the label checks -----------------------------------------------------------------------------


def test_the_label_checks_pass_clean_rows_and_catch_each_defect() -> None:
    assert sf.validate_labels([_row(), _row("Filtering")]) == []
    bad = [
        _row(state="reproted"),
        _row(paper="b", applies_to=" "),
        _row(paper="c", quote=""),
        _row(paper="d", kernel=None, width=None, width_measure=None),
        _row(paper="e", adjudication="Pending the author"),
    ]
    assert [f[2] for f in sf.validate_labels(bad)] == [
        "state not in vocabulary",
        "applies_to empty",
        "reported, no quote",
        "reported, no value",
        "adjudication says pending",
    ]


# --- matching by paper and applies_to ------------------------------------------------------------


def test_an_all_row_matches_the_records_single_stream() -> None:
    (s,) = sf.score([_row()], {"agtzidis_2020": _views(sm={"fwhm_mm": 8.0})})
    assert s.outcome == "scored" and s.state_agrees and s.values["width"] == "agree"
    (s,) = sf.score(
        [_row(applies_to="all (Parts I\u2013III)")], {"agtzidis_2020": _views(sm={"fwhm_mm": 8.0})}
    )
    assert s.outcome == "scored"


def test_a_record_with_one_all_value_equal_to_one_row_is_collapsed() -> None:
    """DESIGN_applies_to.md §5 (Stage 1, 2026-11-11): the stored records' shape for chen_2015."""
    labels = [
        _row(paper="chen_2015", applies_to="ALFF and fALFF"),
        _row(paper="chen_2015", applies_to="ReHo", state="stated_not_performed"),
    ]
    sm = {"fwhm_mm": 8.0, "kernel_type": "gaussian"}
    out = sf.score(labels, {"chen_2015": _views(sm=sm)})
    assert [s.outcome for s in out] == ["collapsed"] * 2
    assert all(s.values == {} and s.scope is not None for s in out)
    assert out[0].scope is not None and out[0].scope.outcome == "collapsed"


def test_an_all_value_equal_to_no_row_misses_every_row_and_is_spurious() -> None:
    """Positive control for the collapsed class: a 6 mm "all" value against an 8 mm row is not
    collapsed; under fork E2 each row is missed and the record's value spurious."""
    labels = [
        _row(paper="chen_2015", applies_to="ALFF and fALFF"),
        _row(paper="chen_2015", applies_to="ReHo", state="stated_not_performed"),
    ]
    out = sf.score(labels, {"chen_2015": _views(sm={"fwhm_mm": 6.0, "kernel_type": "gaussian"})})
    assert [s.outcome for s in out] == ["missed"] * 2
    assert out[0].scope is not None and out[0].scope.spurious == ["all"]


def test_any_paper_with_two_rows_on_a_sheet_is_scored_as_variants_even_if_one_says_all() -> None:
    labels = [_row(), _row(applies_to="ReHo", state="stated_not_performed")]
    out = sf.score(
        labels, {"agtzidis_2020": _views(sm={"fwhm_mm": 8.0, "kernel_type": "gaussian"})}
    )
    assert [s.outcome for s in out] == ["collapsed"] * 2


def test_a_single_row_not_for_all_is_not_matched_silently() -> None:
    sm = {"fwhm_mm": 8.0, "kernel_type": "gaussian"}
    (s,) = sf.score([_row(applies_to="task-fMRI")], {"agtzidis_2020": _views(sm=sm)})
    assert s.outcome == "collapsed"


def test_a_record_with_parts_against_an_all_row_is_split() -> None:
    stream = sf.StepView("reported", {"effective_band_hz": [0.01, 0.1]}, frozenset(), None, "rest")
    (s,) = sf.score([_row("Filtering")], {"agtzidis_2020": _views(streams={"rest": stream})})
    assert s.outcome == "split"


def test_a_record_that_carries_streams_is_scored_per_stream_by_quote_overlap() -> None:
    q1 = "Parts I and II were band-pass filtered at 0.01 to 0.1 Hz."
    q2 = "In Part III the filter was applied after interpolation."
    labels = [
        _row("Filtering", paper="power_2014", applies_to="Parts I\u2013II", quote=q1),
        _row("Filtering", paper="power_2014", applies_to="Part III", quote=q2),
    ]
    # the record calls the part something else; its sentence overlaps the first row's quote only
    stream = sf.StepView(
        "reported",
        {"effective_band_hz": [0.01, 0.1]},
        frozenset(),
        None,
        "the first two parts",
        (q1,),
    )
    out = sf.score(labels, {"power_2014": _views(streams={"the first two parts": stream})})
    assert [s.outcome for s in out] == ["scored", "missed"]
    assert out[0].values["band"] == "agree"
    assert out[0].scope is not None and out[0].scope.spurious == []


def test_a_record_carrying_applies_to_is_read_as_streams() -> None:
    rec = _canned_record()
    for step in rec["preprocessing"]["steps"]:
        if step["kind"] == "spatial_smoothing":
            ext = step["fwhm_mm"]["extraction"]
            span = {"start": 0, "end": 5, "text": "Data were smoothed at 6 mm for ALFF."}
            step["fwhm_mm"]["extraction"] = {
                "status": "VARIED",
                "variants": [
                    {"value": 6.0, "spans": [span], "applies_to": "ALFF", "confidence": 0.8},
                    {"value": 4.0, "spans": [span], "applies_to": "ReHo", "confidence": 0.8},
                ],
            }
            step["fwhm_mm"]["inference"] = {"status": "NOT_APPLICABLE"}
            assert ext["status"] != "VARIED"
    views = sf.record_steps(rec)
    streams = views["spatial_smoothing"].streams
    assert streams is not None and set(streams) == {"alff", "reho"}
    assert streams["alff"].values["fwhm_mm"] == 6.0 and streams["reho"].values["fwhm_mm"] == 4.0
    assert streams["alff"].quotes == ("Data were smoothed at 6 mm for ALFF.",)
    assert views["temporal_filtering"].streams is None


def test_two_spellings_of_one_part_are_one_stream_key_across_steps_stage2c() -> None:
    a, b = "global connectome (DCw and ECw)", "global connectome metrics (DCw, ECw)"
    rec = _canned_record()
    span = {"start": 0, "end": 5, "text": "x"}
    for step in rec["preprocessing"]["steps"]:
        field = {"spatial_smoothing": "fwhm_mm", "temporal_filtering": "performed"}.get(
            step["kind"]
        )
        if field is None:
            continue
        value = 6.0 if field == "fwhm_mm" else True
        step[field]["extraction"] = {
            "status": "VARIED",
            "variants": [
                {"value": value, "spans": [span], "applies_to": p, "confidence": 0.8}
                for p in ((b, "ReHo") if field == "fwhm_mm" else (a, "ReHo"))
            ],
        }
        step[field]["inference"] = {"status": "NOT_APPLICABLE"}
    views = sf.record_steps(rec)
    sm, tf = views["spatial_smoothing"].streams, views["temporal_filtering"].streams
    assert sm is not None and tf is not None
    assert set(sm) == set(tf) == {"global connectome dcw and ecw", "reho"}
    assert sm["global connectome dcw and ecw"].applies_to == b  # the paper's words stay


def test_a_paper_without_a_record_is_no_record() -> None:
    (s,) = sf.score([_row(paper="wheaton_2004")], {})
    assert s.outcome == "no record"


def test_the_records_streams_are_read_only_when_it_carries_applies_to() -> None:
    assert not sf._carries_applies_to({"fwhm_mm": {"extraction": {"status": "EXTRACTED"}}})
    assert sf._carries_applies_to({"fwhm_mm": {"extraction": {"status": "VARIED"}}})


# --- values as stated ----------------------------------------------------------------------------


def test_fwhm_six_agrees_with_six_point_zero_and_sigma_is_a_measure_mismatch() -> None:
    assert sf.compare_smoothing({"width": 6, "width_measure": "FWHM"}, {"fwhm_mm": 6.0})[
        "width"
    ] == ("agree")
    assert sf.compare_smoothing({"width": 6, "width_measure": "FWHM"}, {"fwhm_mm": 8.0})[
        "width"
    ] == ("disagree")
    got = sf.compare_smoothing({"width": 2.55, "width_measure": "sigma"}, {"fwhm_mm": 6.0})
    assert got["width"] == "measure mismatch (label sigma, record FWHM)"
    got = sf.compare_smoothing({"width": 2.55, "width_measure": "sigma"}, {})
    assert got["width"] == "record has no value (label sigma)"
    assert sf.compare_smoothing({"kernel": "Gaussian"}, {"kernel_type": "gaussian"})["kernel"] == (
        "agree"
    )


def test_a_cutoff_in_seconds_or_cycles_is_a_unit_mismatch_never_converted() -> None:
    rec = {"cutoff": 0.01}
    assert sf.compare_filtering({"band_or_cutoff_as_stated": "100 s"}, rec)["band"] == (
        "unit mismatch (label s, record Hz)"
    )
    got = sf.compare_filtering({"band_or_cutoff_as_stated": "three cycles per scan"}, rec)
    assert got["band"] == "unit mismatch (label cycles, record Hz)"
    assert sf.compare_filtering({"band_or_cutoff_as_stated": "not stated"}, rec)["band"] == (
        "not labelled"
    )


def test_a_band_in_hz_agrees_as_a_set_of_edges() -> None:
    rec = {"effective_band_hz": [0.01, 0.1]}
    for stated in ("0.01\u20130.1 Hz", "0.01 Hz and 0.1 Hz", "0.01 < f < 0.1 Hz"):
        assert sf.compare_filtering({"band_or_cutoff_as_stated": stated}, rec)["band"] == "agree"
    assert sf.compare_filtering({"band_or_cutoff_as_stated": "0.009\u20130.08 Hz"}, rec)[
        "band"
    ] == ("disagree")


def test_pass_type_not_in_the_records_schema_is_said_so() -> None:
    label = {"pass_type": "band-pass"}
    assert sf.compare_filtering(label, {}, frozenset({"effective_band_hz"}))["pass_type"] == (
        "not asked in this record's schema"
    )
    assert sf.compare_filtering(label, {}, frozenset({"pass_type"}))["pass_type"] == (
        "record has no value"
    )
    assert sf.compare_filtering(label, {"pass_type": "band_pass"}, frozenset({"pass_type"}))[
        "pass_type"
    ] == ("agree")
    assert sf.compare_filtering({"pass_type": "band (wavelet)"}, {})["pass_type"] == (
        "label not comparable as stated"
    )


# --- classes and the withheld papers -------------------------------------------------------------


def test_the_contamination_classes() -> None:
    assert sf.contamination_class("liu_2005") == sf.AUTHOR_RULED_EXPOSED
    assert sf.contamination_class("wheaton_2004") == sf.AUTHOR_ALONE
    assert sf.contamination_class("tang_2025") == sf.CO_ADJUDICATED
    assert sf.contamination_class("chen_2015") == sf.CO_ADJUDICATED


@pytest.mark.parametrize("paper", sorted(sf.VALUES_WITHHELD))
def test_a_withheld_papers_values_never_reach_the_output(paper: str) -> None:
    label = _row(paper=paper, applies_to="all", width=7.25, kernel="Boxcar", quote="Q-SECRET")
    rec = {paper: _views(sm={"fwhm_mm": 7.25, "kernel_type": "boxcar"})}
    text = sf.render(sf.score([label], rec), "results/x")
    assert paper in text and "reported" in text and "agree" in text
    for secret in ("7.25", "Boxcar", "boxcar", "Q-SECRET", "| all |"):
        assert secret not in text
    sigma = _row(paper=paper, width=2.5, width_measure="sigma", kernel=None)
    text = sf.render(sf.score([sigma], rec), "results/x")
    assert "sigma" not in text and "2.5" not in text and "width: no match" in text


def test_counts_are_grouped_by_class_and_carry_no_rate() -> None:
    labels = [_row(), _row(paper="liu_2005"), _row(paper="wheaton_2004")]
    text = sf.render(sf.score(labels, {"agtzidis_2020": _views(sm={"fwhm_mm": 8.0})}), "r")
    assert "| co-adjudicated | reported | 1 | 0 | 0 | 0 | 0 | 0 |" in text
    assert "| author-ruled, assistant exposure | reported | 0 | 0 | 0 | 0 | 0 | 1 |" in text
    assert "| author alone | reported | 0 | 0 | 0 | 0 | 0 | 1 |" in text
    assert "%" not in text and "rate" not in text.lower().replace("no rates", "")


# --- records read with the current code ----------------------------------------------------------


def _canned_record() -> dict[str, Any]:
    prep, _, _ = extract(
        ParsedPaper(text=FULL_TEXT, source="p"), "m", client=stub_client(_canned_payload())
    )
    return {"preprocessing": prep.model_dump(mode="json")}


def test_a_record_is_read_with_the_reports_own_row_states() -> None:
    views = sf.record_steps(_canned_record())
    assert set(views) == {"spatial_smoothing", "temporal_filtering"}
    assert all(v.state in sf.RECORD_TO_LABEL_STATE.values() for v in views.values())
    assert "pass_type" in views["temporal_filtering"].asked


def test_a_record_written_before_pass_type_does_not_ask_it() -> None:
    rec = _canned_record()
    for step in rec["preprocessing"]["steps"]:
        if step["kind"] == "temporal_filtering":
            step.pop("pass_type", None)
    assert "pass_type" not in sf.record_steps(rec)["temporal_filtering"].asked


def test_a_value_the_records_schema_did_not_have_does_not_block_collapsed() -> None:
    """coverage_v4 predates pass_type: 'not asked in this record's schema' is no evidence either way,
    so the record's one band equal to a row's is collapsed. A band the record lacks is not."""
    labels = [
        _row("Filtering", paper="power_2014", applies_to="Parts I\u2013II"),
        _row("Filtering", paper="power_2014", applies_to="Part III"),
    ]
    old = sf.StepView(
        "reported", {"effective_band_hz": [0.01, 0.1]}, frozenset({"effective_band_hz"})
    )
    views = {**_views(), "temporal_filtering": old}
    assert [s.outcome for s in sf.score(labels, {"power_2014": views})] == ["collapsed"] * 2
    lacking = sf.StepView("reported", {}, frozenset({"effective_band_hz", "pass_type"}))
    views = {**_views(), "temporal_filtering": lacking}
    assert [s.outcome for s in sf.score(labels, {"power_2014": views})] == ["missed"] * 2

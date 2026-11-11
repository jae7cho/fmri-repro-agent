"""scripts/preproc_rows_scoring.py and the twelve score_rows_<sheet>.py (2026-11-11, pre-registered
before any label exists). Offline: labels are built in memory (openpyxl is not a dependency here),
records from the canned extraction."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import preproc_rows_scoring as pr  # noqa: E402

from conftest import FULL_TEXT, _canned_payload, stub_client  # noqa: E402
from extractor_mvp.extractor import extract  # noqa: E402
from extractor_mvp.parsed_paper import ParsedPaper  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "merge_labels", pr.REPO / "scripts" / "merge_labels.py"
)
assert _spec is not None and _spec.loader is not None
ml = importlib.util.module_from_spec(_spec)
sys.modules["merge_labels"] = ml  # dataclasses resolves the module by name
_spec.loader.exec_module(ml)

#: sha256 of the pre-registered scoring rules and each per-sheet script (2026-11-11). A change after
#: labels exist is a dated event: update the pin with a note saying what changed and why.
PINNED_SHA256 = {
    "preproc_rows_scoring.py": "b7e49ab1a1d3ed273bece350d4b50c82351694875d650c1559158ecc82851608",
    "score_rows_slice_time_correction.py": "536fbb158b8bd5e7c1c2dfcdb020494bb4bae2ea53e8a1bbcba61dac07db553e",
    "score_rows_nuisance_regression.py": "1252bd4e6068c4d658a372fc4e89264ca13f2f7acf3aa9d32f0f1f096418d5d9",
    "score_rows_compcor.py": "c06127a52821e59eb1853e8fb3232eab1fcd39ddc254e09873a3810e121c41e2",
    "score_rows_ica_denoise.py": "e9fc4d9ab80360b577945c2c7724bf9ac3ad0b3042fbd1889aaef6e8185f1a9c",
    "score_rows_scrub.py": "fb53c1e8d404bc3bc42ccf193bf39ac9e95da230845a1ad411fbdc08eb1fcef2",
    "score_rows_despike.py": "046b8b94c37f41d89664eef15ee26e82e22f318799c5c9f60ec0dbfd2db2e1ee",
    "score_rows_nonsteadystate_removal.py": "cce423e4fea75f203a13a1227bc4606f05ce7f9a7792cb248a868ae1df9bee5d",
    "score_rows_coregistration.py": "21cb98148b59cca248af4a4f819fd918099f9e1d0ce27e9ea109edd4d49d180d",
    "score_rows_distortion_correction.py": "626841596a7eb7c0addede2c0b03954ca50fe1b76041d84412ac72d1d5270ca6",
    "score_rows_brain_extraction.py": "47c15628eb6c9ccc0e3631bb2379e6a74be06d79cc6242d9517a91b740c2cd39",
    "score_rows_segmentation.py": "cecf4379ee43395a501cffec4266fe3b105db2265b70dd602e5662b2e00d3be7",
    "score_rows_intensity_correction.py": "66254f6508ed1bf7a127ac512c625d5300759fe304ad539a79d95f7acb4a1600",
}


def _label(paper: str = "agtzidis_2020", sheet: str = "scrub", **kw: Any) -> pr.RowLabel:
    values = {f: None for f in pr.step_fields(sheet)}
    values.update(kw.pop("values", {}))
    return pr.RowLabel(
        sheet=sheet,
        paper_id=paper,
        applies_to=kw.pop("applies_to", "all"),
        state=kw.pop("state", "reported"),
        values=values,
        quote=kw.pop("quote", "Frames with FD above 0.5 mm were censored."),
        adjudication=kw.pop("adjudication", "author alone, 2099-01-01"),
    )


def _view(state: str = "reported", values: dict | None = None, **kw: Any) -> pr.StepView:
    asked = frozenset(pr.step_fields("scrub"))
    return pr.StepView(
        state,
        values or {},
        asked,
        kw.get("streams"),
        kw.get("applies_to", "all"),
        kw.get("quotes", ()),
    )


# --- the sheets are the merge script's and the schema's ------------------------------------------


def test_the_sheets_and_columns_are_the_merge_scripts() -> None:
    assert pr.SHEETS == tuple(ml.ROW_STEP_FIELDS)
    for sheet in pr.SHEETS:
        assert pr.step_fields(sheet) == ml.ROW_STEP_FIELDS[sheet]
        assert pr.columns(sheet) == ("paper_id", *ml.ROW_SHEETS[sheet], "adjudication")


def test_one_script_per_sheet_each_calling_the_shared_rules() -> None:
    scripts = sorted(p.name for p in SCRIPTS.glob("score_rows_*.py"))
    assert scripts == sorted(f"score_rows_{s}.py" for s in pr.SHEETS)
    for s in pr.SHEETS:
        assert f'raise SystemExit(main("{s}"))' in (SCRIPTS / f"score_rows_{s}.py").read_text()
    with pytest.raises(ValueError):
        pr.main("motion_correction", [])


@pytest.mark.parametrize("sheet", pr.SHEETS)
def test_with_no_labels_the_run_prints_the_expected_schema_and_exits_0(
    sheet: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = pr.main(sheet, ["--labels", str(tmp_path / "none.xlsx"), "--results-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith(f"# {sheet}: no labels yet")
    assert ", ".join(pr.columns(sheet)) in out and "stated_not_performed" in out


# --- values as stated ----------------------------------------------------------------------------


def test_values_are_compared_as_stated() -> None:
    cv = pr.compare_value
    assert cv("0.5 mm", 0.5) == "agree"  # the unit is not a value; nothing is converted
    assert cv("0.50", 0.5) == "agree" and cv("0.2 mm", 0.5) == "disagree"
    assert cv("0.5 or 1.0 mm", 0.5) == "disagree"  # two numbers are not one
    assert cv("yes", True) == "agree" and cv("no", True) == "disagree"
    term = {"verbatim": "linear interpolation", "resolved": "linear"}
    assert cv("Linear interpolation", term) == "agree" and cv("linear", term) == "agree"
    assert cv("spline", term) == "disagree"
    items = [{"verbatim": "FD", "resolved": "fd"}, {"verbatim": "DVARS", "resolved": "dvars"}]
    assert cv("DVARS and FD", items) == "agree"
    assert cv("FD", items) == "disagree" and cv("FD, DVARS, GS", items) == "disagree"
    assert cv("0.01-0.1 Hz", (0.01, 0.1)) == "agree" and cv("0.009-0.08", (0.01, 0.1)) == "disagree"
    assert cv("3dDespike", "3dDespike") == "agree"


def test_field_outcomes() -> None:
    view = pr.StepView("reported", {"threshold": 0.5}, frozenset({"threshold", "method"}))
    out = pr.compare(
        {"threshold": "0.5 mm", "method": "FD", "criterion": "x", "remediation": None}, view
    )
    assert out == {
        "threshold": "agree",
        "method": "record has no value",
        "criterion": "not asked in this record's schema",
        "remediation": "not labelled",
    }


# --- the applies_to classes ----------------------------------------------------------------------


def test_an_all_row_is_scored_directly() -> None:
    (s,) = pr.score(
        [_label(values={"threshold": "0.5 mm"})],
        {"agtzidis_2020": _view(values={"threshold": 0.5})},
    )
    assert s.outcome == "scored" and s.state_agrees and s.values["threshold"] == "agree"


def test_collapsed_split_missed_and_no_record() -> None:
    rows = [
        _label(applies_to="task runs", values={"threshold": "0.5 mm"}),
        _label(
            applies_to="rest runs",
            state="stated_not_performed",
            quote="Rest runs were not censored.",
        ),
    ]
    out = pr.score(rows, {"agtzidis_2020": _view(values={"threshold": 0.5})})
    assert [s.outcome for s in out] == ["collapsed", "collapsed"]
    out = pr.score(rows, {"agtzidis_2020": _view(values={"threshold": 0.9})})
    assert [s.outcome for s in out] == ["missed", "missed"]
    assert out[0].scope is not None and out[0].scope.spurious == ["all"]
    part = _view(values={"threshold": 0.5}, applies_to="task", quotes=("x",))
    (s,) = pr.score([_label()], {"agtzidis_2020": _view(streams={"task": part})})
    assert s.outcome == "split"
    (s,) = pr.score([_label(paper="nobody_2000")], {})
    assert s.outcome == "no record"


def test_a_record_part_is_matched_by_quote_overlap() -> None:
    q = "Task runs were censored at FD above 0.5 mm."
    rows = [
        _label(applies_to="task runs", values={"threshold": "0.5 mm"}, quote=q),
        _label(
            applies_to="rest runs",
            state="stated_not_performed",
            quote="Rest runs were not censored.",
        ),
    ]
    part = _view(values={"threshold": 0.5}, applies_to="the task data", quotes=(q,))
    out = pr.score(rows, {"agtzidis_2020": _view(streams={"the task data": part})})
    assert [s.outcome for s in out] == ["scored", "missed"]
    assert out[0].values["threshold"] == "agree"


@pytest.mark.parametrize("paper", sorted(pr.VALUES_WITHHELD))
def test_a_withheld_papers_values_never_reach_the_output(paper: str) -> None:
    label = _label(paper=paper, values={"threshold": "7.25 mm"}, quote="Q-SECRET")
    text = pr.render(
        "scrub", pr.score([label], {paper: _view(values={"threshold": 7.25})}), Path("r")
    )
    assert paper in text and "reported" in text and "threshold: match" in text
    parts = [
        _label(
            paper=paper, applies_to="task-SECRET", values={"threshold": "7.25 mm"}, quote="Q-SECRET"
        ),
        _label(paper=paper, applies_to="rest-SECRET", state="not_reported", quote=""),
    ]
    text += pr.render(
        "scrub", pr.score(parts, {paper: _view(values={"threshold": 7.25})}), Path("r")
    )
    assert "collapsed" in text and "(withheld)" in text
    for secret in ("7.25", "SECRET"):
        assert secret not in text


def test_label_checks() -> None:
    bad = [
        _label(state="named_tool"),
        _label(applies_to=""),
        _label(quote=""),
        _label(adjudication="pending the author"),
    ]
    assert [f[1] for f in pr.validate_labels(bad)] == [
        "state not in vocabulary",
        "applies_to empty",
        "reported, no value",
        "reported, no value",
        "reported, no quote",
        "reported, no value",
        "adjudication says pending",
    ]


def test_a_label_check_failure_exits_1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pr, "load_labels", lambda sheet, path: [_label(state="bogus")])
    assert pr.main("scrub", ["--results-dir", str(tmp_path)]) == 1


# --- records -------------------------------------------------------------------------------------


def _canned_record() -> dict[str, Any]:
    prep, _, _ = extract(
        ParsedPaper(text=FULL_TEXT, source="p"), "m", client=stub_client(_canned_payload())
    )
    return {"preprocessing": prep.model_dump(mode="json")}


def test_a_record_is_read_with_the_reports_kind_state() -> None:
    for sheet in pr.SHEETS:
        view = pr.record_view(_canned_record(), sheet)
        assert view.state in pr.RECORD_TO_LABEL_STATE.values()
        assert "performed" not in view.values
        assert set(view.values) <= set(pr.step_fields(sheet)) | {"applied_to"}


def test_an_extracted_performed_sets_the_state_and_is_not_a_value() -> None:
    rec = _canned_record()
    step = next(s for s in rec["preprocessing"]["steps"] if s["kind"] == "scrub")
    span = {"start": 0, "end": 30, "text": "Frames with high motion were censored."}
    step["performed"] = {
        "field_id": "performed",
        "extraction": {"status": "EXTRACTED", "value": True, "spans": [span], "confidence": 0.8},
        "inference": {"status": "NOT_APPLICABLE"},
    }
    view = pr.record_view(rec, "scrub")
    assert view.state == "reported" and "performed" not in view.values
    assert view.quotes == ("Frames with high motion were censored.",)


def test_the_latest_complete_results_directory_is_read(tmp_path: Path) -> None:
    ids = ["a_1", "b_2"]
    for name, have, t in (("old", ids, 100), ("partial", ids[:1], 300), ("new", ids, 200)):
        papers = tmp_path / name / "papers"
        papers.mkdir(parents=True)
        for i in have:
            (papers / f"{i}.json").write_text("{}")
        os.utime(papers, (t, t))
    assert pr.latest_results_dir(tmp_path, ids) == tmp_path / "new"
    assert pr.latest_results_dir(tmp_path, ["c_3"]) is None


def test_the_full_run_reports_against_stored_records(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    (tmp_path / "papers").mkdir()
    (tmp_path / "papers" / "agtzidis_2020.json").write_text(json.dumps(_canned_record()))
    monkeypatch.setattr(
        pr, "load_labels", lambda sheet, path: [_label(state="not_reported", quote="")]
    )
    assert pr.main("scrub", ["--results-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# scrub: stored records vs the author's labels")
    assert "| co-adjudicated | agtzidis_2020 | all | not_reported |" in out
    assert "%" not in out


# --- the pin -------------------------------------------------------------------------------------


def test_the_scoring_rules_are_pinned() -> None:
    names = ["preproc_rows_scoring.py", *(f"score_rows_{s}.py" for s in pr.SHEETS)]
    got = {n: hashlib.sha256((SCRIPTS / n).read_bytes()).hexdigest() for n in names}
    assert got == PINNED_SHA256, (
        "the pre-registered scoring rules changed; update PINNED_SHA256 only with a dated note"
    )

"""scripts/preproc_rows_scoring_v2.py and its four score_rows_<sheet>.py (2026-11-11, the second set,
pre-registered before any label on these sheets exists). Offline: labels are built in memory,
records from the canned extraction, edited where a test needs a value. Every value is invented."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import preproc_rows_scoring as pr  # noqa: E402
import preproc_rows_scoring_v2 as v2  # noqa: E402

from conftest import FULL_TEXT, _canned_payload, stub_client  # noqa: E402
from extractor_mvp.cobidas import Mention  # noqa: E402
from extractor_mvp.extractor import extract  # noqa: E402
from extractor_mvp.parsed_paper import ParsedPaper  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "merge_labels", pr.REPO / "scripts" / "merge_labels.py"
)
assert _spec is not None and _spec.loader is not None
ml = importlib.util.module_from_spec(_spec)
sys.modules["merge_labels"] = ml
_spec.loader.exec_module(ml)

#: sha256 of the pre-registered rules for the four rows and each per-sheet script (2026-11-11). A
#: change after labels exist is a dated event: update the pin with a note saying what changed and why.
PINNED_SHA256 = {
    "preproc_rows_scoring_v2.py": "eef187ad2b6c9636144296c45396ad5e5f7a03d70f2275c7a422173c41554635",
    "score_rows_gradient_distortion_correction.py": "eeac118a4efdb787a7d30f46f508ca94b0176505f283cd6b226aaded52004ba9",
    "score_rows_intersubject_registration.py": "35154fd8064050bdd1c0e5b7921fa754f76b9163d0f0bb6de7b83348964b6dd1",
    "score_rows_resting_state_feature.py": "337093f6c50675032d906900a6c66e7a8df8094c423f481ac6560425c9f949f9",
    "score_rows_software.py": "0c78ddce79919c47eda3dbdfc9528978a281ded2fd4b29c463ac6368e2f394a6",
}

_RECORD: dict[str, Any] | None = None


def _canned_record() -> dict[str, Any]:
    global _RECORD
    if _RECORD is None:
        prep, _, _ = extract(
            ParsedPaper(text=FULL_TEXT, source="p"), "m", client=stub_client(_canned_payload())
        )
        _RECORD = {"preprocessing": prep.model_dump(mode="json")}
    return copy.deepcopy(_RECORD)


def _set(record: dict[str, Any], kind: str, field: str, value: Any, text: str) -> None:
    step = next(s for s in record["preprocessing"]["steps"] if s["kind"] == kind)
    step[field]["extraction"] = {
        "status": "EXTRACTED",
        "value": value,
        "spans": [{"start": 0, "end": len(text), "text": text}],
        "confidence": 0.8,
    }
    step[field]["inference"] = {"status": "NOT_APPLICABLE"}


def _term(x: str) -> dict[str, str]:
    return {"verbatim": x, "resolved": x, "resolution": "resolved"}


def _label(sheet: str, paper: str = "agtzidis_2020", **kw: Any) -> pr.RowLabel:
    values = {f: None for f in v2.FIELDS[sheet]}
    values.update(kw.pop("values", {}))
    return pr.RowLabel(
        sheet=sheet,
        paper_id=paper,
        applies_to=kw.pop("applies_to", "all"),
        state=kw.pop("state", "reported"),
        values=values,
        quote=kw.pop("quote", "A synthetic sentence."),
        adjudication="author alone, 2099-01-01",
    )


# --- the sheets are the merge script's -----------------------------------------------------------


def test_the_four_sheets_and_columns_are_the_merge_scripts() -> None:
    assert v2.FIELDS == ml.ROW_LABEL_FIELDS
    assert v2.KEY == ml.ROW_KEY
    assert not set(v2.SHEETS) & set(pr.SHEETS)
    for sheet in v2.SHEETS:
        assert v2.columns(sheet) == ("paper_id", *ml.ROW_SHEETS[sheet], "adjudication")
    assert tuple(ml.ROW_SHEETS) == (*pr.SHEETS, *v2.SHEETS)


def test_one_script_per_sheet_each_calling_the_v2_rules() -> None:
    for s in v2.SHEETS:
        text = (SCRIPTS / f"score_rows_{s}.py").read_text()
        assert "from preproc_rows_scoring_v2 import main" in text
        assert f'raise SystemExit(main("{s}"))' in text
    with pytest.raises(ValueError):
        v2.main("scrub", [])  # one of the first twelve: not this module's


@pytest.mark.parametrize("sheet", v2.SHEETS)
def test_with_no_labels_the_run_prints_the_expected_schema_and_exits_0(
    sheet: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = v2.main(sheet, ["--labels", str(tmp_path / "none.xlsx"), "--results-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0 and out.startswith(f"# {sheet}: no labels yet")
    assert ", ".join(v2.columns(sheet)) in out


# --- gradient distortion correction --------------------------------------------------------------


def test_gradient_values_only_when_the_records_source_is_gradient_nonlinearity() -> None:
    rec = _canned_record()
    _set(rec, "distortion_correction", "tool", [_term("gradunwarp")], "Gradunwarp was applied.")
    _set(rec, "distortion_correction", "source", [_term("susceptibility_fieldmap")], "Fieldmap.")
    view = v2.gradient_view(rec)
    assert view.values == {} and view.state == "reported"  # the report's row reads the whole step
    out = v2.compare({"method": None, "tool": "gradunwarp"}, view)
    assert out["tool"] == "record has no value"
    _set(
        rec,
        "distortion_correction",
        "source",
        [_term("susceptibility_fieldmap"), _term("gradient_nonlinearity")],
        "Both.",
    )
    view = v2.gradient_view(rec)
    assert v2.compare({"method": None, "tool": "gradunwarp"}, view)["tool"] == "agree"
    assert v2.compare({"method": None, "tool": "fugue"}, view)["tool"] == "disagree"


def test_gradient_state_is_the_reports_own_row_state() -> None:
    from extractor_mvp.cobidas import assess_coverage, row_state

    rec = _canned_record()
    prep, rows, _ = v2._parsed(rec)
    rc = next(
        c
        for c in assess_coverage(rows, None, prep.software_mentions)
        if c.row.row_id == "gradient_distortion_correction"
    )
    assert v2.gradient_view(rec).state == v2.RECORD_TO_LABEL_STATE[row_state(rc, rows)]


# --- intersubject registration -------------------------------------------------------------------


def test_intersubject_values_map_to_normalization_and_surface_fields() -> None:
    rec = _canned_record()
    view = v2.intersubject_view(rec)
    assert view.values["volume_or_surface"] == ["volume"]
    assert "cost_function" not in view.asked  # no schema field
    out = v2.compare({"volume_or_surface": "volume", "cost_function": "mutual information"}, view)
    assert out == {
        "volume_or_surface": "agree",
        "cost_function": "not asked in this record's schema",
    }
    _set(rec, "surface_projection", "target_surface", _term("fsaverage5"), "fsaverage5.")
    view = v2.intersubject_view(rec)
    assert v2.compare({"volume_or_surface": "both"}, view)["volume_or_surface"] == "agree"
    assert v2.compare({"volume_or_surface": "surface"}, view)["volume_or_surface"] == "disagree"
    # template agrees with either the volume target or the surface target
    assert v2.compare({"template": "fsaverage5"}, view)["template"] == "agree"


def test_any_of_agrees_when_one_agrees() -> None:
    rec = ("any of", [{"verbatim": "SyN", "resolved": "nonlinear"}, "affine then SyN"])
    assert v2.compare_value("nonlinear", rec) == "agree"
    assert v2.compare_value("rigid", rec) == "disagree"


def test_intersubject_rows_score_through_the_first_twelves_classes() -> None:
    rec = _canned_record()
    views = {"agtzidis_2020": v2.intersubject_view(rec)}
    (s,) = v2.score(
        [_label("intersubject_registration", values={"volume_or_surface": "volume"})], views
    )
    assert s.outcome == "scored" and s.values["volume_or_surface"] == "agree"
    parts = [
        _label("intersubject_registration", applies_to="task", quote="Task sentence."),
        _label("intersubject_registration", applies_to="rest", quote="Rest sentence."),
    ]
    out = v2.score(parts, views)
    assert {x.outcome for x in out} <= {"missed", "collapsed", "scored"}


# --- resting-state feature -----------------------------------------------------------------------


def test_resting_state_feature_is_not_assessed() -> None:
    view = v2.not_assessed_view(_canned_record())
    rows = [
        _label("resting_state_feature", applies_to="ALFF", values={"band_hz": "0.01-0.08 Hz"}),
        _label("resting_state_feature", applies_to="ReHo", values={"reho_measure": "KCC"}),
        _label("resting_state_feature", paper="nobody_2099", applies_to="ALFF"),
    ]
    alff, reho, nobody = v2.score_not_assessed(rows, {"agtzidis_2020": view})
    assert (alff.outcome, alff.record_state, alff.state_agrees) == ("scored", "not_assessed", False)
    assert reho.values["reho_measure"] == "not asked in this record's schema"
    assert nobody.outcome == "no record"
    # control: through the parts matcher the same rows would be missed, which misstates them
    assert {x.outcome for x in v2.score(rows[:2], {"agtzidis_2020": view})} == {"missed"}
    out = v2.compare({"band_hz": "0.01-0.08 Hz", "measure": ""}, view)
    assert out == {"band_hz": "not asked in this record's schema", "measure": "not labelled"}


# --- software ------------------------------------------------------------------------------------


def _sw(paper: str = "agtzidis_2020", **kw: Any) -> pr.RowLabel:
    return _label("software", paper=paper, **kw)


def test_software_packages_match_by_name_and_compare_version_as_stated() -> None:
    rec = v2.SoftwareRecord(
        [
            Mention("FSL", "6.0.4", "preprocessing"),
            Mention("AFNI", None, None),
            Mention("ANTs", "2.3", None),
        ],
        "partially_reported",
    )
    labels = [
        _sw(applies_to="fsl", values={"version_as_stated": "v6.0.4", "used_for": "preprocessing"}),
        _sw(applies_to="AFNI", state="partially_reported"),
        _sw(applies_to="SPM", values={"version_as_stated": "12"}),
    ]
    results, papers = v2.score_software(labels, {"agtzidis_2020": rec})
    fsl, afni, spm = results
    assert fsl.outcome == "scored" and fsl.state_agrees
    assert fsl.values == {"version_as_stated": "agree", "used_for": "agree"}
    assert afni.outcome == "scored" and afni.record_state == "partially_reported"
    assert spm.outcome == "missed"
    (p,) = papers
    assert p.spurious == 1 and p.label_state == "partially_reported"  # ANTs unlabelled
    assert p.report_state == "partially_reported"
    # a version that differs is a disagreement, digit-exact
    (r,) = v2.score_software(
        [_sw(applies_to="FSL", values={"version_as_stated": "6.0"})], {"agtzidis_2020": rec}
    )[0]
    assert r.values["version_as_stated"] == "disagree"


def test_content_words_join_a_package_name_and_none_named_rows() -> None:
    assert v2.same_package("FreeSurfer (v7)", "freesurfer v7")
    assert not v2.same_package("FSL", "FSL FEAT")
    empty = v2.SoftwareRecord([], "not_reported")
    results, papers = v2.score_software(
        [_sw(applies_to="", state="not_reported", quote="")], {"agtzidis_2020": empty}
    )
    assert results[0].outcome == "none named" and results[0].state_agrees
    assert papers[0].label_state == "not_reported"
    named = v2.SoftwareRecord([Mention("FSL", None, None)], "not_reported")
    results, _ = v2.score_software(
        [_sw(applies_to="", state="not_reported", quote="")], {"agtzidis_2020": named}
    )
    assert results[0].state_agrees is False


def test_software_label_checks() -> None:
    ok = _sw(applies_to="", state="not_reported", quote="")
    bad = _sw(applies_to="", state="reported")
    assert v2.validate_labels("software", [ok]) == []
    assert ("agtzidis_2020", "name empty") in v2.validate_labels("software", [bad])


@pytest.mark.parametrize("paper", ["liu_2005", "tang_2025", "wheaton_2004"])
def test_a_withheld_papers_names_and_values_never_reach_the_output(paper: str) -> None:
    rec = v2.SoftwareRecord([Mention("SecretPkgName", "9.9.9", "zzz")], "reported")
    labels = [_sw(paper=paper, applies_to="SecretPkgName", values={"version_as_stated": "9.9.9"})]
    results, papers = v2.score_software(labels, {paper: rec})
    text = v2.render_software(results, papers, Path("/tmp/x"))
    assert "SecretPkgName" not in text and "9.9.9" not in text and "(withheld)" in text
    assert "match" in text
    # positive control: a paper not held out shows its package
    results, papers = v2.score_software(
        [_sw(applies_to="SecretPkgName", values={"version_as_stated": "9.9.9"})],
        {"agtzidis_2020": rec},
    )
    assert "SecretPkgName" in v2.render_software(results, papers, Path("/tmp/x"))


def test_software_record_reads_the_software_rows_own_list() -> None:
    rec = v2.software_record(_canned_record())
    assert rec.row_state in v2.RECORD_TO_LABEL_STATE.values()
    assert all(hasattr(m, "version") for m in rec.packages)


# --- the pin -------------------------------------------------------------------------------------


def test_the_scoring_rules_for_the_four_rows_are_pinned() -> None:
    got = {n: hashlib.sha256((SCRIPTS / n).read_bytes()).hexdigest() for n in PINNED_SHA256}
    assert got == PINNED_SHA256, (
        "the pre-registered scoring rules changed; update PINNED_SHA256 only with a dated note"
    )


def test_the_resting_state_run_scores_every_row_as_not_assessed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import json

    (tmp_path / "papers").mkdir()
    (tmp_path / "papers" / "agtzidis_2020.json").write_text(json.dumps(_canned_record()))
    rows = [_label("resting_state_feature", applies_to="ALFF", values={"measure": "ALFF"})]
    monkeypatch.setattr(v2, "load_labels", lambda sheet, path: rows)
    code, text = v2.run("resting_state_feature", tmp_path / "x.xlsx", tmp_path)
    assert code == 0
    assert "| co-adjudicated | agtzidis_2020 | ALFF | reported | not_assessed | disagree |" in text
    assert "measure: not asked in this record's schema" in text and "%" not in text

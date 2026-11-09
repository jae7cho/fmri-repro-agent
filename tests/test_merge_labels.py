"""scripts/merge_labels.py on synthetic exports. No paper text: every value below is invented."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import openpyxl
import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("merge_labels", REPO / "scripts" / "merge_labels.py")
assert _spec and _spec.loader
ml = importlib.util.module_from_spec(_spec)
sys.modules["merge_labels"] = ml  # dataclasses look the module up by name
_spec.loader.exec_module(ml)

MOTION_HEAD = [
    "paper_id",
    "method_state",
    "method_value",
    "method_quote",
    "nonrigid_transform_state",
    "nonrigid_transform_verbatim",
    "fieldmap_unwarping_state",
    "fieldmap_unwarping_verbatim",
    "reference_scan_state",
    "reference_scan_verbatim",
    "similarity_metric_state",
    "similarity_metric_verbatim",
    "interpolation_combined_state",
    "interpolation_combined_verbatim",
    "slice_to_volume_state",
    "slice_to_volume_verbatim",
    "notes",
    "attribution",
]
SMOOTHING_HEAD = ["paper_id", "applies_to", "state", "kernel", "width", "width_measure", "space"]
SMOOTHING_HEAD += ["quote", "notes", "adjudication"]
FILTERING_HEAD = ["paper_id", "applies_to", "state", "pass_type", "band_or_cutoff_as_stated"]
FILTERING_HEAD += ["filter_type", "order", "quote", "notes", "adjudication"]

SYNTHETIC = {
    "schema": "aespa-labels/1",
    "paper_id": "synthetic_2099",
    "exported_at": "2099-01-01T00:00:00.000Z",
    "motion": {
        "state": "named_tool",
        "named_tool": "ToolX",
        "attribution": "step",
        "quote": "Synthetic sentence one.",
        "notes": "synthetic note",
    },
    "smoothing": [
        {
            "applies_to": "all",
            "state": "reported",
            "kernel": "Gaussian",
            "width": "6",
            "width_measure": "FWHM",
            "space": "volume",
            "quote": "Synthetic sentence two.",
            "notes": "",
        },
        {
            "applies_to": "stream B",
            "state": "partially_reported",
            "kernel": "",
            "width": "2.5 mm",
            "width_measure": "",
            "space": "",
            "quote": "Synthetic sentence three.",
            "notes": "",
        },
    ],
    "filtering": [
        {
            "applies_to": "all",
            "state": "reported",
            "pass_type": "band",
            "band_or_cutoff_as_stated": "0.01-0.1 Hz",
            "filter_type": "",
            "order": "",
            "quote": "Synthetic sentence four.",
            "notes": "",
        }
    ],
}


def _workbooks(tmp: Path) -> tuple[Path, Path]:
    m = openpyxl.Workbook()
    ws = m.active
    ws.title = "Labels"
    ws.append(MOTION_HEAD)
    ws.append(["existing_2000", "described_only"] + [None] * (len(MOTION_HEAD) - 2))
    mp = tmp / "motion.xlsx"
    m.save(mp)
    s = openpyxl.Workbook()
    s.active.title = "README"
    for name, head in (("Smoothing", SMOOTHING_HEAD), ("Filtering", FILTERING_HEAD)):
        w = s.create_sheet(name)
        w.append(head)
        w.append(["existing_2000", "all", "not_reported"] + [None] * (len(head) - 4) + ["x"])
    sp = tmp / "sf.xlsx"
    s.save(sp)
    return mp, sp


def _export(folder: Path, doc: dict) -> Path:
    folder.mkdir(exist_ok=True)
    p = folder / f"{doc['paper_id']}.labels.json"
    p.write_text(json.dumps(doc))
    return p


def _rows(path: Path, sheet: str) -> list[dict]:
    ws = openpyxl.load_workbook(path)[sheet]
    head = [c.value for c in ws[1]]
    return [dict(zip(head, r, strict=False)) for r in ws.iter_rows(min_row=2, values_only=True)]


def _run(tmp: Path, *extra: str) -> tuple[int, Path, Path]:
    mp, sp = tmp / "motion.xlsx", tmp / "sf.xlsx"
    code = ml.main(
        [str(tmp / "in"), "--motion-workbook", str(mp), "--sf-workbook", str(sp), *extra]
    )
    return code, mp, sp


def test_appends_new_rows_with_author_adjudication(tmp_path, capsys):
    _workbooks(tmp_path)
    _export(tmp_path / "in", SYNTHETIC)
    code, mp, sp = _run(tmp_path, "--date", "2099-01-02")
    assert code == 0
    labels = _rows(mp, "Labels")
    assert [r["paper_id"] for r in labels] == ["existing_2000", "synthetic_2099"]
    new = labels[1]
    assert new["method_state"] == "named_tool"
    assert new["method_value"] == "ToolX"
    assert new["method_quote"] == "Synthetic sentence one."
    assert new["attribution"] == "step"
    assert new["notes"] == "synthetic note"
    assert new["adjudication"] == "author alone, 2099-01-02"
    assert labels[0]["adjudication"] is None  # the added column leaves existing rows blank
    assert all(new[c] is None for c in MOTION_HEAD[4:16])  # bullets 2-7 untouched
    smooth = _rows(sp, "Smoothing")[1:]
    assert [(r["applies_to"], r["state"], r["width"]) for r in smooth] == [
        ("all", "reported", 6),
        ("stream B", "partially_reported", "2.5 mm"),
    ]
    assert smooth[1]["kernel"] is None
    assert {r["adjudication"] for r in smooth} == {"author alone, 2099-01-02"}
    filt = _rows(sp, "Filtering")[1:]
    assert [(r["band_or_cutoff_as_stated"], r["adjudication"]) for r in filt] == [
        ("0.01-0.1 Hz", "author alone, 2099-01-02")
    ]
    out = capsys.readouterr().out
    assert "1 papers appended, 0 refused" in out
    assert "Labels 1, Smoothing 2, Filtering 1" in out


def test_rater_name(tmp_path):
    _workbooks(tmp_path)
    _export(tmp_path / "in", SYNTHETIC)
    code, mp, sp = _run(tmp_path, "--rater", "Rater Two", "--date", "2099-01-03")
    assert code == 0
    assert _rows(mp, "Labels")[1]["adjudication"] == "Rater Two, 2099-01-03"
    assert _rows(sp, "Filtering")[1]["adjudication"] == "Rater Two, 2099-01-03"


def test_refuses_an_existing_paper_id_and_writes_nothing_for_it(tmp_path, capsys):
    mp, sp = _workbooks(tmp_path)
    before = (mp.read_bytes(), sp.read_bytes())
    _export(tmp_path / "in", {**SYNTHETIC, "paper_id": "existing_2000"})
    code, _, _ = _run(tmp_path)
    assert code == 1
    out = capsys.readouterr().out
    assert "refused existing_2000" in out
    assert "already exists in Labels, Smoothing, Filtering" in out
    assert "0 papers appended, 1 refused" in out
    assert (mp.read_bytes(), sp.read_bytes()) == before


def test_refusal_is_per_paper_and_the_rest_is_written(tmp_path, capsys):
    _workbooks(tmp_path)
    _export(tmp_path / "in", SYNTHETIC)
    _export(tmp_path / "in", {**SYNTHETIC, "paper_id": "existing_2000", "motion": {}})
    code, mp, sp = _run(tmp_path)
    assert code == 1
    assert [r["paper_id"] for r in _rows(sp, "Smoothing")].count("existing_2000") == 1
    assert [r["paper_id"] for r in _rows(mp, "Labels")] == ["existing_2000", "synthetic_2099"]
    assert "already exists in Smoothing, Filtering" in capsys.readouterr().out


def test_a_second_merge_of_the_same_folder_refuses_everything(tmp_path):
    _workbooks(tmp_path)
    _export(tmp_path / "in", SYNTHETIC)
    assert _run(tmp_path)[0] == 0
    code, mp, sp = _run(tmp_path)
    assert code == 1
    assert [r["paper_id"] for r in _rows(mp, "Labels")] == ["existing_2000", "synthetic_2099"]
    assert len(_rows(sp, "Smoothing")) == 3


def test_dry_run_writes_nothing(tmp_path, capsys):
    mp, sp = _workbooks(tmp_path)
    before = (mp.read_bytes(), sp.read_bytes())
    _export(tmp_path / "in", SYNTHETIC)
    assert _run(tmp_path, "--dry-run")[0] == 0
    assert (mp.read_bytes(), sp.read_bytes()) == before
    assert "would append: Labels 1, Smoothing 2, Filtering 1" in capsys.readouterr().out


def test_empty_cards_are_skipped(tmp_path, capsys):
    _workbooks(tmp_path)
    doc = {
        **SYNTHETIC,
        "motion": {"state": "", "named_tool": ""},
        "filtering": [{"applies_to": "all"}],
    }
    _export(tmp_path / "in", doc)
    code, mp, sp = _run(tmp_path)
    assert code == 0
    assert len(_rows(mp, "Labels")) == 1
    assert "adjudication" not in [c.value for c in openpyxl.load_workbook(mp)["Labels"][1]]
    assert len(_rows(sp, "Filtering")) == 1
    assert len(_rows(sp, "Smoothing")) == 3
    assert "empty cards skipped: 2" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"schema": "other/1"}, "schema is not"),
        ({"motion": {"state": "named"}}, "not in the workbook vocabulary"),
        ({"motion": {"state": "named_tool", "attribution": "tool"}}, "not step or package"),
        ({"motion": {"named_tool": "ToolX"}}, "motion card is filled but has no state"),
        ({"motion": {"state": "absent", "extra": "x"}}, "unknown fields"),
        ({"smoothing": [{"applies_to": "all", "state": "reported_partly"}]}, "not in the workbook"),
        ({"smoothing": [{"applies_to": "all", "kernel": "Gaussian"}]}, "filled but has no state"),
        ({"smoothing": [{"applies_to": "", "state": "reported"}]}, "empty applies_to"),
        (
            {"filtering": [{"applies_to": "all", "state": "reported"}] * 2},
            "applies_to 'all' appears twice",
        ),
    ],
)
def test_invalid_files_are_refused(tmp_path, capsys, change, reason):
    mp, sp = _workbooks(tmp_path)
    before = (mp.read_bytes(), sp.read_bytes())
    _export(tmp_path / "in", {**SYNTHETIC, **change})
    assert _run(tmp_path)[0] == 1
    out = capsys.readouterr().out
    assert "refused synthetic_2099.labels.json" in out and reason in out
    assert (mp.read_bytes(), sp.read_bytes()) == before


def test_file_name_must_match_paper_id(tmp_path, capsys):
    _workbooks(tmp_path)
    (tmp_path / "in").mkdir()
    (tmp_path / "in" / "renamed.labels.json").write_text(json.dumps(SYNTHETIC))
    assert _run(tmp_path)[0] == 1
    assert "does not match paper_id" in capsys.readouterr().out


def test_usage_errors(tmp_path):
    _workbooks(tmp_path)
    assert ml.main([str(tmp_path / "missing")]) == 2
    (tmp_path / "in").mkdir()
    assert _run(tmp_path, "--date", "09/11/2026")[0] == 2


# --- the real workbooks: vocabulary and headers, and an append to a copy -----------------------


def _dv_lists(path: Path, sheet: str) -> dict[str, tuple[str, ...]]:
    ws = openpyxl.load_workbook(path)[sheet]
    return {
        str(dv.sqref).split(":")[0]: tuple(dv.formula1.strip('"').split(","))
        for dv in ws.data_validations.dataValidation
    }


def test_vocabularies_match_the_workbooks():
    motion = _dv_lists(ml.MOTION_XLSX, "Labels")
    assert motion["B2"] == ml.MOTION_STATES
    assert motion["R2"] == ml.ATTRIBUTION
    for sheet in ("Smoothing", "Filtering"):
        assert _dv_lists(ml.SF_XLSX, sheet)["C2"] == ml.SF_STATES


def test_headers_match_the_workbooks():
    ws = openpyxl.load_workbook(ml.MOTION_XLSX)["Labels"]
    head = [c.value for c in ws[1]]
    assert head[: len(MOTION_HEAD)] == MOTION_HEAD
    assert set(ml.MOTION_COLUMNS.values()) <= set(head)
    wb = openpyxl.load_workbook(ml.SF_XLSX)
    assert [c.value for c in wb["Smoothing"][1]] == SMOOTHING_HEAD
    assert [c.value for c in wb["Filtering"][1]] == FILTERING_HEAD
    assert ["paper_id", *ml.SMOOTHING_FIELDS, "adjudication"] == SMOOTHING_HEAD
    assert ["paper_id", *ml.FILTERING_FIELDS, "adjudication"] == FILTERING_HEAD


def test_labeler_vocabularies_match_the_merge_script():
    html = (REPO / "tools" / "labeler" / "labeler.html").read_text()

    def js_list(name: str) -> tuple[str, ...]:
        m = re.search(rf"const {name} = \[([^\]]*)\];", html)
        assert m, name
        return tuple(re.findall(r'"([^"]+)"', m.group(1)))

    assert js_list("MOTION_STATES") == ml.MOTION_STATES
    assert js_list("SF_STATES") == ml.SF_STATES
    assert js_list("ATTRIBUTION") == ml.ATTRIBUTION
    assert f'const SCHEMA = "{ml.SCHEMA}";' in html
    for key, fields in (("smoothing", ml.SMOOTHING_FIELDS), ("filtering", ml.FILTERING_FIELDS)):
        block = re.search(rf"{key}: \{{.*?fields: \[(.*?)\] \}}", html, re.S)
        assert block, key
        assert tuple(re.findall(r'\["(\w+)"', block.group(1))) == fields
    block = re.search(r"motion: \{.*?fields: \[(.*?)\] \}", html, re.S)
    assert block
    assert tuple(re.findall(r'\["(\w+)"', block.group(1))) == ml.MOTION_FIELDS


def _cells(path: Path) -> dict:
    wb = openpyxl.load_workbook(path)
    return {
        (ws.title, c.coordinate): c.value
        for ws in wb.worksheets
        for row in ws.iter_rows()
        for c in row
    }


def test_append_to_copies_of_the_real_workbooks_keeps_every_existing_cell(tmp_path):
    mp, sp = tmp_path / "motion.xlsx", tmp_path / "sf.xlsx"
    shutil.copy(ml.MOTION_XLSX, mp)
    shutil.copy(ml.SF_XLSX, sp)
    before_m, before_s = _cells(mp), _cells(sp)
    dv_before = {s: _dv_lists(sp, s) for s in ("Smoothing", "Filtering")}
    _export(tmp_path / "in", SYNTHETIC)
    assert _run(tmp_path, "--date", "2099-01-02")[0] == 0
    after_m, after_s = _cells(mp), _cells(sp)
    assert {k: after_m[k] for k in before_m} == before_m
    assert {k: after_s[k] for k in before_s} == before_s
    assert {s: _dv_lists(sp, s) for s in ("Smoothing", "Filtering")} == dv_before
    assert sorted(set(after_s) - set(before_s))[0][0] in ("Smoothing", "Filtering")
    assert sum(r["paper_id"] == "synthetic_2099" for r in _rows(mp, "Labels")) == 1
    assert sum(r["paper_id"] == "synthetic_2099" for r in _rows(sp, "Smoothing")) == 2

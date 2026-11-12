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
sys.path.insert(0, str(REPO / "scripts"))
import make_preproc_rows_workbook as builder  # noqa: E402

#: The label workbooks are untracked from 2026-11-11 (the author's ruling: they hold held-out prose).
#: A check that reads the real ones runs where they exist (the author's machine) and says why it
#: skipped elsewhere (CI). Every merge test builds its own workbooks, so none of them skips.
_REAL = (ml.MOTION_XLSX, ml.SF_XLSX)
needs_real_workbooks = pytest.mark.skipif(
    not all(p.exists() for p in _REAL),
    reason="the label workbooks are untracked (2026-11-11); this check runs where they exist",
)

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
    # 2026-11-11: the remaining-rows workbook and its progress file, copies of the real (empty) ones
    builder.build_workbook(tmp / "rows.xlsx")
    shutil.copy(ml.PROGRESS_CSV, tmp / "progress.csv")
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
    if not (tmp / "rows.xlsx").exists():
        builder.build_workbook(tmp / "rows.xlsx")
        shutil.copy(ml.PROGRESS_CSV, tmp / "progress.csv")
    code = ml.main(
        [
            str(tmp / "in"),
            "--motion-workbook",
            str(mp),
            "--sf-workbook",
            str(sp),
            "--rows-workbook",
            str(tmp / "rows.xlsx"),
            "--progress",
            str(tmp / "progress.csv"),
            "--heldout-sidecar",
            str(tmp / "heldout.local.jsonl"),
            *extra,
        ]
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


@needs_real_workbooks
def test_vocabularies_match_the_workbooks():
    motion = _dv_lists(ml.MOTION_XLSX, "Labels")
    assert motion["B2"] == ml.MOTION_STATES
    assert motion["R2"] == ml.ATTRIBUTION
    for sheet in ("Smoothing", "Filtering"):
        assert _dv_lists(ml.SF_XLSX, sheet)["C2"] == ml.SF_STATES


@needs_real_workbooks
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


@needs_real_workbooks
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


# --- the remaining COBIDAS rows (2026-11-11) ----------------------------------------------------

ROW_KINDS = (
    "slice_time_correction",
    "nuisance_regression",
    "compcor",
    "ica_denoise",
    "scrub",
    "despike",
    "nonsteadystate_removal",
    "coregistration",
    "distortion_correction",
    "brain_extraction",
    "segmentation",
    "intensity_correction",
)


def _row(**kw: str) -> dict:
    return {
        "applies_to": "all",
        "state": "reported",
        "quote": "Synthetic sentence.",
        "notes": "",
        **kw,
    }


ROWS_DOC = {
    "schema": "aespa-labels/1",
    "paper_id": "rows_2099",
    "exported_at": "2099-01-01T00:00:00.000Z",
    "scrub": [
        _row(
            applies_to="task runs",
            method="",
            criterion="FD",
            threshold="0.5 mm",
            remediation="",
            interpolation_method="",
        ),
        _row(
            applies_to="rest runs",
            state="stated_not_performed",
            method="",
            criterion="",
            threshold="",
            remediation="",
            interpolation_method="",
        ),
    ],
    "compcor": [_row(variant="aCompCor", n_components="5", variance_threshold="", mask_source="")],
    "despike": [_row(state="", method="", threshold="", quote="")],  # an empty card, skipped
}


def _source_order() -> dict[str, tuple[str, ...]]:
    """Each step's *_FIELD_META keys in source order, read when this module is collected: a test
    elsewhere monkeypatches an entry out and back in, which keeps the keys but moves that one to
    the end of the dict for every later test."""
    from fmri_repro.spec import preprocessing as spec

    return {k: tuple(getattr(spec, f"{k.upper()}_FIELD_META")) for k in ROW_KINDS}


_FIELD_META_ORDER = _source_order()


def test_the_row_sheets_are_the_schemas_steps_without_performed() -> None:
    assert tuple(ml.ROW_STEP_FIELDS) == ROW_KINDS
    for kind, fields in ml.ROW_STEP_FIELDS.items():
        meta = _FIELD_META_ORDER[kind]
        assert meta[0] == "performed"
        assert fields == tuple(k for k in meta if k != "performed"), kind
        assert ml.ROW_SHEETS[kind] == ("applies_to", "state", *fields, "quote", "notes")
    assert ml.ROW_STATES == ml.SF_STATES


def test_the_rows_workbook_matches_the_merge_script(tmp_path) -> None:
    """The builder's output (CI) and, where it exists, the author's workbook (README and headers)."""
    built = tmp_path / "rows.xlsx"
    builder.build_workbook(built)
    for path in [built] + ([ml.ROWS_XLSX] if ml.ROWS_XLSX.exists() else []):
        _check_rows_workbook(path)


def _check_rows_workbook(path: Path) -> None:
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["README", *ml.ROW_SHEETS]
    for kind in ml.ROW_SHEETS:
        assert [c.value for c in wb[kind][1]] == ["paper_id", *ml.ROW_SHEETS[kind], "adjudication"]
        assert _dv_lists(path, kind)["C2"] == ml.ROW_STATES
    readme = " ".join(str(c.value) for row in wb["README"].iter_rows() for c in row if c.value)
    for text in (*ml.ROW_STATES, *ml.ROW_RULINGS, *builder.LABEL_SHEET_NOTES.values()):
        assert text in readme


def test_the_labeler_cards_and_rulings_match_the_merge_script() -> None:
    html = (REPO / "tools" / "labeler" / "labeler.html").read_text()
    m = re.search(r"const ROW_STATES = \[([^\]]*)\];", html)
    assert m and tuple(re.findall(r'"([^"]+)"', m.group(1))) == ml.ROW_STATES
    cards = dict(re.findall(r"^  (\w+): \{ title: .*?step: \[(.*?)\] \},$", html, re.M))
    assert tuple(cards) == tuple(ml.ROW_SHEETS)
    fields = {**ml.ROW_STEP_FIELDS, **ml.ROW_LABEL_FIELDS}
    for kind, step in cards.items():
        assert tuple(re.findall(r'"(\w+)"', step)) == fields[kind], kind
    # the card keyed by something other than applies_to says so, and adds a package, not a stream
    keyed = re.findall(r'^  (\w+): \{ title: .*?key: "(\w+)", add: "([^"]+)"', html, re.M)
    assert {k: v for k, v, _ in keyed} == ml.ROW_KEY
    assert [a for _, _, a in keyed] == ["add package"]
    rulings = re.search(r'<ol id="row-rulings">(.*?)</ol>', html, re.S)
    assert rulings
    items = [" ".join(i.split()) for i in re.findall(r"<li>(.*?)</li>", rulings.group(1), re.S)]
    assert items == list(ml.ROW_RULINGS)


def test_the_walk_list_is_the_19_corpus_papers_and_progress_starts_with_them() -> None:
    import csv

    walk = [r["paper_id"] for r in csv.DictReader(ml.WALK_CSV.open())]
    assert len(walk) == 19 and walk == sorted(walk) and {"liu_2005", "tang_2025"} <= set(walk)
    if ml.SF_XLSX.exists():  # untracked from 2026-11-11: compared where it exists
        sf_ids = {r["paper_id"] for r in _rows(ml.SF_XLSX, "Smoothing") if r["paper_id"]}
        assert walk == sorted(sf_ids)
    progress = ml.read_progress(ml.PROGRESS_CSV)
    assert [r["paper_id"] for r in progress] == walk
    assert list(progress[0]) == list(ml.PROGRESS_HEAD)


def test_appends_row_sheets_and_updates_progress(tmp_path, capsys) -> None:
    _workbooks(tmp_path)
    m_before, s_before = (
        (tmp_path / "motion.xlsx").read_bytes(),
        (tmp_path / "sf.xlsx").read_bytes(),
    )
    _export(tmp_path / "in", ROWS_DOC)
    code, _, _ = _run(tmp_path, "--date", "2099-01-02")
    assert code == 0
    rows = tmp_path / "rows.xlsx"
    scrub = _rows(rows, "scrub")
    assert [(r["applies_to"], r["state"], r["threshold"]) for r in scrub] == [
        ("task runs", "reported", "0.5 mm"),  # as stated: the unit stays, nothing is converted
        ("rest runs", "stated_not_performed", None),
    ]
    assert {r["adjudication"] for r in scrub} == {"author alone, 2099-01-02"}
    assert _rows(rows, "compcor")[0]["n_components"] == "5"  # text, never coerced
    assert _rows(rows, "despike") == []
    # the motion and smoothing/filtering workbooks are not rewritten
    assert (tmp_path / "motion.xlsx").read_bytes() == m_before
    assert (tmp_path / "sf.xlsx").read_bytes() == s_before
    progress = {r["paper_id"]: r for r in ml.read_progress(tmp_path / "progress.csv")}
    assert progress["rows_2099"]["scrub"] == "2" and progress["rows_2099"]["compcor"] == "1"
    assert progress["rows_2099"]["despike"] == ""
    assert progress["rows_2099"]["last_merged"] == "author alone, 2099-01-02"
    assert len(progress) == 20  # the 19 on the walk list, untouched, and this one appended
    assert all(
        not any(v for k, v in r.items() if k != "paper_id")
        for p, r in progress.items()
        if p != "rows_2099"
    )
    assert "compcor 1, scrub 2" in capsys.readouterr().out


def test_a_paper_on_the_walk_list_gets_its_own_progress_row_filled(tmp_path) -> None:
    _workbooks(tmp_path)
    _export(tmp_path / "in", {**ROWS_DOC, "paper_id": "chen_2015"})
    assert _run(tmp_path)[0] == 0
    progress = ml.read_progress(tmp_path / "progress.csv")
    assert len(progress) == 19
    assert next(r for r in progress if r["paper_id"] == "chen_2015")["scrub"] == "2"


def test_an_existing_row_paper_is_refused_and_progress_is_not_touched(tmp_path, capsys) -> None:
    _workbooks(tmp_path)
    _export(tmp_path / "in", ROWS_DOC)
    assert _run(tmp_path)[0] == 0
    before = (tmp_path / "progress.csv").read_text()
    rows_before = (tmp_path / "rows.xlsx").read_bytes()
    assert _run(tmp_path)[0] == 1
    assert "refused rows_2099: a row for this paper_id already exists in compcor, scrub" in (
        capsys.readouterr().out
    )
    assert (tmp_path / "progress.csv").read_text() == before
    assert (tmp_path / "rows.xlsx").read_bytes() == rows_before


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda d: d["scrub"][0].update(state="named_tool"), "not in the workbook vocabulary"),
        (lambda d: d["compcor"][0].update(performed="yes"), "unknown fields"),
        (lambda d: d["scrub"][1].update(applies_to="task runs"), "appears twice"),
        (lambda d: d["compcor"][0].update(state=""), "filled but has no state"),
    ],
)
def test_invalid_row_cards_are_refused(tmp_path, capsys, change, reason) -> None:
    import copy as _copy

    _workbooks(tmp_path)
    doc = _copy.deepcopy(ROWS_DOC)
    change(doc)
    _export(tmp_path / "in", doc)
    assert _run(tmp_path)[0] == 1
    assert reason in capsys.readouterr().out
    assert all(_rows(tmp_path / "rows.xlsx", k) == [] for k in ROW_KINDS)


def test_a_dry_run_writes_neither_the_rows_workbook_nor_progress(tmp_path) -> None:
    _workbooks(tmp_path)
    before = (tmp_path / "progress.csv").read_text(), (tmp_path / "rows.xlsx").read_bytes()
    _export(tmp_path / "in", ROWS_DOC)
    assert _run(tmp_path, "--dry-run")[0] == 0
    assert (
        (tmp_path / "progress.csv").read_text(),
        (tmp_path / "rows.xlsx").read_bytes(),
    ) == before


def test_a_motion_and_smoothing_export_leaves_the_rows_workbook_alone(tmp_path) -> None:
    _workbooks(tmp_path)
    before = (tmp_path / "progress.csv").read_text(), (tmp_path / "rows.xlsx").read_bytes()
    _export(tmp_path / "in", SYNTHETIC)
    assert _run(tmp_path)[0] == 0
    assert (
        (tmp_path / "progress.csv").read_text(),
        (tmp_path / "rows.xlsx").read_bytes(),
    ) == before


# --- held-out prose never goes into a workbook (2026-11-11) --------------------------------------


def test_a_held_out_papers_prose_goes_to_the_sidecar_and_never_into_a_workbook(tmp_path, capsys):
    _workbooks(tmp_path)
    doc = json.loads(json.dumps(SYNTHETIC))
    doc["paper_id"] = "tang_2025"
    doc["scrub"] = [ROWS_DOC["scrub"][0]]
    _export(tmp_path / "in", doc)
    assert _run(tmp_path, "--date", "2099-01-02")[0] == 0
    motion = next(
        r for r in _rows(tmp_path / "motion.xlsx", "Labels") if r["paper_id"] == "tang_2025"
    )
    assert motion["method_quote"] == ml.REDACTED and motion["notes"] == ml.REDACTED
    assert motion["method_state"] == "named_tool" and motion["method_value"] == "ToolX"
    smoothing = [
        r for r in _rows(tmp_path / "sf.xlsx", "Smoothing") if r["paper_id"] == "tang_2025"
    ]
    assert [r["quote"] for r in smoothing] == [ml.REDACTED, ml.REDACTED]
    assert [r["width"] for r in smoothing] == [6, "2.5 mm"]  # the values are the label: kept
    assert smoothing[0]["notes"] is None  # nothing to withhold stays empty
    (scrub,) = _rows(tmp_path / "rows.xlsx", "scrub")
    assert scrub["quote"] == ml.REDACTED and scrub["threshold"] == "0.5 mm"
    every_cell = " ".join(
        str(c.value)
        for book in ("motion.xlsx", "sf.xlsx", "rows.xlsx")
        for ws in openpyxl.load_workbook(tmp_path / book).worksheets
        for row in ws.iter_rows()
        for c in row
    )
    for prose in ("Synthetic sentence", "synthetic note"):
        assert prose not in every_cell
    side = [json.loads(ln) for ln in (tmp_path / "heldout.local.jsonl").read_text().splitlines()]
    assert {(d["sheet"], d["column"]) for d in side} == {
        ("Labels", "method_quote"),
        ("Labels", "notes"),
        ("Smoothing", "quote"),
        ("Filtering", "quote"),
        ("scrub", "quote"),
    }
    assert len(side) == 6 and {d["paper_id"] for d in side} == {"tang_2025"}
    assert {d["adjudication"] for d in side} == {"author alone, 2099-01-02"}
    assert "held-out prose cells withheld: 6" in capsys.readouterr().out


def test_a_paper_not_held_out_keeps_its_prose_and_writes_no_sidecar(tmp_path):
    _workbooks(tmp_path)
    _export(tmp_path / "in", SYNTHETIC)
    assert _run(tmp_path)[0] == 0
    motion = next(
        r for r in _rows(tmp_path / "motion.xlsx", "Labels") if r["paper_id"] == "synthetic_2099"
    )
    assert motion["method_quote"] == "Synthetic sentence one."
    assert not (tmp_path / "heldout.local.jsonl").exists()


def test_the_held_out_ids_and_the_sidecar_are_where_the_rest_of_the_repo_expects() -> None:
    assert ml._HELD_OUT == frozenset({"liu_2005", "tang_2025", "wheaton_2004"})
    ignore = (REPO / ".gitignore").read_text().splitlines()
    assert "ground_truth/*.local.jsonl" in ignore
    assert "ground_truth/*.xlsx" in ignore


def test_the_redaction_fails_closed_on_a_column_it_does_not_know() -> None:
    """Stage 2b item 5 (2026-11-11): a prose column added later is withheld without being listed."""
    sink: list[dict] = []
    row = {
        "applies_to": "all",
        "state": "reported",
        "threshold": "0.5 mm",
        "quote": "Q.",
        "a_new_comment_column": "prose",
        "empty_new_column": None,
    }
    out = ml._withhold("wheaton_2004", "scrub", row, sink)
    assert out["a_new_comment_column"] == ml.REDACTED and out["quote"] == ml.REDACTED
    assert out["empty_new_column"] is None
    assert (out["applies_to"], out["state"], out["threshold"]) == ("all", "reported", "0.5 mm")
    assert {d["column"] for d in sink} == {"a_new_comment_column", "quote"}
    # every column the merge writes for a label is known, so nothing a label holds is withheld
    for fields in (*ml.ROW_SHEETS.values(), ml.SMOOTHING_FIELDS, ml.FILTERING_FIELDS):
        assert set(fields) - ml.LABEL_COLUMNS <= {"quote", "notes"}
    assert set(ml.MOTION_COLUMNS.values()) - ml.LABEL_COLUMNS == {"method_quote", "notes"}
    # positive control: a paper not held out keeps everything
    assert ml._withhold("chen_2015", "scrub", row, []) == row


# --- the four rows added on 2026-11-11 (second set) ----------------------------------------------

SOFTWARE_DOC = {
    "schema": "aespa-labels/1",
    "paper_id": "sw_2099",
    "exported_at": "2099-01-01T00:00:00.000Z",
    "software": [
        {
            "name": "ToolA",
            "state": "reported",
            "version_as_stated": "v1.2.3",
            "used_for": "synthetic use",
            "quote": "Synthetic sentence.",
            "notes": "",
        },
        {
            "name": "ToolB",
            "state": "partially_reported",
            "version_as_stated": "",
            "used_for": "",
            "quote": "Synthetic sentence.",
            "notes": "",
        },
    ],
    "resting_state_feature": [
        {
            "applies_to": "ALFF",
            "state": "reported",
            "measure": "ALFF",
            "band_hz": "0.01-0.08 Hz",
            "reho_neighbourhood": "",
            "reho_measure": "",
            "quote": "Synthetic sentence.",
            "notes": "",
        }
    ],
    "intersubject_registration": [
        _row(
            method="nonlinear",
            volume_or_surface="volume",
            template="TemplateX",
            resolution="2 mm",
            warp_type="",
            interpolation="",
            cost_function="",
        )
    ],
    "gradient_distortion_correction": [_row(state="not_reported", method="", tool="", quote="")],
}


def test_the_four_rows_sheets_and_the_software_key() -> None:
    assert tuple(ml.ROW_SHEETS)[len(ROW_KINDS) :] == tuple(ml.ROW_LABEL_FIELDS)
    assert ml.ROW_SHEETS["software"] == (
        "name",
        "state",
        "version_as_stated",
        "used_for",
        "quote",
        "notes",
    )
    for sheet in ml.ROW_LABEL_FIELDS:
        if sheet != "software":
            assert ml.ROW_SHEETS[sheet][0] == "applies_to"
    assert ml.PROGRESS_HEAD == ("paper_id", *ml.ROW_SHEETS, "last_merged")
    # every value column is a label column, so only quote and notes are withheld for a held-out paper
    for sheet in ml.ROW_LABEL_FIELDS:
        assert set(ml.ROW_SHEETS[sheet]) - ml.LABEL_COLUMNS == {"quote", "notes"}


def test_software_rows_are_one_per_package_keyed_by_name(tmp_path) -> None:
    _workbooks(tmp_path)
    _export(tmp_path / "in", SOFTWARE_DOC)
    assert _run(tmp_path, "--date", "2099-01-02")[0] == 0
    rows = tmp_path / "rows.xlsx"
    sw = _rows(rows, "software")
    assert [(r["name"], r["state"], r["version_as_stated"]) for r in sw] == [
        ("ToolA", "reported", "v1.2.3"),  # as stated, the "v" kept
        ("ToolB", "partially_reported", None),
    ]
    assert _rows(rows, "resting_state_feature")[0]["band_hz"] == "0.01-0.08 Hz"
    assert _rows(rows, "intersubject_registration")[0]["resolution"] == "2 mm"
    assert _rows(rows, "gradient_distortion_correction")[0]["state"] == "not_reported"
    progress = {r["paper_id"]: r for r in ml.read_progress(tmp_path / "progress.csv")}
    assert progress["sw_2099"]["software"] == "2"


def _sw_doc(rows: list[dict]) -> dict:
    return {
        **SOFTWARE_DOC,
        "software": rows,
        "resting_state_feature": [],
        "intersubject_registration": [],
        "gradient_distortion_correction": [],
    }


def test_a_paper_naming_no_software_is_one_not_reported_row_without_a_name(tmp_path) -> None:
    _workbooks(tmp_path)
    none = {
        "name": "",
        "state": "not_reported",
        "version_as_stated": "",
        "used_for": "",
        "quote": "",
        "notes": "",
    }
    _export(tmp_path / "in", _sw_doc([none]))
    assert _run(tmp_path)[0] == 0
    assert [(r["name"], r["state"]) for r in _rows(tmp_path / "rows.xlsx", "software")] == [
        (None, "not_reported")
    ]


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda r: r[0].update(name=""), "has an empty name"),
        (lambda r: r[1].update(name="ToolA"), "name 'ToolA' appears twice"),
        (lambda r: r[0].update(applies_to="all"), "unknown fields"),
    ],
)
def test_invalid_software_rows_are_refused(tmp_path, capsys, change, reason) -> None:
    import copy as _copy

    _workbooks(tmp_path)
    rows = _copy.deepcopy(SOFTWARE_DOC["software"])
    change(rows)
    _export(tmp_path / "in", _sw_doc(rows))
    assert _run(tmp_path)[0] == 1
    assert reason in capsys.readouterr().out
    assert _rows(tmp_path / "rows.xlsx", "software") == []


def _old_twelve_sheet_workbook(path: Path) -> None:
    builder.build_workbook(path)
    wb = openpyxl.load_workbook(path)
    for sheet in ml.ROW_LABEL_FIELDS:
        del wb[sheet]
    wb.save(path)


def test_a_workbook_without_the_new_sheets_refuses_the_paper_and_names_the_fix(
    tmp_path, capsys
) -> None:
    _workbooks(tmp_path)
    _old_twelve_sheet_workbook(tmp_path / "rows_old.xlsx")
    shutil.move(tmp_path / "rows_old.xlsx", tmp_path / "rows.xlsx")
    _export(tmp_path / "in", SOFTWARE_DOC)
    _export(tmp_path / "in", ROWS_DOC)  # control: a paper on the old sheets is still merged
    assert _run(tmp_path)[0] == 1
    out = capsys.readouterr().out
    assert "refused sw_2099: the rows workbook has no sheet" in out and "--add-sheets" in out
    assert len(_rows(tmp_path / "rows.xlsx", "scrub")) == 2


def test_add_sheets_adds_the_four_keeps_every_existing_cell_and_is_idempotent(tmp_path) -> None:
    path = tmp_path / "rows.xlsx"
    _old_twelve_sheet_workbook(path)
    wb = openpyxl.load_workbook(path)
    wb["scrub"].append(["kept_2099", "all", "reported", "m", "c", "0.5 mm", "r", "", "q", "n", "a"])
    wb.save(path)
    before = {
        n: [[c.value for c in r] for r in openpyxl.load_workbook(path)[n].iter_rows()]
        for n in ["README", *ROW_KINDS]
    }
    assert builder.add_sheets(path) == list(ml.ROW_LABEL_FIELDS)
    after = openpyxl.load_workbook(path)
    for n, rows in before.items():
        got = [[c.value for c in r] for r in after[n].iter_rows()]
        assert got[: len(rows)] == rows, n
        assert n == "README" or len(got) == len(rows), n
    _check_rows_workbook(path)
    assert builder.add_sheets(path) == []  # a second run adds nothing


def test_add_sheets_refuses_a_workbook_whose_headers_differ(tmp_path) -> None:
    path = tmp_path / "rows.xlsx"
    _old_twelve_sheet_workbook(path)
    wb = openpyxl.load_workbook(path)
    wb["scrub"].cell(row=1, column=4, value="renamed")
    wb.save(path)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="sheet scrub has another header"):
        builder.add_sheets(path)
    assert path.read_bytes() == before


def test_widening_the_progress_file_keeps_its_rows_and_counts(tmp_path) -> None:
    import csv

    path = tmp_path / "progress.csv"
    old_head = [c for c in ml.PROGRESS_HEAD if c not in ml.ROW_LABEL_FIELDS]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=old_head, lineterminator="\n")
        w.writeheader()
        w.writerow(
            {
                **dict.fromkeys(old_head, ""),
                "paper_id": "a_2099",
                "scrub": "2",
                "last_merged": "author alone, 2099-01-01",
            }
        )
    assert builder.widen_progress(path) == list(ml.ROW_LABEL_FIELDS)
    (row,) = ml.read_progress(path)
    assert list(row) == list(ml.PROGRESS_HEAD)
    assert (row["scrub"], row["software"], row["last_merged"]) == (
        "2",
        "",
        "author alone, 2099-01-01",
    )
    assert builder.widen_progress(path) == []


def test_a_held_out_papers_software_prose_is_withheld_and_its_label_kept(tmp_path) -> None:
    _workbooks(tmp_path)
    _export(tmp_path / "in", {**SOFTWARE_DOC, "paper_id": "tang_2025"})
    assert _run(tmp_path)[0] == 0
    (a, b) = _rows(tmp_path / "rows.xlsx", "software")
    assert (a["name"], a["version_as_stated"], a["used_for"]) == (
        "ToolA",
        "v1.2.3",
        "synthetic use",
    )
    assert a["quote"] == ml.REDACTED and b["quote"] == ml.REDACTED
    side = [json.loads(x) for x in (tmp_path / "heldout.local.jsonl").read_text().splitlines()]
    assert {(d["sheet"], d["applies_to"]) for d in side if d["sheet"] == "software"} == {
        ("software", "ToolA"),
        ("software", "ToolB"),
    }

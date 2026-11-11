"""fill_motion_resolved and score_motion_resolved (2026-11-09) on a synthetic workbook and records."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import openpyxl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "extractor_mvp" / "scripts"))

import fill_motion_resolved as fill
import score_motion_resolved as smr

HEAD = ["paper_id", "method_state", "method_value", "method_quote", "notes", "attribution"]


def _workbook(tmp_path: Path, rows: list[list[Any]]) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Labels"
    ws.append(HEAD)
    for r in rows:
        ws.append(r)
    ws.append(["A note row, not a paper", None, None, None, None, None])
    p = tmp_path / "labels.xlsx"
    wb.save(p)
    return p


@pytest.mark.parametrize(
    ("state", "value", "expected"),
    [
        ("named_tool", "MCFLIRT", ("fsl MCFLIRT", "program_named")),
        ("named_tool", "SPM12", ("spm Realign", "package_named")),
        ("named_tool", "AFNI", ("afni 3dvolreg", "package_named")),
        ("named_tool", "an in-house tool", None),
        ("described_only", "SPM12", None),
        ("deferred", None, None),
    ],
)
def test_resolve_label(state: str, value: str | None, expected: tuple[str, str] | None) -> None:
    assert fill.resolve_label(state, value) == expected


def test_fill_writes_only_named_tool_rows_and_never_overwrites(tmp_path: Path, capsys: Any) -> None:
    p = _workbook(
        tmp_path,
        [
            ["synth_a", "named_tool", "MCFLIRT", "q", None, "step"],
            ["synth_b", "described_only", None, "q", None, None],
            ["synth_c", "named_tool", "SPM8", "q", None, "package"],
        ],
    )
    assert fill.main(["--workbook", str(p)]) == 0
    ws = openpyxl.load_workbook(p)["Labels"]
    head = [c.value for c in ws[1]]
    assert head[-2:] == ["resolved_tool", "resolved_basis"]
    got = {
        r[0]: (r[-2], r[-1])
        for r in ws.iter_rows(min_row=2, values_only=True)
        if r[0] and " " not in r[0]
    }
    assert got == {
        "synth_a": ("fsl MCFLIRT", "program_named"),
        "synth_b": (None, None),
        "synth_c": ("spm Realign", "package_named"),
    }
    # a value the author set is kept
    wb = openpyxl.load_workbook(p)
    wb["Labels"].cell(row=2, column=len(head) - 1, value="author's own")
    wb.save(p)
    fill.main(["--workbook", str(p)])
    assert "already set, not overwritten 2: synth_a, synth_c" in capsys.readouterr().out
    assert (
        openpyxl.load_workbook(p)["Labels"].cell(row=2, column=len(head) - 1).value
        == "author's own"
    )


def _rec(package: str | None, program: str | None, prov: str, kb: bool = True) -> dict[str, Any]:
    return {
        "resolution": {
            "status": "ok",
            "realignment_tool": {
                "value": package,
                "program": program,
                "provenance": prov,
                "kb": kb,
            },
        }
    }


def test_score_by_paper_and_provenance_group() -> None:
    labels = {
        "p_agree": "fsl MCFLIRT",
        "p_dis": "spm Realign",
        "p_blank": None,
        "p_none": "afni 3dvolreg",
        "p_model": "fsl MCFLIRT",
        "p_missing": "fsl MCFLIRT",
    }
    records = {
        "p_agree": _rec("fsl", "MCFLIRT", "EXTRACTED"),
        "p_dis": _rec("fsl", "FLIRT", "INFERRED_DEFAULT"),
        "p_blank": _rec("afni", "3dvolreg", "INFERRED_DEFAULT"),
        "p_none": _rec(None, None, "UNKNOWN"),
        "p_model": _rec("fsl", "MCFLIRT", "INFERRED_MODEL"),
    }
    rows = {r["paper"]: (r["outcome"], r["group"]) for r in smr.score(labels, records)}
    assert rows == {
        "p_agree": ("agree", "KB-confirmed"),
        "p_dis": ("disagree", "KB-confirmed"),
        "p_blank": ("label blank", "KB-confirmed"),
        "p_none": ("disagree", "unknown"),  # 2026-11-11: UNKNOWN is its own group
        "p_model": ("agree", "model-only"),
        "p_missing": ("no record", ""),
    }
    text = smr.render(smr.score(labels, records), "synthetic")
    assert "| KB-confirmed | 1 | 1 | 1 |" in text and "| model-only | 1 | 0 | 0 |" in text
    assert "| unknown | 0 | 1 | 0 |" in text
    assert "Not scored: no record 1." in text


def test_held_out_papers_show_the_outcome_not_the_tools() -> None:
    rows = smr.score(
        {"liu_2005": "spm Realign"}, {"liu_2005": _rec("spm", "Realign", "INFERRED_DEFAULT")}
    )
    text = smr.render(rows, "synthetic")
    assert "| liu_2005 | agree | KB-confirmed | (held out) | (held out) |" in text
    assert "spm Realign" not in text.split("| paper |", 1)[1].split("| group |", 1)[0]


@pytest.mark.parametrize(
    ("label", "rec", "outcome", "group"),
    [
        # "unknown": agrees only when the record resolves no tool
        ("unknown", (None, None, "UNKNOWN"), "agree", "unknown"),
        ("unknown", ("afni", "3dvolreg", "INFERRED_DEFAULT"), "disagree", "KB-confirmed"),
        # a package alone (the program is unstated): agrees only with that package and no program
        ("afni", ("afni", None, "INFERRED_MODEL"), "agree", "model-only"),
        ("afni", ("afni", "3dvolreg", "INFERRED_DEFAULT"), "disagree", "KB-confirmed"),
        ("afni", ("spm", None, "INFERRED_MODEL"), "disagree", "model-only"),
        ("afni", (None, None, "UNKNOWN"), "disagree", "unknown"),
        # package and program
        (
            "4dfp cross_realign3d_4dfp",
            ("4dfp", "cross_realign3d_4dfp", "INFERRED_DEFAULT"),
            "agree",
            "KB-confirmed",
        ),
        ("fsl FLIRT", ("fsl", None, "INFERRED_MODEL"), "disagree", "model-only"),
    ],
)
def test_the_label_forms(label: str, rec: tuple[Any, Any, str], outcome: str, group: str) -> None:
    rows = smr.score({"p": label}, {"p": _rec(*rec)})
    assert (rows[0]["outcome"], rows[0]["group"]) == (outcome, group)

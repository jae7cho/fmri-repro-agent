"""scripts/score_motion.py (the author's answer of 2026-11-06): the pre-registered state map on a
stored record, the tool comparison, and that a withheld paper's tool never reaches the output.
Offline; records are built in memory."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import score_motion as sm


def _rec(status: str, verbatim: str | None = None, diag: str | None = None) -> dict[str, Any]:
    ext: dict[str, Any] = {"status": status}
    if verbatim is not None:
        ext["value"] = {"verbatim": verbatim, "resolved": None, "resolution": None}
    diags = [{"field": "motion_correction.method", "failure_reason": diag}] if diag else []
    return {
        "preprocessing": {"steps": [{"kind": "motion_correction", "method": {"extraction": ext}}]},
        "diagnostics": diags,
    }


@pytest.mark.parametrize(
    ("record", "state"),
    [
        (_rec("EXTRACTED", "MCFLIRT"), "named_tool"),  # state map row 2
        (_rec("EXTRACTED", "motion correction was performed"), "described_only"),  # row 1
        (_rec("EXTRACTED", "motion correction via ICA-AROMA"), "undecided"),  # row 3
        (_rec("DEFERRED_TO_CITATION"), "deferred"),  # row 4
        (_rec("MISSING_FROM_PAPER"), "absent"),  # row 6
        (
            _rec("MISSING_FROM_PAPER", diag="extraction_quote_unresolved:quote_not_found"),
            "unverifiable",
        ),
        (_rec("INFERRED_FROM_KB"), "other: INFERRED_FROM_KB"),
    ],
)
def test_the_state_map(record: dict[str, Any], state: str) -> None:
    assert sm.record_method(record).state == state


def test_a_record_without_a_motion_step_is_absent() -> None:
    assert sm.record_method({"preprocessing": {"steps": []}}).state == "absent"


def test_a_full_report_record_is_read_through_extraction_json() -> None:
    assert sm.record_method({"extraction_json": _rec("EXTRACTED", "MCFLIRT")}).value == "MCFLIRT"


@pytest.mark.parametrize(
    ("label", "record", "out"),
    [
        ("SPM 12", "SPM12", "agree"),
        ("3dvolreg", "3dVolReg", "agree"),
        ("FSL", "MCFLIRT", "disagree"),
        ("", "MCFLIRT", "not labelled"),
    ],
)
def test_tool_identity(label: str, record: str, out: str) -> None:
    lab = sm.MotionLabel("p", "named_tool", label)
    assert sm.compare_value(lab, sm.MotionRecord("named_tool", record)) == out


def test_a_tool_is_compared_only_when_both_name_one() -> None:
    lab = sm.MotionLabel("p", "named_tool", "MCFLIRT")
    assert sm.compare_value(lab, sm.MotionRecord("deferred", "")) == ""
    assert (
        sm.compare_value(sm.MotionLabel("p", "deferred", ""), sm.MotionRecord("named_tool", "X"))
        == ""
    )


def test_the_report_counts_and_never_prints_a_withheld_tool() -> None:
    labels = [
        sm.MotionLabel("power_2014", "named_tool", "MCFLIRT"),
        sm.MotionLabel("wheaton_2004", "named_tool", "SecretTool"),
        sm.MotionLabel("braun_2015", "deferred", ""),
        sm.MotionLabel("gordon_2014", "named_tool", "SPM"),
    ]
    records = {
        "power_2014": sm.MotionRecord("named_tool", "MCFLIRT"),
        "wheaton_2004": sm.MotionRecord("named_tool", "SecretTool"),
        "braun_2015": sm.MotionRecord("named_tool", "FSL"),
    }
    text = sm.render(sm.score(labels, records), ["r"])
    assert "SecretTool" not in text and "MCFLIRT" not in text and "FSL" not in text
    assert "| wheaton_2004 | named_tool | named_tool | agree | match |" in text
    assert "| power_2014 | named_tool | named_tool | agree | agree |" in text
    assert "| braun_2015 | deferred | named_tool | disagree |  |" in text
    assert "| gordon_2014 | named_tool | no record | | |" in text
    assert "State: 2 agree, 1 disagree, 1 no record." in text


def test_records_come_from_several_directories_once_each(tmp_path: Path) -> None:
    for d, pid in (("a", "p1"), ("b", "p2")):
        (tmp_path / d / "papers").mkdir(parents=True)
        (tmp_path / d / "papers" / f"{pid}.json").write_text(
            json.dumps(_rec("DEFERRED_TO_CITATION"))
        )
    got = sm.load_records(tmp_path / "a", tmp_path / "b")
    assert set(got) == {"p1", "p2"}
    (tmp_path / "b" / "papers" / "p1.json").write_text(json.dumps(_rec("DEFERRED_TO_CITATION")))
    with pytest.raises(SystemExit):
        sm.load_records(tmp_path / "a", tmp_path / "b")

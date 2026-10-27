"""The batch projection emits the motion field's processed layer with no text (Amendment 13).

Synthetic stored results only: an EXTRACTED tool on a span that carries an operation phrase (level
step), a routing-fallback draw (level package by construction), a MISSING field with a reason, and a
paper whose stored result carries no motion step at all (every column empty).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import batch_motion_projection

from extractor_mvp.motion_guard import MOTION_VALUE_ROUTED_FALLBACK


def _doc(
    pid: str,
    *,
    status: str | None,
    verbatim: str = "",
    span_text: str = "",
    reason: str = "",
    diag: str = "",
) -> dict:
    if status is None:
        steps: list[dict] = []
    elif status == "EXTRACTED":
        steps = [
            {
                "kind": "motion_correction",
                "method": {
                    "extraction": {
                        "status": "EXTRACTED",
                        "value": {
                            "verbatim": verbatim,
                            "resolved": None,
                            "resolution": "unrecognized",
                        },
                        "spans": [{"start": 10, "end": 10 + len(span_text), "text": span_text}],
                    },
                    "inference": None,
                },
            }
        ]
    else:
        steps = [
            {
                "kind": "motion_correction",
                "method": {"extraction": {"status": status}, "inference": {"reason": reason}},
            }
        ]
    diags = (
        [
            {
                "field": "motion_correction.method",
                "failure_reason": diag,
                "raw_value": "x",
                "raw_quote": "y",
            }
        ]
        if diag
        else []
    )
    return {
        "paper_id": pid,
        "likely_multi_acquisition": pid == "weber_2024",
        "preprocessing": {"steps": steps},
        "diagnostics": diags,
    }


def test_rows_carry_states_offsets_and_the_derived_level_and_no_text(tmp_path: Path) -> None:
    papers = tmp_path / "run" / "papers"
    papers.mkdir(parents=True)
    docs = [
        _doc(
            "gordon_2014",
            status="EXTRACTED",
            verbatim="SPM8",
            span_text="images were realigned using SPM8",
        ),
        _doc(
            "derosa_2025",
            status="EXTRACTED",
            verbatim="FSL",
            span_text="carried out using FSL, including motion correction via a denoiser",
            diag=f"{MOTION_VALUE_ROUTED_FALLBACK}:ica_aroma->FSL",
        ),
        _doc(
            "mueller_2021", status="MISSING_FROM_PAPER", reason="motion_value_unsupported_by_quote"
        ),
        _doc("weber_2024", status=None),
    ]
    for d in docs:
        (papers / f"{d['paper_id']}.json").write_text(json.dumps(d), encoding="utf-8")
    out = tmp_path / "p.csv"
    assert (
        batch_motion_projection.main(["--results-dir", str(tmp_path / "run"), "--out", str(out)])
        == 0
    )
    text = out.read_text(encoding="utf-8")
    for needle in ("SPM8", "FSL", "realigned", "denoiser"):
        assert needle not in text, needle
    rows = {
        r["paper_id"]: r
        for r in csv.DictReader([line for line in text.splitlines() if not line.startswith("#")])
    }
    assert rows["gordon_2014"]["attribution"] == "step"
    assert rows["gordon_2014"]["heuristic_class"] == "tool_name"
    assert rows["gordon_2014"]["span_start"] == "10"
    assert rows["derosa_2025"]["attribution"] == "package"  # by construction on a fallback draw
    assert rows["derosa_2025"]["diagnostic_base"] == MOTION_VALUE_ROUTED_FALLBACK
    assert rows["mueller_2021"]["motion_status"] == "MISSING_FROM_PAPER"
    assert rows["mueller_2021"]["reason_base"] == "motion_value_unsupported_by_quote"
    assert rows["weber_2024"]["motion_status"] == "" and rows["weber_2024"]["attribution"] == ""
    assert rows["weber_2024"]["likely_multi_acquisition"] == "yes"
    assert [r["class"] for r in rows.values()] == [
        "probe",
        "probe",
        "probe",
        "co-adjudicated, not probed",
    ]


def test_a_paper_outside_the_partition_is_refused(tmp_path: Path) -> None:
    papers = tmp_path / "run" / "papers"
    papers.mkdir(parents=True)
    (papers / "nobody_2000.json").write_text(
        json.dumps(_doc("nobody_2000", status=None)), encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="nobody_2000"):
        batch_motion_projection.main(
            ["--results-dir", str(tmp_path / "run"), "--out", str(tmp_path / "p.csv")]
        )

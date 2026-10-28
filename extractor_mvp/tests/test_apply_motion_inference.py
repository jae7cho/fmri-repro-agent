"""apply_motion_inference.py writes a NEW processed vintage with the record and the clause, and a
projection with the clean three as path-only rows (2026-10-28)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import apply_motion_inference

from test_motion_inference import _method, _prep, _version


def _stored(pid: str, prep) -> dict:
    return {
        "paper_id": pid,
        "path": "x.pdf",
        "status": "success",
        "likely_multi_acquisition": False,
        "preprocessing": prep.model_dump(mode="json"),
        "diagnostics": [],
        "resolutions": [],
        "deferred_fields": [],
    }


def test_the_processed_vintage_carries_the_record_the_clause_and_a_path_only_held_out_row(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src" / "papers"
    src.mkdir(parents=True)
    docs = {
        "vanderwal_2016": _stored(
            "vanderwal_2016",
            _prep(_method("deferred", ref="C-PAC"), "C-PAC", _version("extracted", "1.8.6")),
        ),
        "mueller_2021": _stored("mueller_2021", _prep(_method("described_only"), "SPM12")),
        "ciric_2017": _stored("ciric_2017", _prep(_method("named_tool"), "XCP Engine")),
        "tang_2025": _stored(
            "tang_2025", _prep(_method("described_only"), "SPM12")
        ),  # a synthetic row, not the paper
    }
    for pid, doc in docs.items():
        (src / f"{pid}.json").write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "out"
    proj = tmp_path / "p.csv"
    assert (
        apply_motion_inference.main(
            ["--results-dir", str(tmp_path / "src"), "--out", str(out), "--projection", str(proj)]
        )
        == 0
    )
    v = json.loads((out / "papers" / "vanderwal_2016.json").read_text())
    assert v["motion_inference"]["path"] == "arm" and v["motion_inference"]["program"] == "3dvolreg"
    assert v["processed_vintage"]["model_call"] is False
    step = next(s for s in v["preprocessing"]["steps"] if s["kind"] == "motion_correction")
    assert step["method"]["inference"]["status"] == "INFERRED_DEFAULT"
    assert (
        "AESPA infers 3dvolreg (version_default, "
        in (out / "papers" / "vanderwal_2016.md").read_text()
    )
    m = json.loads((out / "papers" / "mueller_2021.json").read_text())
    assert m["motion_inference"]["path"] == "diagnostic"
    assert "AESPA infers Realign (derived, " in (out / "papers" / "mueller_2021.md").read_text()
    assert (
        json.loads((out / "papers" / "ciric_2017.json").read_text())["motion_inference"]["path"]
        == "never"
    )
    rows = {
        r["paper_id"]: r
        for r in csv.DictReader(
            [line for line in proj.read_text().splitlines() if not line.startswith("#")]
        )
    }
    assert (
        rows["vanderwal_2016"]["basis_type"] == "version_default"
        and rows["vanderwal_2016"]["program"] == "3dvolreg"
    )
    assert rows["tang_2025"]["path"] == "diagnostic"
    assert all(
        rows["tang_2025"][c] == ""
        for c in (
            "basis_name",
            "basis_type",
            "confidence",
            "program",
            "reason_base",
            "n_alternatives",
        )
    )
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["model_call"] is False and manifest["source_vintage"] == "src"


def test_the_output_must_be_a_new_vintage(tmp_path: Path) -> None:
    (tmp_path / "papers").mkdir()
    with pytest.raises(SystemExit, match="NEW vintage"):
        apply_motion_inference.main(
            [
                "--results-dir",
                str(tmp_path),
                "--out",
                str(tmp_path),
                "--projection",
                str(tmp_path / "p.csv"),
            ]
        )

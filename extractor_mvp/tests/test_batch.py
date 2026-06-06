"""End-to-end batch test with load + LLM mocked (no PDF / network)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import extractor_mvp.batch as batch
from extractor_mvp.batch_config import BatchConfig, PdfPaper
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    PreprocessingExtraction,
    extract_preprocessing,
)

FULL_TEXT = "Methods\nData were normalized to MNI152NLin6Asym at 2 mm.\nResults\nFindings."


def _canned_payload() -> PreprocessingExtraction:
    none = FieldExtractionResult(status="missing")
    return PreprocessingExtraction(
        target_space=FieldExtractionResult(
            status="extracted",
            value="MNI152NLin6Asym",
            verbatim_quote="normalized to MNI152NLin6Asym",
        ),
        resolution_mm=FieldExtractionResult(
            status="extracted", value="2", verbatim_quote="at 2 mm"
        ),
        surface_registration=none,
        target_surface=none,
        intensity_convention=none,
        intensity_value=none,
    )


def _patch(monkeypatch: Any) -> None:
    monkeypatch.setattr(batch, "load_pdf_text", lambda _path: (FULL_TEXT, "pypdf"))
    payload = _canned_payload()
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: payload))
    )
    # real extractor, but driven by the canned client (so spans resolve on the real slice)
    monkeypatch.setattr(
        batch,
        "extract_preprocessing",
        lambda paper, model: extract_preprocessing(paper, model, client=fake_client),
    )


def test_run_batch_end_to_end(monkeypatch, tmp_path: Path):
    _patch(monkeypatch)
    config = BatchConfig(
        model="m",
        output_dir=tmp_path / "out",
        papers=[PdfPaper(paper_id="p1", path=tmp_path / "p1.pdf")],
    )
    results = batch.run_batch(config)

    assert len(results) == 1
    r = results[0]
    assert r.status == "success"
    assert r.parser == "pypdf"
    assert r.methods_found_via == "header_match"
    assert r.n_extracted == 2  # target_space + resolution_mm resolved
    assert r.n_missing_not_stated == 4  # the other 4 targeted fields
    assert r.likely_multi_acquisition is False
    assert r.error_message is None

    # summary outputs written
    assert (config.output_dir / "summary.csv").is_file()
    assert (config.output_dir / "summary.md").is_file()
    md = (config.output_dir / "summary.md").read_text()
    assert "p1" in md and "| paper_id |" in md

    # per-paper JSON written, with span translated to full-paper offsets
    paper_json = json.loads((config.output_dir / "papers" / "p1.json").read_text())
    assert paper_json["status"] == "success"
    spans = [
        span
        for step in paper_json["preprocessing"]["steps"]
        for v in step.values()
        if isinstance(v, dict) and isinstance(v.get("extraction"), dict)
        for span in v["extraction"].get("spans", [])
    ]
    assert spans, "expected at least one extracted span"
    for sp in spans:
        assert "span_in_slice" in sp and "span_in_full_paper" in sp


def test_run_batch_pdf_parse_failure(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(batch, "load_pdf_text", lambda _path: ("", "failed"))
    config = BatchConfig(
        model="m",
        output_dir=tmp_path / "out",
        papers=[PdfPaper(paper_id="bad", path=tmp_path / "bad.pdf")],
    )
    results = batch.run_batch(config)
    assert results[0].status == "pdf_parse_failed"
    assert results[0].parser is None
    assert results[0].extraction_json is None

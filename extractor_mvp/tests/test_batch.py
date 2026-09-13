"""End-to-end batch test with load + LLM mocked (no PDF / network)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import extractor_mvp.batch as batch
from extractor_mvp.batch_config import BatchConfig, PdfPaper
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    PreprocessingExtraction,
    extract,
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
    # real orchestrator, but driven by the canned client (so spans resolve on the real slice)
    monkeypatch.setattr(
        batch,
        "extract",
        lambda paper, model, **kwargs: extract(paper, model, client=fake_client),
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
    # 5 targeted fields land MISSING: was 4, +1 for temporal_standardization.method
    # (Build 2 added it as a targeted field; the mock LLM doesn't provide it).
    assert r.n_missing_not_stated == 5
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


def test_run_batch_writes_a_completeness_report_per_paper(monkeypatch, tmp_path: Path):
    """A1: run_batch writes a rendered report alongside papers/{paper_id}.json.

    Pins the two properties that make the report safe rather than merely present: it is a
    SANCTIONED report surface (to_report, so the catalog-driven coverage section is stapled
    on and the D.3 denominator comes from the standard, not the steps present), and its
    per-row wording characterises absence rather than labelling every gap "not reported".
    """
    _patch(monkeypatch)
    config = BatchConfig(
        model="m",
        output_dir=tmp_path / "out",
        papers=[PdfPaper(paper_id="p1", path=tmp_path / "p1.pdf")],
    )
    results = batch.run_batch(config)
    r = results[0]
    assert r.render_error is None

    report_path = config.output_dir / "papers" / "p1.md"
    assert report_path.is_file(), "no report written alongside the per-paper JSON"
    report = report_path.read_text()
    assert report == r.report

    # a REPORT, not a field view: the coverage section and the static 16-row denominator
    assert "COBIDAS D.3 coverage (preprocessing)" in report
    assert "Mandatory rows: 14" in report
    assert "p1" in report  # source is threaded through
    # D: untargeted rows are characterised, never labelled as the author's omission
    assert "not examined by the extractor" in report
    assert ": not reported\n" not in report


def test_render_failure_keeps_the_extraction(monkeypatch, tmp_path: Path):
    """A report failure must not discard a paid-for extraction.

    to_report is pure and well-tested, but it runs inside process_paper (the only place the
    live MethodsSlice exists), which is BEFORE run_batch writes the per-paper JSON. An escaping
    exception would throw away the LLM call. It is recorded and printed instead of swallowed.
    """
    _patch(monkeypatch)

    def _boom(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("render exploded")

    monkeypatch.setattr(batch, "to_report", _boom)
    config = BatchConfig(
        model="m",
        output_dir=tmp_path / "out",
        papers=[PdfPaper(paper_id="p1", path=tmp_path / "p1.pdf")],
    )
    results = batch.run_batch(config)
    r = results[0]

    assert r.status == "success" and r.n_extracted == 2  # extraction preserved
    assert r.report is None
    assert "RuntimeError: render exploded" in (r.render_error or "")
    assert (config.output_dir / "papers" / "p1.json").is_file()  # ...and written
    assert not (config.output_dir / "papers" / "p1.md").exists()  # no half-written report

    # ...and it reaches the DURABLE record, not only stderr: a RENDER-FAIL line printed
    # during a 19-paper run is scrollback, but summary.csv/.md are what gets read after.
    rows = list(csv.DictReader((config.output_dir / "summary.csv").open(encoding="utf-8")))
    assert "RuntimeError: render exploded" in rows[0]["render_error"]
    assert "RuntimeError: render exploded" in (config.output_dir / "summary.md").read_text()


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


def test_run_batch_skips_and_records_excluded(monkeypatch, tmp_path: Path):
    _patch(monkeypatch)
    config = BatchConfig(
        model="m",
        output_dir=tmp_path / "out",
        papers=[
            PdfPaper(paper_id="p1", path=tmp_path / "p1.pdf"),
            PdfPaper(paper_id="cabral_2017", path=tmp_path / "cabral_2017.pdf"),
        ],
    )
    results = batch.run_batch(config)
    # excluded paper is skipped BEFORE extraction: no result, no json emitted
    assert {r.paper_id for r in results} == {"p1"}
    assert not (config.output_dir / "papers" / "cabral_2017.json").exists()
    # summary states the denominator on its face + records the exclusion + rationale
    summary = (config.output_dir / "summary.md").read_text()
    assert "Corpus: 2 PDFs present · 1 excluded · N = 1" in summary
    assert "## Excluded papers" in summary
    assert "cabral_2017" in summary and "Review / modelling paper" in summary


def test_tally_scope_is_step_fields_only() -> None:
    """`_tally` walks preprocessing.steps and excludes base_pipeline — pinned, not incidental.

    The exclusion is a real limitation with a live consequence: n_deferred reads 0 while a
    paper whose base_pipeline is DEFERRED_TO_CITATION plainly defers. Pinning it here means a
    future widening is a deliberate change to this test, not a silent shift in what
    summary.csv means. See the _tally docstring for why widening is not a one-liner.
    """
    from extractor_mvp.batch import _tally
    from extractor_mvp.render import flatten

    prep = _assembled_with_deferred_base()
    counts = _tally(prep)
    assert counts["n_deferred"] == 0, "base_pipeline's deferral must not reach the step tally"

    base = [r for r in flatten(prep) if r.path == "base_pipeline"]
    assert base and base[0].extraction_status == "DEFERRED_TO_CITATION", (
        "fixture must actually defer, or this test pins nothing"
    )


def _assembled_with_deferred_base() -> Any:
    from fmri_repro.spec.preprocessing import Preprocessing
    from fmri_repro.spec.provenance import (
        Deferral,
        DeferredToCitation,
        LeftMissing,
        ProvenancedField,
        Span,
    )
    from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef

    bp = ProvenancedField(
        field_id="base_pipeline",
        extraction=DeferredToCitation(
            deferrals=[
                Deferral(
                    ref="Glasser 2013",
                    span=Span(start=0, end=12, text="as in Glasser"),
                    target_kind="paper",
                )
            ],
            searched_terms=["pipeline"],
            sections_searched=["Methods"],
        ),
        inference=LeftMissing(reason="deferred_to_citation"),
    )
    from tests.test_assemble_v0_3_0 import _assembled

    steps = _assembled().steps
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=bp,
        steps=steps,
    )

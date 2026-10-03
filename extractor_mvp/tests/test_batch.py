"""End-to-end batch test with load + LLM mocked (no PDF / network)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest

if TYPE_CHECKING:
    from extractor_mvp.citation_resolver import CitationResolver

import extractor_mvp.batch as batch
from extractor_mvp.batch_config import BatchConfig, PdfPaper
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    PreprocessingExtraction,
    extract,
)


def test_run_batch_end_to_end(canned_batch: None, tmp_path: Path):
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


def test_run_batch_writes_a_completeness_report_per_paper(canned_batch: None, tmp_path: Path):
    """A1: run_batch writes a rendered report alongside papers/{paper_id}.json.

    Pins the two properties that make the report safe rather than merely present: it is a
    SANCTIONED report surface (to_report, so the catalog-driven coverage section is stapled
    on and the D.3 denominator comes from the standard, not the steps present), and its
    per-row wording characterises absence rather than labelling every gap "not reported".
    """
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


def test_render_failure_keeps_the_extraction(canned_batch: None, monkeypatch, tmp_path: Path):
    """A report failure must not discard a paid-for extraction.

    to_report is pure and well-tested, but it runs inside process_paper (the only place the
    live MethodsSlice exists), which is BEFORE run_batch writes the per-paper JSON. An escaping
    exception would throw away the LLM call. It is recorded and printed instead of swallowed.
    """

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


def test_run_batch_skips_and_records_excluded(canned_batch: None, tmp_path: Path):
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


def test_tally_scope_is_step_fields_only(assembled_with_deferred_base: Any) -> None:
    """`_tally` walks preprocessing.steps and excludes base_pipeline — pinned, not incidental.

    The exclusion is a real limitation with a live consequence: n_deferred reads 0 while a
    paper whose base_pipeline is DEFERRED_TO_CITATION plainly defers. Pinning it here means a
    future widening is a deliberate change to this test, not a silent shift in what
    summary.csv means. See the _tally docstring for why widening is not a one-liner.
    """
    from extractor_mvp.batch import _tally
    from extractor_mvp.render import flatten

    prep = assembled_with_deferred_base
    counts = _tally(prep)
    assert counts["n_deferred"] == 0, "base_pipeline's deferral must not reach the step tally"

    base = [r for r in flatten(prep) if r.path == "base_pipeline"]
    assert base and base[0].extraction_status == "DEFERRED_TO_CITATION", (
        "fixture must actually defer, or this test pins nothing"
    )


@pytest.fixture
def assembled_with_deferred_base(assembled: Any) -> Any:
    from fmri_repro.spec.preprocessing import Preprocessing
    from fmri_repro.spec.provenance import (
        Deferral,
        DeferredToCitation,
        LeftMissing,
        ProvenancedField,
        Span,
    )
    from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef

    bp: Any = ProvenancedField(
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
    steps = assembled.steps
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=bp,
        steps=steps,
    )


# --- the failure-kind split (batch._CODE_DEFECTS) ----------------------------------------------
#
# A batch must absorb DATA failures (one paper's problem) and must NOT absorb CODE defects (every
# paper's problem, identically). Before this split, batch.py:236's `except Exception` recorded both as
# extraction_failed, so a removed field would finish a run green with 19 corrupted rows while blaming
# the corpus. See batch._CODE_DEFECTS for why the fix re-raises defects rather than enumerating the
# data failures.


def test_a_data_failure_is_still_recorded_and_the_batch_continues(
    canned_batch: None, monkeypatch: Any, tmp_path
) -> None:
    """The behaviour the broad catch exists for, pinned so the split does not take it away."""

    def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("bedrock said no")

    monkeypatch.setattr(batch, "extract", boom)
    pdf = tmp_path / "chen_2015.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    result = batch.process_paper("chen_2015", pdf, "model")
    assert result.status == "extraction_failed"
    assert "RuntimeError: bedrock said no" in (result.error_message or "")


@pytest.mark.parametrize(
    "exc", [AttributeError("no attribute 'confidence'"), TypeError("bad signature"), NameError("x")]
)
def test_a_code_defect_aborts_the_run_instead_of_blaming_the_paper(
    canned_batch: None, monkeypatch: Any, tmp_path, exc: BaseException
) -> None:
    """A tool defect must propagate. Recording it as a paper status is wrong twice over: it
    misattributes a tool failure to the paper, and it lets the batch finish green."""

    def boom(*_a: Any, **_k: Any) -> Any:
        raise exc

    monkeypatch.setattr(batch, "extract", boom)
    pdf = tmp_path / "chen_2015.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(type(exc)):
        batch.process_paper("chen_2015", pdf, "model")


def test_the_citation_resolver_attributeerror_propagates_through_the_real_extract_path(
    monkeypatch: Any, tmp_path
) -> None:
    """Closes a test gap: citation_resolver.py:124 reads ``pf.extraction.confidence`` and is
    reachable ONLY by the live test, so the defect that motivated this split had no CI coverage.

    This drives the REAL orchestrator (extractor.py:1190 calls ``resolve_all``) with a stub resolver
    that raises the exact error a removed field produces. The stub stands in for the resolver's
    internals because ``Extracted.confidence`` is a required field and so cannot be removed in a
    fixture; what is under test is the BATCH's handling, which is what the split changed.
    """
    # A DEFERRED step field, so extractor.py:1187-1188's `per_field` is non-empty and resolve_all is
    # actually reached. The deferring sentence must be groundable in the slice, or _process_deferred
    # records deferral_quote_unresolved instead and no DeferralRecord is produced.
    text = "Methods\nData were normalized as described in Smith et al. 2013.\nResults\nFindings."
    monkeypatch.setattr(batch, "load_pdf_text", lambda _path: (text, "pypdf"))
    none = FieldExtractionResult(status="missing")
    payload = PreprocessingExtraction(
        target_space=FieldExtractionResult(
            status="deferred",
            ref_string="Smith et al. 2013",
            deferral_sentence="Data were normalized as described in Smith et al. 2013.",
        ),
        resolution_mm=none,
        surface_registration=none,
        target_surface=none,
        intensity_convention=none,
        intensity_value=none,
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: payload))
    )
    monkeypatch.setattr(
        batch,
        "extract",
        lambda paper, model, **kwargs: extract(
            paper, model, client=fake_client, citation_resolver=kwargs.get("citation_resolver")
        ),
    )

    class BrokenResolver:
        def resolve_all(self, _per_field: Any) -> Any:
            raise AttributeError("'Extracted' object has no attribute 'confidence'")

        def resolve_base_pipeline_deferral(self, *_a: Any, **_k: Any) -> Any:
            raise AssertionError("should not be reached")

    pdf = tmp_path / "chen_2015.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(AttributeError, match="confidence"):
        # cast, not ignore: CitationResolver is a concrete class (citation_resolver.py:61), and the
        # point of the stub is to raise from resolve_all without constructing the real resolver's
        # cache and fetcher. The duck-typed surface used here is resolve_all alone.
        batch.process_paper(
            "chen_2015", pdf, "model", citation_resolver=cast("CitationResolver", BrokenResolver())
        )


def test_a_code_defect_in_to_report_also_propagates(
    canned_batch: None, monkeypatch: Any, tmp_path
) -> None:
    """The same split on the render catch. Sharper there: its own comment argues to_report is pure
    and deterministic, so a code defect in it is identical on every paper by construction."""
    monkeypatch.setattr(
        batch, "to_report", lambda *_a, **_k: (_ for _ in ()).throw(AttributeError("gone"))
    )
    pdf = tmp_path / "chen_2015.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(AttributeError):
        batch.process_paper("chen_2015", pdf, "model")


def test_data_shaped_exceptions_are_deliberately_not_re_raised() -> None:
    """IndexError and KeyError are excluded from _CODE_DEFECTS on purpose: a model returning an
    unexpected key or an empty sequence is a DATA failure, and re-raising it would abort a batch over
    one paper — this defect's mirror image. Pinned so the list is not 'tidied' into including them."""
    assert AttributeError in batch._CODE_DEFECTS
    assert TypeError in batch._CODE_DEFECTS
    assert NameError in batch._CODE_DEFECTS
    assert ImportError in batch._CODE_DEFECTS
    assert IndexError not in batch._CODE_DEFECTS
    assert KeyError not in batch._CODE_DEFECTS

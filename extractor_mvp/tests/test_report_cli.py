"""The single-PDF entry point (A4). No network, no spend: the client is canned.

Uses the ``canned_batch`` fixture, so the orchestrator, the span resolver and the renderer are
all real and only the PDF loader and the model call are stubbed. A test that stubbed ``to_report``
would assert nothing about the artifact the command exists to produce.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from extractor_mvp import report


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    """A path that exists. load_pdf_text is stubbed, so the bytes are never read."""
    p = tmp_path / "schwartz_2018.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return p


def test_writes_a_report_to_stdout(canned_batch: None, capsys: Any, pdf: Path) -> None:
    assert report.main([str(pdf)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Replication Protocol — schwartz_2018")
    assert "## COBIDAS D.3 coverage (preprocessing)" in out


def test_writes_a_report_to_output_path(canned_batch: None, tmp_path: Path, pdf: Path) -> None:
    dest = tmp_path / "nested" / "out.md"
    assert report.main([str(pdf), "--output", str(dest)]) == 0
    assert dest.is_file(), "parent directories should be created"
    assert dest.read_text(encoding="utf-8").startswith("# Replication Protocol — schwartz_2018")


def test_paper_id_defaults_to_the_filename_stem_and_is_overridable(
    canned_batch: None, capsys: Any, pdf: Path
) -> None:
    report.main([str(pdf), "--paper-id", "chosen_id"])
    assert capsys.readouterr().out.startswith("# Replication Protocol — chosen_id")


def test_missing_pdf_names_the_path(tmp_path: Path) -> None:
    """FileNotFoundError carrying the resolved path, not a bare stack trace — the convention
    load_batch_config adopted in 21a40e7."""
    missing = tmp_path / "nope.pdf"
    with pytest.raises(FileNotFoundError, match=str(missing)):
        report.main([str(missing)])


def test_exits_nonzero_when_no_report_is_produced(monkeypatch: Any, capsys: Any, pdf: Path) -> None:
    """process_paper never raises for a bad paper; the single-paper caller inspects instead."""
    monkeypatch.setattr(report, "process_paper", lambda *a, **k: _failed_result(str(pdf)))
    assert report.main([str(pdf)]) == 1
    assert "FAILED" in capsys.readouterr().err


def _failed_result(path: str) -> Any:
    """Keyword-constructed on purpose: PaperResult has 17 positional fields and counting them
    is how the first draft of this test broke. Spelled out rather than **-unpacked so mypy can
    check each argument — a dict[str, int] splat is not narrowable and the hook rejects it."""
    from extractor_mvp.batch import PaperResult

    return PaperResult(
        paper_id="schwartz_2018",
        path=path,
        status="pdf_parse_failed",
        parser=None,
        methods_found_via=None,
        methods_header_matched=None,
        likely_multi_acquisition=False,
        n_extracted=0,
        n_deferred=0,
        n_deferral_quote_unresolved=0,
        n_inferred_from_kb=0,
        n_inferred_from_citation=0,
        n_missing_not_stated=0,
        n_missing_quote_unresolved=0,
        n_value_not_in_literal=0,
        extraction_json=None,
        error_message="pypdf returned no text",
    )


def test_default_model_matches_what_every_tracked_config_names() -> None:
    """The default exists so the printed command stays short; it must not drift from the
    corpus. Every config in extractor_mvp/configs/ names this same model."""
    configs = sorted((Path(__file__).resolve().parents[1] / "configs").rglob("*.yaml"))
    assert configs, "no tracked configs found"
    named = {
        line.split(":", 1)[1].strip()
        for c in configs
        for line in c.read_text(encoding="utf-8").splitlines()
        if line.startswith("model:")
    }
    assert named == {report.DEFAULT_MODEL}

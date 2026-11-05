"""The fMRI gate (fix 1b, the author's list of 2026-11-05). Offline: a stub client answers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import extractor_mvp.batch as batch
from conftest import FULL_TEXT
from extractor_mvp.fmri_gate import FmriGateAnswer, ask_fmri, gate_text, to_not_fmri_report

EEG = (
    "Methods\nWe recorded resting EEG from 64 channels in 40 adults. "
    'Structural T1 images were segmented into "grey matter" and white matter.\n'
    "References\nSmith (2004) Resting-state fMRI networks. NeuroImage.\n"
)


def _client(answer: FmriGateAnswer | Exception, prompts: list[str] | None = None) -> Any:
    def create(**kw: Any) -> Any:
        if prompts is not None:
            prompts.append(kw["messages"][0]["content"])
        if isinstance(answer, Exception):
            raise answer
        return answer

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_a_no_with_a_resolving_sentence_stops_the_paper() -> None:
    q = "We recorded resting EEG from 64 channels in 40 adults."
    g = ask_fmri(EEG, "m", client=_client(FmriGateAnswer(fmri="no", data="EEG, T1", quote=q)))
    assert g["status"] == "ok" and g["quote_resolved"] and g["stop"] is True


def test_only_that_evidence_stops_a_paper() -> None:
    unfound = FmriGateAnswer(fmri="no", data="EEG", quote="A sentence the paper does not hold.")
    assert ask_fmri(EEG, "m", client=_client(unfound))["stop"] is False
    no_quote = FmriGateAnswer(fmri="no", data="EEG", quote=None)
    assert ask_fmri(EEG, "m", client=_client(no_quote))["stop"] is False
    for fmri in ("yes", "unclear"):
        q = "We recorded resting EEG from 64 channels in 40 adults."
        ans = FmriGateAnswer(fmri=fmri, data="x", quote=q)  # type: ignore[arg-type]
        assert ask_fmri(EEG, "m", client=_client(ans))["stop"] is False
    failed = ask_fmri(EEG, "m", client=_client(RuntimeError("down")))
    assert failed["status"] == "call_failed" and failed["stop"] is False


def test_the_gate_reads_the_paper_before_its_references_with_no_double_quote() -> None:
    prompts: list[str] = []
    ask_fmri(EEG, "m", client=_client(FmriGateAnswer(), prompts))
    body = prompts[0].split('Paper text:\n"""', 1)[1]
    assert "Resting-state fMRI networks" not in body  # a reference title is not fMRI in the paper
    assert "'grey matter'" in body and '"grey matter"' not in body
    assert gate_text(EEG).startswith("Methods\nWe recorded")


def test_the_not_fmri_report_says_so_and_quotes_the_sentence() -> None:
    g = {"data": "EEG and T1", "quote": "We recorded  EEG.\n"}
    out = to_not_fmri_report("p", g)
    assert out.startswith("# Replication Protocol — p\n")
    assert "No fMRI in this paper." in out and "«We recorded EEG.»" in out
    assert "COBIDAS D.3 coverage" not in out


def _gate(stop: bool) -> dict[str, Any]:
    return {
        "status": "ok",
        "error": None,
        "fmri": "no" if stop else "yes",
        "data": "EEG",
        "quote": "q",
        "quote_resolved": True,
        "stop": stop,
    }


def test_process_paper_stops_on_the_gate_and_runs_no_extraction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(batch, "load_pdf_text", lambda _p: (FULL_TEXT, "pypdf"))
    monkeypatch.setattr(batch, "ask_fmri", lambda *_a, **_k: _gate(True))

    def no_extract(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("extraction ran on a paper the gate stopped")

    monkeypatch.setattr(batch, "extract", no_extract)
    r = batch.process_paper("p", tmp_path / "p.pdf", "m")
    assert r.status == "not_fmri" and r.n_extracted == 0
    assert r.extraction_json is not None and "preprocessing" not in r.extraction_json
    assert r.extraction_json["fmri_gate"]["stop"] is True
    assert r.report is not None and "No fMRI in this paper." in r.report


def test_process_paper_runs_on_and_stores_the_gate_when_it_does_not_stop(
    canned_batch: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(batch, "ask_fmri", lambda *_a, **_k: _gate(False))
    r = batch.process_paper("p", tmp_path / "p.pdf", "m")
    assert r.status == "success" and r.extraction_json is not None
    assert r.extraction_json["fmri_gate"]["fmri"] == "yes"
    assert "preprocessing" in r.extraction_json


def test_the_rerender_script_renders_a_stopped_record(tmp_path: Path) -> None:
    import importlib.util
    import json

    path = Path(__file__).resolve().parents[1] / "scripts" / "rerender_reports.py"
    spec = importlib.util.spec_from_file_location("rerender_reports", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rec = {"paper_id": "p", "status": "not_fmri", "fmri_gate": _gate(True)}
    (tmp_path / "p.json").write_text(json.dumps(rec))
    assert "No fMRI in this paper." in mod._render_one(tmp_path / "p.json")

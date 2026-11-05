"""aespa-report runs the full setup and meters every call (fix 2, the author's list of 2026-11-05).
Offline: the first hop is the canned batch; the hop, call R and the scan are stubbed where they
would call a model, and the meter is fed LiteLLM's own mock responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from extractor_mvp import full_report, report
from extractor_mvp.citation_hop import CallMeter


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    p = tmp_path / "p1.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return p


def _stub_rest(monkeypatch: pytest.MonkeyPatch, seen: dict[str, Any]) -> None:
    def hop(_text: str, _prep: Any, ref: str, corpus: list[Path], _model: str, **kw: Any) -> list:
        seen.setdefault("refs", []).append(ref)
        seen["corpus"] = corpus
        seen["hop_meter"] = kw.get("meter")
        return [{"ref_string": ref, "status": "reference_not_found"}]

    def release(_text: str, _model: str, **kw: Any) -> dict:
        seen["release_meter"] = kw.get("meter")
        return {"status": "ok", "releases": []}

    def uses(mentions: list, _model: str, **kw: Any) -> list:
        seen["scan_meter"] = kw.get("meter")
        return []

    monkeypatch.setattr(full_report, "run_hop", hop)
    monkeypatch.setattr(full_report, "extract_data_release", release)
    monkeypatch.setattr(full_report, "ask_uses", uses)


def _with_deferrals(monkeypatch: pytest.MonkeyPatch, kinds: list[tuple[str, str]]) -> None:
    real = full_report.process_paper

    def pp(*a: Any, **k: Any) -> Any:
        r = real(*a, **k)
        r.extraction_json["deferred_fields"] = [
            {"field": f"f{i}", "ref_string": ref, "target_kind": kind}
            for i, (ref, kind) in enumerate(kinds)
        ]
        return r

    monkeypatch.setattr(full_report, "process_paper", pp)


def test_the_hop_runs_once_per_distinct_paper_reference_and_never_for_a_supplement(
    canned_batch: None, monkeypatch: pytest.MonkeyPatch, pdf: Path, tmp_path: Path
) -> None:
    seen: dict[str, Any] = {}
    _stub_rest(monkeypatch, seen)
    _with_deferrals(
        monkeypatch,
        [
            ("Smith 2013", "paper"),
            ("Smith 2013", "paper"),
            ("S1", "supplement"),
            ("FSL", "pipeline"),
        ],
    )
    meter = CallMeter()
    out = full_report.run_paper("p1", pdf, "m", [tmp_path], meter=meter)
    # distinct; pipeline targets not hopped; a supplement is not a citation (fix 4, 2026-11-05)
    assert seen["refs"] == ["Smith 2013"]
    assert seen["corpus"] == [tmp_path]
    assert seen["hop_meter"] is meter and seen["release_meter"] is meter
    assert seen["scan_meter"] is meter
    rec = out.record
    assert rec is not None and len(rec["second_hop"]) == 1
    assert rec["data_release"] == {"status": "ok", "releases": []}
    assert rec["citing_software"] == [] and rec["hop_errors"] == []
    assert out.report is not None and "As described in cited papers" in out.report
    assert set(rec["run"]) >= {"wall_s", "n_calls", "retries", "parse_errors", "cost_usd", "calls"}


def test_a_hop_that_raises_is_recorded_and_the_report_stands(
    canned_batch: None, monkeypatch: pytest.MonkeyPatch, pdf: Path, tmp_path: Path
) -> None:
    seen: dict[str, Any] = {}
    _stub_rest(monkeypatch, seen)
    _with_deferrals(monkeypatch, [("Smith 2013", "paper")])

    def boom(*_a: Any, **_k: Any) -> list:
        raise RuntimeError("hop down")

    monkeypatch.setattr(full_report, "run_hop", boom)
    out = full_report.run_paper("p1", pdf, "m", [tmp_path])
    assert out.record is not None and out.record["hop_errors"][0]["ref"] == "Smith 2013"
    assert out.report is not None


def test_a_paper_the_gate_stops_ends_after_the_first_step(
    monkeypatch: pytest.MonkeyPatch, pdf: Path, tmp_path: Path
) -> None:
    import extractor_mvp.batch as batch
    from conftest import FULL_TEXT

    seen: dict[str, Any] = {}
    _stub_rest(monkeypatch, seen)
    monkeypatch.setattr(batch, "load_pdf_text", lambda _p: (FULL_TEXT, "pypdf"))
    gate = {"status": "ok", "fmri": "no", "data": "EEG", "quote": "q", "quote_resolved": True}
    monkeypatch.setattr(batch, "ask_fmri", lambda *_a, **_k: {**gate, "error": None, "stop": True})
    out = full_report.run_paper("p1", pdf, "m", [tmp_path])
    assert out.status == "not_fmri" and seen == {}
    assert out.report is not None and "No fMRI in this paper." in out.report
    assert out.record is not None and "run" in out.record


def test_the_meter_labels_a_first_hop_call_by_its_tool_and_counts_attempts() -> None:
    meter = CallMeter()
    tools = [{"type": "function", "function": {"name": "FmriGateAnswer", "parameters": {}}}]
    msgs = [{"role": "user", "content": "x"}]
    for _ in range(2):
        meter.completion(model="gpt-4o-mini", messages=msgs, tools=tools, mock_response="ok")
    meter.label = "R"
    meter.completion(model="gpt-4o-mini", messages=msgs, mock_response="ok")
    assert [(c["call"], c["attempt"]) for c in meter.calls] == [
        ("first:FmriGateAnswer", 1),
        ("first:FmriGateAnswer", 2),
        ("R", 1),
    ]
    totals = full_report.run_totals(meter.calls, 1.0)
    assert totals["n_calls"] == 3 and totals["retries"] == 1


def test_the_cli_writes_the_run_record_beside_the_report(
    canned_batch: None, monkeypatch: pytest.MonkeyPatch, pdf: Path, tmp_path: Path, capsys: Any
) -> None:
    seen: dict[str, Any] = {}
    _stub_rest(monkeypatch, seen)
    dest = tmp_path / "out" / "p1.md"
    assert report.main([str(pdf), "--output", str(dest)]) == 0
    rec = json.loads((tmp_path / "out" / "p1.record.json").read_text())
    assert rec["paper_id"] == "p1" and "run" in rec and "calls" in rec["run"]
    assert dest.read_text().startswith("# Replication Protocol — p1")
    err = capsys.readouterr().err
    assert "p1: success · " in err and " retries · " in err
    assert "refs" not in seen  # no deferral: the hop is not called
    assert "release_meter" in seen and "scan_meter" in seen  # call R and the scan both ran


def test_process_paper_passes_its_client_to_every_first_hop_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import extractor_mvp.batch as batch
    from conftest import FULL_TEXT, _canned_payload, stub_client

    monkeypatch.setattr(batch, "load_pdf_text", lambda _p: (FULL_TEXT, "pypdf"))
    used: list[str] = []
    inner = stub_client(_canned_payload())

    def create(**kw: Any) -> Any:
        used.append(kw["response_model"].__name__)
        if kw["response_model"].__name__ == "FmriGateAnswer":
            from extractor_mvp.fmri_gate import FmriGateAnswer

            return FmriGateAnswer(fmri="yes", data="fMRI", quote=None)
        return inner.chat.completions.create(**kw)

    from types import SimpleNamespace

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    r = batch.process_paper("p", tmp_path / "p.pdf", "m", client=client)
    assert r.status == "success"
    assert used[0] == "FmriGateAnswer" and "VerifierExtraction" in used
    assert {"PreprocessingExtraction", "SpatialExtraction", "TemporalVolumeExtraction"} <= set(used)


def test_run_paper_hands_process_paper_the_meter_s_client(
    canned_batch: None, monkeypatch: pytest.MonkeyPatch, pdf: Path, tmp_path: Path
) -> None:
    seen: dict[str, Any] = {}
    _stub_rest(monkeypatch, seen)
    real = full_report.process_paper
    got: dict[str, Any] = {}

    def pp(*a: Any, **k: Any) -> Any:
        got.update(k)
        return real(*a, **k)

    monkeypatch.setattr(full_report, "process_paper", pp)
    meter = CallMeter()
    full_report.run_paper("p1", pdf, "m", [tmp_path], meter=meter)
    client = got.get("client")
    assert client is not None
    n = len(meter.calls)
    client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "x"}],
        response_model=None,
        mock_response="ok",
    )
    assert len(meter.calls) == n + 1  # a call through it lands in the meter


def test_a_crash_still_reports_the_calls_it_made(
    monkeypatch: pytest.MonkeyPatch, pdf: Path, tmp_path: Path, capsys: Any
) -> None:
    def crash(*_a: Any, client: Any = None, **_k: Any) -> Any:
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "x"}],
            response_model=None,
            mock_response="ok",
        )
        raise ValueError("a code defect")

    monkeypatch.setattr(full_report, "process_paper", crash)
    with pytest.raises(ValueError):
        full_report.run_paper("p1", pdf, "m", [tmp_path])
    err = capsys.readouterr().err
    assert "p1: crashed; calls made before the crash:" in err and "'n_calls': 1" in err


def test_the_kb_scan_line_renders_on_a_report_with_no_hop(
    canned_batch: None, monkeypatch: pytest.MonkeyPatch, pdf: Path, tmp_path: Path
) -> None:
    # 2026-11-05 (second round, item 4): every report carries the scan's line
    seen: dict[str, Any] = {}
    _stub_rest(monkeypatch, seen)
    monkeypatch.setattr(
        full_report,
        "tool_list",
        lambda _uses: [
            {"display_name": "CONN", "version": None, "kept": True, "use_quote": "q"},
            {"display_name": "SPM", "version": "12", "kept": False},
        ],
    )
    out = full_report.run_paper("p1", pdf, "m", [tmp_path])
    assert out.record is not None and out.record["second_hop"] == []
    assert out.report is not None
    assert "This paper's software by the KB scan" in out.report and "CONN  (fMRI use:" in out.report
    assert "named, no quoted fMRI use: SPM" in out.report
    assert "no field defers to a cited paper, so no hop ran" in out.report


def test_a_record_with_no_scan_release_or_hop_renders_no_section() -> None:
    from extractor_mvp.render import _second_hop_section

    assert _second_hop_section(None, None, None) == []
    assert _second_hop_section([], None, None) == []


def test_the_scan_and_call_r_read_the_reflowed_text_the_extraction_read(
    canned_batch: None, monkeypatch: pytest.MonkeyPatch, pdf: Path, tmp_path: Path
) -> None:
    # the author's list of 2026-11-05, third round, item 4: one text for every step of the report
    import extractor_mvp.batch as batch
    from conftest import FULL_TEXT

    seen: dict[str, Any] = {}
    _stub_rest(monkeypatch, seen)

    def release(text: str, _model: str, **kw: Any) -> dict:
        seen["release_text"] = text
        return {"status": "ok", "releases": []}

    monkeypatch.setattr(full_report, "extract_data_release", release)
    lines: list[str] = []
    for ln in (FULL_TEXT + "\n").splitlines():
        words = ln.split()
        lines.extend([words[0], *(" " + w for w in words[1:])] if words else [" "])
    layer = "\n".join(lines)
    monkeypatch.setattr(batch, "load_pdf_text", lambda _p: (layer, "pypdf"))
    monkeypatch.setattr(full_report, "load_pdf_text", lambda _p: (layer, "pypdf"))
    out = full_report.run_paper("p1", pdf, "m", [tmp_path])
    assert out.record is not None and out.record["text_reflow"] is not None
    assert seen["release_text"] != layer
    assert "".join(seen["release_text"].split()) == "".join(layer.split())

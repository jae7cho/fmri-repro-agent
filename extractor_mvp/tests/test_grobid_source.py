"""GROBID as a text source (the author's request of 2026-11-06): the flattener on TEI fixtures with
gordon_2014's and cattarinussi_2026's structure (synthetic prose), the flag, the cache, the
fallback. Offline: the server is stubbed; no model call."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

import extractor_mvp.batch as batch
from extractor_mvp import grobid_source as gs
from extractor_mvp.grobid_source import flatten_tei
from extractor_mvp.span_resolver import resolve_quote

FIX = Path(__file__).parent / "fixtures" / "grobid"
GORDON = (FIX / "gordon_2014_structure.tei.xml").read_bytes()
CATT = (FIX / "cattarinussi_2026_structure.tei.xml").read_bytes()


# --- the flattener --------------------------------------------------------------------------------


def test_each_head_and_paragraph_is_a_line_in_document_order() -> None:
    lines = flatten_tei(GORDON).splitlines()
    assert lines[0] == "INTRODUCTION"
    assert lines[2:4] == ["METHODS", "Image Preprocessing"]
    assert lines[-2:] == ["RESULTS", "Connectivity changed after the task (Fig. 1)."]


def test_a_citation_becomes_its_position_in_the_reference_list() -> None:
    text = flatten_tei(CATT)
    # GROBID's #b33 is the 34th entry, printed 34 in a numbered style
    assert "pipeline. [34] Briefly" in text
    assert "signals [34] , [35] and" in text


def test_a_citation_without_a_target_keeps_its_own_text() -> None:
    assert "One citation has no entry [36]." in flatten_tei(CATT)


def test_an_author_year_citation_is_rendered_by_its_position_too() -> None:
    text = flatten_tei(GORDON)
    assert "long ago [3] [40]." in text
    assert "earlier resting work [5]." in text
    assert "Author et al." not in text


def test_figures_tables_and_back_matter_are_not_text() -> None:
    gordon, catt = flatten_tei(GORDON), flatten_tei(CATT)
    assert "caption" not in gordon and "Figure 1" not in gordon
    assert "cell text" not in catt and "Table 1" not in catt
    assert "Acknowledgments" not in catt and "Not body text" not in catt


def test_a_non_citation_ref_keeps_its_text() -> None:
    assert "(Fig. 1)" in flatten_tei(GORDON)


def test_a_sentence_comes_out_whole_and_a_quote_across_a_citation_resolves() -> None:
    gordon = flatten_tei(GORDON)
    quote = "Finally, a band-pass filter kept frequencies between 0.01 Hz and 0.1 Hz"
    assert resolve_quote(quote, gordon).span is not None
    catt = flatten_tei(CATT)
    assert resolve_quote("with the consortium pipeline. Briefly, the steps", catt).span is not None


def test_a_tei_without_a_body_is_empty() -> None:
    assert flatten_tei(b'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text/></TEI>') == ""


# --- the server, the cache, the flag, the fallback ------------------------------------------------


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """A stub GROBID: /api/version and /api/processFulltextDocument, counting the POSTs."""
    seen: dict[str, Any] = {"posts": 0, "tei": GORDON}

    def http(url: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> bytes:
        if seen.get("down"):
            raise urllib.error.URLError("connection refused")
        if url.endswith("/api/version"):
            return json.dumps({"version": "0.9.1", "revision": "0.9.1"}).encode()
        assert url.endswith("/api/processFulltextDocument") and data is not None
        seen["posts"] += 1
        return bytes(seen["tei"])

    monkeypatch.setattr(gs, "_http", http)
    monkeypatch.setenv(gs.GROBID_CACHE_ENV, str(tmp_path / "cache"))
    monkeypatch.delenv(gs.GROBID_IMAGE_ENV, raising=False)
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(b"%PDF-1.4 a stand-in")
    seen["pdf"] = pdf
    seen["cache"] = tmp_path / "cache"
    return seen


def test_the_default_text_source_is_pypdf_and_grobid_is_never_asked(
    server: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(gs.TEXT_SOURCE_ENV, raising=False)
    monkeypatch.setattr(batch, "load_pdf_text", lambda _p: ("pypdf text", "pypdf"))
    assert batch.load_text(server["pdf"]) == (
        "pypdf text",
        "pypdf",
        {"text_source": "pypdf", "text_source_fallback": None},
    )
    assert server["posts"] == 0


def test_the_flag_reads_the_tei_body_and_names_version_and_image(
    server: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(gs.TEXT_SOURCE_ENV, "grobid")
    text, parser, prov = batch.load_text(server["pdf"])
    assert parser == "grobid" and text == flatten_tei(GORDON)
    assert prov == {"text_source": "grobid-0.9.1-full", "text_source_fallback": None}
    monkeypatch.setenv(gs.GROBID_IMAGE_ENV, "crf")
    assert batch.load_text(server["pdf"])[2]["text_source"] == "grobid-0.9.1-crf"


def test_the_tei_is_cached_by_pdf_sha_image_and_version(
    server: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(gs.TEXT_SOURCE_ENV, "grobid")
    batch.load_text(server["pdf"])
    batch.load_text(server["pdf"])
    assert server["posts"] == 1
    sha = gs.pdf_sha256(server["pdf"])
    assert (server["cache"] / f"{sha}.full.0.9.1.tei.xml").is_file()
    monkeypatch.setenv(gs.GROBID_IMAGE_ENV, "crf")
    batch.load_text(server["pdf"])
    assert server["posts"] == 2  # another image is another entry


def test_an_unreachable_server_falls_back_to_pypdf_and_says_so(
    server: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(gs.TEXT_SOURCE_ENV, "grobid")
    monkeypatch.setattr(batch, "load_pdf_text", lambda _p: ("pypdf text", "pypdf"))
    server["down"] = True
    text, parser, prov = batch.load_text(server["pdf"])
    assert (text, parser, prov["text_source"]) == ("pypdf text", "pypdf", "pypdf")
    assert prov["text_source_fallback"].startswith("grobid unavailable: URLError")


def test_a_reply_that_is_not_tei_falls_back(
    server: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(gs.TEXT_SOURCE_ENV, "grobid")
    monkeypatch.setattr(batch, "load_pdf_text", lambda _p: ("pypdf text", "pypdf"))
    server["tei"] = b"[GENERAL] An exception occurred"
    _, parser, prov = batch.load_text(server["pdf"])
    assert parser == "pypdf" and "no TEI" in prov["text_source_fallback"]
    assert not list(server["cache"].glob("*"))  # nothing cached from a failed reply


def test_every_record_names_its_text_source(
    server: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from conftest import FULL_TEXT, _canned_payload, stub_client
    from extractor_mvp.extractor import extract

    def fake_extract(paper: Any, model: str, **kw: Any) -> Any:
        return extract(paper, model, client=stub_client(_canned_payload()))

    monkeypatch.setattr(batch, "extract", fake_extract)
    monkeypatch.setattr(batch, "load_pdf_text", lambda _p: (FULL_TEXT, "pypdf"))
    monkeypatch.delenv(gs.TEXT_SOURCE_ENV, raising=False)
    r = batch.process_paper("p", tmp_path / "p.pdf", "m")
    assert r.extraction_json is not None
    assert r.extraction_json["text_source"]["text_source"] == "pypdf"
    monkeypatch.setenv(gs.TEXT_SOURCE_ENV, "grobid")
    server["down"] = True
    r = batch.process_paper("p", tmp_path / "p.pdf", "m")
    assert r.extraction_json is not None
    assert r.extraction_json["text_source"]["text_source_fallback"].startswith("grobid unavailable")


def test_the_cli_flag_sets_the_text_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from extractor_mvp import report

    monkeypatch.delenv(gs.TEXT_SOURCE_ENV, raising=False)
    seen: dict[str, Any] = {}

    def stop(*_a: Any, **_k: Any) -> Any:
        seen["source"] = gs.text_source_requested()
        raise SystemExit(0)

    monkeypatch.setattr(report, "run_paper", stop)
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(b"%PDF")
    with pytest.raises(SystemExit):
        report.main([str(pdf), "--text-source", "grobid"])
    assert seen["source"] == "grobid"

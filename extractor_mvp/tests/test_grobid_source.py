"""GROBID as a text source (the author's request of 2026-11-06): the flattener on TEI fixtures with
gordon_2014's, cattarinussi_2026's and viduarre_2017's structure (synthetic prose), the flag, the
cache, the fallback. Offline: the server is stubbed; no model call."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

import extractor_mvp.batch as batch
from extractor_mvp import grobid_source as gs
from extractor_mvp.grobid_source import flatten_tei
from extractor_mvp.span_resolver import CITATION_CLOSE, CITATION_OPEN, resolve_quote

FIX = Path(__file__).parent / "fixtures" / "grobid"
GORDON = (FIX / "gordon_2014_structure.tei.xml").read_bytes()
CATT = (FIX / "cattarinussi_2026_structure.tei.xml").read_bytes()
VIDUARRE = (FIX / "viduarre_2017_structure.tei.xml").read_bytes()


def _vis(tei: bytes) -> str:
    """The flattened text without the citation delimiters, as a reader sees it."""
    return flatten_tei(tei).replace(CITATION_OPEN, "").replace(CITATION_CLOSE, "")


# --- the flattener --------------------------------------------------------------------------------


def test_each_head_and_paragraph_is_a_line_in_document_order() -> None:
    lines = flatten_tei(GORDON).splitlines()
    assert lines[0] == "INTRODUCTION"
    assert lines[2:4] == ["METHODS", "Image Preprocessing"]
    assert lines[-2:] == ["RESULTS", "Connectivity changed after the task (Fig. 1)."]


def test_a_numbered_citation_is_bracketed_and_its_index_never_used() -> None:
    text = _vis(CATT)
    # GROBID's target #b33 would be the 34th entry; the ref's own text is what is printed
    assert "pipeline. [34] Briefly" in text
    assert "signals [34] , [35] and" in text
    assert "no entry [36]." in text


def test_a_pair_and_a_range_in_one_ref_are_bracketed_whole() -> None:
    assert "one ref [4 , 5] and so do ranges [5 -7] here." in _vis(CATT)


def test_an_author_year_citation_keeps_the_papers_own_text() -> None:
    text = _vis(GORDON)
    assert "long ago [Author et al., 2000; Other et al., 2006]." in text
    assert "earlier resting work [Author, 1995]." in text
    assert "[3]" not in text and "[5]" not in text


def _p(inner: str) -> bytes:
    return (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div><p>'
        + inner
        + "</p></div></body></text></TEI>"
    ).encode()


def test_numerals_inside_a_bracket_the_paper_opened_stay_as_printed() -> None:
    # weber_2024's shape: GROBID splits "[5, 25, 35]" into refs "[5,", "25," and "35]"
    tei = _p(
        'shown before <ref type="bibr" target="#b4">[5,</ref><ref type="bibr" target="#b24">'
        '25,</ref><ref type="bibr" target="#b34">35]</ref> and after <ref type="bibr">7</ref>.'
    )
    assert _vis(tei) == "shown before [5,25,35] and after [7]."


def test_superscript_numerals_with_a_trailing_comma_are_bracketed() -> None:
    # cole_2013's shape: refs "1," and "2" with no bracket in the paper
    tei = _p('most active <ref type="bibr" target="#b0">1,</ref><ref type="bibr">2</ref> here')
    assert _vis(tei) == "most active [1,][2] here"


def test_a_ref_that_is_not_bare_numerals_is_never_bracketed() -> None:
    tei = _p('as before <ref type="bibr" target="#b1">(12)</ref> and <ref type="bibr">S3</ref>.')
    assert _vis(tei) == "as before (12) and S3."


def test_figures_tables_and_the_reference_list_are_not_text() -> None:
    gordon, catt, vid = flatten_tei(GORDON), flatten_tei(CATT), flatten_tei(VIDUARRE)
    assert "caption" not in gordon and "Figure 1" not in gordon
    assert "cell text" not in catt and "Table 1" not in catt
    assert "reference title" not in catt and "reference title" not in vid
    assert "000" not in vid  # the funding listOrg is not prose either


def test_back_matter_prose_follows_the_body() -> None:
    catt = flatten_tei(CATT).splitlines()
    assert catt[-2:] == ["Acknowledgments", "Not body text."]
    vid = flatten_tei(VIDUARRE).splitlines()
    assert vid[:4] == [
        "Results",
        "Networks switched between two states.",
        "Discussion",
        "The states were stable across sessions.",
    ]
    assert vid[4:7] == ["ACKNOWLEDGMENTS.", "Thanks are given to the volunteers.", "Methods"]
    assert vid[-1] == "A hidden Markov model was fitted to all sessions."


def test_a_quote_in_an_annex_methods_section_resolves() -> None:
    vid = flatten_tei(VIDUARRE)
    q = "Time series were cleaned with independent components (13)."
    assert resolve_quote(q, vid).span is not None


def test_a_non_citation_ref_keeps_its_text() -> None:
    assert "(Fig. 1)" in flatten_tei(GORDON)


def test_a_sentence_comes_out_whole_and_a_quote_across_a_citation_resolves() -> None:
    gordon = flatten_tei(GORDON)
    quote = "Finally, a band-pass filter kept frequencies between 0.01 Hz and 0.1 Hz"
    assert resolve_quote(quote, gordon).span is not None
    # gordon_2014's three filtering quotes end with the paper's own author-year citation
    assert resolve_quote(quote + ", as in earlier resting work [Author, 1995].", gordon).span
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


def test_the_default_text_source_is_grobid(
    server: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # the author's ruling 1 of 2026-11-08
    monkeypatch.delenv(gs.TEXT_SOURCE_ENV, raising=False)
    monkeypatch.setattr(batch, "load_pdf_text", lambda _p: ("pypdf text", "pypdf"))
    text, parser, prov = batch.load_text(server["pdf"])
    assert parser == "grobid" and text == flatten_tei(GORDON)
    assert prov == {"text_source": "grobid-0.9.1-crf", "text_source_fallback": None}
    assert server["posts"] == 1


@pytest.mark.parametrize("flag", ["pypdf", "PyPDF", " pypdf "])
def test_the_pypdf_flag_reads_pypdf_and_grobid_is_never_asked(
    server: dict[str, Any], monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    monkeypatch.setenv(gs.TEXT_SOURCE_ENV, flag)
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
    # the image AESPA expects is CRF (the author's ruling 4 of 2026-11-06); full is an option
    assert prov == {"text_source": "grobid-0.9.1-crf", "text_source_fallback": None}
    monkeypatch.setenv(gs.GROBID_IMAGE_ENV, "full")
    assert batch.load_text(server["pdf"])[2]["text_source"] == "grobid-0.9.1-full"


def test_the_tei_is_cached_by_pdf_sha_image_and_version(
    server: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(gs.TEXT_SOURCE_ENV, "grobid")
    batch.load_text(server["pdf"])
    batch.load_text(server["pdf"])
    assert server["posts"] == 1
    sha = gs.pdf_sha256(server["pdf"])
    assert (server["cache"] / f"{sha}.crf.0.9.1.tei.xml").is_file()
    monkeypatch.setenv(gs.GROBID_IMAGE_ENV, "full")
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
    monkeypatch.setenv(gs.TEXT_SOURCE_ENV, "pypdf")
    r = batch.process_paper("p", tmp_path / "p.pdf", "m")
    assert r.extraction_json is not None
    assert r.extraction_json["text_source"] == {
        "text_source": "pypdf",
        "text_source_fallback": None,
    }
    monkeypatch.delenv(gs.TEXT_SOURCE_ENV, raising=False)  # the default: GROBID, here unreachable
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
        report.main([str(pdf)])
    assert seen["source"] == "grobid"  # the default
    with pytest.raises(SystemExit):
        report.main([str(pdf), "--text-source", "pypdf"])
    assert seen["source"] == "pypdf"
    with pytest.raises(SystemExit):
        report.main([str(pdf), "--text-source", "grobid"])
    assert seen["source"] == "grobid"


def test_the_data_release_slice_uses_the_text_source(monkeypatch: pytest.MonkeyPatch) -> None:
    import extractor_mvp.methods_finder as mf
    from extractor_mvp.citation_hop import extract_data_release

    seen: list[str] = []

    class StopError(Exception):
        pass

    def spy(text: str, *, text_source: str = "pypdf") -> Any:
        seen.append(text_source)
        raise StopError

    monkeypatch.setattr(mf, "find_methods_section", spy)
    for source in ("grobid", "pypdf"):
        with pytest.raises(StopError):
            extract_data_release("text", "m", client=object(), text_source=source)
    with pytest.raises(StopError):
        extract_data_release("text", "m", client=object())
    assert seen == ["grobid", "pypdf", "pypdf"]


def test_a_heading_inside_the_reference_list_is_not_text() -> None:
    # TEI allows <head> in <listBibl>; none of the 36 cached TEIs of 2026-11-06 has one
    tei = (
        b'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div><p>Prose.</p></div></body>'
        b'<back><div type="references"><listBibl><head>Cited works</head><biblStruct/></listBibl>'
        b"</div></back></text></TEI>"
    )
    assert flatten_tei(tei) == "Prose."

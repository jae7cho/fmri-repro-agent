"""The citation hop's references through GROBID's ref targets (the author's list of 2026-11-09,
item 4): a deferral's ``<ref type="bibr" target="#bNN">`` followed to its ``<biblStruct>``, with the
marker text against the text layer's reference list as the fallback. Synthetic TEI and prose only;
no model call (the hop's client is never reached or is stubbed) and no GROBID server."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from extractor_mvp import citation_hop, grobid_source
from extractor_mvp.citation_hop import (
    GROBID_REF_TARGET,
    MARKER_TEXT,
    grobid_ref_matches,
    resolve_targets,
    run_hop,
)
from extractor_mvp.grobid_source import (
    GrobidUnavailableError,
    bibliography,
    cached_tei,
    refs_in_sentence,
)

_NS = 'xmlns="http://www.tei-c.org/ns/1.0"'

_BIBL = """
<listBibl>
  <biblStruct xml:id="b2">
    <analytic><title level="a">A synthetic third paper</title>
      <author><persName><forename>Q</forename><surname>Third</surname></persName></author>
    </analytic>
    <monogr><title level="j">J Synth</title><imprint><date type="published" when="2011"/></imprint></monogr>
  </biblStruct>
  <biblStruct xml:id="b3">
    <analytic><title level="a">A synthetic pipeline paper</title>
      <author><persName><forename>A</forename><surname>Alpha</surname></persName></author>
      <author><persName><forename>B</forename><surname>Beta</surname></persName></author>
      <idno type="DOI">10.9999/synthetic.0003</idno>
    </analytic>
    <monogr><title level="j">J Synth</title><imprint><date type="published" when="2019-05"/></imprint></monogr>
  </biblStruct>
  <biblStruct xml:id="b4">
    <analytic><title level="a">A synthetic second paper</title>
      <author><persName><forename>G</forename><surname>Gamma</surname></persName></author>
    </analytic>
    <monogr><title level="j">J Synth</title><imprint><date type="published" when="2020"/></imprint></monogr>
  </biblStruct>
  <biblStruct xml:id="b66">
    <monogr><title level="m">A synthetic book</title>
      <author><persName><forename>D</forename><surname>Delta</surname></persName></author>
      <imprint><date type="published" when="2017"/></imprint></monogr>
  </biblStruct>
</listBibl>
"""


def _tei(body: str, bibl: str = _BIBL) -> bytes:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?><TEI {_NS}><teiHeader/><text><body>{body}</body>'
        f"<back><div>{bibl}</div></back></text></TEI>"
    ).encode()


# "[3,][4]": two refs in a bracket, as the paper prints them; the sentence also cites [2] for
# something else, which is not the deferral's
_BRACKET_P = (
    "<div><head>Preprocessing</head><p>Data were collected as before "
    '<ref type="bibr" target="#b2">[2]</ref>. Motion was corrected as described elsewhere '
    '<ref type="bibr" target="#b3">[3,</ref><ref type="bibr" target="#b4">4]</ref>. '
    "Then smoothing followed.</p></div>"
)
_BRACKET_SENT = "Motion was corrected as described elsewhere ￹[3,￻￹[4]￻."
# a bare superscript number, as "67"
_BARE_P = (
    "<div><p>Images were processed with a published pipeline"
    '<ref type="bibr" target="#b66">67</ref> and then inspected.</p></div>'
)
_BARE_SENT = "Images were processed with a published pipeline67 and then inspected."

# the text layer's reference list, for the marker-text fallback
_PYPDF_REFS = (
    "Methods\nNothing.\nReferences\n"
    "1. One, O., 2001. A first paper. J Synth 1, 1.\n"
    "2. Third, Q., 2011. A synthetic third paper. J Synth 2, 2.\n"
    "3. Alpha, A., Beta, B., 2019. A synthetic pipeline paper. J Synth 3, 3.\n"
    "4. Gamma, G., 2020. A synthetic second paper. J Synth 4, 4.\n"
)


def _ids(matches: list[Any]) -> list[str | None]:
    return [m.entry.bibl_id if m.entry else None for m in matches]


# --- the TEI readers ------------------------------------------------------------------------------


def test_the_bibliography_reads_each_entry_by_id() -> None:
    bib = bibliography(_tei(_BRACKET_P))
    assert set(bib) == {"b2", "b3", "b4", "b66"}
    b3 = bib["b3"]
    assert b3.authors == ("Alpha", "Beta") and b3.year == "2019"
    assert b3.doi == "10.9999/synthetic.0003" and b3.title == "A synthetic pipeline paper"
    # a book has no <analytic>: its authors and title are the volume's
    assert bib["b66"].authors == ("Delta",) and bib["b66"].title == "A synthetic book"
    assert bib["b4"].doi is None


def test_the_refs_inside_a_sentence_are_the_sentences_only() -> None:
    refs = refs_in_sentence(_tei(_BRACKET_P), _BRACKET_SENT)
    assert refs is not None
    assert [(r.text, r.target) for r in refs] == [("[3,", "b3"), ("4]", "b4")]
    assert refs_in_sentence(_tei(_BRACKET_P), "A sentence the paper never wrote.") is None
    assert refs_in_sentence(_tei(_BRACKET_P), "Then smoothing followed.") == []


# --- through the targets --------------------------------------------------------------------------


def test_a_sentence_whose_refs_point_at_two_entries_resolves_to_both() -> None:
    matches, why = grobid_ref_matches("[3,][4]", [("paper", _tei(_BRACKET_P))], [_BRACKET_SENT])
    assert why == "paper:sentence_exact" and matches is not None
    assert _ids(matches) == ["b3", "b4"]  # [2], in the sentence before, is not the deferral's
    assert [m.state for m in matches] == ["resolved", "resolved"]
    e3 = matches[0].entry
    assert e3 is not None
    assert (e3.first_author, e3.year, e3.doi) == ("Alpha", "2019", "10.9999/synthetic.0003")


def test_the_bracket_form_resolves_through_targets() -> None:
    matches, resolution, why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", _tei(_BRACKET_P))], sentences=[_BRACKET_SENT]
    )
    assert resolution == GROBID_REF_TARGET and why == "paper:sentence_exact"
    assert _ids(matches) == ["b3", "b4"]


def test_a_bare_numeric_marker_resolves_through_its_target() -> None:
    # the text layer has no reference 67 at all: only the target can find it
    matches, resolution, why = resolve_targets(
        "67", _PYPDF_REFS, teis=[("paper", _tei(_BARE_P))], sentences=[_BARE_SENT]
    )
    assert resolution == GROBID_REF_TARGET and why == "paper:sentence_exact"
    assert _ids(matches) == ["b66"]
    assert matches[0].entry is not None and matches[0].entry.first_author == "Delta"


# --- the fallback to the marker text --------------------------------------------------------------


def test_a_ref_without_a_target_falls_back_to_the_marker_text() -> None:
    body = _BRACKET_P.replace(' target="#b4"', "")
    matches, resolution, why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", _tei(body))], sentences=[_BRACKET_SENT]
    )
    assert resolution == MARKER_TEXT and why == "ref_without_target"
    # the marker text, against the text layer's list: numbers 3 and 4
    assert [m.part for m in matches] == ["3", "4"]
    assert [m.entry.bibl_id if m.entry else "x" for m in matches] == [None, None]
    assert [m.state for m in matches] == ["resolved", "resolved"]


def test_a_target_outside_the_bibliography_falls_back() -> None:
    body = _BRACKET_P.replace('target="#b4"', 'target="#b99"')
    _m, resolution, why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", _tei(body))], sentences=[_BRACKET_SENT]
    )
    assert resolution == MARKER_TEXT and why == "target_not_in_bibliography"


def test_a_sentence_with_no_ref_of_the_deferral_falls_back() -> None:
    body = _BRACKET_P.replace('<ref type="bibr" target="#b3">[3,</ref>', "[3,").replace(
        '<ref type="bibr" target="#b4">4]</ref>', "4]"
    )
    _m, resolution, why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", _tei(body))], sentences=[_BRACKET_SENT]
    )
    assert resolution == MARKER_TEXT and why == "no_ref_in_sentence"


def test_a_sentence_not_in_the_tei_or_none_given_falls_back() -> None:
    tei = _tei(_BRACKET_P)
    _m, res, why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", tei)], sentences=["Not there."]
    )
    assert (res, why) == (MARKER_TEXT, "sentence_not_in_tei")
    _m, res, why = resolve_targets("[3,][4]", _PYPDF_REFS, teis=[("paper", tei)], sentences=[])
    assert (res, why) == (MARKER_TEXT, "no_deferral_sentence")


def test_a_non_grobid_source_falls_back_to_the_marker_text() -> None:
    matches, resolution, why = resolve_targets("[3,][4]", _PYPDF_REFS, sentences=[_BRACKET_SENT])
    assert resolve_targets("[3,][4]", _PYPDF_REFS, teis=[], sentences=[_BRACKET_SENT])[1:] == (
        MARKER_TEXT,
        "text_source_not_grobid",
    )
    assert resolution == MARKER_TEXT and why == "text_source_not_grobid"
    assert [m.part for m in matches] == ["3", "4"]


def test_an_unreadable_tei_falls_back() -> None:
    _m, resolution, why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", b"<TEI")], sentences=[_BRACKET_SENT]
    )
    assert resolution == MARKER_TEXT and why is not None and why.startswith("tei_unreadable")


# --- the hop records the path and reuses the on-disk lookup ---------------------------------------


def _no_scope(*_a: Any) -> dict[str, Any]:
    return {"asked": [], "software": False, "tools": []}


def test_the_hop_records_its_resolution_and_looks_the_entry_up_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both targets go to ``resolve_local_pdf``: b3 by its DOI printed in the stub PDF, b4 has no
    file. No model call: the lookup is stubbed to stop the hop before any call."""
    seen: list[tuple[str | None, str | None]] = []
    real = citation_hop.resolve_local_pdf

    def lookup(entry: Any, dirs: list[Path], **kw: Any) -> Any:
        state, _path, by = real(
            entry, dirs, read_text=lambda _p: ("doi 10.9999/synthetic.0003", "pypdf")
        )
        seen.append((entry.bibl_id, state))
        return state, None, by  # no path: the hop stops before reading the cited paper

    (tmp_path / "Alpha_2019.pdf").write_bytes(b"%PDF-stub")
    monkeypatch.setattr(citation_hop, "resolve_local_pdf", lookup)
    monkeypatch.setattr(citation_hop, "hop_scope", _no_scope)
    out = run_hop(
        _PYPDF_REFS,
        None,
        "[3,][4]",
        [tmp_path],
        "m",
        client=object(),  # never called
        teis=[("paper", _tei(_BRACKET_P))],
        deferral_sentences=[_BRACKET_SENT],
    )
    assert seen == [("b3", "local_pdf"), ("b4", "no_local_pdf")]
    assert [r["ref_resolution"] for r in out] == [GROBID_REF_TARGET] * 2
    assert [r["ref_resolution_detail"] for r in out] == ["paper:sentence_exact"] * 2
    assert [r["reference"]["bibl_id"] for r in out] == ["b3", "b4"]


def test_the_hop_without_a_tei_records_the_marker_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(citation_hop, "hop_scope", _no_scope)
    out = run_hop(_PYPDF_REFS, None, "[3,][4]", [tmp_path], "m", client=object())
    assert [r["ref_resolution"] for r in out] == [MARKER_TEXT] * 2
    assert [r["ref_resolution_detail"] for r in out] == ["text_source_not_grobid"] * 2
    assert [r["status"] for r in out] == ["not_retrievable"] * 2


# --- the cached TEI -------------------------------------------------------------------------------


def test_the_cached_tei_is_read_by_the_records_text_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(grobid_source.GROBID_CACHE_ENV, str(tmp_path / "cache"))
    pdf = tmp_path / "p.pdf"
    pdf.write_bytes(b"%PDF-stub")
    (tmp_path / "cache").mkdir()
    name = f"{grobid_source.pdf_sha256(pdf)}.crf.0.9.1.tei.xml"
    (tmp_path / "cache" / name).write_bytes(b"<TEI/>")
    assert cached_tei(pdf, "grobid-0.9.1-crf") == b"<TEI/>"
    with pytest.raises(GrobidUnavailableError):
        cached_tei(pdf, "grobid-0.9.1-full")  # another image's entry is never read
    with pytest.raises(GrobidUnavailableError):
        cached_tei(pdf, "pypdf")


# --- a sentence not verbatim; a supplement's own list ---------------------------------------------


def test_a_reworded_sentence_is_found_by_its_words_around_the_refs() -> None:
    reworded = "Motion was then corrected, as described elsewhere [3,][4]."
    matches, resolution, why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", _tei(_BRACKET_P))], sentences=[reworded]
    )
    assert resolution == GROBID_REF_TARGET
    assert why.startswith("paper:sentence_word_overlap=")
    assert _ids(matches) == ["b3", "b4"]


def test_a_sentence_sharing_too_few_words_falls_back() -> None:
    unrelated = "Cortical surfaces were reconstructed with a template [3,][4]."
    _m, resolution, why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", _tei(_BRACKET_P))], sentences=[unrelated]
    )
    assert (resolution, why) == (MARKER_TEXT, "sentence_not_in_tei")


def test_two_equally_near_runs_fall_back_rather_than_choose() -> None:
    twice = _BRACKET_P.replace("</p></div>", " " + _BRACKET_P.split("<p>")[1].split("</p>")[0])
    twice += "</p></div>"
    reworded = "Motion was then corrected, as described elsewhere [3,][4]."
    _m, resolution, why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", _tei(twice))], sentences=[reworded]
    )
    assert (resolution, why) == (MARKER_TEXT, "sentence_not_in_tei")


_SUPP_BIBL = """
<listBibl>
  <biblStruct xml:id="b2">
    <analytic><title level="a">A synthetic supplement source</title>
      <author><persName><forename>E</forename><surname>Epsilon</surname></persName></author>
    </analytic>
    <monogr><title level="j">J Synth</title><imprint><date type="published" when="2018"/></imprint></monogr>
  </biblStruct>
</listBibl>
"""


def test_a_deferral_in_the_supplement_cites_the_supplements_own_list() -> None:
    supp_p = (
        "<div><p>Scanner drift was removed as reported "
        '<ref type="bibr" target="#b2">[3]</ref>.</p></div>'
    )
    teis = [("paper", _tei(_BRACKET_P)), ("supplement", _tei(supp_p, _SUPP_BIBL))]
    matches, resolution, why = resolve_targets(
        "[3]", _PYPDF_REFS, teis=teis, sentences=["Scanner drift was removed as reported [3]."]
    )
    assert resolution == GROBID_REF_TARGET and why == "supplement:sentence_exact"
    assert _ids(matches) == ["supplement:b2"]
    assert matches[0].entry is not None and matches[0].entry.first_author == "Epsilon"


# --- run_paper hands the hop the cached TEIs and the deferring sentences --------------------------


@pytest.mark.parametrize("cached", [True, False, "pypdf"])
def test_run_paper_hands_the_hop_the_cached_tei_and_the_sentences(
    canned_batch: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, cached: bool | str
) -> None:
    import extractor_mvp.batch as batch
    from conftest import FULL_TEXT
    from extractor_mvp import full_report

    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setenv(grobid_source.GROBID_CACHE_ENV, str(tmp_path / "cache"))
    if cached:
        (tmp_path / "cache").mkdir()
        name = f"{grobid_source.pdf_sha256(pdf)}.crf.0.9.1.tei.xml"
        (tmp_path / "cache" / name).write_bytes(_tei(_BRACKET_P))
    real = full_report.process_paper

    def pp(*a: Any, **k: Any) -> Any:
        r = real(*a, **k)
        r.extraction_json["deferred_fields"] = [
            {
                "field": "f0",
                "ref_string": "[3,][4]",
                "target_kind": "paper",
                "deferral_sentence": _BRACKET_SENT,
            },
            {
                "field": "f1",
                "ref_string": "[3,][4]",
                "target_kind": "paper",
                "deferral_sentence": _BRACKET_SENT,
            },
        ]
        return r

    seen: dict[str, Any] = {}

    def hop(_text: str, _prep: Any, ref: str, _c: list[Path], _m: str, **kw: Any) -> list:
        seen["teis"] = [(label, len(t) > 0) for label, t in kw["teis"]]
        seen["sentences"] = kw["deferral_sentences"]
        return []

    monkeypatch.setattr(full_report, "process_paper", pp)
    monkeypatch.setattr(full_report, "run_hop", hop)
    monkeypatch.setattr(full_report, "extract_data_release", lambda *a, **k: {"releases": []})
    monkeypatch.setattr(full_report, "ask_uses", lambda *a, **k: [])
    parser = "pypdf" if cached == "pypdf" else "grobid"
    prov = {"text_source": "pypdf" if cached == "pypdf" else "grobid-0.9.1-crf"}
    monkeypatch.setattr(batch, "load_text", lambda _p: (FULL_TEXT, parser, prov))
    monkeypatch.setattr(full_report, "load_pdf_text", lambda _p: ("References\n1. Smith.", "pypdf"))
    out = full_report.run_paper("p1", pdf, "m", [tmp_path])
    assert seen["sentences"] == [_BRACKET_SENT]  # one per distinct sentence
    assert out.record is not None
    if cached == "pypdf":  # the paper was not read with GROBID: no TEI, even a cached one
        assert seen["teis"] == [] and out.record["hop_tei"] == {}
    elif cached:
        assert seen["teis"] == [("paper", True)]
        assert out.record["hop_tei"] == {"paper": "grobid-0.9.1-crf"}
    else:
        assert seen["teis"] == []
        assert out.record["hop_tei"]["paper"].startswith("unavailable: no cached TEI")


def test_a_ref_in_the_sentence_that_is_not_the_deferrals_is_left_out() -> None:
    body = (
        '<div><p>As before <ref type="bibr" target="#b2">[2]</ref>, motion was corrected '
        '<ref type="bibr" target="#b3">[3,</ref><ref type="bibr" target="#b4">4]</ref>.</p></div>'
    )
    sentence = "As before [2], motion was corrected [3,][4]."
    matches, resolution, _why = resolve_targets(
        "[3,][4]", _PYPDF_REFS, teis=[("paper", _tei(body))], sentences=[sentence]
    )
    assert resolution == GROBID_REF_TARGET and _ids(matches) == ["b3", "b4"]


def test_no_local_pdf_falls_back_to_europepmc_by_doi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """2026-11-09 (the author's item 2): an entry with no PDF on disk is read from Europe PMC's open
    full text, by its DOI, and the record says so."""
    monkeypatch.setattr(citation_hop, "hop_scope", _no_scope)
    monkeypatch.setattr(citation_hop, "crossref_doi", lambda entry, **_: "10.9999/synthetic")
    seen: list[str] = []

    def epmc(doi: str, cache_dir: Path | None) -> tuple[str, Path, str]:
        seen.append(doi)
        return "Methods\nSynthetic text.", tmp_path / "x.europepmc.xml", "0" * 64

    out = run_hop(_PYPDF_REFS, None, "[3,][4]", [tmp_path], "m", client=object(), europepmc=epmc)
    assert seen and all(
        r["target"]["state"] == "europepmc_fulltext" for r in out if r.get("target")
    )
    assert out[0]["target"]["confirmed_by"] == "europepmc_doi"

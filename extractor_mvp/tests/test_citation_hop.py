"""The citation hop (DESIGN_citation_hop.md, forks ratified 2026-11-03), case one's build. Offline:
a fake client serves the hop's calls by response model; the cited PDF is a stubbed text."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conftest import stub_client
from extractor_mvp import citation_hop, render
from extractor_mvp.citation_hop import (
    CallMeter,
    CitingReleases,
    DataRelease,
    HopSpatialExtraction,
    HopTemporalExtraction,
    HopTool,
    HopVariant,
    described_only,
    extract_data_release,
    hop_scope,
    match_reference,
    parse_reference_list,
    release_relation,
    resolve_local_pdf,
    run_hop,
)
from extractor_mvp.coverage_extractor import SoftwareMentionResult, SpatialExtraction
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import PreprocessingExtraction, extract
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.verifier import FieldVerdict, VerifierExtraction

_SMOOTH = "Images were smoothed with a 6 mm FWHM Gaussian kernel."
_BIAS = "Images were corrected for intensity inhomogeneity by bias field estimation."
_BIAS_N4 = "Bias fields were removed with N4."
_DEFER = "More detailed information about MRI preprocessing can be found at Doe et al. (2019)."
CITING = (
    "Methods\n"
    f"{_SMOOTH} {_BIAS} {_BIAS_N4} {_DEFER}\n"
    "Results\nNothing.\n"
    "References\n"
    "Abel, A., Baker, B., 2015. A first paper. J. Neurosci. 1, 1-2.\n"
    "Doe Jr, J. J., Roe, R., Poe, P., Moe, M., Zoe, Z.,\n"
    "Coe, C., 2019. Image processing and analysis methods for a large study.\n"
    "NeuroImage 202, 116091. https://doi.org/10.1016/j.neuroimage.2019.116091.\n"
    "Smith, S., 2013. One. NeuroImage 80, 1.\n"
    "Smith, S., 2013. Two. NeuroImage 80, 2.\n"
)
_FS = "Brain extraction was performed with FreeSurfer 7.1.1 on all data."
_FWHM_GE = "For GE data a 4 mm kernel was used."
_N4 = "Intensity inhomogeneity was corrected with N4ITK's default settings."
_REL = "Processing is described for ABCD Data Releases 1.0 - 2.0.1."
CITED = (
    "Methods\n"
    f"{_FS} Scanner differences were handled per vendor. {_FWHM_GE} {_N4} {_REL}\n"
    'To avoid signal "drop-out" a spin-echo scan was used, \u201cas published\u201d.\n'
    "DOI 10.1016/j.neuroimage.2019.116091\n"
    "Results\nNothing.\n"
)


def _missing() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _citing_prep(**spatial: FieldExtractionResult) -> Any:
    """A citing paper that reports smoothing and defers its base pipeline to Doe et al. (2019)."""
    from extractor_mvp.coverage_extractor import SpatialExtraction as S

    payload = PreprocessingExtraction(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
        base_pipeline_ref=FieldExtractionResult(
            status="deferred", deferral_sentence=_DEFER, ref_string="Doe et al. (2019)"
        ),
    )
    paper = ParsedPaper(text=CITING, source="t", parser="manual")
    prep, _, _ = extract(
        paper,
        "m",
        client=stub_client(
            payload,
            spatial=S(
                smoothing_performed=FieldExtractionResult(
                    status="extracted", value="yes", verbatim_quote=_SMOOTH
                ),
                smoothing_fwhm_mm=FieldExtractionResult(
                    status="extracted", value="6", verbatim_quote=_SMOOTH
                ),
                **spatial,
            ),
        ),
    )
    return prep


# --- the reference list -------------------------------------------------------------------------


def test_an_author_year_ref_matches_one_entry_across_wrapped_author_lines() -> None:
    entries = parse_reference_list(CITING)
    assert [e.first_author for e in entries] == ["Abel", "Doe Jr", "Smith", "Smith"]
    [m] = match_reference("Doe et al. (2019)", entries)
    assert m.state == "resolved" and m.entry is not None
    assert m.entry.year == "2019" and m.entry.doi == "10.1016/j.neuroimage.2019.116091"
    assert CITING[m.entry.start : m.entry.end] == m.entry.text  # a span of the citing text
    assert m.entry.text.startswith("Doe Jr, J. J.") and "Coe, C., 2019" in m.entry.text


def test_no_match_and_two_matches_are_reported_states_never_a_pick() -> None:
    entries = parse_reference_list(CITING)
    assert match_reference("Hagler et al. (2019)", entries)[0].state == "reference_not_found"
    assert match_reference("Smith et al. 2013", entries)[0].state == "reference_ambiguous"
    assert match_reference("Doe et al. (2019)", [])[0].state == "no_reference_section"


def test_a_numbered_ref_gives_one_target_per_number() -> None:
    text = "Intro.\nReferences\n47. Doe J. A paper. 2001.\n48. Roe R. Another. 2002.\n"
    matches = match_reference("refs. 47 and 48", parse_reference_list(text))
    assert [(m.part, m.state) for m in matches] == [("47", "resolved"), ("48", "resolved")]


def test_a_local_pdf_is_found_by_first_author_and_year(tmp_path: Path) -> None:
    [m] = match_reference("Doe et al. (2019)", parse_reference_list(CITING))
    assert m.entry is not None
    assert resolve_local_pdf(m.entry, [tmp_path]) == ("no_local_pdf", None)
    (tmp_path / "Doe_2019.pdf").write_bytes(b"%PDF")
    state, path = resolve_local_pdf(m.entry, [tmp_path])
    assert state == "local_pdf" and path == (tmp_path / "Doe_2019.pdf").resolve()
    other = tmp_path / "other"
    other.mkdir()
    (other / "doe_2019.pdf").write_bytes(b"%PDF")
    assert resolve_local_pdf(m.entry, [tmp_path, other]) == ("local_pdf_ambiguous", None)


# --- the scope (fork A) -------------------------------------------------------------------------


def test_the_scope_skips_rows_the_citing_paper_reports_and_asks_the_software() -> None:
    scope = hop_scope(_citing_prep(), "Doe et al. (2019)")
    asked = {a["field"]: a["why"] for a in scope["asked"]}
    assert scope["software"] is True
    assert not any(
        f.startswith("spatial_smoothing.") for f in asked
    )  # reported by the citing paper
    assert asked["brain_extraction.performed"] == "row not reported: brain_extraction"
    assert "intersubject_registration" in scope["rows_outside_calls"]


# --- the hop end to end -------------------------------------------------------------------------


def _hop_client(counter: dict[str, int], prompts: list[str]) -> Any:
    temporal = HopTemporalExtraction()
    spatial = HopSpatialExtraction(
        brain_extraction_performed=FieldExtractionResult(
            status="extracted", value="yes", verbatim_quote=_FS
        ),
        software_mentions=[
            SoftwareMentionResult(name="FreeSurfer", version="7.1.1", verbatim_quote=_FS)
        ],
        variants=[
            HopVariant(
                field="brain_extraction_method",
                value="4 mm",
                verbatim_quote=_FWHM_GE,
                applies_to="GE",
            ),
            HopVariant(
                field="brain_extraction_method",
                value="x",
                verbatim_quote="a sentence not in the text",
                applies_to="Philips",
            ),
            # a real field the citing paper reports, so outside the scope
            HopVariant(
                field="spatial_smoothing.fwhm_mm",
                value="4",
                verbatim_quote=_FWHM_GE,
                applies_to="GE",
            ),
        ],
        tools=[
            HopTool(field="intensity_correction.method", tool="N4ITK default", verbatim_quote=_N4),
            # a step not asked for its tool
            HopTool(field="motion_correction.method", tool="MCFLIRT", verbatim_quote=_N4),
        ],
        releases_described=[
            DataRelease(dataset="ABCD", release="1.0 - 2.0.1", verbatim_quote=_REL)
        ],
    )
    verdict = VerifierExtraction(
        fields=[
            FieldVerdict(field="brain_extraction.performed", verdict="supported", relied_on=_FS)
        ]
    )

    def create(*, response_model: Any = None, messages: Any = None, **_kw: Any) -> Any:
        name = response_model.__name__
        counter[name] = counter.get(name, 0) + 1
        prompts.append(messages[0]["content"])
        return {
            "HopTemporalExtraction": temporal,
            "HopSpatialExtraction": spatial,
            "VerifierExtraction": verdict,
        }[name]

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kw: Any) -> tuple[list, dict, list]:
    import extractor_mvp.pdf_loader as pdf_loader

    (tmp_path / "Doe_2019.pdf").write_bytes(b"%PDF-stub")
    monkeypatch.setattr(pdf_loader, "load_pdf_text", lambda _p: (CITED, "pypdf"))
    counter: dict[str, int] = {}
    prompts: list[str] = []
    out = run_hop(
        CITING,
        kw.pop("prep", None) or _citing_prep(),
        "Doe et al. (2019)",
        [tmp_path],
        "m",
        client=_hop_client(counter, prompts),
    )
    return out, counter, prompts


def test_the_hop_asks_only_the_scope_and_never_writes_into_the_citing_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = _citing_prep()
    before = prep.model_dump(mode="json")
    [rec], counter, prompts = _run(tmp_path, monkeypatch, prep=prep)
    assert prep.model_dump(mode="json") == before
    assert rec["status"] == "ok" and rec["target"]["state"] == "local_pdf"
    assert rec["target"]["doi_confirmed"] is True
    # calls T (scope has temporal rows), S, the checking pass: one each
    assert counter == {
        "HopTemporalExtraction": 1,
        "HopSpatialExtraction": 1,
        "VerifierExtraction": 1,
    }
    asked = {a["field"] for a in rec["scope"]["asked"]}
    assert set(rec["fields"]) <= asked
    assert rec["fields"]["brain_extraction.performed"]["extraction"]["status"] == "EXTRACTED"
    assert "## This is a CITED paper, read for one hop" in prompts[1]
    only = prompts[1].split("Answer ONLY these fields: ", 1)[1].split(".\nEvery other field", 1)[0]
    assert "brain_extraction_performed" in only and "smoothing_fwhm_mm" not in only
    # variants: quote-checked, one per variant, never chosen; a field outside the scope is dropped
    variants = rec["variants"]["brain_extraction.method"]
    assert [(v["applies_to"], v["quote_resolved"]) for v in variants] == [
        ("GE", True),
        ("Philips", False),
    ]
    assert set(rec["variants"]) == {"brain_extraction.method"}
    assert rec["verifier"]["fields"]["brain_extraction.performed"]["verdict"] == "supported"


def test_an_unmatched_ref_makes_no_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    counter: dict[str, int] = {}
    out = run_hop(
        CITING,
        _citing_prep(),
        "Hagler et al. (2019)",
        [tmp_path],
        "m",
        client=_hop_client(counter, []),
    )
    assert [r["status"] for r in out] == ["reference_not_found"] and counter == {}


def test_a_second_hop_version_leaves_the_software_row_unaddressed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The design's pinned property (§4): a cited paper's exact version is shown "as described in
    <ref>" and never counts toward the citing paper's compliance."""
    prep = _citing_prep()
    [rec], _, _ = _run(tmp_path, monkeypatch, prep=prep)
    with_hop = render.to_report(prep, source="t", second_hop=[rec])
    without = render.to_report(prep, source="t")
    cov = with_hop.split("## COBIDAS D.3 coverage")[1]
    assert cov == without.split("## COBIDAS D.3 coverage")[1]  # coverage untouched by the hop
    assert "unconditional violation" in cov
    assert "Software: version and revision number NOT REPORTED" in cov
    assert "Base pipeline deferred to Doe et al. (2019); version not reported in this paper" in cov
    assert (
        "- Software as described in Doe et al. (2019) (not counted toward this paper's Software "
        "row): FreeSurfer 7.1.1" in with_hop
    )
    assert "- brain_extraction.performed = True — as described in Doe et al. (2019)" in with_hop
    assert "    - GE: 4 mm" in with_hop and "(its quote was not found — unverified)" in with_hop
    assert "## As described in cited papers" not in without


def test_a_failed_target_renders_its_state(tmp_path: Path) -> None:
    out = run_hop(CITING, _citing_prep(), "Doe et al. (2019)", [tmp_path], "m", client=object())
    assert out[0]["status"] == "not_retrievable"
    report = render.to_report(_citing_prep(), source="t", second_hop=out)
    assert "Not retrievable: no local PDF (PubMed Central is not built yet)." in report


def test_the_hop_module_uses_the_pinned_coverage_prompts() -> None:
    assert (
        citation_hop.TEMPORAL_VOLUME_PROMPT
        is __import__("extractor_mvp.coverage_extractor", fromlist=["x"]).TEMPORAL_VOLUME_PROMPT
    )
    assert SpatialExtraction is not HopSpatialExtraction  # its own response model, same fields
    assert set(SpatialExtraction.model_fields) <= set(HopSpatialExtraction.model_fields)


# --- fork A widened: a reported row without a tool is asked for the tool (2026-11-03) --------------


def _bias(value: str, quote: str = _BIAS) -> dict[str, FieldExtractionResult]:
    return {
        "intensity_correction_performed": FieldExtractionResult(
            status="extracted", value="yes", verbatim_quote=quote
        ),
        "intensity_correction_method": FieldExtractionResult(
            status="extracted", value=value, verbatim_quote=quote
        ),
    }


def test_a_reported_row_described_without_a_tool_is_asked_for_its_tool() -> None:
    scope = hop_scope(_citing_prep(**_bias("bias field estimation")), "Doe et al. (2019)")
    assert scope["tools"] == [
        {
            "field": "intensity_correction.method",
            "row": "intensity_correction",
            "described_as": ["bias field estimation"],
        }
    ]
    # its other fields stay unasked: the row is reported
    assert not any(a["field"].startswith("intensity_correction.") for a in scope["asked"])


def test_a_reported_row_that_names_its_tool_is_not_asked() -> None:
    from extractor_mvp.render import flatten

    prep = _citing_prep(**_bias("N4", _BIAS_N4))
    [method] = [r for r in flatten(prep) if r.path == "intensity_correction.method"]
    assert method.extraction_status == "EXTRACTED"  # the case is reached, not dropped upstream
    assert hop_scope(prep, "Doe et al. (2019)")["tools"] == []


def test_described_only_reads_the_resolution_not_the_words() -> None:
    term = SimpleNamespace
    assert described_only(
        term(verbatim="corrected for motion", resolved=None, resolution="unrecognized")
    )
    assert described_only(term(verbatim="in-house", resolved="other", resolution="resolved"))
    assert not described_only(term(verbatim="mcflirt", resolved="mcflirt", resolution="resolved"))
    assert not described_only(
        [
            term(verbatim="a phrase", resolved=None, resolution="unrecognized"),
            term(verbatim="topup", resolved="topup", resolution="resolved"),
        ]
    )


def test_the_tool_is_asked_on_call_s_quote_checked_and_rendered_as_described(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = _citing_prep(**_bias("bias field estimation"))
    [rec], _, prompts = _run(tmp_path, monkeypatch, prep=prep)
    assert "Steps: intensity_correction.method." in prompts[1]
    assert "Steps:" not in prompts[0]  # call T carries no tools
    assert set(rec["tools"]) == {"intensity_correction.method"}  # an unasked step is dropped
    [t] = rec["tools"]["intensity_correction.method"]
    # a possessive aside, the tool is in its quote
    assert (t["tool"], t["quote_resolved"], t["tool_in_quote"]) == ("N4ITK default", True, True)
    assert 'tool.intensity_correction.method | extracted | N4ITK default | quote: "' in prompts[2]
    report = render.to_report(prep, source="t", second_hop=[rec])
    assert (
        '- intensity_correction.method tool (this paper: "bias field estimation", no tool named) '
        "= N4ITK default — as described in Doe et al. (2019)" in report
    )
    rec["tools"]["intensity_correction.method"][0]["tool_in_quote"] = False
    unchecked = render.to_report(prep, source="t", second_hop=[rec])
    assert (
        "= N4ITK default  «" in unchecked and "(it is not in its quote — unverified)" in unchecked
    )
    assert "no tool named in Doe et al. (2019)" not in unchecked


# --- the data release: first hop, and "described vs applied" (2026-11-03) ------------------------


def _rel(dataset: str, release: str, ok: bool = True) -> dict[str, Any]:
    return {"dataset": dataset, "release": release, "quote_resolved": ok, "release_in_quote": ok}


def test_a_later_release_of_the_same_dataset_postdates_what_the_cited_paper_describes() -> None:
    described = [_rel("ABCD Data Releases", "1.0 - 2.0.1")]
    assert release_relation(_rel("ABCD", "3.0"), described) == "postdates"
    assert release_relation(_rel("ABCD", "2.0"), described) == "not_later"
    assert release_relation(_rel("ABCD", "2.0.1"), described) == "not_later"  # the same release
    assert (
        release_relation(_rel("ABCD-BIDS Community Collection", "3165"), described)
        == "undetermined"
    )
    assert release_relation(_rel("ABCD", "3.0", ok=False), described) == "undetermined"
    assert (
        release_relation(_rel("ABCD", "3.0"), [_rel("ABCD", "2.0.1", ok=False)]) == "undetermined"
    )
    assert (
        release_relation(
            _rel("Adolescent Brain Cognitive Development (ABCD) study", "3.0"), described
        )
        == "postdates"
    )


_OWN = "Data were extracted from the ABCD 3.0 release."


def _release_client(releases: list[DataRelease]) -> Any:
    def create(*, response_model: Any = None, **_kw: Any) -> Any:
        assert response_model is CitingReleases
        return CitingReleases(releases=releases)

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_the_citing_release_is_read_in_the_citing_paper_with_its_quote_checked() -> None:
    citing = CITING.replace(_DEFER, f"{_DEFER} {_OWN}")
    out = extract_data_release(
        citing,
        "m",
        client=_release_client(
            [
                DataRelease(dataset="ABCD", release="3.0", verbatim_quote=_OWN),
                DataRelease(dataset="ABCD", release="4.0", verbatim_quote=_OWN),
            ]
        ),
    )
    assert out["status"] == "ok"
    assert [
        (r["release"], r["quote_resolved"], r["release_in_quote"]) for r in out["releases"]
    ] == [
        ("3.0", True, True),
        ("4.0", True, False),
    ]


def test_a_postdating_release_renders_the_note_and_leaves_the_coverage_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prep = _citing_prep()
    [rec], _, _ = _run(tmp_path, monkeypatch, prep=prep)
    release = {"status": "ok", "releases": [{"dataset": "ABCD", **_quoted_ok("3.0")}]}
    report = render.to_report(prep, source="t", second_hop=[rec], data_release=release)
    assert "This paper's data release (read in this paper): ABCD 3.0" in report
    assert (
        "- Data releases whose processing Doe et al. (2019) describes: ABCD 1.0 - 2.0.1" in report
    )
    assert (
        "  Note: this paper's data come from ABCD 3.0, a later release than those Doe et al. (2019) "
        "describes; the pipeline described there may differ from the one applied to this paper's "
        "data." in report
    )
    cov = report.split("## COBIDAS D.3 coverage")[1]
    assert cov == render.to_report(prep, source="t").split("## COBIDAS D.3 coverage")[1]
    unchecked = {
        "status": "ok",
        "releases": [{"dataset": "ABCD", **_quoted_ok("3.0"), "release_in_quote": False}],
    }
    shown = render.to_report(prep, source="t", second_hop=[rec], data_release=unchecked)
    assert (
        "This paper's data release (read in this paper): none kept (1 named without its quote and "
        "value checked, not shown)" in shown
    )
    assert "Note: this paper's data come from" not in shown
    older = {"status": "ok", "releases": [{"dataset": "ABCD", **_quoted_ok("2.0")}]}
    assert "Note: this paper's data come from" not in render.to_report(
        prep, source="t", second_hop=[rec], data_release=older
    )


def _quoted_ok(release: str) -> dict[str, Any]:
    return {
        "release": release,
        "verbatim_quote": _OWN,
        "quote_resolved": True,
        "release_in_quote": True,
    }


# --- the retry: every attempt recorded (2026-11-03) ----------------------------------------------


def test_a_retried_attempt_keeps_its_raw_text_and_its_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import litellm

    replies = ['{"releases": "not a list"}', '{"releases": []}']
    real = litellm.completion
    monkeypatch.setattr(
        litellm, "completion", lambda *a, **kw: real(*a, mock_response=replies.pop(0), **kw)
    )
    meter = CallMeter()
    out = extract_data_release(CITING, "gpt-4o-mini", meter=meter)
    assert out == {"status": "ok", "releases": []}
    first, second = meter.calls
    assert (first["call"], first["attempt"], second["attempt"]) == ("R", 1, 2)
    assert first["raw"] == '{"releases": "not a list"}' and first["finish_reason"] == "stop"
    assert first["parse_error"].startswith("ValidationError") and second["parse_error"] is None


def test_the_cited_text_reaches_every_call_without_a_straight_double_quote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The retry's cause (case one, 2026-11-03): a copied 'signal \u201cdrop-out\u201d', its quotes
    straightened by the model, broke the JSON. Straight and curly double quotes both go."""
    [rec], _, prompts = _run(tmp_path, monkeypatch)
    assert len(prompts) == 3
    for p in prompts:
        assert "signal 'drop-out' a spin-echo scan was used, 'as published'." in p
    assert rec["methods"]["double_quotes_replaced"] == 4
    assert rec["fields"]["brain_extraction.performed"]["extraction"]["status"] == "EXTRACTED"

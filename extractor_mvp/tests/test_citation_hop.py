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
    HopSpatialExtraction,
    HopTemporalExtraction,
    HopVariant,
    hop_scope,
    match_reference,
    parse_reference_list,
    resolve_local_pdf,
    run_hop,
)
from extractor_mvp.coverage_extractor import SoftwareMentionResult, SpatialExtraction
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import PreprocessingExtraction, extract
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.verifier import FieldVerdict, VerifierExtraction

_SMOOTH = "Images were smoothed with a 6 mm FWHM Gaussian kernel."
_DEFER = "More detailed information about MRI preprocessing can be found at Doe et al. (2019)."
CITING = (
    "Methods\n"
    f"{_SMOOTH} {_DEFER}\n"
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
CITED = (
    "Methods\n"
    f"{_FS} Scanner differences were handled per vendor. {_FWHM_GE}\n"
    "DOI 10.1016/j.neuroimage.2019.116091\n"
    "Results\nNothing.\n"
)


def _missing() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _citing_prep() -> Any:
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

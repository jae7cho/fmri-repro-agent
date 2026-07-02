"""Tests for extract_preprocessing with a mocked LLM client."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    PreprocessingExtraction,
    extract_preprocessing,
)
from extractor_mvp.parsed_paper import ParsedPaper

TEXT = (
    "Data were normalized to MNI152NLin6Asym space at 2 mm isotropic resolution. "
    "Cortical surfaces were registered with MSMSulc onto the fsLR_32k atlas. "
    "Functional intensity used grand-mean scaling to 10000."
)


def _paper(text: str = TEXT) -> ParsedPaper:
    return ParsedPaper(text=text, source="test", parser="manual")


def _fake_client(payload: PreprocessingExtraction) -> Any:
    completions = SimpleNamespace(create=lambda **_: payload)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def _extracted(value: str, quote: str) -> FieldExtractionResult:
    return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)


def _missing() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _all_resolvable() -> PreprocessingExtraction:
    return PreprocessingExtraction(
        target_space=_extracted("MNI152NLin6Asym", "normalized to MNI152NLin6Asym"),
        resolution_mm=_extracted("2", "at 2 mm"),
        surface_registration=_extracted("msm_sulc", "registered with MSMSulc"),
        target_surface=_extracted("fsLR_32k", "fsLR_32k atlas"),
        intensity_convention=_extracted("fsl_grand_mean_10000", "grand-mean scaling to 10000"),
        intensity_value=_extracted("10000", "scaling to 10000"),
    )


def _field(preprocessing: Any, dotted: str) -> Any:
    for step in preprocessing.steps:
        for fname in type(step).model_fields:
            if fname == "kind":
                continue
            pf = getattr(step, fname)
            if f"{step.kind}.{pf.field_id}" == dotted:
                return pf
    raise AssertionError(f"no field {dotted}")


def test_all_fields_resolve_to_extracted():
    prep, diags, deferrals = extract_preprocessing(
        _paper(), "m", client=_fake_client(_all_resolvable())
    )
    assert diags == []
    assert deferrals == []
    for fid in (
        "spatial_normalization.target_space",
        "spatial_normalization.resolution_mm",
        "surface_projection.surface_registration",
        "surface_projection.target_surface",
        "intensity_normalization.convention",
        "intensity_normalization.value",
    ):
        pf = _field(prep, fid)
        assert pf.extraction.status == "EXTRACTED", fid
        assert pf.inference.status == "NOT_APPLICABLE"
        span = pf.extraction.spans[0]
        # the span literally points into the paper text (grounding closed)
        assert TEXT[span.start : span.end] == span.text


def test_resolutions_capture_raw_value_on_success():
    # A field that resolves via a SYNONYM alias: the LLM emits the paper's phrasing,
    # the resolver maps it to a canonical literal. The optional resolutions accumulator
    # must retain BOTH — the raw LLM value AND the resolved value/alias — so a firewall
    # leak's LAYER (prompt vs resolver) can be diagnosed from per-paper output. Only
    # the resolved value otherwise reaches the ProvenancedField.
    text = (
        "Cortical surfaces were registered using FreeSurfer's spherical registration. "
        "Data were normalized to MNI152NLin6Asym space at 2 mm isotropic resolution."
    )
    payload = PreprocessingExtraction(
        target_space=_extracted("MNI152NLin6Asym", "normalized to MNI152NLin6Asym"),
        resolution_mm=_missing(),
        surface_registration=_extracted(
            "FreeSurfer's spherical registration",
            "registered using FreeSurfer's spherical registration",
        ),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    resolutions: list[Any] = []
    prep, _, _ = extract_preprocessing(
        _paper(text), "m", client=_fake_client(payload), resolutions=resolutions
    )
    # the field resolved successfully to the canonical literal
    pf = _field(prep, "surface_projection.surface_registration")
    assert pf.extraction.status == "EXTRACTED"
    assert pf.extraction.value == "freesurfer_recon"
    # ...and the accumulator retained the RAW value alongside the resolved one
    rec = next(r for r in resolutions if r.field == "surface_projection.surface_registration")
    assert rec.raw_value == "FreeSurfer's spherical registration"
    assert rec.resolved_value == "freesurfer_recon"
    assert rec.matched_alias == "FreeSurfer's spherical registration"
    # only SUCCESSFUL targeted fields are recorded (missing fields produce no record)
    assert not any(r.field == "surface_projection.target_surface" for r in resolutions)
    # default (no accumulator passed) stays a no-op: existing 3-tuple callers unaffected
    _, diags2, deferrals2 = extract_preprocessing(_paper(text), "m", client=_fake_client(payload))
    assert diags2 == [] and deferrals2 == []


def test_unresolvable_quote_becomes_missing_with_diagnostic():
    payload = _all_resolvable()
    payload.target_space = _extracted(
        "MNI152NLin6Asym", "a phrase that does not appear in the text"
    )
    prep, diags, _ = extract_preprocessing(_paper(), "m", client=_fake_client(payload))
    pf = _field(prep, "spatial_normalization.target_space")
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason.startswith("extraction_quote_unresolved")
    assert any(d.field == "spatial_normalization.target_space" for d in diags)
    assert any("extraction_quote_unresolved" in d.failure_reason for d in diags)


def test_value_not_in_literal_becomes_missing_with_diagnostic():
    payload = _all_resolvable()
    # "MNI152" is underspecified (broader than any TargetSpace member) -> must NOT
    # be coerced; stays value_not_in_literal with an enriched diagnostic.
    payload.target_space = _extracted("MNI152", "normalized to MNI152NLin6Asym")
    prep, diags, _ = extract_preprocessing(_paper(), "m", client=_fake_client(payload))
    pf = _field(prep, "spatial_normalization.target_space")
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason == "value_not_in_literal"
    assert any(d.failure_reason.startswith("value_not_in_literal") for d in diags)
    assert any("underspecified" in d.failure_reason for d in diags)


def test_all_missing_yields_all_missing_no_diagnostics():
    none_payload = PreprocessingExtraction(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    prep, diags, deferrals = extract_preprocessing(_paper(), "m", client=_fake_client(none_payload))
    assert diags == []  # "not stated" is expected, not a diagnostic
    assert deferrals == []
    for fid in (
        "spatial_normalization.target_space",
        "intensity_normalization.value",
    ):
        pf = _field(prep, fid)
        assert pf.extraction.status == "MISSING_FROM_PAPER"
        assert pf.inference.reason == "not_stated_in_text"


# --- Deferred arm (Fork B Part A) ----------------------------------------------

DEFER_TEXT = (
    "Preprocessing followed the procedures in Glasser et al. (2013). "
    "Data were normalized to MNI152NLin6Asym space."
)


def _deferred_target_space(
    deferral_sentence: str, ref: str, target_kind: str = "paper"
) -> PreprocessingExtraction:
    payload = PreprocessingExtraction(
        target_space=FieldExtractionResult(
            status="deferred",
            deferral_sentence=deferral_sentence,
            ref_string=ref,
            target_kind=target_kind,
        ),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )
    return payload


def test_deferred_field_resolves_to_deferred_to_citation():
    payload = _deferred_target_space(
        "Preprocessing followed the procedures in Glasser et al. (2013).",
        "Glasser et al. 2013",
    )
    prep, diags, deferrals = extract_preprocessing(
        _paper(DEFER_TEXT), "m", client=_fake_client(payload)
    )
    pf = _field(prep, "spatial_normalization.target_space")
    assert pf.extraction.status == "DEFERRED_TO_CITATION"
    assert pf.extraction.deferrals[0].ref == "Glasser et al. 2013"
    assert pf.extraction.deferrals[0].target_kind == "paper"
    # span literally points into the paper text
    span = pf.extraction.deferrals[0].span
    assert DEFER_TEXT[span.start : span.end] == span.text
    # DEFERRED arm rejects NOT_APPLICABLE -> LEFT_MISSING until Fork B resolves it
    assert pf.inference.status == "LEFT_MISSING"
    assert diags == []
    # a machine-readable record surfaces for Fork B
    assert len(deferrals) == 1
    rec = deferrals[0]
    assert rec.field == "spatial_normalization.target_space"
    assert rec.ref_string == "Glasser et al. 2013"
    assert rec.target_kind == "paper"
    assert rec.pending_resolution is True


def test_deferred_supplement_maps_to_paper_but_record_preserves_original():
    payload = _deferred_target_space(
        "Preprocessing followed the procedures in Glasser et al. (2013).",
        "Glasser et al. 2013",
        target_kind="supplement",
    )
    prep, _diags, deferrals = extract_preprocessing(
        _paper(DEFER_TEXT), "m", client=_fake_client(payload)
    )
    pf = _field(prep, "spatial_normalization.target_space")
    # frozen provenance Deferral has no "supplement" -> mapped to "paper"
    assert pf.extraction.deferrals[0].target_kind == "paper"
    # ...but the original is preserved verbatim in the record for Fork B
    assert deferrals[0].target_kind == "supplement"


def test_unresolvable_deferral_falls_back_to_missing():
    payload = _deferred_target_space(
        "a deferral sentence that does not appear anywhere in the text",
        "Glasser et al. 2013",
    )
    prep, diags, deferrals = extract_preprocessing(
        _paper(DEFER_TEXT), "m", client=_fake_client(payload)
    )
    pf = _field(prep, "spatial_normalization.target_space")
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason.startswith("deferral_quote_unresolved")
    assert any(d.failure_reason.startswith("deferral_quote_unresolved") for d in diags)
    assert deferrals == []  # unresolved deferral is not a pending record


# --- FieldExtractionResult schema validator (Step 4a) --------------------------

_INVALID = [
    {"status": "extracted", "value": None, "verbatim_quote": "q"},
    {"status": "extracted", "value": "v", "verbatim_quote": None},
    {"status": "extracted", "value": "v", "verbatim_quote": "q", "deferral_sentence": "x"},
    {"status": "missing", "value": "x"},
    {"status": "missing", "deferral_sentence": "x"},
    {"status": "deferred", "deferral_sentence": None, "ref_string": "r"},
    {"status": "deferred", "deferral_sentence": "s", "ref_string": None},
    {"status": "deferred", "value": "x", "deferral_sentence": "s", "ref_string": "r"},
]


@pytest.mark.parametrize("kwargs", _INVALID)
def test_invalid_field_extraction_result_raises(kwargs: dict[str, Any]):
    with pytest.raises(ValidationError):
        FieldExtractionResult(**kwargs)


def test_valid_extracted_construction():
    r = FieldExtractionResult(
        status="extracted",
        value="MNI152NLin6Asym",
        verbatim_quote="Data were registered to MNI152NLin6Asym.",
    )
    assert r.status == "extracted"


def test_valid_missing_construction():
    r = FieldExtractionResult(
        status="missing",
        searched_terms=["MNI", "space"],
        sections_searched=["Methods"],
    )
    assert r.status == "missing"
    assert r.value is None


def test_valid_deferred_construction():
    r = FieldExtractionResult(
        status="deferred",
        deferral_sentence="Preprocessing followed Glasser et al. (2013)",
        ref_string="Glasser et al. 2013",
    )
    assert r.status == "deferred"
    assert r.target_kind == "paper"

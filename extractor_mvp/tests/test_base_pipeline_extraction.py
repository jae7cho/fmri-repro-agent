"""Layer-1 base_pipeline extraction: schema + _build_base_pipeline cases (offline),
plus a live Cho-2021 full-PDF probe (marked ``live``)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fmri_repro.spec.preprocessing import PipelineRef
from fmri_repro.spec.provenance import MissingFromPaper

from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    PreprocessingExtraction,
    _build_base_pipeline,
    extract_preprocessing,
)
from extractor_mvp.parsed_paper import ParsedPaper


# --- 6a: schema ----------------------------------------------------------------
def test_preprocessing_extraction_accepts_layer1_fields():
    payload = PreprocessingExtraction(
        target_space=FieldExtractionResult(status="missing"),
        resolution_mm=FieldExtractionResult(status="missing"),
        surface_registration=FieldExtractionResult(status="missing"),
        target_surface=FieldExtractionResult(status="missing"),
        intensity_convention=FieldExtractionResult(status="missing"),
        intensity_value=FieldExtractionResult(status="missing"),
        base_pipeline_name=FieldExtractionResult(
            status="extracted", value="fMRIPrep", verbatim_quote="We used fMRIPrep."
        ),
        base_pipeline_ref=FieldExtractionResult(
            status="deferred",
            deferral_sentence="Preprocessing followed Glasser et al. (2013).",
            ref_string="Glasser et al. 2013",
        ),
    )
    assert isinstance(payload.base_pipeline_name, FieldExtractionResult)
    assert isinstance(payload.base_pipeline_ref, FieldExtractionResult)


def test_layer1_fields_default_to_missing_when_omitted():
    # pre-existing fixtures omit the new fields; they must still construct.
    payload = PreprocessingExtraction(
        target_space=FieldExtractionResult(status="missing"),
        resolution_mm=FieldExtractionResult(status="missing"),
        surface_registration=FieldExtractionResult(status="missing"),
        target_surface=FieldExtractionResult(status="missing"),
        intensity_convention=FieldExtractionResult(status="missing"),
        intensity_value=FieldExtractionResult(status="missing"),
    )
    assert payload.base_pipeline_name.status == "missing"
    assert payload.base_pipeline_ref.status == "missing"


# --- 6b: _build_base_pipeline four cases ---------------------------------------
def _extracted(value: str, quote: str) -> FieldExtractionResult:
    return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)


def _deferred(sentence: str, ref: str) -> FieldExtractionResult:
    return FieldExtractionResult(status="deferred", deferral_sentence=sentence, ref_string=ref)


def test_case_extracted_name_extracted_ref():
    text = "We used fMRIPrep v20.2.3 (Esteban et al., 2019) to preprocess the data."
    field, deferral = _build_base_pipeline(
        _extracted("fMRIPrep", text),
        _extracted("Esteban et al., 2019", text),
        text,
    )
    assert not isinstance(field, MissingFromPaper)
    assert field.extraction.status == "EXTRACTED"
    assert isinstance(field.extraction.value, PipelineRef)
    assert field.extraction.value.name == "fMRIPrep"
    assert deferral is None  # extracted ref is attribution only


def test_case_extracted_name_deferred_ref():
    text = (
        "Data were processed with the HCP minimal preprocessing pipeline. "
        "Preprocessing followed Glasser et al. (2013)."
    )
    field, deferral = _build_base_pipeline(
        _extracted(
            "HCP minimal preprocessing pipeline",
            "Data were processed with the HCP minimal preprocessing pipeline.",
        ),
        _deferred("Preprocessing followed Glasser et al. (2013).", "Glasser et al. 2013"),
        text,
    )
    assert not isinstance(field, MissingFromPaper)
    assert field.extraction.status == "EXTRACTED"
    assert field.extraction.value.name == "HCP minimal preprocessing pipeline"
    # a DeferralRecord IS emitted for the ref so Fork B can resolve pipeline details
    assert deferral is not None
    assert deferral.field == "base_pipeline"
    assert deferral.ref_string == "Glasser et al. 2013"


def test_case_missing_name_deferred_ref():
    text = "Preprocessing followed Glasser et al. (2013)."
    field, deferral = _build_base_pipeline(
        FieldExtractionResult(status="missing"),
        _deferred("Preprocessing followed Glasser et al. (2013).", "Glasser et al. 2013"),
        text,
    )
    assert not isinstance(field, MissingFromPaper)
    assert field.extraction.status == "DEFERRED_TO_CITATION"
    assert field.extraction.deferrals[0].ref == "Glasser et al. 2013"
    assert deferral is not None and deferral.field == "base_pipeline"


def test_case_missing_name_missing_ref():
    field, deferral = _build_base_pipeline(
        FieldExtractionResult(status="missing"),
        FieldExtractionResult(status="missing"),
        "irrelevant text",
    )
    assert isinstance(field, MissingFromPaper)
    assert deferral is None


# --- 6c: value-support guard (Option A), base_pipeline only --------------------
# The guard runs on EVERY extracted base_pipeline (clean OR recovered): a span match proves the
# QUOTE is real text, not that the VALUE is in it. Recovered cases below mangle the source so the
# quote recovers via tier 5; clean cases give an exact-match source (recovered=False). Both force
# the value check.
def test_parse_attribution_ref_viduarre_and_non_attribution():
    from extractor_mvp.extractor import _parse_attribution_ref

    # viduarre-shaped: method handed to a Title-Case author, no pipeline named.
    assert (
        _parse_attribution_ref(
            "Spatial preprocessing was applied using the procedure described by Glasser et al."
        )
        == "Glasser et al."
    )
    # A quote that names a tool (not a bare citation attribution) -> None, not a fabricated ref.
    assert _parse_attribution_ref("We used fMRIPrep version 20.2.3 for preprocessing.") is None


def test_guard_recovered_value_stated_is_extracted_and_marked():
    # value STATED in the (whitespace-mangled) quote -> honest EXTRACTED + span_recovered=True.
    quote = "processed with fMRIPrep here"
    text = "we then processedwithfMRIPrephere and moved on."
    field, deferral = _build_base_pipeline(
        _extracted("fMRIPrep", quote), FieldExtractionResult(status="missing"), text
    )
    assert not isinstance(field, MissingFromPaper)
    assert field.extraction.status == "EXTRACTED"
    assert field.extraction.value.name == "fMRIPrep"
    assert field.extraction.span_recovered is True  # tolerant-tier provenance is marked
    assert deferral is None


def test_guard_recovered_viduarre_reclassified_as_deferral():
    # viduarre: value INFERRED (not in quote), quote is a bare citation attribution that recovers
    # via tier 5 -> reclassified to DEFERRED_TO_CITATION, NOT a fabricated EXTRACTED.
    quote = "preprocessing was applied using the procedure described by Glasser et al."
    text = "In methods, preprocessingwasappliedusingtheproceduredescribedbyGlasseretal. and so on."
    field, deferral = _build_base_pipeline(
        _extracted("HCP minimal preprocessing pipeline", quote),
        FieldExtractionResult(status="missing"),
        text,
    )
    assert not isinstance(field, MissingFromPaper)
    assert field.extraction.status == "DEFERRED_TO_CITATION"
    assert field.extraction.deferrals[0].ref == "Glasser et al."
    assert field.inference.reason == "citation_shaped_name_value_unsupported"
    # crucially NOT extracted: the inferred pipeline name was never promoted to a value
    assert field.extraction.status != "EXTRACTED"
    assert deferral is None  # no separate ref field -> no DeferralRecord


def test_guard_recovered_unsupported_unparseable_falls_to_bare_missing():
    # Third guard sub-case: recovered span, value NOT in the quote, AND the quote is not a bare
    # citation attribution (nothing to defer to) -> fall through to bare MissingFromPaper. Never
    # a fabricated EXTRACTED, and no invented DeferralRecord.
    value = "SPM12"
    quote = "the data were collected on a Siemens Trio scanner"
    text = "acquisition: thedatawerecollectedonaSiemensTrioscanner at the center."
    field, deferral = _build_base_pipeline(
        _extracted(value, quote), FieldExtractionResult(status="missing"), text
    )
    assert isinstance(field, MissingFromPaper)  # not EXTRACTED, not DEFERRED_TO_CITATION
    assert deferral is None


def test_guard_clean_span_unsupported_reclassified_as_deferral():
    # THE FIX (guard-scope): on a CLEAN span too — value NOT in the quote, quote a bare citation
    # attribution — the value-support guard reclassifies to DEFERRED_TO_CITATION instead of promoting
    # the inferred name to a fabricated EXTRACTED. Before the fix a clean span short-circuited the
    # guard (`(not recovered) or ...`) and this fabrication passed on 2/3 viduarre draws.
    quote = "Spatial preprocessing was applied using the procedure described by Glasser et al."
    text = (
        "In methods, " + quote + " We then computed connectivity."
    )  # clean exact -> recovered False
    field, deferral = _build_base_pipeline(
        _extracted("HCP minimal preprocessing pipeline", quote),
        FieldExtractionResult(status="missing"),
        text,
    )
    assert field.extraction.status == "DEFERRED_TO_CITATION"
    assert field.extraction.deferrals[0].ref == "Glasser et al."
    assert field.inference.reason == "citation_shaped_name_value_unsupported"
    assert deferral is None


def test_guard_clean_span_value_stated_stays_extracted():
    # No false demotion: a CLEAN span whose value IS in its quote stays EXTRACTED with
    # span_recovered=False. The unconditional guard must not demote correct clean extractions —
    # verified across the whole label set (agtzidis SPM12, chen CCS, ...); this pins the invariant.
    quote = "The fMRI data analysis was performed with SPM12 using Matlab."
    text = "Methods. " + quote + " Results follow."
    field, deferral = _build_base_pipeline(
        _extracted("SPM12", quote), FieldExtractionResult(status="missing"), text
    )
    assert not isinstance(field, MissingFromPaper)
    assert field.extraction.status == "EXTRACTED"
    assert field.extraction.value.name == "SPM12"
    assert (
        field.extraction.span_recovered is False
    )  # clean tier, and no longer skipped by the guard
    assert deferral is None


# --- 6d: live Cho 2021 full PDF Layer-1 probe ----------------------------------
MODEL = os.environ.get("EXTRACTOR_MODEL", "bedrock/us.anthropic.claude-sonnet-4-6")
CHO_PDF = Path("/Users/cwook/Documents/neurorepro/tested_lit/multi_batch/Cho_2021.pdf")


@pytest.mark.xfail(
    reason="full-PDF methods-slice dilution: §2.1.1 deferral sentence "
    "treated as attribution on 22KB slice. Fix: sub-section-aware "
    "methods slicing (backlog). Curated-section path proven in "
    "test_citation_resolver.py::test_cho_2021_defers_and_resolves_to_glasser."
)
@pytest.mark.live
def test_cho_2021_full_pdf_base_pipeline_defers_to_glasser():
    from extractor_mvp.methods_finder import find_methods_section
    from extractor_mvp.pdf_loader import load_pdf_text

    assert CHO_PDF.is_file(), f"missing fixture: {CHO_PDF}"
    text, _ = load_pdf_text(CHO_PDF)
    methods = find_methods_section(text)
    paper = ParsedPaper(text=methods.text, source="cho_2021", parser="pypdf")

    prep, _diags, deferrals = extract_preprocessing(paper, MODEL)

    bp = prep.base_pipeline
    bp_status = getattr(bp, "extraction", None) and bp.extraction.status
    bp_records = [d for d in deferrals if d.field == "base_pipeline"]
    # The base pipeline is deferred to Glasser — either the field itself is
    # DEFERRED_TO_CITATION (missing name) OR the name was extracted and a
    # base_pipeline DeferralRecord points at Glasser (extracted name + deferred ref).
    deferred_field = bp_status == "DEFERRED_TO_CITATION"
    glasser_record = any("glasser" in (d.ref_string or "").lower() for d in bp_records)
    assert deferred_field or glasser_record, (
        f"expected base_pipeline deferred to Glasser; bp_status={bp_status}, "
        f"bp_records={[(d.ref_string) for d in bp_records]}"
    )

    # Layer-2 regression: the 6 targeted fields still resolve to valid statuses.
    valid = {"EXTRACTED", "MISSING_FROM_PAPER", "DEFERRED_TO_CITATION"}
    for step in prep.steps:
        for fname in type(step).model_fields:
            if fname == "kind":
                continue
            assert getattr(step, fname).extraction.status in valid

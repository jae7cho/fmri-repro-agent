"""The two coverage calls (DESIGN_coverage_expansion.md, the author's rulings R1-R8 of 2026-10-28).

Offline: the client is the conftest stub, dispatching on response_model. Every assertion is about
the artifact -- the assembled record, the coverage predicate and the rendered report -- never about
the call graph alone.
"""

from __future__ import annotations

from typing import Any

from fmri_repro.spec.preprocessing import Preprocessing, SpatialSmoothing
from fmri_repro.spec.provenance import Extracted, NotApplicable

from conftest import stub_client
from extractor_mvp import render
from extractor_mvp.cobidas import (
    COBIDAS_D3_ROWS,
    VALIDATED_ROWS,
    assess_coverage,
    is_expanded,
    row_state,
)
from extractor_mvp.coverage_extractor import SpatialExtraction, TemporalVolumeExtraction
from extractor_mvp.coverage_fields import COVERAGE_KINDS, COVERAGE_SPECS, SPECS_BY_KIND
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    PreprocessingExtraction,
    _missing_pf,
    extract_preprocessing,
    extract_preprocessing_for_acquisition,
)
from extractor_mvp.parsed_paper import ParsedPaper

TEXT = (
    "Methods. The first 4 volumes were discarded to allow for signal equilibration. "
    "Slice-timing correction was applied with FSL slicetimer using the middle slice as reference. "
    "No spatial smoothing was applied. "
    "Images were smoothed with a 6 mm FWHM Gaussian kernel. "
    "Brain extraction used BET with a fractional intensity threshold of 0.3. "
    "The T1 image was segmented with FAST into gray matter, white matter and CSF. "
    "Functional images were coregistered to the T1 with FLIRT using boundary-based registration. "
    "Field map distortion correction used FUGUE. "
    "Bias field correction used N4. "
    "Nuisance regression removed six motion parameters, white matter and CSF signals. "
    "Volumes with FD > 0.5 mm were censored. "
    "ICA-AROMA was applied. "
    "aCompCor with 5 components was used. "
    "Preprocessing otherwise followed Glasser et al. (2013)."
)
_S = {
    "t1": "The first 4 volumes were discarded to allow for signal equilibration.",
    "stc": "Slice-timing correction was applied with FSL slicetimer using the middle slice as reference.",
    "no_smooth": "No spatial smoothing was applied.",
    "smooth": "Images were smoothed with a 6 mm FWHM Gaussian kernel.",
    "bet": "Brain extraction used BET with a fractional intensity threshold of 0.3.",
    "seg": "The T1 image was segmented with FAST into gray matter, white matter and CSF.",
    "coreg": "Functional images were coregistered to the T1 with FLIRT using boundary-based registration.",
    "dist": "Field map distortion correction used FUGUE.",
    "bias": "Bias field correction used N4.",
    "nuis": "Nuisance regression removed six motion parameters, white matter and CSF signals.",
    "scrub": "Volumes with FD > 0.5 mm were censored.",
    "ica": "ICA-AROMA was applied.",
    "compcor": "aCompCor with 5 components was used.",
    "defer": "Preprocessing otherwise followed Glasser et al. (2013).",
}


def _paper() -> ParsedPaper:
    return ParsedPaper(text=TEXT, source="t", parser="manual")


def _missing() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _ex(value: str, quote: str) -> FieldExtractionResult:
    return FieldExtractionResult(status="extracted", value=value, verbatim_quote=quote)


def _prep_payload() -> PreprocessingExtraction:
    return PreprocessingExtraction(
        target_space=_missing(),
        resolution_mm=_missing(),
        surface_registration=_missing(),
        target_surface=_missing(),
        intensity_convention=_missing(),
        intensity_value=_missing(),
    )


def _run(
    temporal: Any = None,
    spatial: Any = None,
    counter: dict | None = None,
    calls: list | None = None,
) -> Preprocessing:
    prep, _, _ = extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(), temporal=temporal, spatial=spatial, counter=counter, calls=calls
        ),
    )
    return prep


def _field(prep: Preprocessing, kind: str, name: str) -> Any:
    step = next(s for s in prep.steps if s.kind == kind)
    return getattr(step, name)


def _coverage(prep: Preprocessing) -> dict[str, Any]:
    return {rc.row.row_id: rc for rc in assess_coverage(render.flatten(prep), None)}


# ---------------------------------------------------------------------------
# The calls (R1, R8)
# ---------------------------------------------------------------------------


def test_exactly_one_of_each_of_the_four_calls_per_paper_on_the_single_acquisition_path() -> None:
    counter: dict[str, int] = {}
    calls: list[dict] = []
    _run(counter=counter, calls=calls)
    assert counter == {
        "MotionMethodExtraction": 1,
        "TemporalVolumeExtraction": 1,
        "SpatialExtraction": 1,
        "PreprocessingExtraction": 1,
    }, counter
    # the same sampling settings on every call, and the order: motion, T, S, shared
    assert [c["response_model"] for c in calls] == [
        "MotionMethodExtraction",
        "TemporalVolumeExtraction",
        "SpatialExtraction",
        "PreprocessingExtraction",
    ]
    for c in calls:
        assert c["temperature"] == 0.0 and c["max_retries"] == 2 and c["model"] == "m", c


def test_the_multi_acquisition_path_makes_none_of_the_three_extra_calls() -> None:
    counter: dict[str, int] = {}
    prep, _, _ = extract_preprocessing_for_acquisition(
        _paper(), "HCP", "HCP data", "m", client=stub_client(_prep_payload(), counter=counter)
    )
    assert counter == {"PreprocessingExtraction": 1}, counter
    # every field of the thirteen kinds is UNTARGETED there, ``performed`` included: the extractor
    # did not look, so no source-absence reason may stand (B6).
    for kind in COVERAGE_KINDS:
        for spec in SPECS_BY_KIND[kind]:
            pf = _field(prep, kind, spec.field_id)
            assert pf is not None
            assert pf.inference.reason == "not_targeted_by_mvp", (kind, spec.field_id)


def test_every_field_of_the_thirteen_kinds_is_present_on_an_assembled_record() -> None:
    """R6: fields carry states. The schema makes them optional for OLD documents; a record the
    extractor writes never leaves one absent."""
    prep = _run()
    assert [s.kind for s in prep.steps].count("temporal_filtering") == 0
    assert len(prep.steps) == 18
    for kind in COVERAGE_KINDS:
        step = next(s for s in prep.steps if s.kind == kind)
        for name in type(step).model_fields:
            if name in type(step).STRUCTURAL_FIELDS:
                continue
            assert getattr(step, name) is not None, (kind, name)
        assert type(step).model_fields and list(type(step).model_fields)[1] == "performed", kind


# ---------------------------------------------------------------------------
# The coverage mapping: each row to one kind set; a single-row run credits only that row
# ---------------------------------------------------------------------------

_ROW_TO_PERFORMED_ATTR = {
    "t1_stabilization": ("T", "t1_performed", _S["t1"]),
    "brain_extraction": ("S", "brain_extraction_performed", _S["bet"]),
    "segmentation": ("S", "segmentation_performed", _S["seg"]),
    "slice_time_correction": ("T", "stc_performed", _S["stc"]),
    "gradient_distortion_correction": ("S", "distortion_performed", _S["dist"]),
    "distortion_correction": ("S", "distortion_performed", _S["dist"]),
    "coregistration": ("S", "coregistration_performed", _S["coreg"]),
    "intensity_correction": ("S", "intensity_correction_performed", _S["bias"]),
    "artifact_structured_noise_removal": ("T", "nuisance_performed", _S["nuis"]),
    "volume_censoring": ("T", "scrub_performed", _S["scrub"]),
    "spatial_smoothing": ("S", "smoothing_performed", _S["smooth"]),
}


def test_the_eleven_rows_each_map_to_exactly_one_kind_set() -> None:
    rows = {r.row_id: r for r in COBIDAS_D3_ROWS}
    kind_sets = {rid: frozenset(rows[rid].spec_kinds) for rid in _ROW_TO_PERFORMED_ATTR}
    for rid, kinds in kind_sets.items():
        assert kinds and kinds <= set(COVERAGE_KINDS), rid
    # the one documented pair: gradient and field distortion share the folded kind (R1)
    assert kind_sets["gradient_distortion_correction"] == kind_sets["distortion_correction"]
    others = [
        k
        for rid, k in kind_sets.items()
        if rid not in ("gradient_distortion_correction", "distortion_correction")
    ]
    assert len(set(others)) == len(others)


def test_a_single_row_run_credits_only_that_row() -> None:
    for rid, (call, attr, quote) in _ROW_TO_PERFORMED_ATTR.items():
        payload = {attr: _ex("yes", quote)}
        prep = _run(
            temporal=TemporalVolumeExtraction(**payload) if call == "T" else None,
            spatial=SpatialExtraction(**payload) if call == "S" else None,
        )
        addressed = {r for r, rc in _coverage(prep).items() if rc.addressed}
        expected = {rid}
        if rid in ("gradient_distortion_correction", "distortion_correction"):
            expected = {"gradient_distortion_correction", "distortion_correction"}
        assert addressed == expected, (rid, addressed)


# ---------------------------------------------------------------------------
# performed (R2)
# ---------------------------------------------------------------------------


def test_performed_no_is_a_report_and_the_parameters_are_not_applicable() -> None:
    prep = _run(
        spatial=SpatialExtraction(
            smoothing_performed=_ex("no", _S["no_smooth"]),
            smoothing_fwhm_mm=_ex("6", _S["smooth"]),  # the model answered anyway: overridden
        )
    )
    performed = _field(prep, "spatial_smoothing", "performed")
    assert isinstance(performed.extraction, Extracted) and performed.extraction.value is False
    fwhm = _field(prep, "spatial_smoothing", "fwhm_mm")
    assert fwhm.extraction.status == "MISSING_FROM_PAPER"
    assert fwhm.inference.reason == "step_not_performed"
    cov = _coverage(prep)
    assert cov["spatial_smoothing"].addressed is True  # a stated negative is a report
    assert row_state(cov["spatial_smoothing"], render.flatten(prep)) == "performed_no"
    out = render.to_cobidas_coverage(prep)
    assert "performed=no 1" in out
    assert "- Spatial smoothing [unvalidated] — performed: no: performed = False" in out
    assert "not applicable — the paper states this step was not performed" in render.to_report(prep)
    assert "not applicable (step stated as not performed)" in render.to_report(prep)


def test_performed_yes_with_its_quote_reports_the_row_and_the_values_render() -> None:
    prep = _run(
        spatial=SpatialExtraction(
            smoothing_performed=_ex("yes", _S["smooth"]),
            smoothing_fwhm_mm=_ex("6", _S["smooth"]),
            smoothing_kernel_type=_ex("Gaussian", _S["smooth"]),
        )
    )
    kernel = _field(prep, "spatial_smoothing", "kernel_type")
    assert kernel.extraction.value.resolved == "gaussian"
    assert kernel.extraction.value.verbatim == "Gaussian"
    out = render.to_cobidas_coverage(prep)
    assert (
        '- Spatial smoothing [unvalidated] — reported: performed = True; fwhm_mm = 6.0; kernel_type = gaussian (paper: "Gaussian")'
        in out
    )
    assert "«Images were smoothed with a 6 mm FWHM Gaussian kernel.»" in out


def test_performed_deferred_defers_the_row() -> None:
    prep = _run(
        spatial=SpatialExtraction(
            coregistration_performed=FieldExtractionResult(
                status="deferred",
                deferral_sentence=_S["defer"],
                ref_string="Glasser et al. (2013)",
                target_kind="paper",
            )
        )
    )
    cov = _coverage(prep)
    assert cov["coregistration"].addressed is True
    assert row_state(cov["coregistration"], render.flatten(prep)) == "deferred"
    out = render.to_cobidas_coverage(prep)
    assert (
        "coregistration [unvalidated] — deferred: performed: deferred to Glasser et al. (2013)"
        in out
    )


# ---------------------------------------------------------------------------
# The support check by field type (R3): failures render unverifiable, never not reported
# ---------------------------------------------------------------------------


def _unverifiable(prep: Preprocessing, row_id: str, kind: str, field: str) -> None:
    pf = _field(prep, kind, field)
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason == "value_unsupported_by_quote", pf.inference.reason
    cov = _coverage(prep)
    rc = cov[row_id]
    assert (rc.addressed, rc.covered_by_extractor, rc.unverifiable) == (False, False, True)
    assert row_state(rc, render.flatten(prep)) == "unverifiable"
    out = render.to_cobidas_coverage(prep)
    assert f"{rc.row.d3_aspect} [unvalidated] — examined; the extractor could not verify" in out
    assert f"- {rc.row.d3_aspect}  (no fields assessed by current extractor)" not in out


def test_a_term_whose_alias_is_not_in_the_quote_is_unverifiable() -> None:
    prep = _run(spatial=SpatialExtraction(smoothing_kernel_type=_ex("gaussian", _S["bet"])))
    _unverifiable(prep, "spatial_smoothing", "spatial_smoothing", "kernel_type")


def test_a_number_not_in_the_quote_is_unverifiable_digit_exact() -> None:
    prep = _run(spatial=SpatialExtraction(smoothing_fwhm_mm=_ex("8", _S["smooth"])))
    _unverifiable(prep, "spatial_smoothing", "spatial_smoothing", "fwhm_mm")
    ok = _run(spatial=SpatialExtraction(smoothing_fwhm_mm=_ex("6.0", _S["smooth"])))
    assert _field(ok, "spatial_smoothing", "fwhm_mm").extraction.value == 6.0


def test_free_text_not_in_the_quote_is_unverifiable_and_in_it_is_kept() -> None:
    prep = _run(
        spatial=SpatialExtraction(
            brain_extraction_parameters=_ex("fractional intensity threshold of 0.5", _S["bet"])
        )
    )
    _unverifiable(prep, "brain_extraction", "brain_extraction", "parameters")
    ok = _run(
        spatial=SpatialExtraction(
            brain_extraction_parameters=_ex("fractional intensity threshold of 0.3", _S["bet"])
        )
    )
    assert _field(ok, "brain_extraction", "parameters").extraction.value == (
        "fractional intensity threshold of 0.3"
    )


def test_a_boolean_has_no_token_check_but_a_non_yes_no_is_unmappable() -> None:
    prep = _run(spatial=SpatialExtraction(brain_extraction_manual_edits=_ex("yes", _S["bet"])))
    assert _field(prep, "brain_extraction", "manual_edits").extraction.value is True
    bad = _run(spatial=SpatialExtraction(brain_extraction_manual_edits=_ex("maybe", _S["bet"])))
    pf = _field(bad, "brain_extraction", "manual_edits")
    assert pf.inference.reason == "value_not_boolean"
    assert "non-yes/no" in render.to_report(bad)


def test_a_term_the_table_does_not_know_stays_extracted_with_the_papers_words() -> None:
    text_quote = "Brain extraction used BET with a fractional intensity threshold of 0.3."
    prep = _run(spatial=SpatialExtraction(brain_extraction_method=_ex("BET", text_quote)))
    pf = _field(prep, "brain_extraction", "method")
    assert (pf.extraction.value.verbatim, pf.extraction.value.resolved) == ("BET", "bet")
    # an unlisted tool: kept verbatim, resolution unrecognized, still EXTRACTED (the 0.5.0 rule)
    prep2 = _run(spatial=SpatialExtraction(segmentation_method=_ex("FAST", _S["seg"])))
    assert _field(prep2, "segmentation", "method").extraction.value.resolved == "fsl_fast"
    prep3 = _run(
        spatial=SpatialExtraction(coregistration_nonlinear_transform_type=_ex("FLIRT", _S["coreg"]))
    )
    assert _field(prep3, "coregistration", "nonlinear_transform_type").extraction.value == "FLIRT"


def test_a_list_field_resolves_every_item_and_every_item_must_be_in_the_quote() -> None:
    prep = _run(
        temporal=TemporalVolumeExtraction(
            nuisance_tissue_regressors=_ex("white matter, CSF", _S["nuis"])
        )
    )
    value = _field(prep, "nuisance_regression", "tissue_regressors").extraction.value
    assert [v.resolved for v in value] == ["white_matter", "ventricles"]
    assert (
        'tissue_regressors = white_matter (paper: "white matter"), ventricles (paper: "CSF")'
        in render.to_report(prep)
    )
    bad = _run(
        temporal=TemporalVolumeExtraction(
            nuisance_tissue_regressors=_ex("white matter, global signal", _S["nuis"])
        )
    )
    _unverifiable(
        bad, "artifact_structured_noise_removal", "nuisance_regression", "tissue_regressors"
    )


def test_an_integer_field_takes_the_leading_number_and_refuses_a_fraction() -> None:
    prep = _run(temporal=TemporalVolumeExtraction(t1_n_discarded=_ex("4", _S["t1"])))
    assert (
        _field(prep, "nonsteadystate_removal", "n_nonsteadystate_discarded").extraction.value == 4
    )
    bad = _run(temporal=TemporalVolumeExtraction(compcor_n_components=_ex("5.5", _S["compcor"])))
    assert _field(bad, "compcor", "n_components").inference.reason == "value_not_numeric"


# ---------------------------------------------------------------------------
# Render (R5): the tags, the header over 14 rows, the pre-0.5.2 record unchanged
# ---------------------------------------------------------------------------


def test_the_validation_tags_name_the_three_rows_with_labels_and_no_other() -> None:
    assert VALIDATED_ROWS == {"software", "intersubject_registration", "motion_correction"}
    out = render.to_cobidas_coverage(_run())
    assert "- Software [validated against labels]" in out
    assert "- Intersubject registration [validated against labels]" in out
    assert "- Motion correction [validated against labels]" in out
    assert out.count("[validated against labels]") == 3
    assert out.count("[unvalidated]") == 11
    assert "### Rows" in out


def test_the_header_partition_sums_to_fourteen_on_an_expanded_record() -> None:
    import re

    prep = _run(
        spatial=SpatialExtraction(
            smoothing_performed=_ex("no", _S["no_smooth"]),
            brain_extraction_performed=_ex("yes", _S["bet"]),
            smoothing_kernel_type=_ex("gaussian", _S["bet"]),  # overridden: performed is no
        ),
        temporal=TemporalVolumeExtraction(stc_interpolation=_ex("sinc", _S["t1"])),  # unverifiable
    )
    out = render.to_cobidas_coverage(prep)
    assessed = int(re.search(r"Assessed by AESPA: (\d+)", out).group(1))
    not_assessed = int(re.search(r"Not assessed by AESPA: (\d+)", out).group(1))
    assert assessed + not_assessed == 14
    a = int(re.search(r"addressed (\d+)", out).group(1))
    p = int(re.search(r"performed=no (\d+)", out).group(1))
    r = int(re.search(r"not reported (\d+)", out).group(1))
    assert a + p + r == assessed
    assert p == 1 and a >= 1
    assert "targeted but unverifiable 1" in out


def test_a_record_written_before_0_5_2_renders_without_the_expanded_section() -> None:
    step = SpatialSmoothing(
        fwhm_mm=_missing_pf("fwhm_mm", float, "not_stated_in_text"),
        space=_missing_pf("space", str, "not_stated_in_text"),
        kernel_type=_missing_pf("kernel_type", str, "not_stated_in_text"),
        approach=_missing_pf("approach", str, "not_stated_in_text"),
    )
    prep = Preprocessing(applies_to=_run().applies_to, base_pipeline=NotApplicable(), steps=[step])
    assert step.performed is None and step.method is None
    assert is_expanded(prep) is False
    out = render.to_cobidas_coverage(prep)
    assert "performed=no" not in out
    assert "### Rows" not in out
    assert "[unvalidated]" not in out
    # and the record still renders and tallies
    assert "Mandatory rows: 14" in render.to_report(prep)


def test_every_spec_has_an_alias_table_only_when_it_is_a_term() -> None:
    for spec in COVERAGE_SPECS:
        assert (spec.synonyms is not None) == (spec.value_kind in ("term", "term_list")), spec.attr
        assert (spec.literal_type is not None) == (spec.value_kind in ("term", "term_list")), (
            spec.attr
        )

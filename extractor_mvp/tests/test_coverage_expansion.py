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
from extractor_mvp.coverage_extractor import (
    SPATIAL_PROMPT,
    TEMPORAL_VOLUME_PROMPT,
    SpatialExtraction,
    TemporalVolumeExtraction,
)
from extractor_mvp.coverage_fields import (
    COVERAGE_KINDS,
    COVERAGE_SPECS,
    PERFORMED_PHRASES,
    SPECS_BY_KIND,
)
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
    "Preprocessing otherwise followed Glasser et al. (2013). "
    "Linear and quadratic trends were removed from the time series. "
    "Distortion correction for magnetic field inhomogeneities used a field map. "
    "Nuisance regressors included 24 movement regressors derived by Volterra expansion."
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
    "trends": "Linear and quadratic trends were removed from the time series.",
    "inhomo": "Distortion correction for magnetic field inhomogeneities used a field map.",
    "volterra": "Nuisance regressors included 24 movement regressors derived by Volterra expansion.",
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


def test_performed_is_never_deferred_but_a_parameter_may_be() -> None:
    """The never-deferred rule is a POST-CHECK, never a reask (the author's ruling of 2026-10-29;
    the 2026-10-28 validator cost ciric_2017 its whole report in coverage_v2). A deferred
    ``performed`` constructs, each call is made exactly once, and the field is coerced to
    MissingFromPaper ``performed_cannot_defer`` with the deferral kept as a diagnostic and NOT
    routed to the citation resolver. A deferred parameter still defers the row."""
    deferred = FieldExtractionResult(
        status="deferred",
        deferral_sentence=_S["defer"],
        ref_string="Glasser et al. (2013)",
        target_kind="paper",
    )
    # the reask path cannot return: the response models accept the answer as given
    SpatialExtraction(coregistration_performed=deferred)
    TemporalVolumeExtraction(scrub_performed=deferred)
    counter: dict[str, int] = {}
    prep, diags, deferrals = extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            spatial=SpatialExtraction(coregistration_performed=deferred),
            counter=counter,
        ),
    )
    assert counter["SpatialExtraction"] == 1 and counter["TemporalVolumeExtraction"] == 1
    pf = _field(prep, "coregistration", "performed")
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason == "performed_cannot_defer"
    assert any(
        d.failure_reason == "performed_cannot_defer" and d.field == "coregistration.performed"
        for d in diags
    )
    assert not any(d.field == "coregistration.performed" for d in deferrals)
    rc = _coverage(prep)["coregistration"]
    assert (rc.addressed, rc.unverifiable) == (False, True)
    out = render.to_report(prep)
    assert "the extractor was given a citation instead of whether this step was performed" in out
    # a deferred PARAMETER still defers the row
    prep2 = _run(spatial=SpatialExtraction(coregistration_method=deferred))
    cov = _coverage(prep2)
    assert cov["coregistration"].addressed is True
    assert row_state(cov["coregistration"], render.flatten(prep2)) == "deferred"
    rule = 'performed` is NEVER "deferred"'
    assert rule in SPATIAL_PROMPT and rule in TEMPORAL_VOLUME_PROMPT


def test_a_performed_quote_must_name_its_step() -> None:
    """Item 2: the boolean's quote must carry a phrase from the step's frozen list; chen's
    slice-timing ``performed`` quoting the de-spiking sentence is the observed case."""
    ok = _run(spatial=SpatialExtraction(smoothing_performed=_ex("yes", _S["smooth"])))
    assert _field(ok, "spatial_smoothing", "performed").extraction.value is True
    bad = _run(spatial=SpatialExtraction(smoothing_performed=_ex("yes", _S["bet"])))
    _unverifiable(bad, "spatial_smoothing", "spatial_smoothing", "performed")
    # a stated negative is checked the same way: the sentence must be about the step
    neg = _run(spatial=SpatialExtraction(smoothing_performed=_ex("no", _S["no_smooth"])))
    assert _field(neg, "spatial_smoothing", "performed").extraction.value is False
    # the other booleans keep no token check
    other = _run(spatial=SpatialExtraction(brain_extraction_manual_edits=_ex("yes", _S["smooth"])))
    assert _field(other, "brain_extraction", "manual_edits").extraction.value is True
    assert set(PERFORMED_PHRASES) == set(COVERAGE_KINDS)


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


# ---------------------------------------------------------------------------
# Item 3 (2026-10-28): the alias fixes
# ---------------------------------------------------------------------------


def test_underscore_space_and_hyphen_are_one_separator_in_alias_matching() -> None:
    prep = _run(
        spatial=SpatialExtraction(
            segmentation_tissue_classes=_ex(
                "gray_matter, white-matter, cerebrospinal_fluid", _S["seg"]
            )
        )
    )
    items = _field(prep, "segmentation", "tissue_classes").extraction.value
    assert [i.resolved for i in items] == ["gray_matter", "white_matter", "csf"]
    prep2 = _run(
        spatial=SpatialExtraction(coregistration_cost_function=_ex("boundary_based", _S["coreg"]))
    )
    assert (
        _field(prep2, "coregistration", "cost_function").extraction.value.resolved
        == "boundary_based"
    )


def test_magnetic_field_inhomogeneities_resolve_to_a_susceptibility_fieldmap() -> None:
    prep = _run(
        spatial=SpatialExtraction(
            distortion_source=_ex("magnetic field inhomogeneities", _S["inhomo"])
        )
    )
    terms = _field(prep, "distortion_correction", "source").extraction.value
    assert [(t.resolved, t.resolution) for t in terms] == [("susceptibility_fieldmap", "resolved")]


def test_a_listed_field_holds_every_source_the_paper_states() -> None:
    """report v2 §1b (2026-10-29): Gracia-Tabuenca corrects susceptibility AND gradient
    nonlinearity; the distortion source holds both, each item support-checked."""
    quote = "Distortion correction for magnetic field inhomogeneities used a field map."
    two = "fMRI volumes were corrected for susceptibility distortion and gradient nonlinearity distortions."
    paper = ParsedPaper(text=TEXT + " " + two, source="t", parser="manual")
    prep, _, _ = extract_preprocessing(
        paper,
        "m",
        client=stub_client(
            _prep_payload(),
            spatial=SpatialExtraction(
                distortion_source=_ex("susceptibility, gradient nonlinearity", two)
            ),
        ),
    )
    terms = _field(prep, "distortion_correction", "source").extraction.value
    assert [t.resolved for t in terms] == ["susceptibility_fieldmap", "gradient_nonlinearity"]
    bad, _, _ = extract_preprocessing(
        paper,
        "m",
        client=stub_client(
            _prep_payload(),
            spatial=SpatialExtraction(
                distortion_source=_ex("susceptibility, gradient nonlinearity", quote)
            ),
        ),
    )
    assert (
        _field(bad, "distortion_correction", "source").inference.reason
        == "value_unsupported_by_quote"
    )


def test_volterra_resolves_to_friston24() -> None:
    prep = _run(
        temporal=TemporalVolumeExtraction(
            nuisance_motion_expansion=_ex("Volterra expansion", _S["volterra"])
        )
    )
    term = _field(prep, "nuisance_regression", "motion_expansion").extraction.value
    assert (term.verbatim, term.resolved) == ("Volterra expansion", "friston24")


def test_detrend_takes_the_highest_order_the_quote_names() -> None:
    prep, diags, _ = extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            temporal=TemporalVolumeExtraction(nuisance_detrend=_ex("linear", _S["trends"])),
        ),
    )
    term = _field(prep, "nuisance_regression", "detrend").extraction.value
    assert (term.verbatim, term.resolved) == ("linear", "quadratic")
    assert any(d.failure_reason == "detrend_highest_order_named:linear->quadratic" for d in diags)
    # already the highest: untouched, no diagnostic
    prep2, diags2, _ = extract_preprocessing(
        _paper(),
        "m",
        client=stub_client(
            _prep_payload(),
            temporal=TemporalVolumeExtraction(nuisance_detrend=_ex("quadratic", _S["trends"])),
        ),
    )
    assert _field(prep2, "nuisance_regression", "detrend").extraction.value.resolved == "quadratic"
    assert not any(d.failure_reason.startswith("detrend_highest") for d in diags2)


# ---------------------------------------------------------------------------
# Item 4 (2026-10-28): coregistration method = the tool; the cost function has its own vocabulary
# ---------------------------------------------------------------------------


def test_bbr_is_a_cost_function_not_a_method() -> None:
    prep = _run(
        spatial=SpatialExtraction(
            coregistration_method=_ex("boundary-based registration", _S["coreg"]),
            coregistration_cost_function=_ex("bbr", _S["coreg"]),
        )
    )
    # the cost-function phrase no longer resolves as a METHOD: kept verbatim, unrecognized
    method = _field(prep, "coregistration", "method").extraction.value
    assert (method.resolved, method.resolution) == (None, "unrecognized")
    assert method.verbatim == "boundary-based registration"
    cost = _field(prep, "coregistration", "cost_function").extraction.value
    assert cost.resolved == "boundary_based"
    tool = _run(spatial=SpatialExtraction(coregistration_method=_ex("FLIRT", _S["coreg"])))
    assert _field(tool, "coregistration", "method").extraction.value.resolved == "flirt"
    assert "canonical bbr, mutual_information, correlation_ratio, other" in SPATIAL_PROMPT
    assert "A cost function is\n  NOT a tool" in SPATIAL_PROMPT


# ---------------------------------------------------------------------------
# Item 6 (2026-10-28): kind-prefixed fields on rows with sibling kinds
# ---------------------------------------------------------------------------


def test_rows_with_sibling_kinds_name_the_kind_on_each_field() -> None:
    prep = _run(
        temporal=TemporalVolumeExtraction(
            ica_performed=_ex("yes", _S["ica"]),
            compcor_performed=_ex("yes", _S["compcor"]),
            compcor_n_components=_ex("5", _S["compcor"]),
            despike_performed=_ex("no", "No spatial smoothing was applied."),  # unverifiable
            scrub_performed=_ex("yes", _S["scrub"]),
        ),
        spatial=SpatialExtraction(smoothing_performed=_ex("yes", _S["smooth"])),
    )
    out = render.to_cobidas_coverage(prep)
    assert (
        "Artifact and structured noise removal [unvalidated] — reported: ica_denoise.performed = True; "
        "compcor.performed = True; compcor.n_components = 5" in out
    )
    assert "Volume censoring [unvalidated] — reported: scrub.performed = True" in out
    # a one-kind row stays bare
    assert "Spatial smoothing [unvalidated] — reported: performed = True" in out
    assert "spatial_smoothing.performed" not in out


# ---------------------------------------------------------------------------
# Item 5 (2026-10-28): multiple_pipelines on both calls, a header line on the steps section
# ---------------------------------------------------------------------------

_VARIANTS = (
    "Two preprocessing variants (n = 2) were compared: with and without global signal regression."
)


def _run_with_record(temporal: Any = None, spatial: Any = None) -> tuple[Any, dict | None, str]:
    text = TEXT + " " + _VARIANTS
    paper = ParsedPaper(text=text, source="t", parser="manual")
    coverage_out: list[Any] = []
    prep, _, _ = extract_preprocessing(
        paper,
        "m",
        client=stub_client(_prep_payload(), temporal=temporal, spatial=spatial),
        coverage_out=coverage_out,
    )
    dump = coverage_out[0].multiple_pipelines_dump() if coverage_out else None
    return prep, dump, render.to_report(prep, source="t", multiple_pipelines=dump)


def test_both_calls_carry_the_record_level_fields_and_a_yes_renders_a_header() -> None:
    for model in (TemporalVolumeExtraction, SpatialExtraction):
        assert {"multiple_pipelines", "pipeline_variant_count"} <= set(model.model_fields)
    prep, dump, out = _run_with_record(
        temporal=TemporalVolumeExtraction(
            multiple_pipelines=_ex("yes", _VARIANTS), pipeline_variant_count=_ex("2", _VARIANTS)
        )
    )
    assert dump is not None
    assert dump["T"]["multiple_pipelines"]["extraction"]["status"] == "EXTRACTED"
    assert dump["T"]["multiple_pipelines"]["extraction"]["value"] is True
    assert dump["T"]["pipeline_variant_count"]["extraction"]["value"] == 2
    assert dump["S"]["multiple_pipelines"]["extraction"]["status"] == "MISSING_FROM_PAPER"
    head = out.split("### 1.")[0]
    assert "> ⚠ More than one preprocessing variant is described — call T: yes, count 2" in head
    assert "«Two preprocessing variants (n = 2) were compared" in head
    assert "call S" not in head
    # the record-level answers are not step fields: no step carries them
    assert all("multiple_pipelines" not in type(s).model_fields for s in prep.steps)


def test_no_variant_answer_renders_no_header_and_a_count_not_in_its_quote_is_dropped() -> None:
    _, dump, out = _run_with_record()
    assert dump is not None and "⚠ More than one" not in out
    assert (
        render.to_report(_run().__class__ and _run(), source="t", multiple_pipelines=None).count(
            "⚠ More"
        )
        == 0
    )
    _, dump2, out2 = _run_with_record(
        spatial=SpatialExtraction(
            multiple_pipelines=_ex("yes", _VARIANTS), pipeline_variant_count=_ex("3", _VARIANTS)
        )
    )
    assert dump2["S"]["pipeline_variant_count"]["extraction"]["status"] == "MISSING_FROM_PAPER"
    assert "call S: yes, count not stated" in out2


def test_the_rerender_script_passes_the_stored_answers_through(tmp_path: Any) -> None:
    import json
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(render.__file__).parents[2] / "scripts"))
    from rerender_reports import _render_one

    prep, dump, _out = _run_with_record(
        temporal=TemporalVolumeExtraction(multiple_pipelines=_ex("yes", _VARIANTS))
    )
    stored = {
        "paper_id": "t",
        "methods": {
            "found_via": "header_match",
            "matched_header": "Methods",
            "start_offset": 0,
            "end_offset": 10,
            "slice_ratio": 0.5,
            "ended_at": None,
            "suspicious": False,
        },
        "preprocessing": prep.model_dump(mode="json"),
        "multiple_pipelines": dump,
    }
    f = tmp_path / "t.json"
    f.write_text(json.dumps(stored))
    assert "⚠ More than one preprocessing variant" in _render_one(f)
    stored.pop("multiple_pipelines")
    f.write_text(json.dumps(stored))
    assert "⚠ More than one preprocessing variant" not in _render_one(f)


# ---------------------------------------------------------------------------
# 2026-10-29: the value-support check reads the REPAIRED text when the span carries tier-6 repairs
# ---------------------------------------------------------------------------

_POLDRACK_EXCERPT = "and spectral ﬁltering 45. Frames with framewise displacement 40.25 mm\nwere censored, as well as"


def test_a_number_is_checked_on_the_repaired_text_when_the_span_was_repaired() -> None:
    """poldrack: the text layer prints ">0.25" as "40.25". The span resolves through tier 6 (>→4);
    the number check must read ">0.25", not "40.25", or the threshold fails on a correct value."""
    quote = "Frames with framewise displacement >0.25 mm were censored"
    paper = ParsedPaper(text=_POLDRACK_EXCERPT, source="t", parser="manual")
    prep, _, _ = extract_preprocessing(
        paper,
        "m",
        client=stub_client(
            _prep_payload(),
            temporal=TemporalVolumeExtraction(scrub_threshold=_ex("0.25", quote)),
        ),
    )
    pf = _field(prep, "scrub", "threshold")
    assert pf.extraction.status == "EXTRACTED", pf.inference
    assert pf.extraction.value == 0.25
    assert pf.extraction.spans[0].repairs == [">→4"]
    # and a number that is NOT in the repaired quote still fails: the switch reads the quote, it
    # does not loosen the check
    bad, _, _ = extract_preprocessing(
        paper,
        "m",
        client=stub_client(
            _prep_payload(),
            temporal=TemporalVolumeExtraction(scrub_threshold=_ex("40.25", quote)),
        ),
    )
    assert _field(bad, "scrub", "threshold").inference.reason == "value_unsupported_by_quote"


# ---------------------------------------------------------------------------
# report v2 step 2 (2026-10-29): software_mentions and the rebuilt Software row
# ---------------------------------------------------------------------------

_SW_TEXT = (
    "Cortical surfaces were reconstructed with FreeSurfer v5.3. "
    "The data were mapped to a common space using BioImage Suite software. "
    "Statistics were computed in R version 4.1.0."
)


def _run_sw(mentions: list[Any]) -> Preprocessing:
    from extractor_mvp.coverage_extractor import SoftwareMentionResult

    paper = ParsedPaper(text=_SW_TEXT, source="t", parser="manual")
    prep, _, _ = extract_preprocessing(
        paper,
        "m",
        client=stub_client(
            _prep_payload(),
            spatial=SpatialExtraction(
                software_mentions=[SoftwareMentionResult(**m) for m in mentions]
            ),
        ),
    )
    return prep


_FS = {
    "name": "FreeSurfer",
    "version": "5.3",
    "used_for": "Cortical surfaces were reconstructed",
    "verbatim_quote": "Cortical surfaces were reconstructed with FreeSurfer v5.3.",
}
_BIS = {
    "name": "BioImage Suite",
    "verbatim_quote": "The data were mapped to a common space using BioImage Suite software.",
}
_R = {
    "name": "R",
    "version": "4.1.0",
    "verbatim_quote": "Statistics were computed in R version 4.1.0.",
}


def test_some_software_without_a_version_is_partially_reported_and_named() -> None:
    prep = _run_sw([_FS, _BIS])
    assert [pf.extraction.value.name for pf in prep.software_mentions] == [
        "FreeSurfer",
        "BioImage Suite",
    ]
    rc = _coverage_with_mentions(prep)["software"]
    assert (rc.addressed, rc.partial, rc.covered_by_extractor) == (False, True, True)
    out = render.to_cobidas_coverage(prep)
    assert "partially reported 1" in out
    assert (
        "- Software [validated against labels] — partially reported: FreeSurfer 5.3 — Cortical surfaces were reconstructed; BioImage Suite (no version)"
        in out
    )
    assert (
        "Software named without a version: BioImage Suite. Named with a version: FreeSurfer 5.3."
        in out
    )


def test_every_software_versioned_addresses_the_row() -> None:
    rc = _coverage_with_mentions(_run_sw([_FS, _R]))["software"]
    assert (rc.addressed, rc.partial) == (True, False)


def test_a_version_not_in_the_quote_makes_the_mention_unverifiable() -> None:
    bad = dict(_FS, version="6.0")
    prep = _run_sw([bad])
    pf = prep.software_mentions[0]
    assert pf.extraction.status == "MISSING_FROM_PAPER"
    assert pf.inference.reason == "value_unsupported_by_quote"
    rc = _coverage_with_mentions(prep)["software"]
    assert (rc.addressed, rc.covered_by_extractor, rc.unverifiable) == (False, False, True)


def test_a_used_for_not_in_the_quote_is_dropped_and_the_mention_kept() -> None:
    prep = _run_sw([dict(_FS, used_for="tissue segmentation")])
    v = prep.software_mentions[0].extraction.value
    assert (v.name, v.version, v.used_for) == ("FreeSurfer", "5.3", None)


def _coverage_with_mentions(prep: Preprocessing) -> dict[str, Any]:
    rows = render.flatten(prep)
    return {rc.row.row_id: rc for rc in assess_coverage(rows, None, prep.software_mentions)}

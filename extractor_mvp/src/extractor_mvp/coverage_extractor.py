"""The two coverage calls: the eleven mandatory D.3 rows the extractor never examined before.

``docs/design/DESIGN_coverage_expansion.md`` -- the author's rulings R1-R8 of 2026-10-28. Two
model-facing prompts, each with its own pinned hash (``tests/test_prompt_pin.py``): call T
(temporal/volume: T1 stabilization, slice time correction, volume censoring, artifact and
structured noise removal) and call S (spatial: brain extraction, segmentation, coregistration,
distortion correction with gradient distortion folded in, intensity correction, spatial
smoothing). Both run on the SAME slice as the motion and the shared call, with the same model,
temperature and ``max_retries``, on the single-acquisition path only.

Every field is a three-state ``FieldExtractionResult`` and goes through ``_process_field`` (the one
span path), with the coercion and the value-support check picked by the field's value kind
(``coverage_fields``). ``performed`` comes first on every step (R2): a stated negative is EXTRACTED
``False`` with its quote, and the step's parameters are then ``step_not_performed``.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from fmri_repro.spec.preprocessing import Detrend, SpecifiedTerm
from fmri_repro.spec.provenance import Extracted, ProvenancedField
from pydantic import BaseModel, Field

from extractor_mvp.coverage_fields import (
    CALL_S_SPECS,
    CALL_T_SPECS,
    COVERAGE_KINDS,
    DETREND,
    RECORD_SPECS,
    SPECS_BY_KIND,
    CoverageFieldSpec,
)
from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.extractor import (
    DeferralRecord,
    ExtractionDiagnostic,
    _extracted_pf,
    _process_field,
    _step_not_performed_pf,
    build_client,
)
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.quote_support import phrase_in_quote

_SHARED_RULES = """\
## How every step is handled

For EACH step below, decide `<step>_performed` FIRST:
- "extracted" with value "yes" when the text states the step was done; verbatim_quote = the
  sentence that says so. "extracted" with value "no" when the text states the step was NOT done
  ("no slice-timing correction was applied", "data were not smoothed"); verbatim_quote = the
  sentence stating that. A stated negative is a report.
- "missing" when the text is silent about the step, AND when the text says the step -- or the
  preprocessing as a whole -- followed a cited publication or a named pipeline without stating
  anything itself about the step. `<step>_performed` is NEVER "deferred": a deferral is not a
  statement that the step was performed. In that case the step's PARAMETER fields are "deferred":
  deferral_sentence = that sentence; ref_string = the citation or the pipeline name as written;
  target_kind = "pipeline" for a named pipeline, else "paper".

The quote for `<step>_performed` must be the sentence that names THIS step (the slice-timing
sentence for slice timing, the smoothing sentence for smoothing); a sentence about a different step
does not support it and is discarded.

The step's parameter fields are asked ONLY when `<step>_performed` is "yes" or unstated:
- performed "no" -> every parameter field of that step is "missing".
- performed "yes" or "missing" -> a parameter the text states in its own words is "extracted";
  one it does not state is "missing"; one it attributes to a citation or a named pipeline
  without stating it is "deferred" (same rule as above).

FIREWALL: extract only what the paper STATES. Do NOT infer a tool, a value or whether a step was
performed from a pipeline's identity (fMRIPrep, HCP, CCS, C-PAC, ...), from a lab's conventions,
or from your own knowledge of what a package does by default. If the paper names a pipeline and
says nothing about a step, that step is "missing" (or "deferred" when the text defers to the
pipeline). A software PACKAGE named for the analysis as a whole (SPM, FSL, AFNI) is not a
statement that any particular step was performed.

Typed fields: use the canonical value when the paper's term maps to one; otherwise return the
paper's term VERBATIM. Numbers as strings, digits as the paper writes them ("0.5", "6", "3").
Yes/no fields: exactly "yes" or "no". List fields: the items separated by commas, canonical where
they map, verbatim otherwise.

The value must be stated IN the verbatim_quote: quote the sentence that carries it, not a nearby
one. verbatim_quote and deferral_sentence are copied EXACTLY from the text, character for
character; a field whose quote cannot be found is discarded.
"""

_RECORD_RULES = """\
## More than one preprocessing variant (a record-level question, asked once per call)
multiple_pipelines: "yes" if the methods text describes MORE THAN ONE preprocessing variant for
  the functional data -- two pipelines compared, a main pipeline and an alternative, different
  preprocessing for different datasets or analyses; verbatim_quote = the sentence that introduces
  the alternative. "missing" when one preprocessing is described. Never "no" and never
  "deferred".
pipeline_variant_count: when multiple_pipelines is "yes", the number of variants described, as an
  integer string, quoting the sentence that lets it be counted; "missing" otherwise.

"""

_OUTPUT_STATUS = """\
## Output status for each field

"extracted": the paper states a value for this field.
  - value: the value as a string; verbatim_quote: the exact sentence(s), copied verbatim.
"missing": the paper does not state it (or the step is performed "no").
  - value: null, verbatim_quote: null; searched_terms and sections_searched as you looked.
"deferred": the paper says this detail is described in another source (a citation or a named
  pipeline), and states nothing itself.
  - deferral_sentence: that sentence verbatim; ref_string: the citation or pipeline name as
    written; target_kind: "paper" / "pipeline" / "dataset_doc" / "supplement".

CRITICAL: when uncertain, use "missing", not "deferred". Each field is independent. Do not apply
"deferred" to every field because one field is deferred.

Text:
\"\"\"
{text}
\"\"\"
"""

TEMPORAL_VOLUME_PROMPT = (
    """\
You are extracting four COBIDAS D.3 preprocessing rows from an fMRI methods text: T1
stabilization, slice time correction, volume censoring, and artifact and structured noise removal.
Read the methods text below; nothing comes from anywhere else.

"""
    + _SHARED_RULES
    + """
## T1 stabilization (nonsteadystate_removal)
D.3 asks: "Number of initial 'dummy' scans discarded as part of preprocessing (if not already
performed by scanner)."
t1_performed: were initial volumes discarded IN PREPROCESSING (not by the scanner)?
t1_n_discarded: the number of initial volumes discarded, as an integer string ("4"). Scanner
  dummies ("the first 4 volumes were discarded by the scanner") are NOT this field -> missing.

## Slice time correction (slice_time_correction)
D.3 asks: name of software/method; whether performed after or before motion correction; the
reference slice; interpolation type and order.
stc_performed: was slice-timing correction applied?
stc_method: the software/tool named FOR this step. Canonical: fsl_slicetimer, spm_slice_timing,
  afni_3dtshift, other. A package named for the whole analysis is NOT this field.
stc_relative_to_motion_correction: canonical before, after (relative to motion correction).
stc_reference: canonical first, middle, specific_slice, specific_time (a reference time such as
  the middle of the TR is specific_time).
stc_interpolation: canonical linear, spline, sinc.
stc_interpolation_order: the order as an integer string ("3" for "3rd order spline").

## Volume censoring (despike, scrub)
D.3 asks: "Remediation of problem scans, also known as 'scrubbing' or 'de-spiking'": name of
software/method; criteria (frame-by-frame displacement threshold, percentage BOLD change); use of
censoring or interpolation; if interpolation, the method.
Two kinds, each with its own performed:
despike_performed: was per-voxel spike removal (de-spiking, e.g. AFNI 3dDespike) applied?
despike_method: canonical afni_3dDespike, other.  despike_threshold: the number stated.
scrub_performed: were motion-contaminated VOLUMES removed or interpolated (scrubbing, censoring,
  motion censoring)? Regressing motion parameters is NOT censoring; excluding whole SUBJECTS or
  RUNS by a motion criterion is NOT censoring (that is a subject exclusion rule) -> missing.
scrub_method: the tool named for the censoring. Canonical afni_3dtproject, fsl_motion_outliers,
  custom (an in-house implementation the text describes), other.
scrub_criterion: canonical fd_power (framewise displacement, Power), fd_jenkinson (RMS relative
  displacement, Jenkinson), dvars, bold_pct (percentage BOLD change); the paper's term verbatim
  otherwise.
scrub_threshold: the threshold number as written ("0.5" for "FD > 0.5 mm"); the quote carries the
  unit.
scrub_remediation: canonical censor (volumes removed, scrubbed, excluded) or interpolate.
scrub_interpolation_method: canonical spline, spectral, other -- only when interpolated.

## Artifact and structured noise removal (ica_denoise, compcor, nuisance_regression)
D.3 asks: "Use of physiological noise correction method. Name of software/method used (e.g.
CompCor, ICA-FIX, ICA-AROMA). If using a nuisance regression method, specify regressors used; for
each type: motion parameters (expansion basis and order); tissue signals (tissue type, tissue
definition, signal definition); physiological signals (modeling choices, number of regressors)."
Three kinds, each with its own performed:
ica_performed: was ICA-based denoising (ICA-FIX, ICA-AROMA, or another ICA cleanup) applied?
ica_method: canonical fix, aroma; verbatim otherwise.  ica_training_set: the FIX training set as
  named.  ica_threshold: the classifier threshold number.  ica_aggressive: "yes" if the aggressive
  variant, "no" if non-aggressive, missing if not stated.
compcor_performed: was CompCor (anatomical or temporal) applied?
compcor_variant: canonical a (aCompCor), t (tCompCor).  compcor_n_components: the number of
  components as an integer string.  compcor_variance_threshold: the variance fraction/percentage
  as written.  compcor_mask_source: how the noise mask was defined, the paper's words.
nuisance_performed: were nuisance signals REGRESSED from the time series (motion parameters,
  tissue signals, global signal, physiological regressors)? ICA cleanup alone is NOT this field.
nuisance_method: the tool named for the regression. Canonical afni_3dtproject, afni_3dbandpass,
  afni_3ddeconvolve, fsl_regfilt, spm, nilearn, custom, other.
nuisance_regressor_list: the regressors AS THE PAPER LISTS THEM, copied from the text (for example
  "six motion parameters, white matter, CSF and global signal").
nuisance_motion_expansion: canonical none (no motion regressors), 6param (the six parameters),
  friston24 (24-parameter: the six, their derivatives and squares), volterra; verbatim otherwise.
nuisance_tissue_regressors: a comma-separated list from whole_brain (global signal), gray_matter,
  white_matter, ventricles (CSF); verbatim items otherwise.
nuisance_tissue_definition: how the tissue masks were defined (a priori seed, automatic
  segmentation, eroded masks, ...), the paper's words.
nuisance_tissue_signal_definition: how the signal was computed (mean of voxels, first singular
  vector / principal component, ...), the paper's words.
nuisance_physio_regressors: canonical retroicor, rvt, none; verbatim otherwise.
nuisance_physio_n_regressors: the number of physiological regressors as an integer string.
nuisance_detrend: canonical linear, quadratic, none; verbatim otherwise.
nuisance_filtering_integrated: "yes" if temporal filtering was applied WITHIN the same regression
  (simultaneously, e.g. AFNI 3dTproject), "no" if as a separate step, missing if not stated.

"""
    + _RECORD_RULES
    + _OUTPUT_STATUS
)

SPATIAL_PROMPT = (
    """\
You are extracting six COBIDAS D.3 preprocessing rows from an fMRI methods text: brain
extraction, segmentation, function-structure (intra-subject) coregistration, distortion correction
(field or gradient nonlinearity), intensity correction, and spatial smoothing. Read the methods
text below; nothing comes from anywhere else.

"""
    + _SHARED_RULES
    + """
## Brain extraction (brain_extraction)
D.3 asks: name of software/method (BET, recon-all, ...); parameter choices (BET's fractional
intensity threshold); any manual editing applied to the brain masks.
brain_extraction_performed: was skull-stripping / brain extraction applied?
brain_extraction_method: canonical bet, afni_3dskullstrip, freesurfer_recon_all, ants, synthstrip,
  other; verbatim otherwise.
brain_extraction_parameters: the parameter choices stated, the paper's words ("fractional
  intensity threshold of 0.3").
brain_extraction_manual_edits: "yes" if the masks were manually edited, "no" if the text says they
  were not, missing if not stated.

## Segmentation (segmentation)
D.3 asks: "For structural images, method used to extract gray, white, CSF and other tissue
classes."
segmentation_performed: was the structural image segmented into tissue classes?
segmentation_method: canonical fsl_fast, spm_segment, freesurfer_recon_all, ants_atropos, other.
segmentation_tissue_classes: a comma-separated list from gray_matter, white_matter, csf.

## Function-structure (intra-subject) coregistration (coregistration)
D.3 asks: name of software/method; type of transformation (rigid, nonlinear; if nonlinear, its
type); cost function; interpolation method. This is the EPI-to-T1 (functional-to-structural)
registration of the same subject -- NOT registration to a template or atlas (a different row),
NOT between-volume motion correction.
coregistration_performed: was the functional image registered to the subject's structural image?
coregistration_method: the TOOL that performed the registration (FLIRT, bbregister, SPM
  Coregister, ANTs, ...): canonical flirt, bbregister, spm_coreg, ants, other. A cost function is
  NOT a tool: "boundary-based registration (BBR)" is the cost function below, and the method is
  the tool it ran in, if the text names one; otherwise the method is missing.
coregistration_transform: canonical rigid, affine, nonlinear.
coregistration_nonlinear_transform_type: when nonlinear, its type, the paper's words.
coregistration_cost_function: canonical bbr, mutual_information, correlation_ratio, other;
  verbatim otherwise.
coregistration_interpolation: canonical linear, spline, sinc, other.

## Distortion correction (distortion_correction) -- field AND gradient nonlinearity
D.3 asks: "Use of any distortion correction due to field or gradient nonlinearity"; gradient
distortion correction is reported here too.
distortion_performed: was any distortion correction applied (field-map based, fieldmap-less, or
  gradient-nonlinearity unwarping)?
distortion_source: canonical susceptibility_fieldmap (a field map / phase difference / spin-echo
  pair), gradient_nonlinearity (gradient distortion), fieldmap_less (SyN-based or similar).
distortion_method: canonical topup, fugue, gradunwarp, sdc_fieldmapless, other; verbatim
  otherwise.

## Intensity correction (intensity_correction)
D.3 asks: "Bias field corrections for structural MRI, but also correction of odd versus even
slice intensity differences attributable to interleaved EPI acquisition without gaps."
intensity_correction_performed: was a bias-field (intensity inhomogeneity) correction or an
  odd/even slice intensity correction applied? Grand-mean / intensity NORMALIZATION (scaling the
  time series to a target mean) is NOT this row -> missing.
intensity_correction_target: canonical bias_field, interleaved_slice.
intensity_correction_method: canonical n4, fast_bias, other; verbatim otherwise.

## Spatial smoothing (spatial_smoothing)
D.3 asks: name of software/method; size and type of smoothing kernel; filtering approach (fixed
kernel or iterative smoothing until a fixed FWHM); the space in which smoothing is performed.
smoothing_performed: was spatial smoothing applied? A statement that the data were NOT smoothed
  is performed "no".
smoothing_method: the tool named for the smoothing. Canonical fsl_susan, fsl_fslmaths,
  spm_smooth, afni_3dmerge, afni_3dblurtofwhm, workbench, other.
smoothing_fwhm_mm: the kernel FWHM in mm as a number string ("6").
smoothing_kernel_type: canonical gaussian, other.
smoothing_approach: canonical fixed_kernel, iterate_to_fwhm.
smoothing_space: canonical native_volume, native_surface, mni_volume, template_surface.

"""
    + _RECORD_RULES
    + _OUTPUT_STATUS
)


def _missing_field() -> FieldExtractionResult:
    return FieldExtractionResult(status="missing")


def _no_deferred_performed(model: BaseModel) -> BaseModel:
    """``performed`` is never deferred (the author's item 2, 2026-10-28): a deferral is not a
    statement that the step was performed. A violation is a validation error -- under instructor,
    a reask -- never a silent coercion."""
    for name in type(model).model_fields:
        if name.endswith("_performed") and getattr(model, name).status == "deferred":
            raise ValueError(
                f"{name}: performed is never 'deferred' -- use 'missing' when the text defers the "
                "step and states nothing itself; defer the step's parameter fields instead"
            )
    return model


def _response_model(name: str, specs: tuple[CoverageFieldSpec, ...]) -> type[BaseModel]:
    """One ``FieldExtractionResult`` per spec, defaulted to missing so a stub may omit any; the
    never-deferred rule on every ``performed`` field."""
    from pydantic import create_model, model_validator

    fields: dict[str, Any] = {
        spec.attr: (FieldExtractionResult, Field(default_factory=_missing_field))
        for spec in specs + RECORD_SPECS
    }
    validators: dict[str, Any] = {
        "_no_deferred_performed": model_validator(mode="after")(_no_deferred_performed)
    }
    return create_model(name, __validators__=validators, **fields)


#: The LLM output schemas of the two calls, built from the field table so the two cannot drift.
TemporalVolumeExtraction: type[BaseModel] = _response_model(
    "TemporalVolumeExtraction", CALL_T_SPECS
)
SpatialExtraction: type[BaseModel] = _response_model("SpatialExtraction", CALL_S_SPECS)


@dataclasses.dataclass
class CoverageExtraction:
    """The two calls' processed fields by kind and bare id, with their diagnostics and deferrals;
    ``record`` holds the record-level answers by call ("T" / "S") -- item 5's
    ``multiple_pipelines`` and ``pipeline_variant_count``."""

    fields: dict[str, dict[str, ProvenancedField]]
    diagnostics: list[ExtractionDiagnostic]
    deferrals: list[DeferralRecord]
    record: dict[str, dict[str, ProvenancedField]] = dataclasses.field(default_factory=dict)

    def multiple_pipelines_dump(self) -> dict[str, dict[str, Any]]:
        """The record-level answers as plain dicts, the shape the batch stores and the renderer reads."""
        return {
            call: {name: pf.model_dump(mode="json") for name, pf in fields.items()}
            for call, fields in self.record.items()
        }


def _call(
    client: Any, model: str, prompt: str, response_model: type[BaseModel], text: str
) -> BaseModel:
    result: BaseModel = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt.format(text=text)}],
        response_model=response_model,
        temperature=0.0,
        max_retries=2,
    )
    return result


def _process(
    extraction: BaseModel,
    specs: tuple[CoverageFieldSpec, ...],
    text: str,
    out: CoverageExtraction,
) -> None:
    for spec in specs:
        fe: FieldExtractionResult = getattr(extraction, spec.attr)
        pf, diag, deferral = _process_field(
            spec.field_id,
            spec.dotted,
            fe,
            spec.literal_type,
            spec.t,
            text,
            None,
            use_synonym_table=False,
            value_kind=spec.value_kind,
            synonyms=(spec.synonyms, spec.underspecified) if spec.synonyms is not None else None,
        )
        out.fields.setdefault(spec.kind, {})[spec.field_id] = pf
        if diag is not None:
            out.diagnostics.append(diag)
        if deferral is not None:
            out.deferrals.append(deferral)


#: The detrend orders, lowest to highest (the author's item 3, 2026-10-28): the field takes the
#: HIGHEST order the quoted sentence names, whatever single order the model returned.
_DETREND_ORDER: tuple[str, ...] = ("none", "linear", "quadratic")
DETREND_HIGHEST_ORDER = "detrend_highest_order_named"


def _apply_detrend_highest_order(out: CoverageExtraction) -> None:
    """``nuisance_regression.detrend``: when the located quote names a higher order than the value
    resolved to ("linear or quadratic trends" with value "linear"), the resolved member becomes the
    highest order named; the paper's words stay as verbatim; a diagnostic records the move."""
    pf = out.fields.get("nuisance_regression", {}).get("detrend")
    if pf is None or not isinstance(pf.extraction, Extracted):
        return
    term = pf.extraction.value
    quote = pf.extraction.spans[0].text
    named = [
        member
        for member in _DETREND_ORDER
        if any(phrase_in_quote(alias, quote) for alias in DETREND.get(member, ()))
    ]
    if not named:
        return
    highest = max(named, key=_DETREND_ORDER.index)
    current = getattr(term, "resolved", None)
    if current is not None and _DETREND_ORDER.index(current) >= _DETREND_ORDER.index(highest):
        return
    out.fields["nuisance_regression"]["detrend"] = _extracted_pf(
        "detrend",
        SpecifiedTerm[Detrend],
        SpecifiedTerm(verbatim=term.verbatim, resolved=highest, resolution="resolved"),
        pf.extraction.spans[0],
        pf.extraction.span_recovered,
    )
    out.diagnostics.append(
        ExtractionDiagnostic(
            "nuisance_regression.detrend",
            f"{DETREND_HIGHEST_ORDER}:{current}->{highest}",
            term.verbatim,
            quote,
        )
    )


def _process_record(extraction: BaseModel, call: str, text: str, out: CoverageExtraction) -> None:
    """Item 5: the two record-level fields of one call, through the same span path."""
    for spec in RECORD_SPECS:
        fe: FieldExtractionResult = getattr(extraction, spec.attr)
        pf, diag, deferral = _process_field(
            spec.field_id,
            f"record.{spec.field_id}",
            fe,
            None,
            spec.t,
            text,
            None,
            use_synonym_table=False,
            value_kind=spec.value_kind,
        )
        out.record.setdefault(call, {})[spec.field_id] = pf
        if diag is not None:
            out.diagnostics.append(diag)
        if deferral is not None:
            out.deferrals.append(deferral)


def _apply_not_performed(out: CoverageExtraction) -> None:
    """R2: when a kind's ``performed`` is EXTRACTED ``False``, its parameters are
    ``step_not_performed`` whatever the model returned for them."""
    for kind in COVERAGE_KINDS:
        fields = out.fields.get(kind, {})
        performed = fields.get("performed")
        if performed is None or not isinstance(performed.extraction, Extracted):
            continue
        if performed.extraction.value is not False:
            continue
        for spec in SPECS_BY_KIND[kind]:
            if spec.field_id == "performed":
                continue
            fields[spec.field_id] = _step_not_performed_pf(spec.field_id, spec.t)


def extract_coverage(
    parsed_paper: ParsedPaper,
    model: str,
    *,
    client: Any | None = None,
    raw_out: list[BaseModel] | None = None,
) -> CoverageExtraction:
    """Two ``create()`` calls per paper -- call T then call S -- on the SAME slice as the main call.

    Same model, temperature and ``max_retries`` as the other two calls; the same
    ``_process_field`` span path, so the gap reasons are the standard ones plus the two this build
    adds (``step_not_performed``, ``value_not_boolean``). ``raw_out`` captures the two raw
    responses in order, for a recorder.
    """
    client = client or build_client()
    out = CoverageExtraction(fields={}, diagnostics=[], deferrals=[])
    temporal = _call(
        client, model, TEMPORAL_VOLUME_PROMPT, TemporalVolumeExtraction, parsed_paper.text
    )
    spatial = _call(client, model, SPATIAL_PROMPT, SpatialExtraction, parsed_paper.text)
    if raw_out is not None:
        raw_out.extend([temporal, spatial])
    _process(temporal, CALL_T_SPECS, parsed_paper.text, out)
    _process(spatial, CALL_S_SPECS, parsed_paper.text, out)
    _process_record(temporal, "T", parsed_paper.text, out)
    _process_record(spatial, "S", parsed_paper.text, out)
    _apply_not_performed(out)
    _apply_detrend_highest_order(out)
    return out

"""Single-pass preprocessing extraction: text -> span-grounded ProvenancedField.

One LLM call per ``Preprocessing`` block returns ``(value, verbatim_quote)`` per
field; the quote is resolved to a char-offset ``Span`` Python-side, so a span
literally contains its value (Tier-1-consistent by construction). A field is
``Extracted`` only when its value validates AND its quote resolves; otherwise it
is ``MissingFromPaper`` with the reason recorded on the ``LeftMissing`` inference
arm and (for non-trivial failures) in the diagnostics list.

Spec note: ``MissingFromPaper`` carries ``searched_terms`` / ``sections_searched``
(no ``reason`` field), so the per-field reason string lives on the coupled
``LeftMissing(reason=...)`` inference arm. ``bandpass`` is intentionally omitted
for the MVP (Position-A "no step" semantics; post-abstract).

``litellm`` / ``instructor`` are imported lazily in :func:`build_client`.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import date

    from fmri_repro.spec.provenance import InferredDefault

    from extractor_mvp.citation_resolver import CitationResolver

from fmri_repro.spec.preprocessing import (
    IntensityNormalization,
    IntensityNormalizationConvention,
    PipelineRef,
    Preprocessing,
    SpatialNormalization,
    SurfaceProjection,
    SurfaceRegistration,
    TargetSpace,
    TargetSurface,
)
from fmri_repro.spec.provenance import (
    Deferral,
    DeferredToCitation,
    Extracted,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
)
from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef
from pydantic import BaseModel, Field

from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.span_resolver import resolve_quote
from extractor_mvp.synonym_resolver import SYNONYMS_BY_FIELD, resolve_to_literal


def _coerce_float(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


_CONFIDENCE = 0.8  # placeholder for MVP; calibration is post-abstract


class PreprocessingExtraction(BaseModel):
    """LLM output schema for one ``Preprocessing`` block.

    Each field is a three-state :class:`FieldExtractionResult`
    (extracted / missing / deferred); see ``extraction_result.py``.
    """

    target_space: FieldExtractionResult
    resolution_mm: FieldExtractionResult
    surface_registration: FieldExtractionResult
    target_surface: FieldExtractionResult
    intensity_convention: FieldExtractionResult
    intensity_value: FieldExtractionResult
    # bandpass intentionally skipped for MVP (see module docstring).

    # Layer 1: base preprocessing pipeline (new). Defaulted to status="missing" so
    # pre-existing fixtures that omit them still construct; the Layer-1 prompt directs
    # the LLM to populate them on real extractions.
    base_pipeline_name: FieldExtractionResult = Field(
        default_factory=lambda: FieldExtractionResult(status="missing")
    )  # e.g. "fMRIPrep", "HCP minimal preprocessing"
    base_pipeline_ref: FieldExtractionResult = Field(
        default_factory=lambda: FieldExtractionResult(status="missing")
    )  # deferred to "Glasser et al. 2013", or extracted attribution


EXTRACTION_PROMPT = """\
You are extracting preprocessing parameters from an fMRI methods text. For EACH
field below, decide its status (see "Output status for each field") and fill in
the corresponding fields.

For typed fields, use the canonical name when the paper uses it (e.g.,
MNI152NLin6Asym, msm_sulc). If the paper uses a different term, return the
paper's term verbatim. For numeric fields, return the number as a string.

Do not infer values from the named pipeline. Do not fill in defaults you might
know.

## Layer 1: Base preprocessing pipeline

base_pipeline_name: The name of the base preprocessing pipeline the paper used.
  Examples: "fMRIPrep", "HCP minimal preprocessing pipeline", "CCS pipeline",
            "ABCD processing pipeline", "SPM12"
  status="extracted": pipeline is named anywhere in the methods text.
    value = the pipeline name as written; verbatim_quote = the sentence naming it.
  status="missing": no base pipeline is named.

base_pipeline_ref: The citation the paper gives for the base pipeline.
  status="deferred": the paper says preprocessing DETAILS are in another publication.
    Use ONLY when you can quote a sentence like:
      "preprocessing followed Glasser et al. (2013)"
      "see Esteban et al. (2019) for full preprocessing details"
      "data were processed as described in [citation]"
    deferral_sentence = that exact sentence verbatim; ref_string = the citation.
  status="extracted": the paper names a tool and cites its paper as attribution only —
    the paper itself then states the parameters used.
    Example: "We used fMRIPrep v20.2.3 (Esteban et al., 2019)" followed by the paper
    describing its own parameters. value = the citation string.
  status="missing": no pipeline citation appears.

CRITICAL: status="deferred" means preprocessing DETAILS are outsourced to the cited
paper. If the paper describes its own parameters after naming a tool, use "extracted".

## Layer 2: Investigator-added preprocessing

These fields capture preprocessing steps the AUTHORS added beyond the base pipeline.
Look for language like "additionally", "further processed", "we applied", "we smoothed".
If the paper only states a base pipeline and defers all details, these fields are missing.

## Layer 2 field definitions

For the six targeted Layer-2 fields below, apply these scoped definitions. Use the
canonical value when the paper's term maps to one; otherwise return the paper's term
verbatim (see the typed-field rule above).

target_space: The standard/atlas space the functional data were normalized to.
Canonical values: MNI152NLin6Asym, MNI152NLin2009cAsym, Talairach, native_volume, other.
  extracted: "registered to MNI152NLin6Asym" -> value=MNI152NLin6Asym
  If the paper names a space without a precise variant, return its term verbatim
  (e.g. bare "MNI" or "MNI152" with no NLin variant -> return that term).
  missing: data analyzed only in subject/native functional space, no atlas target.

resolution_mm: The isotropic voxel size of the functional data IN ATLAS SPACE after
spatial normalization, measured in mm. Extract ONLY when the paper states this in the
context of normalization, resampling, or registration to a standard/atlas space.

status="extracted" examples:
  "resampled in atlas space on an isotropic 3 mm grid" -> value=3.0
  "normalized to MNI space and resampled to 3x3x3mm voxels" -> value=3.0
  "resampled at the 3x3x3mm3 resolution of the MNI normalized brain space" -> value=3.0
    (the "of the MNI/normalized brain space" clause is the atlas-space cue -- extract)

status="missing" -- do NOT extract for any of the following:
  - Acquisition voxel size from scanner parameters:
    "FOV = 192x192mm; resolution = 3x3x3mm" -> missing (this is acquisition, not preprocessing)
    "voxel size = 2mm; multiband factor = 8" -> missing (acquisition, not normalization)
  - ROI sphere or searchlight radii:
    "mean time series in 5-mm spheres" -> missing (sphere radius, not voxel resolution)
    "within 6-mm spheres around coordinates" -> missing
  - Template construction resolution:
    "study-specific template generated from 120 subjects" -> missing (template building)
  - Structural/anatomical image resolution

If the paper only describes acquisition parameters and does not state the resolution
after normalization, use status="missing".

surface_registration: The surface registration approach aligning each subject's cortical
surface to a template. Canonical values: freesurfer_recon, msm_sulc, msm_all, other.
  extracted: "surfaces aligned with MSMAll" -> value=msm_all
  missing: volume-only analysis, no surface registration step described.

target_surface: The surface template to which volume data were projected.
Canonical values: native, fsaverage, fsaverage5, fsaverage6, fsLR_32k, fsLR_164k, other.
  extracted: "data were mapped to the fsLR 32k surface" -> value=fsLR_32k
  missing: no surface projection -- data kept in volume space only.

intensity_convention: The global/grand-mean intensity normalization convention applied
to the 4D BOLD series. Canonical values: spm_grand_mean_100, fsl_grand_mean_10000,
fsl_median_10000, voxel_temporal_zscore, global_median_1000, global_mode_1000, other.
  extracted: "scaled each run to a grand mean of 10000" -> value=fsl_grand_mean_10000
  missing: no intensity scaling/normalization of the time series is described.

intensity_value: The target intensity magnitude after normalization (the number, e.g.
1000 or 10000). Null for z-score conventions, which have no target magnitude.
  extracted: "grand mean scaling to 10000" -> value=10000
  missing: no intensity normalization stated, OR a z-score convention (no target value).

## Output status for each field

For each field output exactly one of three statuses:

"extracted": The paper explicitly states a value for this field.
  - value: the extracted value as a string
  - verbatim_quote: copy the exact sentence(s) from the paper verbatim. Do not paraphrase.

"missing": The paper does not state a value for this field.
  - value: null, verbatim_quote: null
  - searched_terms: terms you looked for
  - sections_searched: section headers you checked

"deferred": The paper explicitly says preprocessing details are described in another source.
  Use ONLY when the paper contains a sentence you can quote verbatim such as:
    "Preprocessing followed the procedures in Glasser et al. (2013)"
    "Data were processed as described in [citation]"
    "See Smith et al. (2013) for full preprocessing details"
  - deferral_sentence: copy that sentence verbatim from the paper
  - ref_string: the citation exactly as written in the text, e.g. "Glasser et al. 2013"
  - target_kind: "paper" for external publications, "pipeline" for named pipelines
    (e.g. "HCP minimal preprocessing pipeline"), "dataset_doc" for dataset
    documentation, "supplement" for the same paper's supplementary materials
  - searched_terms and sections_searched as above

CRITICAL: When uncertain, use "missing" not "deferred". A field is "deferred" only
when you can quote a verbatim sentence pointing to another source. If the paper
simply does not mention a field, that is "missing".

CRITICAL: Each field is independent. A paper can have target_space="extracted",
smoothing_fwhm="deferred", and intensity_normalization="missing" simultaneously.
Do not apply "deferred" to all fields because one field is deferred.

Text:
\"\"\"
{text}
\"\"\"
"""


@dataclass(frozen=True)
class ExtractionDiagnostic:
    field: str
    failure_reason: str
    raw_value: object | None
    raw_quote: str | None


@dataclass(frozen=True)
class DeferralRecord:
    """A resolved DEFERRED_TO_CITATION field, surfaced for Fork B (citation
    resolution) without it having to parse the provenance coupling.

    ``target_kind`` is the ORIGINAL LLM value, including ``"supplement"`` (which
    the frozen ``provenance.Deferral`` cannot hold — it is mapped to ``"paper"``
    on the provenance arm but preserved verbatim here)."""

    field: str  # dotted path, e.g. "spatial_normalization.target_space"
    ref_string: str
    target_kind: str
    deferral_sentence: str
    pending_resolution: bool = True


# (LLM attr, bare step field_id, dotted path for reports, literal type | None, generic T).
# The bare field_id MUST equal the step model's attribute name (a step invariant);
# the dotted path is only for diagnostics / the summary. Note the intensity LLM
# attrs map to the step's "convention" / "value" fields.
_FIELD_SPECS: list[tuple[str, str, str, Any, Any]] = [
    (
        "target_space",
        "target_space",
        "spatial_normalization.target_space",
        TargetSpace,
        TargetSpace,
    ),
    ("resolution_mm", "resolution_mm", "spatial_normalization.resolution_mm", None, float),
    (
        "surface_registration",
        "surface_registration",
        "surface_projection.surface_registration",
        SurfaceRegistration,
        SurfaceRegistration,
    ),
    (
        "target_surface",
        "target_surface",
        "surface_projection.target_surface",
        TargetSurface,
        TargetSurface,
    ),
    (
        "intensity_convention",
        "convention",
        "intensity_normalization.convention",
        IntensityNormalizationConvention,
        IntensityNormalizationConvention,
    ),
    ("intensity_value", "value", "intensity_normalization.value", None, float),
]


def build_client() -> Any:
    """Instructor-wrapped LiteLLM client in JSON mode (Bedrock-portable)."""
    import instructor
    from litellm import completion

    return instructor.from_litellm(completion, mode=instructor.Mode.JSON)


def _missing_pf(field_id: str, t: Any, reason: str) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[field_id], sections_searched=["full_text"]),
        inference=LeftMissing(reason=reason),
    )


def _extracted_pf(field_id: str, t: Any, value: Any, span: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=Extracted[t](value=value, spans=[span], confidence=_CONFIDENCE),
        inference=NotApplicable(),
    )


def _deferred_pf(
    field_id: str, t: Any, deferral: Deferral, fe: FieldExtractionResult
) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=DeferredToCitation(
            deferrals=[deferral],
            searched_terms=fe.searched_terms,
            sections_searched=fe.sections_searched,
        ),
        # ProvenancedField rejects NOT_APPLICABLE on the DEFERRED arm; LEFT_MISSING
        # mirrors MissingFromPaper until Fork B resolves the citation.
        inference=LeftMissing(reason="deferred_to_citation"),
    )


def _process_field(
    field_id: str,
    dotted: str,
    fe: FieldExtractionResult,
    literal_type: Any,
    t: Any,
    text: str,
    value_context: float | None = None,
) -> tuple[ProvenancedField, ExtractionDiagnostic | None, DeferralRecord | None]:
    """Turn one LLM FieldExtractionResult into a ProvenancedField.

    Returns ``(provenanced_field, optional diagnostic, optional deferral record)``.
    ``field_id`` is the bare step attribute name (a step invariant); ``dotted`` is
    the human-readable path used for diagnostics and the deferral record. For
    Literal-typed fields the LLM's free text is first run through the synonym
    resolver (precision-only: underspecified terms stay unresolved →
    ``value_not_in_literal``).
    """
    if fe.status == "missing":
        return _missing_pf(field_id, t, "not_stated_in_text"), None, None

    if fe.status == "deferred":
        return _process_deferred(field_id, dotted, fe, t, text)

    # fe.status == "extracted" — value validated, then quote resolved to a span.
    # The extracted arm guarantees both are set (enforce_status_constraints);
    # guard with a raise (not assert) so -O keeps it and value narrows to str.
    if fe.value is None or fe.verbatim_quote is None:
        raise ValueError("extracted FieldExtractionResult must set value and verbatim_quote")
    if literal_type is not None:
        synonyms_entry = SYNONYMS_BY_FIELD.get(field_id)
        if synonyms_entry is not None:
            syns, under = synonyms_entry
            res = resolve_to_literal(str(fe.value), syns, under, value_context)
            if res.status == "resolved":
                value: Any = res.resolved
            elif fe.value in typing.get_args(literal_type):
                value = fe.value  # LLM emitted an exact member already (e.g. "other")
            else:
                reason = f"value_not_in_literal:{res.status}"
                if res.matched_alias:
                    reason += f"[{res.matched_alias}]"
                return (
                    _missing_pf(field_id, t, "value_not_in_literal"),
                    ExtractionDiagnostic(dotted, reason, fe.value, fe.verbatim_quote),
                    None,
                )
        elif fe.value not in typing.get_args(literal_type):
            return (
                _missing_pf(field_id, t, "value_not_in_literal"),
                ExtractionDiagnostic(dotted, "value_not_in_literal", fe.value, fe.verbatim_quote),
                None,
            )
        else:
            value = fe.value
    else:
        try:
            value = float(fe.value)
        except (TypeError, ValueError):
            return (
                _missing_pf(field_id, t, "value_not_numeric"),
                ExtractionDiagnostic(dotted, "value_not_numeric", fe.value, fe.verbatim_quote),
                None,
            )

    if not fe.verbatim_quote:
        return (
            _missing_pf(field_id, t, "extraction_quote_missing"),
            ExtractionDiagnostic(dotted, "extraction_quote_missing", fe.value, fe.verbatim_quote),
            None,
        )

    resolution = resolve_quote(fe.verbatim_quote, text)
    if resolution.span is None:
        return (
            _missing_pf(field_id, t, f"extraction_quote_unresolved:{resolution.failure_reason}"),
            ExtractionDiagnostic(
                dotted,
                f"extraction_quote_unresolved:{resolution.failure_reason}",
                fe.value,
                fe.verbatim_quote,
            ),
            None,
        )

    return _extracted_pf(field_id, t, value, resolution.span), None, None


def _process_deferred(
    field_id: str, dotted: str, fe: FieldExtractionResult, t: Any, text: str
) -> tuple[ProvenancedField, ExtractionDiagnostic | None, DeferralRecord | None]:
    """Resolve a DEFERRED field's sentence to a span and build the DEFERRED arm.

    If the deferral sentence cannot be located verbatim, fall back to
    MissingFromPaper with a ``deferral_quote_unresolved`` diagnostic — the same
    treatment as an unresolvable extraction quote.
    """
    # The deferred arm of FieldExtractionResult guarantees these are set
    # (enforce_status_constraints); guard with a raise (not assert) so -O keeps it.
    if fe.deferral_sentence is None or fe.ref_string is None:
        raise ValueError("deferred FieldExtractionResult must set deferral_sentence and ref_string")
    resolution = resolve_quote(fe.deferral_sentence, text)
    if resolution.span is None:
        reason = f"deferral_quote_unresolved:{resolution.failure_reason}"
        return (
            _missing_pf(field_id, t, reason),
            ExtractionDiagnostic(dotted, reason, fe.ref_string, fe.deferral_sentence),
            None,
        )

    # provenance.Deferral.target_kind does not include "supplement" (FROZEN). Map
    # to "paper" for schema validity; the original is preserved in the
    # DeferralRecord so Fork B can skip supplement targets at resolution time.
    deferral_target_kind = "paper" if fe.target_kind == "supplement" else fe.target_kind
    deferral = Deferral(ref=fe.ref_string, span=resolution.span, target_kind=deferral_target_kind)
    record = DeferralRecord(
        field=dotted,
        ref_string=fe.ref_string,
        target_kind=fe.target_kind,
        deferral_sentence=fe.deferral_sentence,
    )
    return _deferred_pf(field_id, t, deferral, fe), None, record


def _build_base_pipeline(
    name_result: FieldExtractionResult,
    ref_result: FieldExtractionResult,
    text: str,
) -> tuple[ProvenancedField[PipelineRef] | MissingFromPaper, DeferralRecord | None]:
    """Assemble Preprocessing.base_pipeline from the two Layer-1 extraction results.

    Returns ``(field_or_bare_missing, optional DeferralRecord)`` — the record can't
    ride the field's return type, so it's a second tuple element (cf. _process_field).

    Four cases:
      (extracted name, extracted ref)  -> Extracted(PipelineRef(name=name))
                                          ref is attribution only; version LEFT_MISSING
      (extracted name, deferred ref)   -> Extracted(PipelineRef(name=name)) +
                                          DeferralRecord for Fork B on the ref
      (missing name,   deferred ref)   -> DeferredToCitation on the pipeline itself
      (missing name,   missing/extracted ref) -> MissingFromPaper (bare)
    """
    bp_id = "base_pipeline"
    # version is never paper-stated here; deferred to the KB inference path.
    version_pf: ProvenancedField[str] = ProvenancedField[str](
        field_id="base_pipeline.version",
        extraction=MissingFromPaper(searched_terms=[], sections_searched=[]),
        inference=LeftMissing(reason="version_deferred_to_kb"),
    )

    # Resolve a deferred ref once (with full narrowing so mypy is happy).
    ref_span = None
    ref_record: DeferralRecord | None = None
    deferred_pipeline_field: ProvenancedField[PipelineRef] | None = None
    if ref_result.status == "deferred" and ref_result.ref_string and ref_result.deferral_sentence:
        ref_string = ref_result.ref_string
        ref_sentence = ref_result.deferral_sentence
        ref_span = resolve_quote(ref_sentence, text).span
        if ref_span is not None:
            ref_record = DeferralRecord(
                field=bp_id,
                ref_string=ref_string,
                target_kind=ref_result.target_kind,
                deferral_sentence=ref_sentence,
            )
            # provenance.Deferral.target_kind has no "supplement" (FROZEN) -> map to "paper".
            tk = "paper" if ref_result.target_kind == "supplement" else ref_result.target_kind
            deferred_pipeline_field = ProvenancedField[PipelineRef](
                field_id=bp_id,
                extraction=DeferredToCitation(
                    deferrals=[Deferral(ref=ref_string, span=ref_span, target_kind=tk)],
                    searched_terms=ref_result.searched_terms,
                    sections_searched=ref_result.sections_searched,
                ),
                inference=LeftMissing(reason="deferred_to_citation"),
            )

    # Case A/B: pipeline NAME is extracted and its quote resolves -> base_pipeline EXTRACTED.
    if name_result.status == "extracted" and name_result.value and name_result.verbatim_quote:
        name_span = resolve_quote(name_result.verbatim_quote, text).span
        if name_span is not None:
            pipeline = PipelineRef(name=name_result.value, version=version_pf)
            field: ProvenancedField[PipelineRef] = ProvenancedField[PipelineRef](
                field_id=bp_id,
                extraction=Extracted[PipelineRef](
                    value=pipeline, spans=[name_span], confidence=_CONFIDENCE
                ),
                inference=NotApplicable(),
            )
            return field, ref_record  # ref deferral (if any) handed to Fork B

    # Case C: name not (validly) extracted but ref deferred & resolved -> pipeline DEFERRED.
    if deferred_pipeline_field is not None:
        return deferred_pipeline_field, ref_record

    # Case D: both missing (or unresolved) -> bare MissingFromPaper; caller wraps it.
    return (
        MissingFromPaper(
            searched_terms=name_result.searched_terms or ["base pipeline"],
            sections_searched=name_result.sections_searched or ["full_text"],
        ),
        None,
    )


def _assemble(
    pf: dict[str, ProvenancedField],
    base_pipeline: ProvenancedField[PipelineRef] | MissingFromPaper,
) -> Preprocessing:
    """Wrap the extracted/missing fields into a schema-valid Preprocessing block.

    Fields the MVP does not target are present as MissingFromPaper so each step
    validates. ``base_pipeline`` comes from :func:`_build_base_pipeline`; a bare
    MissingFromPaper is wrapped here into the required ProvenancedField coupling.
    """
    # field_id MUST be the bare step attribute name (step invariant).
    untargeted = "not_targeted_by_mvp"
    spatial = SpatialNormalization(
        target_space=pf["target_space"],
        resolution_mm=pf["resolution_mm"],
        method=_missing_pf("method", str, untargeted),
        warp=_missing_pf("warp", str, untargeted),
        transform_type=_missing_pf("transform_type", str, untargeted),
        interpolation=_missing_pf("interpolation", str, untargeted),
        regularization=_missing_pf("regularization", str, untargeted),
    )
    surface = SurfaceProjection(
        target_surface=pf["target_surface"],
        surface_registration=pf["surface_registration"],
        vol2surf_sampling=_missing_pf("vol2surf_sampling", str, untargeted),
        cifti=_missing_pf("cifti", str, untargeted),
    )
    intensity = IntensityNormalization(
        convention=pf["intensity_convention"],
        value=pf["intensity_value"],
        scope=_missing_pf("scope", str, untargeted),
    )
    if isinstance(base_pipeline, MissingFromPaper):
        base_pipeline_field: ProvenancedField[PipelineRef] = ProvenancedField[PipelineRef](
            field_id="base_pipeline",
            extraction=base_pipeline,
            inference=LeftMissing(reason="no_base_pipeline_named"),
        )
    else:
        base_pipeline_field = base_pipeline
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=base_pipeline_field,
        steps=[spatial, surface, intensity],
    )


# Fork C: per-acquisition scope prefix prepended to the v3 extraction prompt.
PER_ACQUISITION_EXTRACTION_PROMPT = (
    """\
You are extracting preprocessing parameters for ONE specific acquisition from
a paper that may describe multiple datasets or cohorts.

The acquisition you are extracting for is named: "{paper_name}".
This acquisition is introduced in the text near: "{characterizing_quote}".

Focus on preprocessing steps that apply to THIS acquisition. If the paper
describes preprocessing that applies to all datasets generally (e.g., "all
datasets were preprocessed with fMRIPrep"), you may still extract that for
this acquisition — shared values will be detected automatically.

If a preprocessing step is described only for a different acquisition (e.g.,
"the HCP data, but not ABCD, was projected to fsLR"), do NOT extract that
value for this acquisition — use status="missing" for that field.

"""
    + EXTRACTION_PROMPT
)


def _extract_from_prompt(
    parsed_paper: ParsedPaper, model: str, prompt_text: str, client: Any | None
) -> tuple[Preprocessing, list[ExtractionDiagnostic], list[DeferralRecord]]:
    """Run one LLM extraction call + the shared post-processing pipeline."""
    client = client or build_client()
    extraction: PreprocessingExtraction = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt_text}],
        response_model=PreprocessingExtraction,
        temperature=0.0,
        max_retries=2,
    )

    # intensity_convention is disambiguated by the sibling intensity_value number
    # (e.g. "mode" + 1000 -> global_mode_1000; "mode" + 10000 -> no match).
    intensity_value_ctx = _coerce_float(extraction.intensity_value.value)

    pf: dict[str, ProvenancedField] = {}
    diagnostics: list[ExtractionDiagnostic] = []
    deferrals: list[DeferralRecord] = []
    for attr, field_id, dotted, literal_type, t in _FIELD_SPECS:
        value_context = intensity_value_ctx if field_id == "convention" else None
        field_pf, diag, deferral = _process_field(
            field_id,
            dotted,
            getattr(extraction, attr),
            literal_type,
            t,
            parsed_paper.text,
            value_context,
        )
        pf[attr] = field_pf
        if diag is not None:
            diagnostics.append(diag)
        if deferral is not None:
            deferrals.append(deferral)

    # Layer 1: base preprocessing pipeline (name + optional citation/deferral).
    base_pipeline, bp_deferral = _build_base_pipeline(
        extraction.base_pipeline_name, extraction.base_pipeline_ref, parsed_paper.text
    )
    if bp_deferral is not None:
        deferrals.append(bp_deferral)

    return _assemble(pf, base_pipeline), diagnostics, deferrals


def extract_preprocessing(
    parsed_paper: ParsedPaper, model: str, *, client: Any | None = None
) -> tuple[Preprocessing, list[ExtractionDiagnostic], list[DeferralRecord]]:
    """Single-pass extraction -> (Preprocessing, diagnostics, deferral records)."""
    return _extract_from_prompt(
        parsed_paper, model, EXTRACTION_PROMPT.format(text=parsed_paper.text), client
    )


def extract_preprocessing_for_acquisition(
    parsed_paper: ParsedPaper,
    paper_name: str,
    characterizing_quote: str,
    model: str,
    *,
    client: Any | None = None,
) -> tuple[Preprocessing, list[ExtractionDiagnostic], list[DeferralRecord]]:
    """Pass 2 (Fork C): extract preprocessing scoped to one named acquisition."""
    prompt = PER_ACQUISITION_EXTRACTION_PROMPT.format(
        paper_name=paper_name,
        characterizing_quote=characterizing_quote,
        text=parsed_paper.text,
    )
    return _extract_from_prompt(parsed_paper, model, prompt, client)


def _apply_resolved_citations(
    preprocessing: Preprocessing, resolved: dict[str, InferredDefault]
) -> Preprocessing:
    """Return a NEW Preprocessing with resolved fields' inference arm upgraded.

    For each field whose dotted path is in ``resolved`` and whose extraction arm is
    NOT EXTRACTED — ``DEFERRED_TO_CITATION`` (per-field path) or ``MISSING_FROM_PAPER``
    (base-pipeline expansion) — rebuild the ProvenancedField: the extraction arm is
    kept UNCHANGED and only the inference arm upgrades (LeftMissing -> InferredDefault).
    EXTRACTED fields are never touched (couple_stages forbids EXTRACTED + INFERRED_DEFAULT).
    Rebuilding via the model constructor re-runs the coupling validator. Never mutates in place.
    """
    if not resolved:
        return preprocessing
    new_steps = []
    for step in preprocessing.steps:
        updates: dict[str, Any] = {}
        for fname in type(step).model_fields:
            if fname == "kind":
                continue
            pf = getattr(step, fname)
            inferred = resolved.get(f"{step.kind}.{pf.field_id}")
            if inferred is not None and pf.extraction.status != "EXTRACTED":
                updates[fname] = type(pf)(
                    field_id=pf.field_id,
                    extraction=pf.extraction,  # unchanged
                    inference=inferred,  # LeftMissing -> InferredDefault
                )
        new_steps.append(step.model_copy(update=updates) if updates else step)
    updated: Preprocessing = preprocessing.model_copy(update={"steps": new_steps})
    return updated


# The six targeted Layer-2 step fields (bare field_id). Filler fields are always
# LEFT_MISSING ("not_targeted_by_mvp"), so the routing gate must look only at these.
_LAYER2_FIELD_IDS: frozenset[str] = frozenset(
    {
        "target_space",
        "resolution_mm",
        "surface_registration",
        "target_surface",
        "convention",
        "value",
    }
)


def _any_step_fields_left_missing(preprocessing: Preprocessing) -> bool:
    """True if any of the six targeted Layer-2 fields still have LEFT_MISSING inference."""
    for step in preprocessing.steps:
        for fname in type(step).model_fields:
            if fname == "kind":
                continue
            pf = getattr(step, fname)
            if pf.field_id in _LAYER2_FIELD_IDS and pf.inference.status == "LEFT_MISSING":
                return True
    return False


def _resolve_deferrals(
    preprocessing: Preprocessing,
    deferral_records: list[DeferralRecord],
    *,
    paper_date: date | None,
    citation_resolver: CitationResolver | None,
) -> Preprocessing:
    """Apply one-hop deferral resolution to a single Preprocessing.

    (2) Per-field deferrals -> citation resolver (PriorPublicationBasis).
    (3) Base-pipeline deferral -> KB path (recognized pipelines at VersionDefaultBasis
        when ``paper_date`` is known) then the citation fallback for the step fields the
        KB leaves open. Shared by :func:`extract` and the multi-acquisition runner.
    """
    per_field = [d for d in deferral_records if d.field != "base_pipeline"]
    if citation_resolver is not None and per_field:
        preprocessing = _apply_resolved_citations(
            preprocessing, citation_resolver.resolve_all(per_field)
        )

    base_pipeline = [d for d in deferral_records if d.field == "base_pipeline"]
    if base_pipeline:
        if paper_date is not None:
            # Configurator helpers; imported lazily so the KB stays an optional dep.
            from fmri_repro.kb_client.base_pipeline import (
                fill_dependent_defaults,
                infer_base_pipeline_version,
            )

            preprocessing = infer_base_pipeline_version(preprocessing, paper_date)
            preprocessing = fill_dependent_defaults(preprocessing, paper_date)

        if citation_resolver is not None and _any_step_fields_left_missing(preprocessing):
            resolved = citation_resolver.resolve_base_pipeline_deferral(
                base_pipeline, preprocessing
            )
            if resolved:
                preprocessing = _apply_resolved_citations(preprocessing, resolved)

    return preprocessing


def extract(
    parsed_paper: ParsedPaper,
    model: str,
    *,
    client: Any | None = None,
    citation_resolver: CitationResolver | None = None,
    paper_date: date | None = None,
) -> tuple[Preprocessing, list[ExtractionDiagnostic], list[DeferralRecord]]:
    """Single-pass extraction with one-hop deferral resolution.

    Pipeline:
      1. Pass 2 (:func:`extract_preprocessing`).
      2. Per-field deferrals (a step field defers to a citation) -> resolve one hop
         via the citation resolver (PriorPublicationBasis).
      3. Base-pipeline deferrals -> KB path first (recognized pipelines at
         VersionDefaultBasis, 0.95, via the Configurator helpers) when ``paper_date``
         is known; then the citation fallback (PriorPublicationBasis, 0.60) for any
         step fields the KB left open.
    The extraction arms and the returned ``deferral_records`` are unchanged.
    """
    preprocessing, diagnostics, deferral_records = extract_preprocessing(
        parsed_paper, model, client=client
    )
    preprocessing = _resolve_deferrals(
        preprocessing,
        deferral_records,
        paper_date=paper_date,
        citation_resolver=citation_resolver,
    )
    return preprocessing, diagnostics, deferral_records

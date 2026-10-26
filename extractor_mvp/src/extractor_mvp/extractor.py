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

import re
import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from datetime import date

    from fmri_repro.spec.provenance import InferredDefault

    from extractor_mvp.citation_resolver import CitationResolver

from fmri_repro.spec.preprocessing import (
    BrainExtraction,
    IntensityNormalization,
    IntensityNormalizationConvention,
    MotionCorrection,
    MotionCorrectionMethod,
    MotionInterpolation,
    MotionReferenceScan,
    MotionSimilarityMetric,
    NuisanceRegression,
    PipelineRef,
    Preprocessing,
    Segmentation,
    SpatialNormalization,
    SpecifiedTerm,
    SurfaceProjection,
    SurfaceRegistration,
    TargetSpace,
    TargetSurface,
    TemporalStandardization,
    TemporalStandardizationMethod,
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
from pydantic import BaseModel, Field, model_validator

from extractor_mvp.extraction_result import FieldExtractionResult
from extractor_mvp.motion_guard import motion_post_check
from extractor_mvp.parsed_paper import ParsedPaper
from extractor_mvp.quote_support import step_value_supported
from extractor_mvp.span_resolver import SpanResolution, quote_supports_value, resolve_quote
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
    base_pipeline_version: FieldExtractionResult = Field(
        default_factory=lambda: FieldExtractionResult(status="missing")
    )  # a SEPARATELY-stated version ("0.4.0", "5.0.10", "1.1-beta"); fused "SPM12" is name-only (Q1)
    # Build 2: per-voxel temporal z-scoring of the BOLD SIGNAL itself (Liu/Cho).
    # Defaulted to status="missing" so pre-existing fixtures still construct.
    temporal_standardization_method: FieldExtractionResult = Field(
        default_factory=lambda: FieldExtractionResult(status="missing")
    )  # voxel_temporal_zscore when the BOLD SIGNAL is z-scored (Liu/Cho); missing otherwise


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

base_pipeline_version: The version of the base pipeline, ONLY if the paper writes a
  SEPARATE version string for the pipeline it named.
  Examples: "C-PAC version 0.4.0" -> value "0.4.0"; "FSL suite (version 5.0.10)" -> "5.0.10";
            "FCP analysis scripts (version 1.1-beta)" -> "1.1-beta".
  status="extracted": the paper states a separate version string for the named pipeline.
    value = the version string as written; verbatim_quote = the exact sentence stating it.
  status="missing": no separate version string is stated. This INCLUDES a version FUSED into the
    tool name ("SPM12", "SPM8", "SPM99") -- that is a NAME, not a separately stated version
    (base_pipeline_name already carries "SPM12"), so base_pipeline_version is missing.
  PAPER-ONLY: do NOT infer a version from the tool's release history, the publication date, or what
    version was "current" -- only what the paper literally writes.

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

FIREWALL: extract only what the paper STATES. Do NOT infer a canonical tool, space,
or method from the pipeline's identity, lab conventions, or your own knowledge of
what a named pipeline typically uses. If the paper names a pipeline (e.g. CCS,
fMRIPrep, HCP) but states only a generic method term for a field, return that generic
term verbatim -- do NOT substitute the tool the pipeline is known to use. Naming the
tool is correct ONLY when the paper's own text names it.

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

surface_registration: The surface registration approach aligning each subject's
cortical surface to a template. Canonical values: freesurfer_recon, msm_sulc,
msm_all, other.
  extracted (paper NAMES the tool): "surfaces aligned with MSMAll" -> value=msm_all;
    "registered with FreeSurfer recon-all" -> value=freesurfer_recon.
  If the paper names only a generic registration METHOD without naming the tool
    (e.g. "sphere registration", "spherical registration", "surfaces were
    reconstructed and registered") return that term VERBATIM -- do NOT infer
    freesurfer_recon or msm_* from pipeline context. Bare "sphere registration" is
    ambiguous across FreeSurfer/MSM/others.
  missing: volume-only analysis, no surface registration step described.

target_surface: The surface template to which volume data were projected.
Canonical values: native, fsaverage, fsaverage5, fsaverage6, fsLR_32k, fsLR_164k, other.
  extracted (paper NAMES the surface): "data were mapped to the fsLR 32k surface"
    -> value=fsLR_32k; "resampled onto fsaverage5" -> value=fsaverage5.
  If the paper implies a surface only via pipeline context without naming it (e.g. it
    names an HCP/FreeSurfer pipeline but never states the target surface) return the
    paper's term VERBATIM -- do NOT infer fsaverage/fsLR from pipeline context.
  missing: no surface projection -- data kept in volume space only.

intensity_convention: The global/grand-mean intensity MAGNITUDE-scaling convention
applied to the 4D BOLD series (scaling the signal so a summary statistic hits a target
number). Canonical values: spm_grand_mean_100, fsl_grand_mean_10000, fsl_median_10000,
global_median_1000, global_mode_1000, other.
  extracted (paper NAMES the convention): "scaled each run to a grand mean of 10000"
    -> value=fsl_grand_mean_10000.
  If the paper uses generic scaling language without a convention that maps to a
    canonical member (e.g. "intensity normalized" with no target, "grand-mean scaled"
    with no number) return that term VERBATIM -- do NOT infer a canonical convention
    from pipeline context (e.g. fMRIPrep/FSL/SPM).
  missing: no magnitude scaling of the time series is described.
  NOT this field: per-voxel z-scoring / standardization to unit variance -> that is
    temporal_standardization_method, NOT an intensity convention. Fisher z-transform of
    correlations, DVARS, and statistical-map z-scores are NOT intensity conventions.

intensity_value: The target intensity magnitude after normalization (the number, e.g.
1000 or 10000).
  extracted: "grand mean scaling to 10000" -> value=10000
  missing: no magnitude scaling stated.

temporal_standardization_method: Whether the PREPROCESSED BOLD SIGNAL ITSELF was
temporally standardized per voxel (each voxel's time series transformed to zero mean and
unit variance across time, i.e. z-scored over time) as a preprocessing step before
analysis. Canonical values: voxel_temporal_zscore, other.
  DECISION RULE (apply BEFORE choosing status): identify the SUBJECT of any "normalized" /
  "standardized" / "z-scored" / "0 mean and 1 variance" / "unit variance" operation. This
  field is "extracted" ONLY when that subject is the voxelwise or vertexwise BOLD TIME SERIES
  itself. If the subject is a measure DERIVED from the signal -- a connectivity estimate
  (FC, SFC, ReHo, seed-connectivity), a correlation/connectivity matrix, a gradient,
  ICA/PCA components, nuisance regressors, classifier features, QC metrics, or a statistical
  map -- the field is "missing", no matter the wording used. When in doubt about the subject,
  choose "missing".
  NEAR-MISS that is MISSING (do NOT extract): "this surface-based SFC was estimated using the
  same preprocessed rfMRI data as ReHo but normalized (0 mean and 1 variance)" -> missing,
  because the SUBJECT normalized is the SFC connectivity map (a derived metric), not the BOLD
  time series.
  extracted: "for each voxel, the signal was temporally normalized by subtracting its
    mean and dividing by its temporal standard deviation" -> value=voxel_temporal_zscore
  extracted: "the BOLD time series were z-scored" -> value=voxel_temporal_zscore
  missing: no per-voxel temporal standardization of the signal is described.

  CRITICAL -- this field is ONLY for standardization of the BOLD SIGNAL ITSELF. It is
  "missing" (do NOT populate it) for ALL of the following, even though they use words
  like "standardized", "z-score", "unit variance", "zero mean":
    - Standardization of a FUNCTIONAL-CONNECTIVITY value or CONNECTIVITY-DERIVED product
      -- a correlation / connectivity matrix, a connectivity map such as SFC, ReHo, or
      seed-connectivity, a gradient -- to zero mean / unit variance -> NOT this field
      (these are connectivity products derived from the signal, not the signal). This
      applies REGARDLESS of the operation: Fisher r-to-z transform ("correlations were
      Fisher z-transformed") OR z-scoring the product to unit variance ("the SFC map was
      normalized to 0 mean and 1 variance").
    - Standardization of NUISANCE REGRESSORS / the design matrix
      ("regressors were standardized to zero-mean unit variance") -> NOT this field.
    - Standardization of ICA / PCA COMPONENTS after decomposition
      ("ICA component time series standardized to mean 0 SD 1") -> NOT this field
      (components are analysis products, not the signal).
    - Standardization of MVPA / classification FEATURES
      ("across-feature normalization") -> NOT this field.
    - Standardization of BEHAVIORAL / PHENOTYPE scores (IQ, symptom scales) -> NOT this
      field.
    - DVARS or other QC METRICS that are "standardized" -> NOT this field.
    - Z-scores in STATISTICAL MAPS / activation tables -> NOT this field.
  Ask: is the paper transforming the fMRI SIGNAL that carries forward into analysis, or
  is it transforming something DERIVED from the signal (a correlation, a regressor, a
  component, a feature, a metric)? Only the former is voxel_temporal_zscore.

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
class ResolutionRecord:
    """A SUCCESSFULLY-extracted targeted field, capturing what the LLM emitted
    (``raw_value``) alongside what the synonym resolver produced (``resolved_value``,
    ``matched_alias``). The counterpart to :class:`ExtractionDiagnostic` for the
    success path: ``ExtractionDiagnostic`` retains ``fe.value`` on failure, but on
    success the raw value is otherwise discarded (only the resolved value reaches the
    ProvenancedField). Diagnostic-only — never alters the spec/ProvenancedField schema.

    Lets us tell a firewall leak's LAYER apart: if ``raw_value`` is already a canonical
    literal (e.g. an inferred tool name) while the paper never names it, the leak is at
    the PROMPT/LLM layer; if ``raw_value`` is the paper's own phrasing but
    ``resolved_value`` is a different literal, the leak is at the RESOLVER."""

    field: str  # dotted path, e.g. "surface_projection.surface_registration"
    raw_value: object | None  # str(fe.value) as the LLM emitted it
    resolved_value: object | None  # the value written to the ProvenancedField
    matched_alias: str | None  # which synonym alias matched (None if exact member / non-literal)


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
    # 0.5.0 retype: literal_type (4th) stays the bare Literal (drives resolver + membership);
    # t (5th, the ProvenancedField generic) becomes SpecifiedTerm[X] so the verbatim term is
    # always recorded. The numeric fields (literal_type=None) keep t=float — different path.
    (
        "target_space",
        "target_space",
        "spatial_normalization.target_space",
        TargetSpace,
        SpecifiedTerm[TargetSpace],
    ),
    ("resolution_mm", "resolution_mm", "spatial_normalization.resolution_mm", None, float),
    (
        "surface_registration",
        "surface_registration",
        "surface_projection.surface_registration",
        SurfaceRegistration,
        SpecifiedTerm[SurfaceRegistration],
    ),
    (
        "target_surface",
        "target_surface",
        "surface_projection.target_surface",
        TargetSurface,
        SpecifiedTerm[TargetSurface],
    ),
    (
        "intensity_convention",
        "convention",
        "intensity_normalization.convention",
        IntensityNormalizationConvention,
        SpecifiedTerm[IntensityNormalizationConvention],
    ),
    ("intensity_value", "value", "intensity_normalization.value", None, float),
    # No value_context (no sibling number); field_id "method" != "convention", so the
    # value_context guard at _extract_from_prompt leaves it None. Direct Literal
    # validation (no synonym table — "method" is not a SYNONYMS_BY_FIELD key).
    (
        "temporal_standardization_method",
        "method",
        "temporal_standardization.method",
        TemporalStandardizationMethod,
        SpecifiedTerm[TemporalStandardizationMethod],
    ),
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


def _extracted_pf(
    field_id: str, t: Any, value: Any, span: Any, span_recovered: bool = False
) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=Extracted[t](
            value=value, spans=[span], confidence=_CONFIDENCE, span_recovered=span_recovered
        ),
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
    use_synonym_table: bool = True,
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
        # 0.5.0 retype: recording NEVER depends on resolution succeeding. The paper's verbatim
        # term is always kept; ``resolved`` is filled only when the resolver produced a member,
        # and ``res_status`` records the resolver's verdict. A term the resolver cannot map is now
        # EXTRACTED with resolved=None — no longer relabeled MissingFromPaper (the false-missing
        # defect: the spec asserting absence where there was presence). See
        # spec.preprocessing.SpecifiedTerm and docs/findings/target_space-false-missing.md.
        verbatim = str(fe.value)
        resolved: Any
        res_status: Literal["resolved", "underspecified", "unrecognized"]
        # SYNONYMS_BY_FIELD is keyed on the BARE field_id, and ``method`` is now the bare id of
        # TWO fields: temporal_standardization.method and motion_correction.method. One entry
        # added under "method" would silently serve both, in either direction. Today neither has
        # an entry and the lookup is inert -- but that is a fact about the map's CONTENTS, not a
        # property of this code. ``use_synonym_table=False`` lets a caller make its exclusion
        # explicit rather than depend on that absence continuing.
        #
        # Re-keying the map on (step kind, field) was the alternative. It would change the
        # resolution path the SHARED call runs for four existing fields -- a larger change than
        # the collision warrants while exactly one caller needs to opt out.
        synonyms_entry = SYNONYMS_BY_FIELD.get(field_id) if use_synonym_table else None
        if synonyms_entry is not None:
            syns, under = synonyms_entry
            res = resolve_to_literal(verbatim, syns, under, value_context)
            if res.status == "resolved":
                resolved, res_status = res.resolved, "resolved"
            elif fe.value in typing.get_args(literal_type):
                resolved, res_status = (
                    fe.value,
                    "resolved",
                )  # LLM emitted an exact member (e.g. "other")
            else:
                # underspecified ("MNI") stays distinct from unrecognized ("atlas space") /
                # ambiguous so the completeness derivation can grade family vs absent.
                resolved = None
                res_status = "underspecified" if res.status == "underspecified" else "unrecognized"
        elif fe.value in typing.get_args(literal_type):
            resolved, res_status = fe.value, "resolved"  # no synonym table; exact member only
        else:
            resolved, res_status = None, "unrecognized"
        value: Any = SpecifiedTerm(verbatim=verbatim, resolved=resolved, resolution=res_status)
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
    # A tolerant-tier RECOVERED span (span_resolver tier 5) is now KEPT and marked
    # span_recovered=True — honest because the marker distinguishes it from a clean match.
    # Step fields are marked-only in this release (no value-support guard here; that guard is
    # base_pipeline-scoped — see _build_base_pipeline). Only a genuine not-found span drops.
    # DATED NOTE, 2026-10-26: motion_correction.method is the first exception — extract_motion_method
    # applies motion_guard.motion_post_check AFTER this function returns (DELTA_value_in_quote_motion.md
    # §4). LATER THE SAME DAY the seven step fields got their own check, below, at the Extracted
    # return (quote_support.step_value_supported; DELTA_value_in_quote_step_fields.md §5): alias-whole
    # for the five Literal fields, digit-exact for the two numbers. "Marked-only" is no longer true of
    # any targeted field; the survey that preceded the change is
    # docs/findings/value-support-survey-step-fields.md.
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

    # Quote-support check for the step fields (quote_support.py; DELTA_value_in_quote_step_fields.md
    # §5, the author's rulings of 2026-10-26). Runs on the text the resolver LOCATED, after the span
    # resolved: a Literal value is supported when an alias of it, taken whole, is in that text; a
    # number when the number is in it, digit-exact. The motion field is not covered here (it has its
    # own post-check in extract_motion_method) and None means "not a checked field". One literal
    # reason at one _missing_pf call, so tests/test_render.py's reason scan can see it.
    supported = step_value_supported(dotted, value, resolution.span.text)
    if supported is False:
        return (
            _missing_pf(field_id, t, "value_unsupported_by_quote"),
            ExtractionDiagnostic(dotted, "value_unsupported_by_quote", fe.value, fe.verbatim_quote),
            None,
        )
    return (
        _extracted_pf(field_id, t, value, resolution.span, span_recovered=resolution.recovered),
        None,
        None,
    )


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


_ATTRIBUTION_TRIGGERS = re.compile(
    r"(?:described|outlined|detailed|reported)\s+(?:by|in)"
    r"|following\b|as\s+(?:described\s+)?in\b"
    r"|procedures?\s+(?:of|in|described\s+(?:by|in))",
    re.IGNORECASE,
)
_AUTHOR = re.compile(
    # Curly apostrophe kept verbatim to match typographic author names (e.g. O'Connor).
    r"[A-Z][A-Za-z'’\-]+(?:\s+et\s+al\.?)?(?:\s+(?:and|&)\s+[A-Z][A-Za-z'’\-]+)?"  # noqa: RUF001
    r"(?:\s*,?\s*\(?\s*\d{4}[a-z]?\s*\)?)?"
)


def _parse_attribution_ref(quote: str) -> str | None:
    """If ``quote`` is a bare citation-attribution (hands the method to a Title-Case author,
    naming no pipeline), return the author/citation token; else None. Deliberately narrow
    (viduarre-class); returns None — not a fabricated ref — when it cannot cleanly parse an
    author."""
    m = _ATTRIBUTION_TRIGGERS.search(quote)
    if m is None:
        return None
    am = _AUTHOR.match(quote[m.end() :].lstrip())
    if am is None:
        return None
    return am.group(0).strip().rstrip(",") or None


def _build_version_pf(
    version_result: FieldExtractionResult | None, text: str
) -> ProvenancedField[str]:
    """Q1 — the PAPER-STATED base_pipeline version (extraction arm only; paper-only, firewall-clean).

    EXTRACTED iff the paper wrote a SEPARATE version string AND that value is supported by its own
    quote (``quote_supports_value`` — the SAME guard the name uses, so an INFERRED version — "0.4.0
    was current then" — cannot pass as EXTRACTED; that is Q2's job with a basis). Otherwise
    MissingFromPaper. The inference arm stays ``LeftMissing(version_deferred_to_kb)`` so Q2
    (``infer_base_pipeline_version``) still fires downstream — and Q2 bails on an EXTRACTED extraction
    arm, so the two never cross. A version only *attaches* when a name is extracted (it rides inside
    ``PipelineRef``); this helper's result is discarded on the missing-name branches below. ``None``
    (no version field supplied, e.g. legacy fixtures) is treated as MISSING.
    """
    if (
        version_result is not None
        and version_result.status == "extracted"
        and version_result.value
        and version_result.verbatim_quote
    ):
        vres = resolve_quote(version_result.verbatim_quote, text)
        if vres.span is not None and quote_supports_value(
            version_result.value, version_result.verbatim_quote
        ):
            # EXTRACTED value is certain -> inference NOT_APPLICABLE (the ProvenancedField invariant;
            # same as the extracted name). Q2 (infer_base_pipeline_version) bails on an EXTRACTED
            # extraction arm regardless, so Q1 and Q2 still never cross.
            return ProvenancedField[str](
                field_id="base_pipeline.version",
                extraction=Extracted[str](
                    value=version_result.value,
                    spans=[vres.span],
                    confidence=_CONFIDENCE,
                    span_recovered=vres.recovered,
                ),
                inference=NotApplicable(),
            )
    return ProvenancedField[str](
        field_id="base_pipeline.version",
        extraction=MissingFromPaper(searched_terms=[], sections_searched=[]),
        inference=LeftMissing(reason="version_deferred_to_kb"),
    )


def _build_base_pipeline(
    name_result: FieldExtractionResult,
    ref_result: FieldExtractionResult,
    text: str,
    version_result: FieldExtractionResult | None = None,
) -> tuple[ProvenancedField[PipelineRef] | MissingFromPaper, DeferralRecord | None]:
    """Assemble Preprocessing.base_pipeline from the three Layer-1 extraction results.

    Returns ``(field_or_bare_missing, optional DeferralRecord)`` — the record can't
    ride the field's return type, so it's a second tuple element (cf. _process_field).
    ``version_result`` is Q1: a paper-STATED version rides inside ``PipelineRef`` when a name is
    extracted (see :func:`_build_version_pf`); it is discarded on the missing-name branches.

    Four cases:
      (extracted name, extracted ref)  -> Extracted(PipelineRef(name=name, version=Q1 or MISSING))
                                          ref is attribution only
      (extracted name, deferred ref)   -> Extracted(PipelineRef(name=name)) +
                                          DeferralRecord for Fork B on the ref
      (missing name,   deferred ref)   -> DeferredToCitation on the pipeline itself
      (missing name,   missing/extracted ref) -> MissingFromPaper (bare)
    """
    bp_id = "base_pipeline"
    # Q1: a paper-STATED version becomes EXTRACTED here (paper-only, quote-guarded); else MISSING.
    # The inference arm stays LeftMissing so Q2 (infer_base_pipeline_version) still fires downstream.
    version_pf: ProvenancedField[str] = _build_version_pf(version_result, text)

    # Resolve a deferred ref once (with full narrowing so mypy is happy).
    ref_span = None
    ref_record: DeferralRecord | None = None
    deferred_pipeline_field: ProvenancedField[PipelineRef] | None = None
    # A reported deferral whose sentence will not ground is the FOURTH collapsing condition. It used
    # to fall through indistinguishably into the no-name gap, so a paper that named a citation was
    # told "no base pipeline named in source".
    ref_deferral_unresolved = False
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
        else:
            ref_deferral_unresolved = True

    # Case A/B: pipeline NAME is extracted and its quote resolves -> base_pipeline EXTRACTED,
    # guarded (Option A, value-support). The model can INFER a pipeline name from a citation rather
    # than read it (viduarre: value "HCP minimal preprocessing pipeline", quote "…procedure described
    # by Glasser et al." — the name is nowhere in the quote), and it does so on CLEAN spans too: the
    # quote it cites is real paper text, it just does not contain the value. So the value-support
    # check runs UNCONDITIONALLY on every extracted base_pipeline — clean or recovered — because a
    # clean span match only proves the QUOTE is real, not that the VALUE is in it. Promoting an
    # unsupported value to EXTRACTED would fabricate a name. The guard compares the model's OWN value
    # against its OWN quote — firewall-clean (no KB at extraction). Blast radius verified on the label
    # set: every correct clean-span extraction has its value in its quote, so none is demoted; the two
    # that flip (viduarre, poldrack) were wrong EXTRACTEDs that reclassify to their correct DEFERRED.
    # Scope: base_pipeline only (step-field recoveries stay span_recovered-only, not value-guarded).
    # Hoisted: ``name_res is None`` is the test for "the guard was never entered", which the gap
    # reason needs AFTER the guard. Scoped inside it, the no-name branch could not see it.
    name_res: SpanResolution | None = None
    if name_result.status == "extracted" and name_result.value and name_result.verbatim_quote:
        name_res = resolve_quote(name_result.verbatim_quote, text)
        if name_res.span is not None:
            recovered = name_res.recovered
            if quote_supports_value(name_result.value, name_result.verbatim_quote):
                # Value actually stated in the quote -> honest EXTRACTED (span_recovered still marks
                # a tolerant-tier provenance when the span itself was recovered).
                pipeline = PipelineRef(name=name_result.value, version=version_pf)
                field: ProvenancedField[PipelineRef] = ProvenancedField[PipelineRef](
                    field_id=bp_id,
                    extraction=Extracted[PipelineRef](
                        value=pipeline,
                        spans=[name_res.span],
                        confidence=_CONFIDENCE,
                        span_recovered=recovered,
                    ),
                    inference=NotApplicable(),
                )
                return field, ref_record  # ref deferral (if any) handed to Fork B
            # Recovered BUT value unsupported -> value-mislocalization. If the quote is a bare
            # citation attribution, reclassify as a deferral (the honest four-state answer); else
            # fall through to bare MISSING — never a fabricated EXTRACTED. A distinct LeftMissing
            # reason keeps this guard reclassification greppable vs a model-declared deferral.
            parsed_ref = _parse_attribution_ref(name_result.verbatim_quote)
            if parsed_ref is not None:
                guard_field: ProvenancedField[PipelineRef] = ProvenancedField[PipelineRef](
                    field_id=bp_id,
                    extraction=DeferredToCitation(
                        deferrals=[
                            Deferral(ref=parsed_ref, span=name_res.span, target_kind="paper")
                        ],
                        searched_terms=name_result.searched_terms,
                        sections_searched=name_result.sections_searched,
                    ),
                    inference=LeftMissing(reason="citation_shaped_name_value_unsupported"),
                )
                return guard_field, ref_record
        # name_res.span is None (genuine not-found), or unsupported-and-unparseable: fall through
        # to the existing Case C (deferred ref) / Case D (bare MissingFromPaper) below.

    # Case C: name not (validly) extracted but ref deferred & resolved -> pipeline DEFERRED.
    if deferred_pipeline_field is not None:
        return deferred_pipeline_field, ref_record

    # Case D: a gap. WHICH gap now lands on the inference arm instead of collapsing onto one
    # caller-side constant. MissingFromPaper carries no reason field (provenance.py:59-62), so a
    # reason-bearing gap must return the WRAPPED ProvenancedField the way the two deferral branches
    # above already do; the no-name gap keeps returning bare so _assemble's isinstance branch (and
    # every case-A paper's bytes) is untouched.
    missing = MissingFromPaper(
        searched_terms=name_result.searched_terms or ["base pipeline"],
        sections_searched=name_result.sections_searched or ["full_text"],
    )

    # Each reason is written INLINE at its own LeftMissing site, and the branches are spelled out
    # rather than funnelled through one construction. Two reasons for that, both about the AST guard
    # in tests/test_render.py:
    #   * a local bound to a FUNCTION RETURN is unresolvable, so the guard refuses it loudly (it did:
    #     "reason argument(s) this scan cannot resolve");
    #   * a local bound to a literal in each of three branches is WORSE — the scan's `consts` map is
    #     last-write-wins (test_render.py:669-671), so it would resolve one base, register only that
    #     one, and PASS while two producers went unenumerated. A silent false negative in the one
    #     guard that keeps raw reason tokens out of author-facing output.
    # Verbose beats either. ``name_res is None`` is the "guard never entered" test; PRECEDENCE is name
    # over ref, because the name is this field's own value.
    if name_res is not None and name_res.span is None:
        # Quote did not ground. Mirrors _process_field's form, carrying the resolver's own
        # failure_reason — which does NOT decide tool-vs-model, and the state says so by staying
        # MISSING_FROM_PAPER rather than claiming a determination (DELTA §4 ruling).
        return (
            ProvenancedField[PipelineRef](
                field_id=bp_id,
                extraction=missing,
                inference=LeftMissing(
                    reason=f"extraction_quote_unresolved:base_pipeline_name:{name_res.failure_reason}"
                ),
            ),
            None,
        )
    if name_res is not None:
        # Quote GROUNDED and does not state the value, and did not parse as an attribution. No
        # existing reason's sentence is true of this, which is why it is the one new base.
        return (
            ProvenancedField[PipelineRef](
                field_id=bp_id,
                extraction=missing,
                inference=LeftMissing(reason="base_pipeline_value_unsupported"),
            ),
            None,
        )
    if ref_deferral_unresolved:
        # A reported deferral whose sentence would not ground. The existing base's sentence is true
        # of this verbatim, so it reuses it.
        return (
            ProvenancedField[PipelineRef](
                field_id=bp_id,
                extraction=missing,
                inference=LeftMissing(reason="deferral_quote_unresolved:base_pipeline_ref"),
            ),
            None,
        )
    # Genuine no-name gap: bare, so _assemble stamps no_base_pipeline_named and every case-A paper's
    # bytes are untouched. The one case where that sentence is true.
    return missing, None


def _assemble(
    pf: dict[str, ProvenancedField],
    base_pipeline: ProvenancedField[PipelineRef] | MissingFromPaper,
    motion_method: ProvenancedField | None = None,
) -> Preprocessing:
    """Wrap the extracted/missing fields into a schema-valid Preprocessing block.

    Fields the MVP does not target are present as MissingFromPaper so each step
    validates. ``base_pipeline`` comes from :func:`_build_base_pipeline`; a bare
    MissingFromPaper is wrapped here into the required ProvenancedField coupling.
    """
    # field_id MUST be the bare step attribute name (step invariant).
    untargeted = "not_targeted_by_mvp"
    # Anatomical-target steps (v0.3.0), schema-present but not targeted by the MVP. Placed
    # before spatial normalization per pipeline order (COBIDAS §4.3) — canonically they sit
    # just before coregistration, which _assemble does not yet build, so spatial is the
    # earliest present consumer of their outputs.
    brain_extraction = BrainExtraction(
        method=_missing_pf("method", str, untargeted),
        manual_edits=_missing_pf("manual_edits", bool, untargeted),
    )
    segmentation = Segmentation(
        method=_missing_pf("method", str, untargeted),
        tissue_classes=_missing_pf("tissue_classes", list, untargeted),
    )
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
    # NuisanceRegression (COBIDAS-mandatory) is emitted as a decision point even though the
    # MVP targets none of its fields: a silently absent step tells the replicator nothing,
    # whereas an all-unassessed step surfaces that a high-variance choice exists here. Placed
    # after surface_projection, before intensity_normalization (catalog order 8 -> 9c).
    nuisance_regression = NuisanceRegression(
        motion_expansion=_missing_pf("motion_expansion", str, untargeted),
        tissue_regressors=_missing_pf("tissue_regressors", list, untargeted),
        physio_regressors=_missing_pf("physio_regressors", str, untargeted),
        physio_n_regressors=_missing_pf("physio_n_regressors", int, untargeted),
        detrend=_missing_pf("detrend", str, untargeted),
        method=_missing_pf("method", str, untargeted),
        filtering_integrated=_missing_pf("filtering_integrated", bool, untargeted),
    )
    intensity = IntensityNormalization(
        convention=pf["intensity_convention"],
        value=pf["intensity_value"],
        scope=_missing_pf("scope", str, untargeted),
    )
    temporal_standardization = TemporalStandardization(
        method=pf["temporal_standardization_method"],
    )
    if isinstance(base_pipeline, MissingFromPaper):
        base_pipeline_field: ProvenancedField[PipelineRef] = ProvenancedField[PipelineRef](
            field_id="base_pipeline",
            extraction=base_pipeline,
            inference=LeftMissing(reason="no_base_pipeline_named"),
        )
    else:
        base_pipeline_field = base_pipeline
    # motion_correction. ``method`` comes from its OWN call (ruling A); the other nine fields are
    # untargeted, exactly as every other partially-targeted step here. When no motion call was made
    # -- the per-acquisition path, which reuses the shared prompt and so cannot carry this field --
    # ``method`` is ``not_targeted_by_mvp`` too, NEVER ``not_stated_in_text``: the extractor did not
    # look, and a source-absence reason there would be a claim about the paper. Ruling A records
    # that omission as a cost of the separate call, not as an oversight.
    motion_correction = MotionCorrection(
        method=(
            motion_method
            if motion_method is not None
            else _missing_pf("method", SpecifiedTerm[MotionCorrectionMethod], untargeted)
        ),
        reference_scan=_missing_pf(
            "reference_scan", SpecifiedTerm[MotionReferenceScan], untargeted
        ),
        similarity_metric=_missing_pf(
            "similarity_metric", SpecifiedTerm[MotionSimilarityMetric], untargeted
        ),
        interpolation=_missing_pf("interpolation", SpecifiedTerm[MotionInterpolation], untargeted),
        transforms_combined=_missing_pf("transforms_combined", bool, untargeted),
        nonrigid=_missing_pf("nonrigid", bool, untargeted),
        transform_type=_missing_pf("transform_type", str, untargeted),
        fieldmap_unwarping=_missing_pf("fieldmap_unwarping", bool, untargeted),
        unwarping_method=_missing_pf("unwarping_method", str, untargeted),
        slice_to_volume=_missing_pf("slice_to_volume", bool, untargeted),
    )
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=base_pipeline_field,
        steps=[
            brain_extraction,
            segmentation,
            motion_correction,
            spatial,
            surface,
            nuisance_regression,
            intensity,
            temporal_standardization,
        ],
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


# ---------------------------------------------------------------------------------------------
# motion_correction.method — its OWN call and its OWN prompt (ruling A, 2026-10-19).
#
# NOT a stanza in EXTRACTION_PROMPT. That constant is hash-pinned by tests/test_prompt_pin.py
# because a change to it re-vintages every field already validated under it; the v1->v2 change
# coerced 5 of 7 MNI terms at the shipped level. A separate call keeps each row's validation
# intact when the next row lands.
#
# Written FROM docs/ground-truth-protocol-motion_correction.md v1.5, not from any paper's text.
# Three papers -- liu_2005, tang_2025, wheaton_2004 -- are the only uncontaminated cells left in
# the motion corpus (prereg C11, C26) and were not read while writing this.
#
# FOUR CORRECTIONS, 2026-10-21, before this ever ran:
#   1. the no-bound-tool rule emitted a FIXED token ("other"). Run through the prereg's own frozen
#      heuristic (:97-111) that token returns **undecided** -- so every described_only cell would
#      land in the bucket whose count :107-108 uses to judge whether ruling (b) is adequate. The
#      probe would have measured this stanza's choice of word instead of the heuristic. It also
#      makes binder's pre-declared reading unobservable, since that reading turns on whether the
#      value is the algorithm description or the word "coregistered" -- and "coregistered" returns
#      operation_phrase. The value is now the paper's own words.
#   2. the subject gate stopped the whole extraction at the first anatomical/atlas/surface
#      alignment. Most methods sections describe realignment AND EPI-to-T1 coregistration (COBIDAS
#      gives them separate rows), so that produced false "missing" -- the class of error no honesty
#      check detects (DESIGN_methods_finder.md:23). The gate is now per passage.
#   3. STEP 0 said "say so in the quote", which contradicts the exact-copy requirement that makes a
#      quote resolvable at all.
#   4. STEP 3's example was derosa's own case, and derosa is one of the six probe papers. Naming it
#      in the stanza would have made its probe result circular.
#
# FIFTH AND SIXTH CORRECTIONS, 2026-10-21, also before any run:
#   5. STEP 4's deferral arm was unscoped -- it fired whenever the estimate was "attributed to" a
#      citation or an unnamed-internals package. That catches two probe papers whose COMMITTED label
#      is described_only, and neither "deferred" outcome is among the pre-declared readings: binder,
#      whose quote describes the procedure and cites Cox (1996b) FOR it, and derosa, where FSL is
#      named as the governing package (reading 1). CALL 7 draws the line the arm was missing --
#      "does the citation SUBSTITUTE for a description of that row, or SUPPORT one that is present?
#      Substitutes -> deferred. Supports -> not a deferral" -- and names binder as the support case:
#      "the Cox (1996b) reference supports a described algorithm -> described_only". CALL 7 also says
#      "a citation's scope does not extend to rows the paper describes itself". The arm now carries
#      that limit, with the NOT BOUND case routed to the paper's-own-words rule instead.
#   6. STEP 2 said "the surviving passage" while STEP 1 can keep several. Now "the kept passages".
#
# SEVENTH CORRECTION, 2026-10-22, AFTER the first run -- a prereg C11 iteration, not a pre-run fix:
#   7. STEP 3's "BOUND BUT ROUTED ELSEWHERE" was abstract, and on the 2026-10-21 run derosa returned
#      `ICA-AROMA` on 10 of 10 draws (prereg reading 2, "CALL 4 territory"). It now names the row
#      and the tools: COBIDAS D.3 p.57 lists CompCor, ICA-FIX and ICA-AROMA under "Artifact and
#      structured noise removal" (verified against the report), so they belong to that row, supply
#      nothing here, and the value is the paper's own phrase for the operation. STEP 4's first rule
#      gained "and not routed elsewhere" so the two rules cannot both fire.
#      This REVERSES correction 4's reasoning by choice: derosa's own tool is now named in the
#      stanza, so derosa's result under this stanza is FITTED, not independent. Recorded in the
#      pin's dated note and in prereg Amendment 4. A second iteration the author proposed (the
#      deferral line between poldrack and liu_2013) is HELD pending a ruling -- checked against
#      CALL 6, CALL 7 and CALL 2a, it conflicts with CALL 7's enumeration criterion and does not
#      separate the two anchors on the axis it names; the conflict is reported in Amendment 4,
#      not resolved here.
#
# VERSION 3, 2026-10-26 (later): written from protocol v1.7 (CALL 11, rule A) and option (c) of
# prereg Amendment 1 -- not from any paper's text. Two changes to the 56bc6305... stanza:
#   * a CITATION step (STEP 4) carrying CALL 11 as ordered steps: with no bound ESTIMATE tool, the
#     method is DEFERRED to a citation only when the text states none of the algorithm, the transform
#     type, the reference image or the cost function; stating any one makes it described in the
#     paper's own words, whatever it cites. The 56bc deferral arm had carried CALL 7's
#     substitute-or-support test, which left poldrack on row 1 on 20 of 20 draws against a
#     `deferred` label (Amendment 4 §3). The model has returned "deferred" on 0 of 180 draws; this
#     version is the first test of whether that state is reachable.
#   * option (c): the model states the CALL 1 binding itself in a new response-model field,
#     `motion_correction_binding`, set only when status is "extracted". The frozen heuristic
#     (scripts/motion_value_kind.py) keeps running as the independent control; the projection
#     carries both and counts disagreements. This supersedes Amendment 2 ruling 4 (Amendment 7).
# The structured-noise routing and the value-in-quote check stay in code (motion_guard.py); the
# stanza does not name those tools. Pinned in tests/test_prompt_pin.py with a dated note; 56bc6305...
# and 378a294f... retained there.
#
# REVERTED 2026-10-26, by the author's ruling, to the stanza as it stood before correction 7 (sha256
# 56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a, restored verbatim from the parent
# of the commit that made the correction). The same-day control of 2026-10-25
# (docs/findings/motion-probe-ab-stanza-vs-day.md, prereg Amendment 5) showed that correction 7 is
# what moved agtzidis to `SPM12` on 10 of 10 and binder to `AFNI` on 8 of 10 -- both values pulled
# from a sentence other than the one quoted -- while derosa, the paper it was written for, returned
# `ICA-AROMA` on all 20 draws across both versions. Restoring a measured version creates no new
# vintage. The routing of CompCor / ICA-FIX / ICA-AROMA moves to code
# (docs/design/DELTA_value_in_quote_motion.md, ruling 4); the comment block above is kept as the
# record of what was tried.
#
# ORDERED STEPS, not prose exclusions, because the protocol says so in as many words
# (protocol:526): "the axes are to be **emitted as discrete steps**, not offered as prose
# guidance." Its reason is docs/findings/temporal-firewall-fix.md, which found the model
# OVERRODE an explicit, near-identical prose exclusion and followed a mandatory subject-first
# decision instead. That finding bounds itself: it converted ONE derived-subject shape and left
# TWO untouched (:173-179), so it is evidence for the STRUCTURE, not proof it generalises.
# ---------------------------------------------------------------------------------------------
MOTION_METHOD_PROMPT = """\
You are extracting ONE field from an fMRI methods text: the method used for MOTION CORRECTION
(between-volume realignment of the functional time series).

Work through the steps IN ORDER. Do not start from a tool name. A tool name is never the entry
point.

## STEP 0 -- what is being labelled
The unit is the PREPROCESSING applied to an acquisition, not an analysis run on it. One
preprocessing feeding two analyses is one unit. If the text describes two separately preprocessed
pipelines, use the main one.

## STEP 1 -- SUBJECT (a gate, applied to EACH alignment passage separately)
Most methods sections describe several alignments. Find every passage describing an alignment, and
ask of EACH ONE: what is aligned to what?
- Functional-to-functional: EPI to EPI, or EPI to a within-run or within-session reference volume
  or mean image -> KEEP this passage and carry it to step 2.
- EPI to an anatomical image, EPI to an atlas or template, or surface registration -> SET THIS
  PASSAGE ASIDE. It belongs to a different field. Do NOT stop; keep reading.
Then:
- If at least one passage was kept, continue to step 2 using only the kept passages.
- Only if NO passage was kept -- the text describes no functional-to-functional alignment at all --
  output status "missing".
- If the text states the step was NOT performed, output status "missing".

## STEP 2 -- ROLE (for every tool named in the kept passages, assign exactly one)
- ESTIMATE: computes the rigid-body transform between functional volumes. ONLY this role can
  supply the value.
- APPLY: resamples data using a transform estimated elsewhere. Supplies NOTHING here, EVEN WHEN
  the phrase "head motion correction" appears in the same sentence.
- CONSUME: takes already-estimated motion parameters as input to something else -- nuisance
  regressors, censoring, exclusion criteria, or a summary statistic such as FD or RMS
  displacement. Supplies nothing here.
- HOST: a language or environment the estimator runs in, such as MATLAB or Python. Never the
  value.

## STEP 3 -- BINDING (apply to the tool you placed in ESTIMATE)
Does the text attribute that tool to THIS step, or only to the enclosing set of procedures?
- BOUND: the step is described in the paper's own voice and the named package governs it. The
  tool supplies the value.
- NOT BOUND: a package named as governing a procedure set supplies nothing. It is NOT enough that
  the package is named, named with a version, or named in the same sentence as the step.
- BOUND BUT ROUTED ELSEWHERE: if the only tool bound to this step performs an operation that
  belongs to a different field, then the assertion that motion correction was performed still
  stands, but no tool name survives.

## STEP 4 -- CITATION (only when step 3 found NO bound tool in ESTIMATE)
If a tool is BOUND in ESTIMATE, skip this step: the tool is the method.
Otherwise decide between "deferred" and the paper's own words by what the text itself states
about HOW the motion was estimated. Exactly four details count:
  (a) the algorithm, (b) the transform type (for example rigid body), (c) the reference image the
  volumes are aligned to, (d) the cost function.
- The operation is named under a cited pipeline, a cited method or a cited paper, and the text
  states NONE of the four details -> the method is DEFERRED to that citation.
- The text states ANY of the four details -> the method is DESCRIBED in the paper's own words,
  whatever it cites. A citation beside a stated detail supports the description; it does not
  replace it.
- The text cites nothing for the operation -> the method is DESCRIBED in the paper's own words,
  on the paper's own assertion.
A package name alone is neither a statement of how the motion was estimated nor a citation.
Listing the step among others under a citation is a description ONLY when the listing carries
one of the four details.

## STEP 5 -- OUTPUT
- Exactly one tool in ESTIMATE and BOUND, and not routed elsewhere -> status "extracted"; value =
  that tool; verbatim_quote = the ESTIMATE mention SPECIFICALLY (never a CONSUME mention of the
  same tool); motion_correction_binding = "named_tool".
- The subject gate passed and the method is DESCRIBED (step 4), with no bound tool in ESTIMATE ->
  status "extracted"; value = THE PAPER'S OWN WORDS for the operation, copied from the text (for
  example the phrase it uses to name what was done); verbatim_quote = the sentence containing
  those words; motion_correction_binding = "described_only". Do NOT substitute a word of your
  own, and do NOT invent a category. Tools named elsewhere in the kept passages do NOT license a
  value.
- The method is DEFERRED (step 4) -> status "deferred"; ref_string = the pipeline name if the
  text gives one, else the citation as written; deferral_sentence = the sentence that names the
  operation under the citation; leave motion_correction_binding unset.
- Nothing about between-volume alignment, or the step is stated as not performed -> status
  "missing"; leave motion_correction_binding unset.

motion_correction_binding is set ONLY when status is "extracted", and then it is ALWAYS set:
"named_tool" when step 3 found a bound tool, "described_only" otherwise.

verbatim_quote and deferral_sentence must be copied EXACTLY from the text below, character for
character, or the field is discarded.

Text:
\"\"\"
{text}
\"\"\"
"""


class MotionMethodExtraction(BaseModel):
    """LLM output schema for the one-field motion call.

    Separate from :class:`PreprocessingExtraction` so that adding this row could not alter the
    hash-pinned shared prompt or the response model every other field is extracted under. The
    precedent is ``acquisition_discovery._LLMAcquisitionList``: a private one-purpose schema with
    its own prompt constant and the same create() settings.

    ``motion_correction_binding`` — option (c) of prereg Amendment 1, adopted 2026-10-26 (Amendment
    7): the model states the CALL 1 binding itself. Set ONLY when ``status == "extracted"``, and then
    always: ``"named_tool"`` when a tool is bound to the step, ``"described_only"`` when the value is
    the paper's own words. Deferred and missing keep the existing status path and leave it unset.
    The frozen heuristic (``scripts/motion_value_kind.py``) still classifies the value independently;
    the probe's projection carries both and counts the disagreements. Enforced by a validator, so a
    missing or stray binding is a reask the probe counts, not a silent default.
    """

    motion_correction_method: FieldExtractionResult
    motion_correction_binding: Literal["named_tool", "described_only"] | None = None

    @model_validator(mode="after")
    def enforce_binding_constraints(self) -> MotionMethodExtraction:
        status = self.motion_correction_method.status
        if status == "extracted" and self.motion_correction_binding is None:
            raise ValueError(
                "status='extracted' requires motion_correction_binding: 'named_tool' when a tool is "
                "BOUND to this step (STEP 3), 'described_only' when the value is the paper's own words."
            )
        if status != "extracted" and self.motion_correction_binding is not None:
            raise ValueError(
                "motion_correction_binding is set only when status='extracted'; leave it unset for "
                "'deferred' and 'missing'."
            )
        return self


#: The ``_FIELD_SPECS`` row for the motion call, kept beside it rather than in that list: the
#: list drives the SHARED call's loop, and an entry there would make the shared response model
#: require a field it does not have.
_MOTION_FIELD_SPEC: tuple[str, str, str, Any, Any] = (
    "motion_correction_method",
    "method",
    "motion_correction.method",
    MotionCorrectionMethod,
    SpecifiedTerm[MotionCorrectionMethod],
)


def extract_motion_method(
    parsed_paper: ParsedPaper,
    model: str,
    *,
    client: Any | None = None,
    raw_out: list[MotionMethodExtraction] | None = None,
) -> tuple[ProvenancedField, ExtractionDiagnostic | None, DeferralRecord | None]:
    """One extra ``create()`` per paper, on the SAME slice as the main call.

    Same ParsedPaper, same model, same temperature and max_retries, and the same
    ``_process_field`` span-resolution path -- so its gap reasons are the standard ones
    (``extraction_quote_missing``, ``extraction_quote_unresolved:*``, ``deferral_quote_unresolved:*``,
    ``not_stated_in_text``) that the conditional-row rule already handles, rather than a private
    vocabulary this call would have to teach every downstream reader.

    Cost, recorded honestly: one additional model call per paper on the single-acquisition path,
    and it doubles the reask surface because ``max_retries`` applies per call.

    **This call's latency is UNMEASURED.** An earlier version of this docstring gave it "the
    measured mean of 11.87 s per paper" — that figure is `DESIGN_kdraw_stability.md` §3g's, and it
    measures the SHARED call: a 13,480-character prompt returning seven fields, timed from
    per-paper JSON mtimes. This prompt is 3,887 characters and returns one field, so borrowing that
    number would assert a measurement nobody has taken, and would almost certainly overstate it.
    What is known is the call COUNT, which doubles; the wall-clock cost is not known until a run
    reports it. `scripts/motion_probe.py` logs per-draw wall time for exactly that reason, so the
    first probe run measures this instead of inheriting it.
    """
    client = client or build_client()
    extraction: MotionMethodExtraction = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": MOTION_METHOD_PROMPT.format(text=parsed_paper.text)}],
        response_model=MotionMethodExtraction,
        temperature=0.0,
        max_retries=2,
    )
    # ``raw_out``: pass a list to capture the model's OWN response (the FieldExtractionResult and
    # the binding it states) before
    # _process_field turns it into a SpecifiedTerm. Same idiom as extract_preprocessing's
    # ``resolutions`` — diagnostic capture only, and the default None is a no-op that changes
    # nothing. The reachability probe needs it because the pre-registration asks for the processed
    # layer (verbatim/resolved/resolution/span, :8) while Amendment 1 states the LLM schema is
    # FieldExtractionResult (:45-46), and how its ``verbatim=None`` trigger maps between the two is
    # NOT yet ruled. Recording both layers means the run survives either ruling without a re-run.
    if raw_out is not None:
        # the WHOLE response, since 2026-10-26: the binding the model states travels with the
        # FieldExtractionResult it qualifies (the probe records both; Amendment 7).
        raw_out.append(extraction)
    _attr, field_id, dotted, literal_type, t = _MOTION_FIELD_SPEC
    raw = extraction.motion_correction_method
    pf, diag, deferral = _process_field(
        field_id,
        dotted,
        raw,
        literal_type,
        t,
        parsed_paper.text,
        None,
        # Opt OUT of the bare-id synonym lookup: "method" is shared with
        # temporal_standardization.method, and a synonym written for that field must never resolve
        # a motion value. Asserted in tests/test_motion_method.py.
        use_synonym_table=False,
    )
    # The value-in-quote post-check, DELTA_value_in_quote_motion.md §4 (rulings 1-4, 2026-10-26).
    # Runs on the PROCESSED layer only -- after the quote has resolved, never as a reask -- and
    # compares the model's own value with its own quote. The 2026-10-22 and 2026-10-25 runs
    # produced 30 resolved draws whose tool name came from a sentence other than the one quoted;
    # _process_field cannot see that, because resolving the quote proves the QUOTE is real, not that
    # the VALUE is in it (:571-573 records why the step-field path was built without this check).
    # Two inline returns rather than one reason variable, so tests/test_render.py's reason scan can
    # read both bases (a local bound to a function return is refused there).
    if isinstance(pf.extraction, Extracted):
        verdict = motion_post_check(raw.value, raw.verbatim_quote)
        if verdict == "motion_value_unsupported_by_quote":
            return (
                _missing_pf(field_id, t, "motion_value_unsupported_by_quote"),
                ExtractionDiagnostic(dotted, verdict, raw.value, raw.verbatim_quote),
                deferral,
            )
        if verdict is not None:
            tool = verdict.split(":", 1)[1]
            return (
                _missing_pf(field_id, t, f"motion_value_routed_structured_noise:{tool}"),
                ExtractionDiagnostic(dotted, verdict, raw.value, raw.verbatim_quote),
                deferral,
            )
    return pf, diag, deferral


def _extract_from_prompt(
    parsed_paper: ParsedPaper,
    model: str,
    prompt_text: str,
    client: Any | None,
    resolutions: list[ResolutionRecord] | None = None,
    motion_method: ProvenancedField | None = None,
) -> tuple[Preprocessing, list[ExtractionDiagnostic], list[DeferralRecord]]:
    """Run one LLM extraction call + the shared post-processing pipeline.

    ``resolutions`` (optional): if a list is passed, one :class:`ResolutionRecord`
    per SUCCESSFULLY-extracted targeted field is appended, capturing the raw LLM
    value alongside the resolved value/alias. Default ``None`` collects nothing,
    preserving the 3-tuple return and all existing callers' behavior."""
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
        fe = getattr(extraction, attr)
        field_pf, diag, deferral = _process_field(
            field_id,
            dotted,
            fe,
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
        # Capture the raw LLM value on SUCCESS. A clean success is exactly when
        # _process_field returned an Extracted arm (the only path that does); every
        # failure returns MissingFromPaper + a diagnostic, deferrals return
        # DeferredToCitation. The isinstance check both signals success and narrows
        # the extraction union so .value is well-typed.
        if resolutions is not None and isinstance(field_pf.extraction, Extracted):
            matched_alias = None
            if literal_type is not None:
                synonyms_entry = SYNONYMS_BY_FIELD.get(field_id)
                if synonyms_entry is not None:
                    syns, under = synonyms_entry
                    matched_alias = resolve_to_literal(
                        str(fe.value), syns, under, value_context
                    ).matched_alias
            _resolved_val = field_pf.extraction.value
            resolutions.append(
                ResolutionRecord(
                    field=dotted,
                    raw_value=fe.value,
                    # 0.5.0: the retyped fields carry a SpecifiedTerm; record the resolved member
                    # (None when unresolved) so the record keeps its raw->resolved semantics.
                    resolved_value=(
                        _resolved_val.resolved
                        if isinstance(_resolved_val, SpecifiedTerm)
                        else _resolved_val
                    ),
                    matched_alias=matched_alias,
                )
            )

    # Layer 1: base preprocessing pipeline (name + optional citation/deferral).
    base_pipeline, bp_deferral = _build_base_pipeline(
        extraction.base_pipeline_name,
        extraction.base_pipeline_ref,
        parsed_paper.text,
        version_result=extraction.base_pipeline_version,
    )
    if bp_deferral is not None:
        deferrals.append(bp_deferral)

    return _assemble(pf, base_pipeline, motion_method), diagnostics, deferrals


def extract_preprocessing(
    parsed_paper: ParsedPaper,
    model: str,
    *,
    client: Any | None = None,
    resolutions: list[ResolutionRecord] | None = None,
) -> tuple[Preprocessing, list[ExtractionDiagnostic], list[DeferralRecord]]:
    """Single-pass extraction -> (Preprocessing, diagnostics, deferral records).

    ``resolutions`` (optional): pass a list to collect per-field
    :class:`ResolutionRecord`s for successfully-extracted targeted fields (raw LLM
    value + resolved value/alias). Diagnostic capture only; default ``None`` is a
    no-op that preserves existing behavior and the 3-tuple return."""
    # Ruling A: motion_correction.method is its OWN call, on the SAME ParsedPaper and slice.
    # Reached only here, on the single-acquisition path. The per-acquisition path below reuses the
    # shared prompt and so gets no motion call -- a cost ruling A records, and the reason _assemble
    # leaves ``method`` untargeted rather than not-stated when this is None.
    #
    # One client for both calls, so a caller's stub serves both and a real run opens one connection:
    # the same shape extract_multi_acquisition uses for its discovery + per-acquisition calls.
    client = client or build_client()
    motion_method, motion_diag, motion_deferral = extract_motion_method(
        parsed_paper, model, client=client
    )
    prep, diagnostics, deferrals = _extract_from_prompt(
        parsed_paper,
        model,
        EXTRACTION_PROMPT.format(text=parsed_paper.text),
        client,
        resolutions,
        motion_method,
    )
    if motion_diag is not None:
        diagnostics.append(motion_diag)
    if motion_deferral is not None:
        deferrals.append(motion_deferral)
    return prep, diagnostics, deferrals


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


def _base_pipeline_extracted(bp: ProvenancedField | NotApplicable) -> bool:
    """True iff ``base_pipeline`` is a paper-named (EXTRACTED) pipeline (not from-scratch)."""
    return not isinstance(bp, NotApplicable) and bp.extraction.status == "EXTRACTED"


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
    # Version inference for an EXTRACTED base pipeline: the name is available so
    # resolve_version can fire. Fills ONLY the version field (date_inferred_version /
    # version_default); fill_dependent_defaults is deliberately NOT called here — param fill
    # on a merely inferred version would overwrite value_not_in_literal fields (e.g.
    # target_space) with a KB default (false precision). The version-certainty gate stays.
    # Mutually exclusive with the base-pipeline *deferral* branch below (extraction status).
    if paper_date is not None and _base_pipeline_extracted(preprocessing.base_pipeline):
        from fmri_repro.kb_client.base_pipeline import infer_base_pipeline_version

        preprocessing = infer_base_pipeline_version(preprocessing, paper_date)

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
    resolutions: list[ResolutionRecord] | None = None,
) -> tuple[Preprocessing, list[ExtractionDiagnostic], list[DeferralRecord]]:
    """Single-pass extraction with one-hop deferral resolution.

    ``resolutions`` (optional): forwarded to :func:`extract_preprocessing` to collect
    per-field :class:`ResolutionRecord`s (raw LLM value + resolved value/alias) for
    successfully-extracted targeted fields. Deferral resolution never touches EXTRACTED
    arms, so the captured records reflect the final shipped values. Default ``None`` is
    a no-op, preserving the 3-tuple return.

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
        parsed_paper, model, client=client, resolutions=resolutions
    )
    preprocessing = _resolve_deferrals(
        preprocessing,
        deferral_records,
        paper_date=paper_date,
        citation_resolver=citation_resolver,
    )
    return preprocessing, diagnostics, deferral_records

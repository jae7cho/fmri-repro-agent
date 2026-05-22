"""Preprocessing group for ReplicationSpec v0.1.0.

The 16-kind ordered preprocessing chain that replaces the
``Preprocessing`` stub in :mod:`fmri_repro.spec.v0_1_0`. Field-level spec is
authoritatively defined in ``docs/spec/preprocessing_catalog_v0.1.0.md``;
this module mirrors the acquisition-arm patterns one-for-one:

- Per-step :data:`FieldMeta` registry keyed by bare attribute name.
- Import-time bijection check (:func:`_check_step_bijection`) raises
  ``RuntimeError`` if any registry diverges from its step class.
- :func:`_validate_step_invariants` enforces ``field_id == attribute_name``
  and the ``inference_applicable`` invariant on every step's
  ``@model_validator(mode="after")``.
- Steps are siblings under a flat :data:`PreprocStep` discriminated union
  (discriminator: ``kind``). Operations COBIDAS groups under one reporting
  row but occurring at different pipeline stages are modeled as sibling
  kinds (e.g. ``despike`` + ``scrub``; ``ica_denoise`` + ``compcor`` +
  ``nuisance_regression``) with per-kind uniqueness.

The :class:`Preprocessing` model carries ``applies_to`` (acquisition
references), ``base_pipeline`` (a provenanced ``PipelineRef`` reference, or
explicit :class:`NotApplicable` for hand-rolled pipelines like Bassett 2011),
and the ordered ``steps`` list (list position IS the order — COBIDAS §4.3).

``base_pipeline`` is a 2-arm union:

- ``ProvenancedField[PipelineRef]`` — nested provenance. The outer arm carries
  the paper's claim about the base pipeline (Extracted / DeferredToCitation /
  MissingFromPaper / InferredDefault). The inner ``PipelineRef.version`` is
  itself a :class:`ProvenancedField[str]` so the version can be deferred or
  inferred independently from the pipeline identity.
- ``NotApplicable`` — the spec asserts no base pipeline (Bassett-style
  from-scratch). Coupling rule: ``NotApplicable + steps == []`` is rejected
  (no preprocessing at all is incoherent for a spec carrying functional data).
"""

from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Self

from pydantic import BaseModel, Field, model_validator

from fmri_repro.spec.provenance import NotApplicable, ProvenancedField
from fmri_repro.spec.refs import AcquisitionRef, FieldMeta

# ---------------------------------------------------------------------------
# Pipeline reference (used by ``Preprocessing.base_pipeline``)
# ---------------------------------------------------------------------------


class PipelineRef(BaseModel):
    """Reference to a base preprocessing pipeline (e.g. HCP MPP, fMRIPrep, CCS).

    ``name`` is plain — when a base pipeline is invoked the name is known.
    ``version`` is provenanced so it can carry one of:

    - :class:`Extracted` (paper states the pipeline version)
    - :class:`DeferredToCitation` with ``target_kind="pipeline"`` (paper cites
      the pipeline but doesn't pin a version)
    - :class:`InferredDefault` with ``version_default`` or
      ``date_inferred_version`` basis (Configurator filled in)
    - :class:`MissingFromPaper` + :class:`LeftMissing`

    Configurator/KB role only — the base pipeline is never expanded into
    stored steps.
    """

    name: str
    version: ProvenancedField[str]


# ---------------------------------------------------------------------------
# Per-step FieldMeta registries
#
# One dict per step kind, keyed by the bare attribute name (NOT a dotted
# ``preprocessing.motion_correction.method`` path). Mirrors the per-arm
# acquisition registries.
#
# ``inference_applicable`` flags come from
# ``docs/spec/preprocessing_catalog_v0.1.0.md``; the conservative bias is
# extracted-or-missing unless a base pipeline supplies a defensible default.
# ---------------------------------------------------------------------------


NONSTEADYSTATE_REMOVAL_FIELD_META: dict[str, FieldMeta] = {
    "n_nonsteadystate_discarded": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
}


SLICE_TIME_CORRECTION_FIELD_META: dict[str, FieldMeta] = {
    "reference": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
    "relative_to_motion_correction": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "interpolation": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
}


MOTION_CORRECTION_FIELD_META: dict[str, FieldMeta] = {
    "method": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "reference_scan": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
    "similarity_metric": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
    "interpolation": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
    "nonrigid": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "transform_type": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "fieldmap_unwarping": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "unwarping_method": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "slice_to_volume": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
}


# ``intended_fieldmap`` is structural (an AcquisitionRef | NotApplicable),
# not provenanced — excluded from this registry.
DISTORTION_CORRECTION_FIELD_META: dict[str, FieldMeta] = {
    "source": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "method": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
}


COREGISTRATION_FIELD_META: dict[str, FieldMeta] = {
    "transform": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "method": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "cost_function": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
    "interpolation": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
}


INTENSITY_CORRECTION_FIELD_META: dict[str, FieldMeta] = {
    "target": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "method": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
}


SPATIAL_NORMALIZATION_FIELD_META: dict[str, FieldMeta] = {
    # ``target_space`` / ``resolution_mm`` are version_default-only (defensible
    # only when a base pipeline is named). KB integration → flip to True later.
    "target_space": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "resolution_mm": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
        unit="mm",
    ),
    "method": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "warp": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "transform_type": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "interpolation": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
    "regularization": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
}


SURFACE_PROJECTION_FIELD_META: dict[str, FieldMeta] = {
    # ``target_surface`` / ``surface_registration`` are version_default-only
    # (defensible only when a base pipeline is named, e.g. HCP MPP → fsLR_32k
    # / MSMAll). KB integration → flip to True later.
    "target_surface": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "vol2surf_sampling": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
    "surface_registration": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "cifti": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
}


ICA_DENOISE_FIELD_META: dict[str, FieldMeta] = {
    "method": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "training_set": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "threshold": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "aggressive": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
}


COMPCOR_FIELD_META: dict[str, FieldMeta] = {
    "variant": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "n_components": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "variance_threshold": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "mask_source": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
}


# Conservative bias: every reported nuisance-regression param defaults to
# extracted-or-missing. Motion-expansion order is high-variance and
# prior-leaky (Extractor never infers it).
NUISANCE_REGRESSION_FIELD_META: dict[str, FieldMeta] = {
    "motion_expansion": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "tissue_regressors": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "physio_regressors": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "physio_n_regressors": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
    "detrend": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
}


DESPIKE_FIELD_META: dict[str, FieldMeta] = {
    "method": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "threshold": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
}


SCRUB_FIELD_META: dict[str, FieldMeta] = {
    "criterion": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "threshold": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "remediation": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "interpolation_method": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
}


TEMPORAL_FILTERING_FIELD_META: dict[str, FieldMeta] = {
    # ``effective_band_hz`` is version_default-only when a base pipeline is
    # named — field_convention defaults would be confirmation-bias. KB
    # integration → flip to True later.
    "effective_band_hz": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
        unit="Hz",
    ),
    "method": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
    "low_hz": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
        unit="Hz",
    ),
    "high_hz": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
        unit="Hz",
    ),
    "order": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=True,
        source="derived",
    ),
    "cutoff": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "scale": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "nominal_band_hz": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
        unit="Hz",
    ),
}


INTENSITY_NORMALIZATION_FIELD_META: dict[str, FieldMeta] = {
    "scope": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    # ``convention`` / ``value`` are version_default-only (defensible only
    # when a base pipeline / software is known). KB integration → flip later.
    "convention": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "value": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
}


SPATIAL_SMOOTHING_FIELD_META: dict[str, FieldMeta] = {
    "fwhm_mm": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
        unit="mm",
    ),
    "space": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="derived",
    ),
    "kernel_type": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
    ),
    "approach": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="derived",
    ),
}


# ---------------------------------------------------------------------------
# Bijection + invariants helpers (mirror v0_1_0._check_arm_bijection /
# _validate_arm_invariants)
# ---------------------------------------------------------------------------


def _check_step_bijection(
    cls: type[BaseModel],
    registry: dict[str, FieldMeta],
) -> None:
    """Each step class's ``ProvenancedField`` attributes must equal its
    registry exactly. Module-level raising guard (not ``assert``: ``python -O``
    strips asserts and would silently disable the check)."""
    structural: frozenset[str] = getattr(cls, "STRUCTURAL_FIELDS", frozenset())
    provenanced = {n for n in cls.model_fields if n not in structural}
    expected = set(registry)
    if provenanced != expected:
        raise RuntimeError(
            f"{cls.__name__} registry/field mismatch: "
            f"missing_from_registry={provenanced - expected}, "
            f"extra_in_registry={expected - provenanced}"
        )


def _validate_step_invariants(
    step: BaseModel,
    registry: dict[str, FieldMeta],
) -> None:
    """field_id↔name consistency + ``inference_applicable`` invariant for one step.

    Raises ``ValueError`` on first violation; called from each step subclass's
    ``model_validator(mode="after")``."""
    structural: frozenset[str] = getattr(type(step), "STRUCTURAL_FIELDS", frozenset())
    for name in type(step).model_fields:
        if name in structural:
            continue
        pf = getattr(step, name)
        if pf.field_id != name:
            raise ValueError(
                f"field_id mismatch: attribute {name!r} has field_id {pf.field_id!r}, "
                f"expected {name!r}"
            )
        meta = registry[name]
        if not meta.inference_applicable and pf.inference.status == "INFERRED_DEFAULT":
            raise ValueError(
                f"{name}: inference_applicable=False — "
                "INFERRED_DEFAULT not permitted; use LEFT_MISSING."
            )


# ---------------------------------------------------------------------------
# Step kinds — one class per ``kind`` discriminator value
#
# Every step model carries:
#   * ``kind: Literal["..."]`` — Pydantic discriminator (plain).
#   * ``cobidas_row: ClassVar[str]`` — COBIDAS D.3 row tag (or DIVERGENCE).
#   * ``STRUCTURAL_FIELDS: ClassVar[frozenset[str]]`` — names excluded from
#     the registry (``"kind"`` always; plus per-step structural pointers
#     like ``intended_fieldmap``).
#   * ``ARM_REGISTRY: ClassVar[dict[str, FieldMeta]]`` — pointer to the
#     per-kind registry.
#   * ``@model_validator(mode="after")`` calling
#     :func:`_validate_step_invariants`.
# ---------------------------------------------------------------------------


# 1. NonsteadystateRemoval — COBIDAS T1 stabilization
class NonsteadystateRemoval(BaseModel):
    kind: Literal["nonsteadystate_removal"] = "nonsteadystate_removal"
    n_nonsteadystate_discarded: ProvenancedField[int]

    cobidas_row: ClassVar[str] = "T1_stabilization"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = NONSTEADYSTATE_REMOVAL_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, NONSTEADYSTATE_REMOVAL_FIELD_META)
        return self


# 2. SliceTimeCorrection — COBIDAS slice time correction
SliceTimingReference = Literal["first", "middle", "specific_slice", "specific_time"]
SliceTimingRelativeToMC = Literal["before", "after"]
SliceTimingInterpolation = Literal["linear", "spline", "sinc"]


class SliceTimeCorrection(BaseModel):
    kind: Literal["slice_time_correction"] = "slice_time_correction"
    reference: ProvenancedField[SliceTimingReference]
    relative_to_motion_correction: ProvenancedField[SliceTimingRelativeToMC]
    interpolation: ProvenancedField[SliceTimingInterpolation]

    cobidas_row: ClassVar[str] = "slice_time_correction"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = SLICE_TIME_CORRECTION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, SLICE_TIME_CORRECTION_FIELD_META)
        return self


# 3. MotionCorrection — COBIDAS motion correction
MotionCorrectionMethod = Literal["mcflirt", "spm_realign", "afni_3dvolreg", "ants", "other"]
MotionReferenceScan = Literal["first", "middle", "mean", "specific"]
MotionSimilarityMetric = Literal["normalized_correlation", "mutual_information", "ssd", "other"]
MotionInterpolation = Literal["linear", "spline", "sinc", "other"]


class MotionCorrection(BaseModel):
    kind: Literal["motion_correction"] = "motion_correction"
    method: ProvenancedField[MotionCorrectionMethod]
    reference_scan: ProvenancedField[MotionReferenceScan]
    similarity_metric: ProvenancedField[MotionSimilarityMetric]
    interpolation: ProvenancedField[MotionInterpolation]
    nonrigid: ProvenancedField[bool]
    transform_type: ProvenancedField[str]
    fieldmap_unwarping: ProvenancedField[bool]
    unwarping_method: ProvenancedField[str]
    slice_to_volume: ProvenancedField[bool]

    cobidas_row: ClassVar[str] = "motion_correction"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = MOTION_CORRECTION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, MOTION_CORRECTION_FIELD_META)
        return self


# 4. DistortionCorrection — COBIDAS distortion + gradient-distortion correction
DistortionSource = Literal["susceptibility_fieldmap", "gradient_nonlinearity", "fieldmap_less"]
DistortionMethod = Literal["topup", "fugue", "gradunwarp", "sdc_fieldmapless", "other"]


class DistortionCorrection(BaseModel):
    kind: Literal["distortion_correction"] = "distortion_correction"
    source: ProvenancedField[DistortionSource]
    method: ProvenancedField[DistortionMethod]
    intended_fieldmap: AcquisitionRef | NotApplicable

    cobidas_row: ClassVar[str] = "distortion_correction"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind", "intended_fieldmap"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = DISTORTION_CORRECTION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, DISTORTION_CORRECTION_FIELD_META)
        return self


# 5. Coregistration — COBIDAS function↔structure intra-subject coregistration
CoregistrationTransform = Literal["rigid", "affine", "nonlinear"]
CoregistrationMethod = Literal["flirt_bbr", "flirt", "spm_coreg", "bbregister", "ants", "other"]
CoregistrationCostFunction = Literal[
    "correlation_ratio", "mutual_information", "boundary_based", "ssd"
]
CoregistrationInterpolation = Literal["linear", "spline", "sinc", "other"]


class Coregistration(BaseModel):
    kind: Literal["coregistration"] = "coregistration"
    transform: ProvenancedField[CoregistrationTransform]
    method: ProvenancedField[CoregistrationMethod]
    cost_function: ProvenancedField[CoregistrationCostFunction]
    interpolation: ProvenancedField[CoregistrationInterpolation]

    cobidas_row: ClassVar[str] = "function_structure_intrasubject_coregistration"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = COREGISTRATION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, COREGISTRATION_FIELD_META)
        return self


# 6. IntensityCorrection — COBIDAS intensity correction
IntensityCorrectionTarget = Literal["bias_field", "interleaved_slice"]
IntensityCorrectionMethod = Literal["n4", "fast_bias", "other"]


class IntensityCorrection(BaseModel):
    kind: Literal["intensity_correction"] = "intensity_correction"
    target: ProvenancedField[IntensityCorrectionTarget]
    method: ProvenancedField[IntensityCorrectionMethod]

    cobidas_row: ClassVar[str] = "intensity_correction"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = INTENSITY_CORRECTION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, INTENSITY_CORRECTION_FIELD_META)
        return self


# 7. SpatialNormalization — COBIDAS intersubject registration (volume only)
TargetSpace = Literal[
    "MNI152NLin6Asym",
    "MNI152NLin2009cAsym",
    "Talairach",
    "native_volume",
    "other",
]
SpatialNormalizationMethod = Literal["fnirt", "ants_syn", "spm_normalise", "dartel", "other"]
WarpType = Literal["rigid", "affine", "nonlinear"]
SpatialNormalizationInterpolation = Literal["linear", "spline", "sinc", "other"]


class SpatialNormalization(BaseModel):
    kind: Literal["spatial_normalization"] = "spatial_normalization"
    target_space: ProvenancedField[TargetSpace]
    resolution_mm: ProvenancedField[float]
    method: ProvenancedField[SpatialNormalizationMethod]
    warp: ProvenancedField[WarpType]
    transform_type: ProvenancedField[str]
    interpolation: ProvenancedField[SpatialNormalizationInterpolation]
    regularization: ProvenancedField[str]

    cobidas_row: ClassVar[str] = "intersubject_registration_volume"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = SPATIAL_NORMALIZATION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, SPATIAL_NORMALIZATION_FIELD_META)
        return self


# 8. SurfaceProjection — DIVERGENCE (split out of intersubject registration)
TargetSurface = Literal[
    "native",
    "fsaverage",
    "fsaverage5",
    "fsaverage6",
    "fsLR_32k",
    "fsLR_164k",
    "other",
]
Vol2SurfSampling = Literal["ribbon_constrained", "trilinear", "nearest"]
SurfaceRegistration = Literal["freesurfer_recon", "msm_sulc", "msm_all", "other"]


class SurfaceProjection(BaseModel):
    kind: Literal["surface_projection"] = "surface_projection"
    target_surface: ProvenancedField[TargetSurface]
    vol2surf_sampling: ProvenancedField[Vol2SurfSampling]
    surface_registration: ProvenancedField[SurfaceRegistration]
    cifti: ProvenancedField[bool]

    cobidas_row: ClassVar[str] = "surface_projection"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = SURFACE_PROJECTION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, SURFACE_PROJECTION_FIELD_META)
        return self


# 9a. ICADenoise — COBIDAS artifact + structured noise removal (sibling)
ICADenoiseMethod = Literal["fix", "aroma"]


class ICADenoise(BaseModel):
    kind: Literal["ica_denoise"] = "ica_denoise"
    method: ProvenancedField[ICADenoiseMethod]
    training_set: ProvenancedField[str]
    threshold: ProvenancedField[float]
    aggressive: ProvenancedField[bool]

    cobidas_row: ClassVar[str] = "artifact_structured_noise_removal"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = ICA_DENOISE_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, ICA_DENOISE_FIELD_META)
        return self


# 9b. CompCor — COBIDAS artifact + structured noise removal (sibling)
CompCorVariant = Literal["a", "t"]


class CompCor(BaseModel):
    kind: Literal["compcor"] = "compcor"
    variant: ProvenancedField[CompCorVariant]
    n_components: ProvenancedField[int]
    variance_threshold: ProvenancedField[float]
    mask_source: ProvenancedField[str]

    cobidas_row: ClassVar[str] = "artifact_structured_noise_removal"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = COMPCOR_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, COMPCOR_FIELD_META)
        return self


# 9c. NuisanceRegression — COBIDAS artifact + structured noise removal (sibling)
MotionExpansion = Literal["none", "6param", "friston24", "volterra"]
TissueRegressor = Literal["whole_brain", "gray_matter", "white_matter", "ventricles"]
PhysioRegressor = Literal["retroicor", "rvt", "none"]
Detrend = Literal["linear", "quadratic", "none"]


class NuisanceRegression(BaseModel):
    kind: Literal["nuisance_regression"] = "nuisance_regression"
    motion_expansion: ProvenancedField[MotionExpansion]
    tissue_regressors: ProvenancedField[list[TissueRegressor]]
    physio_regressors: ProvenancedField[PhysioRegressor]
    physio_n_regressors: ProvenancedField[int]
    detrend: ProvenancedField[Detrend]

    cobidas_row: ClassVar[str] = "artifact_structured_noise_removal"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = NUISANCE_REGRESSION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, NUISANCE_REGRESSION_FIELD_META)
        return self


# 10a. Despike — COBIDAS volume censoring (sibling, early)
DespikeMethod = Literal["afni_3dDespike", "other"]


class Despike(BaseModel):
    kind: Literal["despike"] = "despike"
    method: ProvenancedField[DespikeMethod]
    threshold: ProvenancedField[float]

    cobidas_row: ClassVar[str] = "volume_censoring"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = DESPIKE_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, DESPIKE_FIELD_META)
        return self


# 10b. Scrub — COBIDAS volume censoring (sibling, late)
ScrubCriterion = Literal["fd_power", "fd_jenkinson", "dvars", "bold_pct"]
ScrubRemediation = Literal["censor", "interpolate"]
ScrubInterpolationMethod = Literal["spline", "spectral", "other"]


class Scrub(BaseModel):
    kind: Literal["scrub"] = "scrub"
    criterion: ProvenancedField[ScrubCriterion]
    threshold: ProvenancedField[float]
    remediation: ProvenancedField[ScrubRemediation]
    interpolation_method: ProvenancedField[ScrubInterpolationMethod]

    cobidas_row: ClassVar[str] = "volume_censoring"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = SCRUB_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, SCRUB_FIELD_META)
        return self


# 11. TemporalFiltering — DIVERGENCE (added as a discrete step)
TemporalFilteringMethod = Literal["butterworth_bandpass", "highpass_only", "wavelet_decomposition"]


class TemporalFiltering(BaseModel):
    kind: Literal["temporal_filtering"] = "temporal_filtering"
    # Method-independent canonical band. For butterworth this is the passband;
    # for wavelet this is the scale's nominal frequency support — NOT a passband.
    effective_band_hz: ProvenancedField[tuple[float | None, float | None]]
    method: ProvenancedField[TemporalFilteringMethod]
    # butterworth_bandpass per-method params
    low_hz: ProvenancedField[float]
    high_hz: ProvenancedField[float]
    order: ProvenancedField[int]
    # highpass_only per-method param
    cutoff: ProvenancedField[float]
    # wavelet_decomposition per-method params
    scale: ProvenancedField[int]
    nominal_band_hz: ProvenancedField[tuple[float, float]]

    cobidas_row: ClassVar[str] = "temporal_filtering"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = TEMPORAL_FILTERING_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, TEMPORAL_FILTERING_FIELD_META)
        self._check_band_consistency()
        return self

    def _check_band_consistency(self) -> None:
        """Cross-field check: for ``butterworth_bandpass``, the canonical
        ``effective_band_hz`` must match ``(low_hz, high_hz)`` when all three
        sides are EXTRACTED. For ``wavelet_decomposition``, the canonical band
        must match ``nominal_band_hz`` when both are EXTRACTED. ``highpass_only``
        skips (cutoff units vary; no enforced cross-check)."""

        method_value = _extracted_value(self.method)
        if method_value is None:
            return  # method unknown — nothing to enforce

        eff = _extracted_value(self.effective_band_hz)
        if eff is None:
            return  # canonical band unknown — nothing to enforce

        if method_value == "butterworth_bandpass":
            low = _extracted_value(self.low_hz)
            high = _extracted_value(self.high_hz)
            if low is None or high is None:
                return
            if eff != (low, high):
                raise ValueError(
                    f"temporal_filtering: effective_band_hz={eff} disagrees with "
                    f"(low_hz, high_hz)=({low}, {high}) for method=butterworth_bandpass"
                )
        elif method_value == "wavelet_decomposition":
            nominal = _extracted_value(self.nominal_band_hz)
            if nominal is None:
                return
            if eff != nominal:
                raise ValueError(
                    f"temporal_filtering: effective_band_hz={eff} disagrees with "
                    f"nominal_band_hz={nominal} for method=wavelet_decomposition"
                )


def _extracted_value(pf: ProvenancedField) -> object | None:
    """Return ``pf.extraction.value`` iff status==EXTRACTED, else ``None``.

    Used by cross-field consistency checks that skip when either side is
    Missing/Deferred/Inferred — we never invent a value to compare against."""
    return pf.extraction.value if pf.extraction.status == "EXTRACTED" else None


# 12. IntensityNormalization — COBIDAS intensity normalization (non-mandatory)
IntensityNormalizationScope = Literal["per_run", "global"]
IntensityNormalizationConvention = Literal["spm_grand_mean_100", "fsl_mode_10000", "other"]


class IntensityNormalization(BaseModel):
    kind: Literal["intensity_normalization"] = "intensity_normalization"
    scope: ProvenancedField[IntensityNormalizationScope]
    convention: ProvenancedField[IntensityNormalizationConvention]
    value: ProvenancedField[float]

    cobidas_row: ClassVar[str] = "intensity_normalization"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = INTENSITY_NORMALIZATION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, INTENSITY_NORMALIZATION_FIELD_META)
        return self


# 13. SpatialSmoothing — COBIDAS spatial smoothing
SmoothingSpace = Literal["native_volume", "native_surface", "mni_volume", "template_surface"]
SmoothingKernelType = Literal["gaussian", "other"]
SmoothingApproach = Literal["fixed_kernel", "iterate_to_fwhm"]


class SpatialSmoothing(BaseModel):
    kind: Literal["spatial_smoothing"] = "spatial_smoothing"
    fwhm_mm: ProvenancedField[float]
    space: ProvenancedField[SmoothingSpace]
    kernel_type: ProvenancedField[SmoothingKernelType]
    approach: ProvenancedField[SmoothingApproach]

    cobidas_row: ClassVar[str] = "spatial_smoothing"
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = SPATIAL_SMOOTHING_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, SPATIAL_SMOOTHING_FIELD_META)
        return self


# ---------------------------------------------------------------------------
# Module-level bijection guards — raise on import if any registry diverges
# from its class.
# ---------------------------------------------------------------------------
_check_step_bijection(NonsteadystateRemoval, NONSTEADYSTATE_REMOVAL_FIELD_META)
_check_step_bijection(SliceTimeCorrection, SLICE_TIME_CORRECTION_FIELD_META)
_check_step_bijection(MotionCorrection, MOTION_CORRECTION_FIELD_META)
_check_step_bijection(DistortionCorrection, DISTORTION_CORRECTION_FIELD_META)
_check_step_bijection(Coregistration, COREGISTRATION_FIELD_META)
_check_step_bijection(IntensityCorrection, INTENSITY_CORRECTION_FIELD_META)
_check_step_bijection(SpatialNormalization, SPATIAL_NORMALIZATION_FIELD_META)
_check_step_bijection(SurfaceProjection, SURFACE_PROJECTION_FIELD_META)
_check_step_bijection(ICADenoise, ICA_DENOISE_FIELD_META)
_check_step_bijection(CompCor, COMPCOR_FIELD_META)
_check_step_bijection(NuisanceRegression, NUISANCE_REGRESSION_FIELD_META)
_check_step_bijection(Despike, DESPIKE_FIELD_META)
_check_step_bijection(Scrub, SCRUB_FIELD_META)
_check_step_bijection(TemporalFiltering, TEMPORAL_FILTERING_FIELD_META)
_check_step_bijection(IntensityNormalization, INTENSITY_NORMALIZATION_FIELD_META)
_check_step_bijection(SpatialSmoothing, SPATIAL_SMOOTHING_FIELD_META)


# ---------------------------------------------------------------------------
# Discriminated step union — flat siblings, no nested unions.
# ---------------------------------------------------------------------------
PreprocStep = Annotated[
    NonsteadystateRemoval
    | SliceTimeCorrection
    | MotionCorrection
    | DistortionCorrection
    | Coregistration
    | IntensityCorrection
    | SpatialNormalization
    | SurfaceProjection
    | ICADenoise
    | CompCor
    | NuisanceRegression
    | Despike
    | Scrub
    | TemporalFiltering
    | IntensityNormalization
    | SpatialSmoothing,
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Preprocessing model
# ---------------------------------------------------------------------------
class Preprocessing(BaseModel):
    """One ordered preprocessing pipeline applied to one or more functional
    acquisitions in the same :class:`ReplicationSpec`.

    Validation:
      * Per-kind uniqueness on ``steps`` (one step per ``kind``); sibling
        kinds (``despike`` + ``scrub``; ``ica_denoise`` + ``compcor`` +
        ``nuisance_regression``) are admitted because their ``kind`` values
        differ.
      * ``applies_to`` referential integrity and the functional-partition
        rule (every functional acquisition covered exactly once across all
        ``Preprocessing`` entries in the spec) are enforced at the
        :class:`ReplicationSpec` level.
    """

    applies_to: list[AcquisitionRef] = Field(min_length=1)
    base_pipeline: ProvenancedField[PipelineRef] | NotApplicable
    steps: list[PreprocStep] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_step_uniqueness(self) -> Self:
        kinds: set[str] = set()
        for s in self.steps:
            if s.kind in kinds:
                raise ValueError(f"duplicate preprocessing step kind: {s.kind!r}")
            kinds.add(s.kind)
        return self

    @model_validator(mode="after")
    def _check_base_pipeline_steps_coupling(self) -> Self:
        """Reject the one incoherent combination: ``NotApplicable`` base
        pipeline with empty ``steps`` (no preprocessing at all). Pipeline-as-is
        (``ProvenancedField[PipelineRef]`` + ``steps=[]``), honestly unreported
        (``ProvenancedField[PipelineRef]`` with extraction=MissingFromPaper +
        ``steps=[]``), and deferred (extraction=DeferredToCitation + ``steps=[]``)
        all carry SOME signal about preprocessing and are accepted."""
        if isinstance(self.base_pipeline, NotApplicable) and not self.steps:
            raise ValueError(
                "Preprocessing: base_pipeline=NotApplicable with empty steps "
                "claims no base pipeline and no preprocessing steps — "
                "incoherent for a spec carrying functional data."
            )
        return self

    def steps_in_group(self, cobidas_row: str) -> list[PreprocStep]:
        """Return the (zero or more) steps tagged with the given COBIDAS row.

        Useful for queries like "what artifact-removal steps are in this
        pipeline?" without enumerating sibling kinds at the call site."""
        return [s for s in self.steps if type(s).cobidas_row == cobidas_row]

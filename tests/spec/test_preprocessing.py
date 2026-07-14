"""Verification suite for the v0.1.0 preprocessing group.

Covers:
1. Per-kind uniqueness (sibling kinds can co-occur; same kind twice rejected).
2. ``applies_to`` referential integrity + the ``ReplicationSpec`` functional
   partition (every functional covered exactly once).
3. ``inference_applicable`` invariant per step kind.
4. ``TemporalFiltering`` cross-method band consistency
   (butterworth ↔ low/high; wavelet ↔ nominal_band_hz).
5. ``PipelineRef`` version provenance: Extracted / DeferredToCitation
   (``target_kind="pipeline"``) / InferredDefault (version_default or
   date_inferred_version) / Missing+LeftMissing.
6. Per-step registry bijection + field-id-must-match-attribute-name.
7. Step union discriminator dispatch + JSON schema export.
8. Structural round-trip vs evidence base: Cho HCP / HNU / MSC + Bassett 2011.
9. ``steps_in_group`` helper returns COBIDAS-row siblings.
"""

from __future__ import annotations

import json
import runpy
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from fmri_repro.spec import preprocessing as pp_mod
from fmri_repro.spec.core import ReplicationSpec
from fmri_repro.spec.preprocessing import (
    COMPCOR_FIELD_META,
    COREGISTRATION_FIELD_META,
    DESPIKE_FIELD_META,
    DISTORTION_CORRECTION_FIELD_META,
    ICA_DENOISE_FIELD_META,
    INTENSITY_CORRECTION_FIELD_META,
    INTENSITY_NORMALIZATION_FIELD_META,
    MOTION_CORRECTION_FIELD_META,
    NONSTEADYSTATE_REMOVAL_FIELD_META,
    NUISANCE_REGRESSION_FIELD_META,
    SCRUB_FIELD_META,
    SLICE_TIME_CORRECTION_FIELD_META,
    SPATIAL_NORMALIZATION_FIELD_META,
    SPATIAL_SMOOTHING_FIELD_META,
    SURFACE_PROJECTION_FIELD_META,
    TEMPORAL_FILTERING_FIELD_META,
    CompCor,
    Coregistration,
    Despike,
    DistortionCorrection,
    ICADenoise,
    IntensityCorrection,
    IntensityNormalization,
    MotionCorrection,
    NonsteadystateRemoval,
    NuisanceRegression,
    PipelineRef,
    Preprocessing,
    PreprocStep,
    Scrub,
    SliceTimeCorrection,
    SpatialNormalization,
    SpatialSmoothing,
    SurfaceProjection,
    TemporalFiltering,
    TemporalStandardization,
    _check_step_bijection,
)
from fmri_repro.spec.provenance import (
    DateInferredVersionBasis,
    Deferral,
    DeferredToCitation,
    Extracted,
    FieldConventionBasis,
    InferredDefault,
    LabPriorBasis,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
    VersionDefaultBasis,
)
from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef
from fmri_repro.spec.v0_4_0 import StudySpec as CurrentStudySpec
from tests.spec.test_acquisition import (
    _anatomical_payload,
    _fieldmap_payload,
    _functional_payload,
    _replication_spec_payload,
)

# ---------------------------------------------------------------------------
# ProvenancedField helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_schema.py"


def _span(text: str = "stub", start: int = 0) -> Span:
    return Span(start=start, end=start + len(text), text=text, section="Methods")


def _pf_missing(field_id: str, t: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
        inference=LeftMissing(reason="placeholder"),
    )


def _pf_extracted(field_id: str, value: Any, t: Any, confidence: float = 0.9) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=Extracted[t](
            value=value,
            spans=[_span(str(value))],
            confidence=confidence,
        ),
        inference=NotApplicable(),
    )


def _pf_inferred(
    field_id: str,
    value: Any,
    t: Any,
    basis: Any,
    confidence: float = 0.3,
) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
        inference=InferredDefault[t](
            value=value,
            basis=basis,
            confidence=confidence,
            alternative_inferences=[],
        ),
    )


# ---------------------------------------------------------------------------
# Per-step builders (every reported field defaults to MISSING + LEFT_MISSING
# unless a positive test cares about that field).
# ---------------------------------------------------------------------------


def _nonsteadystate_removal(n_discarded: int | None = None) -> NonsteadystateRemoval:
    n_pf = (
        _pf_extracted("n_nonsteadystate_discarded", n_discarded, int)
        if n_discarded is not None
        else _pf_missing("n_nonsteadystate_discarded", int)
    )
    return NonsteadystateRemoval(n_nonsteadystate_discarded=n_pf)


def _slice_time_correction() -> SliceTimeCorrection:
    return SliceTimeCorrection(
        reference=_pf_missing("reference", str),
        relative_to_motion_correction=_pf_missing("relative_to_motion_correction", str),
        interpolation=_pf_missing("interpolation", str),
    )


def _motion_correction(method: str = "mcflirt") -> MotionCorrection:
    return MotionCorrection(
        method=_pf_extracted("method", method, str),
        reference_scan=_pf_missing("reference_scan", str),
        similarity_metric=_pf_missing("similarity_metric", str),
        interpolation=_pf_missing("interpolation", str),
        nonrigid=_pf_missing("nonrigid", bool),
        transform_type=_pf_missing("transform_type", str),
        fieldmap_unwarping=_pf_missing("fieldmap_unwarping", bool),
        unwarping_method=_pf_missing("unwarping_method", str),
        slice_to_volume=_pf_missing("slice_to_volume", bool),
    )


def _distortion_correction(
    intended_fieldmap: AcquisitionRef | NotApplicable | None = None,
) -> DistortionCorrection:
    return DistortionCorrection(
        source=_pf_missing("source", str),
        method=_pf_missing("method", str),
        intended_fieldmap=intended_fieldmap if intended_fieldmap is not None else NotApplicable(),
    )


def _coregistration() -> Coregistration:
    return Coregistration(
        transform=_pf_missing("transform", str),
        method=_pf_missing("method", str),
        cost_function=_pf_missing("cost_function", str),
        interpolation=_pf_missing("interpolation", str),
    )


def _intensity_correction() -> IntensityCorrection:
    return IntensityCorrection(
        target=_pf_missing("target", str),
        method=_pf_missing("method", str),
    )


def _spatial_normalization() -> SpatialNormalization:
    return SpatialNormalization(
        target_space=_pf_missing("target_space", str),
        resolution_mm=_pf_missing("resolution_mm", float),
        method=_pf_missing("method", str),
        warp=_pf_missing("warp", str),
        transform_type=_pf_missing("transform_type", str),
        interpolation=_pf_missing("interpolation", str),
        regularization=_pf_missing("regularization", str),
    )


def _surface_projection(target_surface: str = "fsLR_32k") -> SurfaceProjection:
    return SurfaceProjection(
        target_surface=_pf_extracted("target_surface", target_surface, str),
        vol2surf_sampling=_pf_missing("vol2surf_sampling", str),
        surface_registration=_pf_missing("surface_registration", str),
        cifti=_pf_missing("cifti", bool),
    )


def _ica_denoise(method: str = "fix") -> ICADenoise:
    return ICADenoise(
        method=_pf_extracted("method", method, str),
        training_set=_pf_missing("training_set", str),
        threshold=_pf_missing("threshold", float),
        aggressive=_pf_missing("aggressive", bool),
    )


def _compcor() -> CompCor:
    return CompCor(
        variant=_pf_missing("variant", str),
        n_components=_pf_missing("n_components", int),
        variance_threshold=_pf_missing("variance_threshold", float),
        mask_source=_pf_missing("mask_source", str),
    )


def _nuisance_regression(motion_expansion: str = "friston24") -> NuisanceRegression:
    return NuisanceRegression(
        motion_expansion=_pf_extracted("motion_expansion", motion_expansion, str),
        tissue_regressors=_pf_extracted(
            "tissue_regressors",
            ["white_matter", "ventricles"],
            list[str],
        ),
        physio_regressors=_pf_missing("physio_regressors", str),
        physio_n_regressors=_pf_missing("physio_n_regressors", int),
        detrend=_pf_extracted("detrend", "linear", str),
        method=_pf_missing("method", str),
        filtering_integrated=_pf_missing("filtering_integrated", bool),
    )


def _despike() -> Despike:
    return Despike(
        method=_pf_extracted("method", "afni_3dDespike", str),
        threshold=_pf_missing("threshold", float),
    )


def _scrub() -> Scrub:
    return Scrub(
        criterion=_pf_extracted("criterion", "fd_power", str),
        threshold=_pf_extracted("threshold", 0.2, float),
        remediation=_pf_extracted("remediation", "censor", str),
        interpolation_method=_pf_missing("interpolation_method", str),
    )


def _temporal_filtering_butter(
    low: float = 0.01,
    high: float = 0.1,
    effective_band: tuple[float | None, float | None] | None = None,
) -> TemporalFiltering:
    band = effective_band if effective_band is not None else (low, high)
    return TemporalFiltering(
        effective_band_hz=_pf_extracted(
            "effective_band_hz", band, tuple[float | None, float | None]
        ),
        method=_pf_extracted("method", "butterworth_bandpass", str),
        low_hz=_pf_extracted("low_hz", low, float),
        high_hz=_pf_extracted("high_hz", high, float),
        order=_pf_missing("order", int),
        cutoff=_pf_missing("cutoff", float),
        scale=_pf_missing("scale", int),
        nominal_band_hz=_pf_missing("nominal_band_hz", tuple[float, float]),
    )


def _temporal_filtering_wavelet(
    scale: int = 2,
    nominal_band: tuple[float, float] = (0.06, 0.12),
    effective_band: tuple[float | None, float | None] | None = None,
) -> TemporalFiltering:
    band = effective_band if effective_band is not None else nominal_band
    return TemporalFiltering(
        effective_band_hz=_pf_extracted(
            "effective_band_hz", band, tuple[float | None, float | None]
        ),
        method=_pf_extracted("method", "wavelet_decomposition", str),
        low_hz=_pf_missing("low_hz", float),
        high_hz=_pf_missing("high_hz", float),
        order=_pf_missing("order", int),
        cutoff=_pf_missing("cutoff", float),
        scale=_pf_extracted("scale", scale, int),
        nominal_band_hz=_pf_extracted("nominal_band_hz", nominal_band, tuple[float, float]),
    )


def _intensity_normalization() -> IntensityNormalization:
    return IntensityNormalization(
        scope=_pf_missing("scope", str),
        convention=_pf_missing("convention", str),
        value=_pf_missing("value", float),
    )


def _spatial_smoothing(fwhm: float = 6.0, space: str = "mni_volume") -> SpatialSmoothing:
    return SpatialSmoothing(
        fwhm_mm=_pf_extracted("fwhm_mm", fwhm, float),
        space=_pf_extracted("space", space, str),
        kernel_type=_pf_missing("kernel_type", str),
        approach=_pf_missing("approach", str),
    )


def _temporal_standardization() -> TemporalStandardization:
    return TemporalStandardization(method=_pf_missing("method", str))


# ---------------------------------------------------------------------------
# Preprocessing + ReplicationSpec assembly helpers
# ---------------------------------------------------------------------------


def _pipeline_ref_extracted(name: str, version: str) -> PipelineRef:
    """Inner ``PipelineRef`` with inner-version Extracted."""
    return PipelineRef(name=name, version=_pf_extracted("version", version, str))


def _pipeline_ref_deferred(name: str, citation: str) -> PipelineRef:
    """Inner ``PipelineRef`` with inner-version DeferredToCitation(target_kind='pipeline')."""
    return PipelineRef(
        name=name,
        version=ProvenancedField[str](
            field_id="version",
            extraction=DeferredToCitation(
                deferrals=[
                    Deferral(ref=citation, span=_span(citation), target_kind="pipeline"),
                ],
                searched_terms=["version"],
                sections_searched=["Methods"],
            ),
            inference=LeftMissing(reason="pipeline version not pinned"),
        ),
    )


def _pipeline_ref_inferred_version_default(name: str, tool: str, value: str) -> PipelineRef:
    """Inner ``PipelineRef`` with inner-version InferredDefault(version_default)."""
    return PipelineRef(
        name=name,
        version=ProvenancedField[str](
            field_id="version",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
            inference=InferredDefault[str](
                value=value,
                basis=VersionDefaultBasis(tool=tool, version=value),
                confidence=0.9,
                alternative_inferences=[],
            ),
        ),
    )


# Wrappers for the OUTER provenance of ``Preprocessing.base_pipeline``.
# Pair an inner-built ``PipelineRef`` (from the helpers above) with an outer
# extraction/inference status.


def _base_pipeline_extracted(pipeline_ref: PipelineRef) -> ProvenancedField[PipelineRef]:
    """Outer Extracted (paper named the base pipeline) + inner version as built."""
    return ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=Extracted[PipelineRef](
            value=pipeline_ref,
            spans=[_span(pipeline_ref.name)],
            confidence=0.9,
        ),
        inference=NotApplicable(),
    )


def _base_pipeline_deferred(citation: str, inner: PipelineRef) -> ProvenancedField[PipelineRef]:
    """Outer DeferredToCitation(target_kind='pipeline') + inferred PipelineRef."""
    return ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=DeferredToCitation(
            deferrals=[
                Deferral(ref=citation, span=_span(citation), target_kind="pipeline"),
            ],
            searched_terms=["base pipeline"],
            sections_searched=["Methods"],
        ),
        inference=InferredDefault[PipelineRef](
            value=inner,
            basis=VersionDefaultBasis(tool=inner.name, version="circa"),
            confidence=0.85,
            alternative_inferences=[],
        ),
    )


def _base_pipeline_missing() -> ProvenancedField[PipelineRef]:
    """Outer MissingFromPaper + LeftMissing — paper said nothing about a base pipeline."""
    return ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=MissingFromPaper(
            searched_terms=["base pipeline", "preprocessing pipeline"],
            sections_searched=["Methods"],
        ),
        inference=LeftMissing(reason="no base pipeline reported"),
    )


def _bold_ref(task: str = "rest") -> AcquisitionRef:
    return AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task=task))


_ACQ_REF_TYPE_ADAPTER: TypeAdapter[AcquisitionRef] = TypeAdapter(AcquisitionRef)


def _bold_ref_payload(task: str = "rest") -> dict[str, Any]:
    return {"suffix": "bold", "entities": {"task": task}}


def _minimal_preprocessing_for_bold(task: str = "rest") -> Preprocessing:
    return Preprocessing(
        applies_to=[_bold_ref(task=task)],
        base_pipeline=NotApplicable(),
        steps=[_nonsteadystate_removal()],
    )


# ---------------------------------------------------------------------------
# 1. Per-kind uniqueness
# ---------------------------------------------------------------------------


def test_two_despike_steps_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        Preprocessing(
            applies_to=[_bold_ref()],
            base_pipeline=NotApplicable(),
            steps=[_despike(), _despike()],
        )
    assert "duplicate preprocessing step kind" in str(excinfo.value)
    assert "despike" in str(excinfo.value)


def test_temporal_standardization_step_accepted_in_preprocessing() -> None:
    # The new terminal step is a distinct kind and is accepted in a steps list.
    prep = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=NotApplicable(),
        steps=[_temporal_standardization()],
    )
    assert [s.kind for s in prep.steps] == ["temporal_standardization"]


def test_despike_and_scrub_accepted_at_different_positions() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=NotApplicable(),
        steps=[_despike(), _motion_correction(), _scrub()],
    )
    assert [s.kind for s in pp.steps] == ["despike", "motion_correction", "scrub"]


def test_ica_denoise_and_nuisance_regression_with_temporal_filter_between_accepted() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=NotApplicable(),
        steps=[
            _ica_denoise(),
            _temporal_filtering_butter(),
            _nuisance_regression(),
        ],
    )
    kinds = [s.kind for s in pp.steps]
    assert kinds == ["ica_denoise", "temporal_filtering", "nuisance_regression"]


def test_two_nuisance_regression_steps_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        Preprocessing(
            applies_to=[_bold_ref()],
            base_pipeline=NotApplicable(),
            steps=[_nuisance_regression(), _nuisance_regression()],
        )
    assert "nuisance_regression" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 2. ``Preprocessing.steps_in_group`` helper
# ---------------------------------------------------------------------------


def test_steps_in_group_returns_volume_censoring_siblings() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=NotApplicable(),
        steps=[_despike(), _motion_correction(), _scrub()],
    )
    censoring = pp.steps_in_group("volume_censoring")
    assert {type(s).__name__ for s in censoring} == {"Despike", "Scrub"}


def test_steps_in_group_returns_artifact_structured_noise_siblings() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=NotApplicable(),
        steps=[_ica_denoise(), _temporal_filtering_butter(), _compcor(), _nuisance_regression()],
    )
    noise = pp.steps_in_group("artifact_structured_noise_removal")
    assert {type(s).__name__ for s in noise} == {"ICADenoise", "CompCor", "NuisanceRegression"}


def test_steps_in_group_returns_empty_when_no_match() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=NotApplicable(),
        steps=[_nonsteadystate_removal()],
    )
    assert pp.steps_in_group("volume_censoring") == []


# ---------------------------------------------------------------------------
# 3. ``applies_to`` referential integrity + functional partition
# ---------------------------------------------------------------------------


def _spec_payload_with_preprocessing(
    acquisitions: list[dict[str, Any]],
    preprocessing_objs: list[Preprocessing],
) -> dict[str, Any]:
    # Build via test_acquisition helper, then override preprocessing.
    payload = _replication_spec_payload(acquisitions)
    payload["preprocessing"] = [json.loads(p.model_dump_json()) for p in preprocessing_objs]
    return payload


def test_applies_to_dangling_ref_rejected() -> None:
    # Reference is to a task that doesn't exist in the spec.
    pp = Preprocessing(
        applies_to=[_bold_ref(task="DOESNOTEXIST")],
        base_pipeline=NotApplicable(),
        steps=[_nonsteadystate_removal()],
    )
    payload = _spec_payload_with_preprocessing(
        acquisitions=[_functional_payload(entities={"task": "rest"})],
        preprocessing_objs=[pp],
    )
    with pytest.raises(ValidationError) as excinfo:
        ReplicationSpec.model_validate(payload)
    msg = str(excinfo.value)
    assert "applies_to" in msg
    assert "DOESNOTEXIST" in msg


def test_functional_uncovered_rejected() -> None:
    # Spec has TWO functionals (rest + nback) but Preprocessing covers only rest.
    pp = _minimal_preprocessing_for_bold(task="rest")
    payload = _spec_payload_with_preprocessing(
        acquisitions=[
            _functional_payload(entities={"task": "rest"}),
            _functional_payload(entities={"task": "nback"}),
        ],
        preprocessing_objs=[pp],
    )
    with pytest.raises(ValidationError) as excinfo:
        ReplicationSpec.model_validate(payload)
    assert "expected exactly 1" in str(excinfo.value)


def test_two_preprocessings_double_covering_one_functional_rejected() -> None:
    pp_a = _minimal_preprocessing_for_bold(task="rest")
    pp_b = _minimal_preprocessing_for_bold(task="rest")
    payload = _spec_payload_with_preprocessing(
        acquisitions=[_functional_payload(entities={"task": "rest"})],
        preprocessing_objs=[pp_a, pp_b],
    )
    with pytest.raises(ValidationError) as excinfo:
        ReplicationSpec.model_validate(payload)
    msg = str(excinfo.value)
    assert "covered by 2" in msg


def test_anatomical_not_required_to_be_covered() -> None:
    # T1w present, no functional → preprocessing may be empty.
    payload = _replication_spec_payload(acquisitions=[_anatomical_payload("T1w")])
    payload["preprocessing"] = []
    spec = ReplicationSpec.model_validate(payload)
    assert spec.preprocessing == []


def test_two_preprocessings_partition_distinct_functionals_accepted() -> None:
    pp_rest = _minimal_preprocessing_for_bold(task="rest")
    pp_nback = _minimal_preprocessing_for_bold(task="nback")
    payload = _spec_payload_with_preprocessing(
        acquisitions=[
            _functional_payload(entities={"task": "rest"}),
            _functional_payload(entities={"task": "nback"}),
        ],
        preprocessing_objs=[pp_rest, pp_nback],
    )
    spec = ReplicationSpec.model_validate(payload)
    assert len(spec.preprocessing) == 2


def test_distortion_correction_intended_fieldmap_resolves() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref(task="rest")],
        base_pipeline=NotApplicable(),
        steps=[
            _distortion_correction(
                intended_fieldmap=AcquisitionRef(
                    suffix="epi", entities=AcquisitionEntities(dir="PA")
                ),
            ),
        ],
    )
    payload = _spec_payload_with_preprocessing(
        acquisitions=[
            _functional_payload(entities={"task": "rest"}),
            _fieldmap_payload(entities={"dir": "PA"}),
        ],
        preprocessing_objs=[pp],
    )
    spec = ReplicationSpec.model_validate(payload)
    step = spec.preprocessing[0].steps[0]
    assert isinstance(step, DistortionCorrection)
    assert isinstance(step.intended_fieldmap, AcquisitionRef)


def test_distortion_correction_intended_fieldmap_dangling_rejected() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref(task="rest")],
        base_pipeline=NotApplicable(),
        steps=[
            _distortion_correction(
                intended_fieldmap=AcquisitionRef(
                    suffix="epi", entities=AcquisitionEntities(dir="AP")
                ),
            ),
        ],
    )
    payload = _spec_payload_with_preprocessing(
        acquisitions=[
            _functional_payload(entities={"task": "rest"}),
            _fieldmap_payload(entities={"dir": "PA"}),  # not AP
        ],
        preprocessing_objs=[pp],
    )
    with pytest.raises(ValidationError) as excinfo:
        ReplicationSpec.model_validate(payload)
    assert "intended_fieldmap" in str(excinfo.value)


def test_distortion_correction_intended_fieldmap_not_applicable_accepted() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref(task="rest")],
        base_pipeline=NotApplicable(),
        steps=[_distortion_correction(intended_fieldmap=NotApplicable())],
    )
    payload = _spec_payload_with_preprocessing(
        acquisitions=[_functional_payload(entities={"task": "rest"})],
        preprocessing_objs=[pp],
    )
    spec = ReplicationSpec.model_validate(payload)
    step = spec.preprocessing[0].steps[0]
    assert isinstance(step, DistortionCorrection)
    assert isinstance(step.intended_fieldmap, NotApplicable)


# ---------------------------------------------------------------------------
# 4. ``inference_applicable`` invariant
# ---------------------------------------------------------------------------


# (step_class, non_flagged_field_name, sample_value, type)
# Covers Fix 3: fields demoted to inference_applicable=False (version_default-
# only candidates; flip to True when the KB lands).
_NON_FLAGGED_CASES: list[tuple[type[BaseModel], str, Any, Any]] = [
    (MotionCorrection, "method", "mcflirt", str),
    (DistortionCorrection, "method", "topup", str),
    (Coregistration, "method", "flirt_bbr", str),
    (ICADenoise, "method", "fix", str),
    (NuisanceRegression, "motion_expansion", "friston24", str),
    (Despike, "method", "afni_3dDespike", str),
    (Scrub, "criterion", "fd_power", str),
    (SpatialSmoothing, "fwhm_mm", 6.0, float),
    (CompCor, "variant", "a", str),
    # Note: target_space, target_surface, convention, effective_band_hz
    # were flipped to inference_applicable=True once the fmri-defaults-kb
    # pipeline registry + kb_client.base_pipeline integration landed.
]


@pytest.mark.parametrize(("step_class", "field_name", "value", "field_type"), _NON_FLAGGED_CASES)
def test_inferred_default_on_non_flagged_field_rejected(
    step_class: type[BaseModel],
    field_name: str,
    value: Any,
    field_type: Any,
) -> None:
    """Each tested field is ``inference_applicable=False`` per the catalog.
    Constructing the step with INFERRED_DEFAULT on that field must raise."""
    builders: dict[type[BaseModel], Callable[[], BaseModel]] = {
        MotionCorrection: _motion_correction,
        DistortionCorrection: _distortion_correction,
        Coregistration: _coregistration,
        ICADenoise: _ica_denoise,
        NuisanceRegression: _nuisance_regression,
        Despike: _despike,
        Scrub: _scrub,
        SpatialSmoothing: _spatial_smoothing,
        CompCor: _compcor,
        SpatialNormalization: _spatial_normalization,
        SurfaceProjection: _surface_projection,
        IntensityNormalization: _intensity_normalization,
        TemporalFiltering: _temporal_filtering_butter,
    }
    # Start from a valid instance, mutate one field to INFERRED_DEFAULT.
    instance = builders[step_class]()
    payload = json.loads(instance.model_dump_json())
    payload[field_name] = json.loads(
        _pf_inferred(
            field_name,
            value,
            field_type,
            basis=FieldConventionBasis(source="test"),
        ).model_dump_json()
    )
    with pytest.raises(ValidationError) as excinfo:
        step_class.model_validate(payload)
    assert "inference_applicable=False" in str(excinfo.value)
    assert field_name in str(excinfo.value)


def test_inferred_default_on_flagged_kernel_type_accepted() -> None:
    """Counter-test: ``SpatialSmoothing.kernel_type`` is inference_applicable=True
    per the catalog — INFERRED_DEFAULT under ceiling must round-trip."""
    smoothing = SpatialSmoothing(
        fwhm_mm=_pf_extracted("fwhm_mm", 6.0, float),
        space=_pf_extracted("space", "mni_volume", str),
        kernel_type=_pf_inferred(
            "kernel_type",
            "gaussian",
            str,
            basis=FieldConventionBasis(source="catalog default"),
            confidence=0.4,
        ),
        approach=_pf_missing("approach", str),
    )
    assert smoothing.kernel_type.inference.status == "INFERRED_DEFAULT"


def test_inferred_default_on_flagged_slice_time_interpolation_accepted() -> None:
    """Counter-test for Fix 3: ``slice_time_correction.interpolation`` remains
    inference_applicable=True (field_convention-defensible)."""
    stc = SliceTimeCorrection(
        reference=_pf_missing("reference", str),
        relative_to_motion_correction=_pf_missing("relative_to_motion_correction", str),
        interpolation=_pf_inferred(
            "interpolation",
            "spline",
            str,
            basis=FieldConventionBasis(source="catalog default"),
            confidence=0.4,
        ),
    )
    assert stc.interpolation.inference.status == "INFERRED_DEFAULT"


def test_inferred_default_on_flagged_temporal_filter_method_accepted() -> None:
    """Counter-test for Fix 3: ``temporal_filtering.method`` remains True
    (field_convention default = butterworth)."""
    payload = json.loads(_temporal_filtering_butter().model_dump_json())
    payload["method"] = json.loads(
        _pf_inferred(
            "method",
            "butterworth_bandpass",
            str,
            basis=FieldConventionBasis(source="RS-FC convention default"),
            confidence=0.4,
        ).model_dump_json()
    )
    tf = TemporalFiltering.model_validate(payload)
    assert tf.method.inference.status == "INFERRED_DEFAULT"


def test_over_basis_ceiling_confidence_rejected_on_step_field() -> None:
    """Smoke: the BASIS_CEILINGS check fires when wrapped inside a step."""
    with pytest.raises(ValidationError) as excinfo:
        SliceTimeCorrection(
            reference=ProvenancedField[str](
                field_id="reference",
                extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
                inference=InferredDefault[str](
                    value="middle",
                    basis=LabPriorBasis(lab_id="x"),
                    confidence=0.60,  # exceeds 0.50 ceiling
                    alternative_inferences=[],
                ),
            ),
            relative_to_motion_correction=_pf_missing("relative_to_motion_correction", str),
            interpolation=_pf_missing("interpolation", str),
        )
    msg = str(excinfo.value)
    assert "confidence 0.6" in msg
    assert "lab_prior" in msg


# ---------------------------------------------------------------------------
# 5. TemporalFiltering cross-method band consistency
# ---------------------------------------------------------------------------


def test_butterworth_effective_band_matches_low_high() -> None:
    tf = _temporal_filtering_butter(low=0.01, high=0.1)
    assert tf.effective_band_hz.extraction.value == (0.01, 0.1)
    assert tf.method.extraction.value == "butterworth_bandpass"


def test_butterworth_effective_band_mismatch_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _temporal_filtering_butter(low=0.01, high=0.1, effective_band=(0.02, 0.2))
    assert "effective_band_hz" in str(excinfo.value)
    assert "butterworth_bandpass" in str(excinfo.value)


def test_wavelet_effective_band_equals_nominal_band() -> None:
    """Honesty check: for wavelet, effective_band_hz IS the nominal band
    (not a passband). The validator requires equality when both Extracted."""
    tf = _temporal_filtering_wavelet(scale=2, nominal_band=(0.06, 0.12))
    assert tf.effective_band_hz.extraction.value == (0.06, 0.12)
    assert tf.nominal_band_hz.extraction.value == (0.06, 0.12)


def test_wavelet_effective_band_mismatch_with_nominal_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        _temporal_filtering_wavelet(
            scale=2,
            nominal_band=(0.06, 0.12),
            effective_band=(0.01, 0.1),
        )
    assert "nominal_band_hz" in str(excinfo.value)


def test_temporal_filtering_skips_check_when_method_missing() -> None:
    """If ``method`` is MISSING, the cross-field check is bypassed (we don't
    invent a method to validate against)."""
    tf = TemporalFiltering(
        effective_band_hz=_pf_extracted(
            "effective_band_hz", (0.01, 0.1), tuple[float | None, float | None]
        ),
        method=_pf_missing("method", str),
        low_hz=_pf_missing("low_hz", float),
        high_hz=_pf_missing("high_hz", float),
        order=_pf_missing("order", int),
        cutoff=_pf_missing("cutoff", float),
        scale=_pf_missing("scale", int),
        nominal_band_hz=_pf_missing("nominal_band_hz", tuple[float, float]),
    )
    assert tf.effective_band_hz.extraction.value == (0.01, 0.1)


# ---------------------------------------------------------------------------
# 6. PipelineRef.version provenance variants
# ---------------------------------------------------------------------------


def test_pipeline_ref_version_extracted_round_trip() -> None:
    pr = _pipeline_ref_extracted("HCP MPP", "2013.10")
    again = PipelineRef.model_validate_json(pr.model_dump_json())
    assert again == pr
    assert pr.version.extraction.status == "EXTRACTED"


def test_pipeline_ref_version_deferred_to_citation_pipeline() -> None:
    pr = _pipeline_ref_deferred("CCS", citation="Xu 2015")
    again = PipelineRef.model_validate_json(pr.model_dump_json())
    assert again == pr
    assert pr.version.extraction.status == "DEFERRED_TO_CITATION"
    assert pr.version.extraction.deferrals[0].target_kind == "pipeline"


def test_pipeline_ref_version_inferred_version_default() -> None:
    pr = _pipeline_ref_inferred_version_default("fMRIPrep", "fMRIPrep", "23.2.1")
    again = PipelineRef.model_validate_json(pr.model_dump_json())
    assert again == pr
    assert pr.version.inference.status == "INFERRED_DEFAULT"


def test_pipeline_ref_version_inferred_date_inferred() -> None:
    pr = PipelineRef(
        name="HCP MPP",
        version=ProvenancedField[str](
            field_id="version",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
            inference=InferredDefault[str](
                value="2013-circa",
                basis=DateInferredVersionBasis(
                    tool="HCP MPP",
                    inferred_version="2013-circa",
                    paper_date=date(2013, 10, 15),
                ),
                confidence=0.7,
                alternative_inferences=[],
            ),
        ),
    )
    again = PipelineRef.model_validate_json(pr.model_dump_json())
    assert again == pr
    assert pr.version.inference.basis.basis_type == "date_inferred_version"


def test_base_pipeline_not_applicable_round_trips() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=NotApplicable(),
        steps=[_motion_correction()],
    )
    again = Preprocessing.model_validate_json(pp.model_dump_json())
    assert again == pp
    assert isinstance(pp.base_pipeline, NotApplicable)


def test_base_pipeline_provenanced_round_trips() -> None:
    """Outer ProvenancedField[PipelineRef] arm round-trips, with nested
    inner ``PipelineRef.version`` provenance preserved."""
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=_base_pipeline_extracted(
            _pipeline_ref_deferred("HCP MPP", "Glasser 2013"),
        ),
        steps=[_motion_correction()],
    )
    again = Preprocessing.model_validate_json(pp.model_dump_json())
    assert again == pp
    assert isinstance(pp.base_pipeline, ProvenancedField)
    assert pp.base_pipeline.extraction.status == "EXTRACTED"
    assert pp.base_pipeline.extraction.value.name == "HCP MPP"


def test_base_pipeline_outer_deferred_to_citation_pipeline_round_trips() -> None:
    """Outer DeferredToCitation(target_kind='pipeline') is the canonical
    encoding when a paper cites the pipeline without naming a specific version."""
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=_base_pipeline_deferred(
            citation="Glasser 2013",
            inner=_pipeline_ref_inferred_version_default("HCP MPP", "HCP MPP", "2013-circa"),
        ),
        steps=[],
    )
    again = Preprocessing.model_validate_json(pp.model_dump_json())
    assert again == pp
    assert isinstance(pp.base_pipeline, ProvenancedField)
    assert pp.base_pipeline.extraction.status == "DEFERRED_TO_CITATION"
    assert pp.base_pipeline.extraction.deferrals[0].target_kind == "pipeline"


def test_base_pipeline_name_extracted_plus_inner_version_inferred() -> None:
    """Outer Extracted (paper named the pipeline) AND inner version
    InferredDefault (Configurator filled the version)."""
    inner = _pipeline_ref_inferred_version_default("HCP MPP", "HCP MPP", "v4.3.0")
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=_base_pipeline_extracted(inner),
        steps=[],
    )
    again = Preprocessing.model_validate_json(pp.model_dump_json())
    assert again == pp
    assert pp.base_pipeline.extraction.status == "EXTRACTED"
    assert pp.base_pipeline.extraction.value.version.inference.status == "INFERRED_DEFAULT"


def test_base_pipeline_outer_missing_round_trips() -> None:
    """Outer MissingFromPaper (paper silent) + steps=[] (honestly unreported)."""
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=_base_pipeline_missing(),
        steps=[],
    )
    again = Preprocessing.model_validate_json(pp.model_dump_json())
    assert again == pp
    assert pp.base_pipeline.extraction.status == "MISSING_FROM_PAPER"
    assert pp.base_pipeline.inference.status == "LEFT_MISSING"


def test_inner_version_over_ceiling_confidence_rejected() -> None:
    """The BASIS_CEILINGS check applies independently at the nested
    ``PipelineRef.version`` level."""
    with pytest.raises(ValidationError) as excinfo:
        PipelineRef(
            name="HCP MPP",
            version=ProvenancedField[str](
                field_id="version",
                extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
                inference=InferredDefault[str](
                    value="v1",
                    basis=VersionDefaultBasis(tool="HCP MPP", version="v1"),
                    confidence=0.96,  # exceeds version_default ceiling 0.95
                    alternative_inferences=[],
                ),
            ),
        )
    assert "version_default" in str(excinfo.value)


def test_outer_couple_stages_enforced_on_base_pipeline() -> None:
    """Outer ``couple_stages``: MissingFromPaper + NotApplicable rejected."""
    with pytest.raises(ValidationError) as excinfo:
        ProvenancedField[PipelineRef](
            field_id="base_pipeline",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
            inference=NotApplicable(),
        )
    assert "MISSING_FROM_PAPER" in str(excinfo.value)


def test_inner_couple_stages_enforced_on_pipeline_version() -> None:
    """Inner ``couple_stages`` on PipelineRef.version: Missing + NotApplicable rejected
    even when nested inside an outer Extracted[PipelineRef]."""
    with pytest.raises(ValidationError) as excinfo:
        ProvenancedField[PipelineRef](
            field_id="base_pipeline",
            extraction=Extracted[PipelineRef](
                value=PipelineRef(
                    name="HCP MPP",
                    version=ProvenancedField[str](
                        field_id="version",
                        extraction=MissingFromPaper(searched_terms=[], sections_searched=[]),
                        inference=NotApplicable(),  # illegal coupling
                    ),
                ),
                spans=[_span("HCP MPP")],
                confidence=0.9,
            ),
            inference=NotApplicable(),
        )
    msg = str(excinfo.value)
    assert (
        "MISSING_FROM_PAPER" in msg
        or "couple_stages" in msg.lower()
        or "INFERRED_DEFAULT or LEFT_MISSING" in msg
    )


def test_pipeline_version_deferred_plus_not_applicable_rejected() -> None:
    """``couple_stages``: DEFERRED_TO_CITATION cannot pair with NOT_APPLICABLE."""
    with pytest.raises(ValidationError) as excinfo:
        ProvenancedField[str](
            field_id="version",
            extraction=DeferredToCitation(
                deferrals=[
                    Deferral(ref="HCP MPP", span=_span(), target_kind="pipeline"),
                ],
                searched_terms=[],
                sections_searched=["Methods"],
            ),
            inference=NotApplicable(),
        )
    assert "DEFERRED_TO_CITATION" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 7. Per-step bijection + field-id consistency
# ---------------------------------------------------------------------------


_STEP_REGISTRY_PAIRS: list[tuple[type, dict, str]] = [
    (NonsteadystateRemoval, NONSTEADYSTATE_REMOVAL_FIELD_META, "n_nonsteadystate_discarded"),
    (SliceTimeCorrection, SLICE_TIME_CORRECTION_FIELD_META, "reference"),
    (MotionCorrection, MOTION_CORRECTION_FIELD_META, "method"),
    (DistortionCorrection, DISTORTION_CORRECTION_FIELD_META, "source"),
    (Coregistration, COREGISTRATION_FIELD_META, "transform"),
    (IntensityCorrection, INTENSITY_CORRECTION_FIELD_META, "target"),
    (SpatialNormalization, SPATIAL_NORMALIZATION_FIELD_META, "target_space"),
    (SurfaceProjection, SURFACE_PROJECTION_FIELD_META, "target_surface"),
    (ICADenoise, ICA_DENOISE_FIELD_META, "method"),
    (CompCor, COMPCOR_FIELD_META, "variant"),
    (NuisanceRegression, NUISANCE_REGRESSION_FIELD_META, "motion_expansion"),
    (Despike, DESPIKE_FIELD_META, "method"),
    (Scrub, SCRUB_FIELD_META, "criterion"),
    (TemporalFiltering, TEMPORAL_FILTERING_FIELD_META, "method"),
    (IntensityNormalization, INTENSITY_NORMALIZATION_FIELD_META, "scope"),
    (SpatialSmoothing, SPATIAL_SMOOTHING_FIELD_META, "fwhm_mm"),
]


def test_all_steps_bijective_on_unmodified_state() -> None:
    for step_class, registry, _ in _STEP_REGISTRY_PAIRS:
        _check_step_bijection(step_class, registry)


@pytest.mark.parametrize(
    ("step_class", "registry", "victim"),
    _STEP_REGISTRY_PAIRS,
)
def test_step_bijection_rejects_missing_registry_entry(
    step_class: type,
    registry: dict,
    victim: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(registry, victim)
    with pytest.raises(RuntimeError, match="registry/field mismatch"):
        _check_step_bijection(step_class, registry)


def test_field_id_must_match_attribute_name() -> None:
    """If a step is constructed with a mismatched ``field_id``, the
    per-step ``_validate_step_invariants`` rejects it."""
    bad_method = ProvenancedField[str](
        field_id="WRONG",
        extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
        inference=LeftMissing(reason="x"),
    )
    with pytest.raises(ValidationError) as excinfo:
        MotionCorrection(
            method=bad_method,
            reference_scan=_pf_missing("reference_scan", str),
            similarity_metric=_pf_missing("similarity_metric", str),
            interpolation=_pf_missing("interpolation", str),
            nonrigid=_pf_missing("nonrigid", bool),
            transform_type=_pf_missing("transform_type", str),
            fieldmap_unwarping=_pf_missing("fieldmap_unwarping", bool),
            unwarping_method=_pf_missing("unwarping_method", str),
            slice_to_volume=_pf_missing("slice_to_volume", bool),
        )
    assert "field_id mismatch" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 8. Discriminator dispatch + round-trip via the union
# ---------------------------------------------------------------------------


_STEP_BUILDERS: dict[str, Any] = {
    "nonsteadystate_removal": _nonsteadystate_removal,
    "slice_time_correction": _slice_time_correction,
    "motion_correction": _motion_correction,
    "distortion_correction": _distortion_correction,
    "coregistration": _coregistration,
    "intensity_correction": _intensity_correction,
    "spatial_normalization": _spatial_normalization,
    "surface_projection": _surface_projection,
    "ica_denoise": _ica_denoise,
    "compcor": _compcor,
    "nuisance_regression": _nuisance_regression,
    "despike": _despike,
    "scrub": _scrub,
    "temporal_filtering": _temporal_filtering_butter,
    "intensity_normalization": _intensity_normalization,
    "spatial_smoothing": _spatial_smoothing,
    "temporal_standardization": _temporal_standardization,
}


_STEP_UNION_ADAPTER: TypeAdapter[PreprocStep] = TypeAdapter(PreprocStep)


@pytest.mark.parametrize("kind", sorted(_STEP_BUILDERS.keys()))
def test_step_discriminator_dispatch(kind: str) -> None:
    instance = _STEP_BUILDERS[kind]()
    payload = json.loads(instance.model_dump_json())
    parsed = _STEP_UNION_ADAPTER.validate_python(payload)
    assert parsed.kind == kind
    assert type(parsed) is type(instance)


@pytest.mark.parametrize("kind", sorted(_STEP_BUILDERS.keys()))
def test_each_step_round_trips_via_union(kind: str) -> None:
    instance = _STEP_BUILDERS[kind]()
    js = _STEP_UNION_ADAPTER.dump_json(instance)
    again = _STEP_UNION_ADAPTER.validate_json(js)
    assert again == instance


def test_preprocstep_union_in_json_schema_export() -> None:
    schema = _STEP_UNION_ADAPTER.json_schema()
    blob = json.dumps(schema)
    for cls_name in (
        "NonsteadystateRemoval",
        "SliceTimeCorrection",
        "MotionCorrection",
        "DistortionCorrection",
        "BrainExtraction",
        "Segmentation",
        "Coregistration",
        "IntensityCorrection",
        "SpatialNormalization",
        "SurfaceProjection",
        "ICADenoise",
        "CompCor",
        "NuisanceRegression",
        "Despike",
        "Scrub",
        "TemporalFiltering",
        "IntensityNormalization",
        "SpatialSmoothing",
        "TemporalStandardization",
    ):
        assert cls_name in blob, f"{cls_name} missing from PreprocStep schema"


def test_unknown_kind_rejected() -> None:
    bad_payload = {"kind": "NOTREAL"}
    with pytest.raises(ValidationError) as excinfo:
        _STEP_UNION_ADAPTER.validate_python(bad_payload)
    msg = str(excinfo.value).lower()
    assert "discriminator" in msg or "tag" in msg or "kind" in msg


# ---------------------------------------------------------------------------
# 9. ``Preprocessing`` cardinality + base_pipeline/steps coupling
# ---------------------------------------------------------------------------


def test_steps_empty_allowed_with_provenanced_base_pipeline() -> None:
    """Pipeline-as-is: paper named the base pipeline (Extracted), no added steps."""
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=_base_pipeline_extracted(_pipeline_ref_extracted("HCP MPP", "v4.3.0")),
        steps=[],
    )
    assert pp.steps == []


def test_steps_empty_allowed_with_deferred_base_pipeline() -> None:
    """Pipeline-as-is alternative: paper deferred to citation, no added steps."""
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=_base_pipeline_deferred(
            citation="Glasser 2013",
            inner=_pipeline_ref_inferred_version_default("HCP MPP", "HCP MPP", "2013-circa"),
        ),
        steps=[],
    )
    assert pp.base_pipeline.extraction.status == "DEFERRED_TO_CITATION"


def test_steps_empty_allowed_with_missing_base_pipeline() -> None:
    """Honestly unreported: paper silent, no inference, no steps. Allowed."""
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=_base_pipeline_missing(),
        steps=[],
    )
    assert pp.base_pipeline.extraction.status == "MISSING_FROM_PAPER"


def test_not_applicable_base_with_empty_steps_rejected() -> None:
    """The single incoherent combo: NotApplicable (no base pipeline) + steps=[]
    (no preprocessing) = no preprocessing at all, which contradicts having
    functional data."""
    with pytest.raises(ValidationError) as excinfo:
        Preprocessing(
            applies_to=[_bold_ref()],
            base_pipeline=NotApplicable(),
            steps=[],
        )
    msg = str(excinfo.value)
    assert "NotApplicable" in msg or "incoherent" in msg


def test_not_applicable_base_with_steps_accepted() -> None:
    """Bassett-style: no base pipeline, but explicit step list. Allowed."""
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=NotApplicable(),
        steps=[_motion_correction()],
    )
    assert isinstance(pp.base_pipeline, NotApplicable)
    assert len(pp.steps) == 1


def test_preprocessing_applies_to_min_length_one() -> None:
    with pytest.raises(ValidationError):
        Preprocessing(
            applies_to=[],
            base_pipeline=NotApplicable(),
            steps=[_motion_correction()],
        )


# ---------------------------------------------------------------------------
# 10. Structural round-trip vs evidence base
#
# Each builds a ReplicationSpec with the prescribed step list, validates,
# and round-trips JSON. Field-level fidelity is deliberately shallow — the
# point is to prove the model accepts the structural shape claimed by each
# paper.
# ---------------------------------------------------------------------------


def _spec_with(
    acquisitions: list[dict[str, Any]],
    preprocessing_objs: list[Preprocessing],
) -> ReplicationSpec:
    payload = _spec_payload_with_preprocessing(acquisitions, preprocessing_objs)
    return cast(ReplicationSpec, ReplicationSpec.model_validate(payload))


def test_cho_hcp_preprocessing_validates() -> None:
    """Cho HCP: HCP-minimal base pipeline (outer Deferred + inner version
    inferred via version_default) + surface-aware steps. Real build → validate."""
    pp = Preprocessing(
        applies_to=[_bold_ref(task="rest")],
        base_pipeline=_base_pipeline_deferred(
            citation="Glasser 2013",
            inner=_pipeline_ref_inferred_version_default("HCP MPP", "HCP MPP", "v4.3.0"),
        ),
        steps=[
            _motion_correction(method="mcflirt"),
            _surface_projection(target_surface="fsLR_32k"),
            _nuisance_regression(motion_expansion="friston24"),
            _temporal_filtering_butter(low=0.01, high=0.1),
            _spatial_smoothing(fwhm=6.0, space="template_surface"),
            _ica_denoise(method="fix"),
        ],
    )
    spec = _spec_with(
        acquisitions=[_functional_payload(entities={"task": "rest"})],
        preprocessing_objs=[pp],
    )
    again = ReplicationSpec.model_validate_json(spec.model_dump_json())
    assert again == spec
    pp_back = spec.preprocessing[0]
    assert isinstance(pp_back.base_pipeline, ProvenancedField)
    assert pp_back.base_pipeline.extraction.status == "DEFERRED_TO_CITATION"


def test_cho_hnu_preprocessing_validates() -> None:
    """Cho HNU: CCS base (outer Extracted + inner version Deferred) +
    despike early + drop-TR + motion + nuisance + filter."""
    pp = Preprocessing(
        applies_to=[_bold_ref(task="rest")],
        base_pipeline=_base_pipeline_extracted(
            _pipeline_ref_deferred("CCS", citation="Xu 2015"),
        ),
        steps=[
            _nonsteadystate_removal(n_discarded=4),
            _despike(),
            _motion_correction(method="mcflirt"),
            _nuisance_regression(motion_expansion="friston24"),
            _temporal_filtering_butter(low=0.01, high=0.1),
        ],
    )
    spec = _spec_with(
        acquisitions=[_functional_payload(entities={"task": "rest"})],
        preprocessing_objs=[pp],
    )
    again = ReplicationSpec.model_validate_json(spec.model_dump_json())
    assert again == spec
    pp_back = spec.preprocessing[0]
    assert pp_back.base_pipeline.extraction.value.name == "CCS"


def test_cho_msc_preprocessing_validates() -> None:
    """Cho MSC: lighter pipeline (outer Missing + inner Inferred via
    version_default) + motion + smoothing."""
    pp = Preprocessing(
        applies_to=[_bold_ref(task="rest")],
        base_pipeline=ProvenancedField[PipelineRef](
            field_id="base_pipeline",
            extraction=MissingFromPaper(searched_terms=["pipeline"], sections_searched=["Methods"]),
            inference=InferredDefault[PipelineRef](
                value=_pipeline_ref_inferred_version_default("fMRIPrep", "fMRIPrep", "23.2.1"),
                basis=VersionDefaultBasis(tool="fMRIPrep", version="23.2.1"),
                confidence=0.9,
                alternative_inferences=[],
            ),
        ),
        steps=[
            _motion_correction(method="mcflirt"),
            _spatial_smoothing(fwhm=6.0, space="mni_volume"),
        ],
    )
    spec = _spec_with(
        acquisitions=[_functional_payload(entities={"task": "rest"})],
        preprocessing_objs=[pp],
    )
    again = ReplicationSpec.model_validate_json(spec.model_dump_json())
    assert again == spec
    pp_back = spec.preprocessing[0]
    assert pp_back.base_pipeline.inference.status == "INFERRED_DEFAULT"


def test_bassett_2011_preprocessing_validates() -> None:
    """Bassett 2011: hand-rolled FSL pipeline → ``base_pipeline=NotApplicable``
    (the from-scratch arm of the 2-arm union), with steps non-empty.
    Wavelet-based temporal filtering (scale-two band ~ 0.06-0.12 Hz)."""
    pp = Preprocessing(
        applies_to=[_bold_ref(task="motor_learning")],
        base_pipeline=NotApplicable(),
        steps=[
            _motion_correction(method="mcflirt"),
            _spatial_smoothing(fwhm=8.0, space="mni_volume"),
            _temporal_filtering_wavelet(scale=2, nominal_band=(0.06, 0.12)),
        ],
    )
    spec = _spec_with(
        acquisitions=[_functional_payload(entities={"task": "motor_learning"})],
        preprocessing_objs=[pp],
    )
    again = ReplicationSpec.model_validate_json(spec.model_dump_json())
    assert again == spec
    pp_back = spec.preprocessing[0]
    assert isinstance(pp_back.base_pipeline, NotApplicable)


# ---------------------------------------------------------------------------
# 11. Schema export contains all 16 preprocessing kinds + PipelineRef
# ---------------------------------------------------------------------------


def test_schema_export_contains_all_preprocessing_kinds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(EXPORT_SCRIPT.parent))
    try:
        runpy.run_path(str(EXPORT_SCRIPT), run_name="__main__")
    finally:
        sys.path.remove(str(EXPORT_SCRIPT.parent))

    version = CurrentStudySpec.model_fields["schema_version"].default
    out_path = tmp_path / "schema" / f"study_spec-{version}.schema.json"
    schema = json.loads(out_path.read_text())
    def_names = "\n".join(schema["$defs"].keys())
    for name in (
        "Preprocessing",
        "PipelineRef",
        "NonsteadystateRemoval",
        "SliceTimeCorrection",
        "MotionCorrection",
        "DistortionCorrection",
        "BrainExtraction",
        "Segmentation",
        "Coregistration",
        "IntensityCorrection",
        "SpatialNormalization",
        "SurfaceProjection",
        "ICADenoise",
        "CompCor",
        "NuisanceRegression",
        "Despike",
        "Scrub",
        "TemporalFiltering",
        "IntensityNormalization",
        "SpatialSmoothing",
        "TemporalStandardization",
    ):
        assert name in def_names, f"{name!r} not in $defs"


# ---------------------------------------------------------------------------
# 12. Sanity: empty preprocessing rejected when functionals are present
# ---------------------------------------------------------------------------


def test_empty_preprocessing_with_functional_rejected() -> None:
    payload = _replication_spec_payload(
        acquisitions=[_functional_payload(entities={"task": "rest"})],
    )
    payload["preprocessing"] = []
    with pytest.raises(ValidationError) as excinfo:
        ReplicationSpec.model_validate(payload)
    assert "preprocessing is empty" in str(excinfo.value)


# ---------------------------------------------------------------------------
# v0.3.0: anatomical-target steps + tool/method separation
# ---------------------------------------------------------------------------


def _brain_extraction(method: str = "bet") -> pp_mod.BrainExtraction:
    return pp_mod.BrainExtraction(
        method=_pf_extracted("method", method, str),
        manual_edits=_pf_missing("manual_edits", bool),
    )


def _segmentation() -> pp_mod.Segmentation:
    return pp_mod.Segmentation(
        method=_pf_extracted("method", "fsl_fast", str),
        tissue_classes=_pf_extracted(
            "tissue_classes", ["gray_matter", "white_matter", "csf"], list
        ),
    )


def test_v0_3_0_ants_added_to_spatial_normalization_method() -> None:
    # Additive: the new tool member validates, and every prior value still does.
    for m in ("ants", "fnirt", "ants_syn", "spm_normalise", "dartel", "other"):
        pf = ProvenancedField[pp_mod.SpatialNormalizationMethod](
            field_id="method",
            extraction=Extracted[pp_mod.SpatialNormalizationMethod](
                value=m, spans=[_span(m)], confidence=0.9
            ),
            inference=NotApplicable(),
        )
        assert pf.extraction.value == m


def test_v0_3_0_nuisance_regression_method_and_filtering_integrated_roundtrip() -> None:
    for integrated in (True, False):
        nr = pp_mod.NuisanceRegression(
            motion_expansion=_pf_missing("motion_expansion", str),
            tissue_regressors=_pf_missing("tissue_regressors", list),
            physio_regressors=_pf_missing("physio_regressors", str),
            physio_n_regressors=_pf_missing("physio_n_regressors", int),
            detrend=_pf_missing("detrend", str),
            method=_pf_extracted("method", "afni_3dtproject", str),
            filtering_integrated=_pf_extracted("filtering_integrated", integrated, bool),
        )
        back = pp_mod.NuisanceRegression.model_validate_json(nr.model_dump_json())
        assert back.method.extraction.value == "afni_3dtproject"
        assert back.filtering_integrated.extraction.value is integrated


def test_v0_3_0_both_new_kinds_roundtrip_through_union() -> None:
    adapter: TypeAdapter[PreprocStep] = TypeAdapter(PreprocStep)
    for step in (_brain_extraction(), _segmentation()):
        again = adapter.validate_json(adapter.dump_json(step))
        assert type(again) is type(step)
        assert again == step


def test_v0_3_0_anatomical_steps_accepted_before_coregistration() -> None:
    pp = Preprocessing(
        applies_to=[_bold_ref()],
        base_pipeline=NotApplicable(),
        steps=[_brain_extraction(), _segmentation()],
    )
    assert [s.kind for s in pp.steps] == ["brain_extraction", "segmentation"]


def test_v0_3_0_duplicate_brain_extraction_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        Preprocessing(
            applies_to=[_bold_ref()],
            base_pipeline=NotApplicable(),
            steps=[_brain_extraction(), _brain_extraction()],
        )
    assert "duplicate preprocessing step kind" in str(excinfo.value)
    assert "brain_extraction" in str(excinfo.value)


def test_v0_3_0_step_invariant_fires_on_field_id_mismatch() -> None:
    # BrainExtraction: manual_edits carries a wrong field_id -> validator raises.
    with pytest.raises(ValidationError, match="field_id mismatch"):
        pp_mod.BrainExtraction(
            method=_pf_extracted("method", "bet", str),
            manual_edits=_pf_missing("WRONG", bool),
        )
    # Segmentation: tissue_classes carries a wrong field_id -> validator raises.
    with pytest.raises(ValidationError, match="field_id mismatch"):
        pp_mod.Segmentation(
            method=_pf_extracted("method", "fsl_fast", str),
            tissue_classes=_pf_missing("WRONG", list),
        )


def test_v0_3_0_version_and_frozen_predecessors() -> None:
    # Predecessors are demoted to version constants; only v0.4.0 has a live StudySpec root.
    from fmri_repro.spec import v0_1_0, v0_2_0

    assert CurrentStudySpec.model_fields["schema_version"].default == "0.4.0"
    assert v0_1_0.SCHEMA_VERSION == "0.1.0"
    assert v0_2_0.SCHEMA_VERSION == "0.2.0"


def test_v0_3_0_native_preprocessing_stamp() -> None:
    prep = Preprocessing(
        applies_to=[_bold_ref()], base_pipeline=NotApplicable(), steps=[_brain_extraction()]
    )
    # A natively-written document: schema_version == written_under, no migration record.
    assert prep.schema_version == "0.4.0"
    assert prep.written_under == "0.4.0"
    assert prep.written_under_inferred is False
    assert prep.migration is None
    # written_under survives a round-trip (normalized from None on input).
    assert Preprocessing.model_validate_json(prep.model_dump_json()).written_under == "0.4.0"


def test_v0_3_0_migration_record_requires_divergent_written_under() -> None:
    # A migration record on a document whose written_under == schema_version is incoherent
    # (that is a native document, not a migrated one) -> rejected.
    with pytest.raises(ValidationError, match="written_under == schema_version"):
        Preprocessing(
            written_under="0.4.0",
            migration=pp_mod.MigrationInfo(migrated_from="0.2.0", migrator_version="x"),
            applies_to=[_bold_ref()],
            base_pipeline=NotApplicable(),
            steps=[_brain_extraction()],
        )


# Silence ruff: keep the unused import alive (it's a tested module).
_ = pp_mod

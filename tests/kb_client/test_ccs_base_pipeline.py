"""CCS gate tests for fmri_repro.kb_client.base_pipeline.

Mirrors tests/kb_client/test_base_pipeline.py (the HCP minimal cases) on the
CCS pipeline seeded in fmri-defaults-kb/kb/pipelines/ccs.yaml. CCS is the
contrast case:

- No within-pipeline keying: the 2015 paper-anchored entry and the 2021
  commit checkpoint carry IDENTICAL defaults (HCP keys surface_registration
  FS→MSMSulc; CCS keys nothing).
- Only FIVE KB-backed fields are pinned (HCP pins six concrete + one
  not_applicable). CCS deliberately omits surface_projection.target_surface
  and temporal_filtering.effective_band_hz (Xu 2015 documents both as
  user-configurable), so the fixture has NO TemporalFiltering step at all
  (Position A — CCS makes filtering optional).

The option-(a) gate must behave identically on this no-within-keying
pipeline: a date_inferred_version leaves the five fields LeftMissing; a
certain version fires exactly five version_default fills.
"""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from fmri_repro.kb_client.base_pipeline import (
    fill_dependent_defaults,
    infer_base_pipeline_version,
)
from fmri_repro.spec.preprocessing import (
    IntensityNormalization,
    PipelineRef,
    Preprocessing,
    SpatialNormalization,
    SurfaceProjection,
    TemporalFiltering,
)
from fmri_repro.spec.provenance import (
    BASIS_CEILINGS,
    Deferral,
    DeferredToCitation,
    Extracted,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
)
from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef

# A 2021 paper that cites CCS without pinning a commit. The latest CCS version
# record on or before this date is "2015" (the commit checkpoint is dated
# 2021-11-08, after this date), so resolve_version lands on "2015" via the
# date_inferred_version arm — version_certain=False.
CCS_PAPER_DATE = date(2021, 6, 1)

# The five fields CCS pins (kb/pipelines/ccs.yaml). target_surface and
# effective_band_hz are deliberately NOT pinned.
CCS_FILLED: tuple[tuple[type, str, Any], ...] = (
    (SpatialNormalization, "target_space", "MNI152NLin6Asym"),
    (SpatialNormalization, "resolution_mm", 3),
    (SurfaceProjection, "surface_registration", "freesurfer_recon"),
    (IntensityNormalization, "convention", "fsl_grand_mean_10000"),
    (IntensityNormalization, "value", 10000),
)


# --- fixture helpers (mirror tests/kb_client/test_base_pipeline.py) ---------


def _span(text: str = "stub", start: int = 0) -> Span:
    return Span(start=start, end=start + len(text), text=text, section="Methods")


def _pf_missing(field_id: str, t: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
        inference=LeftMissing(reason="awaiting KB"),
    )


def _pf_extracted(field_id: str, value: Any, t: Any, confidence: float = 1.0) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=Extracted[t](value=value, spans=[_span(str(value))], confidence=confidence),
        inference=NotApplicable(),
    )


def _pf_deferred(field_id: str, t: Any, ref: str = "Xu et al. 2015") -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=DeferredToCitation(
            deferrals=[Deferral(ref=ref, span=_span(ref), target_kind="paper")],
            searched_terms=[],
            sections_searched=["Methods"],
        ),
        inference=LeftMissing(reason="awaiting KB"),
    )


def _spatial_normalization_missing() -> SpatialNormalization:
    return SpatialNormalization(
        target_space=_pf_missing("target_space", str),
        resolution_mm=_pf_missing("resolution_mm", float),
        method=_pf_missing("method", str),
        warp=_pf_missing("warp", str),
        transform_type=_pf_missing("transform_type", str),
        interpolation=_pf_missing("interpolation", str),
        regularization=_pf_missing("regularization", str),
    )


def _surface_projection_missing() -> SurfaceProjection:
    return SurfaceProjection(
        target_surface=_pf_missing("target_surface", str),
        vol2surf_sampling=_pf_missing("vol2surf_sampling", str),
        surface_registration=_pf_missing("surface_registration", str),
        cifti=_pf_missing("cifti", bool),
    )


def _intensity_normalization_missing() -> IntensityNormalization:
    return IntensityNormalization(
        scope=_pf_missing("scope", str),
        convention=_pf_missing("convention", str),
        value=_pf_missing("value", float),
    )


def _make_ccs_preprocessing(base_pipeline: ProvenancedField) -> Preprocessing:
    """CCS fixture. NO TemporalFiltering step — CCS makes filtering optional,
    so the base pipeline contributes no filtering step (Position A). An absent
    step is the correct encoding for "this pipeline pins no filtering"."""
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=base_pipeline,
        steps=[
            _spatial_normalization_missing(),
            _surface_projection_missing(),
            _intensity_normalization_missing(),
        ],
    )


def _extracted_ccs_with_version(version: str) -> ProvenancedField[PipelineRef]:
    return ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=Extracted[PipelineRef](
            value=PipelineRef(
                name="Connectome Computation System",
                version=_pf_extracted("version", version, str, confidence=1.0),
            ),
            spans=[_span(f"CCS {version}")],
            confidence=1.0,
        ),
        inference=NotApplicable(),
    )


def _extracted_ccs_with_deferred_version() -> ProvenancedField[PipelineRef]:
    """Paper names CCS but cites Xu 2015 instead of pinning a commit — the
    typical case, since CCS has no release tags to cite."""
    return ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=Extracted[PipelineRef](
            value=PipelineRef(
                name="Connectome Computation System",
                version=_pf_deferred("version", str, ref="Xu et al. 2015"),
            ),
            spans=[_span("Connectome Computation System (CCS)")],
            confidence=1.0,
        ),
        inference=NotApplicable(),
    )


def _step_field(prep: Preprocessing, step_cls: type, field_name: str) -> ProvenancedField:
    for s in prep.steps:
        if isinstance(s, step_cls):
            # getattr() is typed Any; every step field is a ProvenancedField.
            return cast(ProvenancedField, getattr(s, field_name))
    raise AssertionError(f"no {step_cls.__name__} step in fixture")


# ===========================================================================
# Test 5 — option-(a) gate: uncertain CCS version → five fields LeftMissing
# ===========================================================================


def test_ccs_option_a_gate_date_inferred_leaves_five_left_missing():
    """REALISTIC fixture: 2021 paper names CCS but defers to Xu 2015 rather
    than pinning a commit. The Configurator:
    (1) infers version="2015" via date_inferred_version (latest CCS record ≤
        2021-06-01; the commit checkpoint is dated later), then
    (2) the gate refuses to stack params on an inferred version, leaving all
        five KB-backed CCS fields LeftMissing.

    Confirms the option-(a) gate behaves identically on a pipeline with NO
    within-pipeline keying (contrast: HCP minimal's six-field version).
    """
    prep = _make_ccs_preprocessing(_extracted_ccs_with_deferred_version())

    infer_base_pipeline_version(prep, CCS_PAPER_DATE)
    version_pf = prep.base_pipeline.extraction.value.version
    assert version_pf.inference.status == "INFERRED_DEFAULT"
    assert version_pf.inference.basis.basis_type == "date_inferred_version"
    assert version_pf.inference.value == "2015"

    fill_dependent_defaults(prep, CCS_PAPER_DATE)
    assert not any(isinstance(s, TemporalFiltering) for s in prep.steps)
    for step_cls, field_name, _ in CCS_FILLED:
        pf = _step_field(prep, step_cls, field_name)
        assert pf.inference.status == "LEFT_MISSING", (
            f"{step_cls.__name__}.{field_name}: should be LEFT_MISSING on a "
            f"date_inferred_version, got {pf.inference.status}"
        )


# ===========================================================================
# Test 6 — certain CCS version fires EXACTLY five version_default fills
# ===========================================================================


def test_ccs_certain_version_fires_exactly_five_version_defaults():
    """SYNTHETIC fixture: paper Extracted base_pipeline name AND version
    ("2015"). fill_dependent_defaults wraps the five KB-documented CCS fields
    as InferredDefault(version_default), each confidence ≤ 0.95, each carrying
    VersionDefaultBasis(tool="ccs", version="2015").

    The count is EXACTLY five — not six, not seven:
    - surface_projection.target_surface stays LeftMissing (CCS pins no default);
    - temporal_filtering.effective_band_hz has no step to fill (absent).
    """
    prep = _make_ccs_preprocessing(_extracted_ccs_with_version("2015"))
    fill_dependent_defaults(prep, CCS_PAPER_DATE)

    fired = 0
    for step_cls, field_name, expected_value in CCS_FILLED:
        pf = _step_field(prep, step_cls, field_name)
        assert pf.inference.status == "INFERRED_DEFAULT", (
            f"{step_cls.__name__}.{field_name}: expected INFERRED_DEFAULT, "
            f"got {pf.inference.status}"
        )
        assert pf.inference.value == expected_value
        assert pf.inference.basis.basis_type == "version_default"
        assert pf.inference.basis.tool == "ccs"
        assert pf.inference.basis.version == "2015"
        assert pf.inference.confidence <= BASIS_CEILINGS["version_default"]
        fired += 1

    assert fired == 5

    # Deliberately-omitted field stays LeftMissing (no CCS default for it).
    target_surface = _step_field(prep, SurfaceProjection, "target_surface")
    assert target_surface.inference.status == "LEFT_MISSING"

    # No filtering step exists to fill effective_band_hz into.
    assert not any(isinstance(s, TemporalFiltering) for s in prep.steps)

    # Whole-spec guard: across every KB-targeted step field, exactly five
    # version_default fills fired (proves no spurious sixth/seventh fill).
    total_version_default = 0
    for step in prep.steps:
        for fname in type(step).model_fields:
            if fname == "kind":
                continue
            pf = getattr(step, fname)
            inf = getattr(pf, "inference", None)
            if (
                getattr(inf, "status", None) == "INFERRED_DEFAULT"
                and getattr(inf.basis, "basis_type", None) == "version_default"
            ):
                total_version_default += 1
    assert total_version_default == 5

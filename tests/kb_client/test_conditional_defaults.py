"""B1: consumer resolution of a conditional (derived) param default keyed on a sibling
extracted field (`target_surface` -> `surface_registration`).

Offline; no Bedrock. Exercises ``_apply_param_result``'s derived branch directly.
"""

from __future__ import annotations

from typing import Any

from fmri_defaults_kb import ConditionalParam, ConditionalRule, ParamResult

from fmri_repro.kb_client.base_pipeline import _apply_param_result
from fmri_repro.spec.preprocessing import (
    IntensityNormalization,
    Preprocessing,
    SpatialNormalization,
    SurfaceProjection,
)
from fmri_repro.spec.provenance import (
    BASIS_CEILINGS,
    Extracted,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
)
from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef

_COND = ConditionalParam(
    conditional_on="surface_projection.target_surface",
    rules=(
        ConditionalRule(
            when=("fsLR_32k",),
            value="msm_sulc",
            proposed_confidence=0.70,
            source="code-verified: run_msmsulc",
        ),
        ConditionalRule(
            when=("fsaverage", "fsaverage5", "fsaverage6", "fsnative"),
            value="freesurfer_recon",
            proposed_confidence=0.55,
            source="lineage-inferred: FreeSurfer mri_vol2surf anchor",
        ),
    ),
)
_RESULT = ParamResult(value=_COND, basis_type="derived", proposed_confidence=0.0, source="")


def _span(v: Any) -> Span:
    s = str(v) or "x"
    return Span(start=0, end=len(s), text=s, section="Methods")


def _missing(field_id: str, t: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
        inference=LeftMissing(reason="not stated"),
    )


def _extracted(field_id: str, value: Any, t: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=Extracted[t](value=value, spans=[_span(value)], confidence=0.9),
        inference=NotApplicable(),
    )


def _preprocessing(
    target_surface_pf: ProvenancedField, surfreg_pf: ProvenancedField
) -> Preprocessing:
    surface = SurfaceProjection(
        target_surface=target_surface_pf,
        vol2surf_sampling=_missing("vol2surf_sampling", str),
        surface_registration=surfreg_pf,
        cifti=_missing("cifti", bool),
    )
    spatial = SpatialNormalization(
        target_space=_missing("target_space", str),
        resolution_mm=_missing("resolution_mm", float),
        method=_missing("method", str),
        warp=_missing("warp", str),
        transform_type=_missing("transform_type", str),
        interpolation=_missing("interpolation", str),
        regularization=_missing("regularization", str),
    )
    intensity = IntensityNormalization(
        scope=_missing("scope", str),
        convention=_missing("convention", str),
        value=_missing("value", float),
    )
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=NotApplicable(),
        steps=[spatial, surface, intensity],
    )


def _apply(prep: Preprocessing) -> ProvenancedField:
    _apply_param_result(
        prep, "surface_projection", "surface_registration", _RESULT, "fmriprep", "24.0.0"
    )
    step = next(s for s in prep.steps if s.kind == "surface_projection")
    return step.surface_registration


def test_fslr_32k_derives_msm_sulc_at_ceiling():
    prep = _preprocessing(
        _extracted("target_surface", "fsLR_32k", str),
        _missing("surface_registration", str),
    )
    sr = _apply(prep)
    assert sr.inference.status == "INFERRED_DEFAULT"
    assert sr.inference.value == "msm_sulc"
    assert sr.inference.basis.basis_type == "derived"
    assert sr.inference.basis.source_field_ids == ["surface_projection.target_surface"]
    assert sr.inference.confidence == 0.70  # min(0.70, BASIS_CEILINGS["derived"])
    assert "code-verified" in (sr.inference.basis.note or "")


def test_fsaverage5_derives_freesurfer_recon_below_ceiling():
    prep = _preprocessing(
        _extracted("target_surface", "fsaverage5", str),
        _missing("surface_registration", str),
    )
    sr = _apply(prep)
    assert sr.inference.status == "INFERRED_DEFAULT"
    assert sr.inference.value == "freesurfer_recon"
    assert sr.inference.confidence == 0.55  # lineage-inferred, below the 0.70 ceiling
    assert sr.inference.confidence < BASIS_CEILINGS["derived"]


def test_target_surface_missing_fails_closed():
    prep = _preprocessing(
        _missing("target_surface", str),  # sibling not extracted
        _missing("surface_registration", str),
    )
    sr = _apply(prep)
    assert sr.inference.status == "LEFT_MISSING"  # no inference fired


def test_target_surface_matches_no_rule_fails_closed():
    prep = _preprocessing(
        _extracted("target_surface", "native", str),  # matches no rule's `when`
        _missing("surface_registration", str),
    )
    sr = _apply(prep)
    assert sr.inference.status == "LEFT_MISSING"


def test_surface_registration_already_extracted_is_untouched():
    prep = _preprocessing(
        _extracted("target_surface", "fsLR_32k", str),
        _extracted("surface_registration", "msm_all", str),  # paper stated it
    )
    sr = _apply(prep)
    assert sr.extraction.status == "EXTRACTED"
    assert sr.extraction.value == "msm_all"  # unchanged; inherited EXTRACTED guard
    assert sr.inference.status == "NOT_APPLICABLE"

"""Integration tests for fmri_repro.kb_client.base_pipeline.

Exercises both branches end-to-end against the real fmri-defaults-kb data
(seeded in kb/pipelines/hcp_minimal.yaml + fmriprep.yaml):

- Branch (a) — version certain: synthetic fixture with Extracted version
  (clearly labelled), KB fires version_default for documented fields.
- Branch (b) — version uncertain: realistic fixture for a 2021 paper that
  cites HCP minimal but doesn't pin a version; date_inferred_version arm,
  seven KB-backed fields stay LeftMissing.

Other tests cover the date→version ground truth, the basis-literal contract
between the two repos, ceiling clamping, never-null sentinel decoding, and
the negative-control path (unknown pipeline → no KB call, seven fields
untouched).
"""

from __future__ import annotations

from datetime import date
from typing import Any, cast
from unittest.mock import patch

import pytest
from fmri_defaults_kb import (
    KB_BASIS_LITERALS,
    resolve_version,
)
from fmri_defaults_kb import (
    NotApplicable as KbNotApplicable,
)

from fmri_repro.kb_client.base_pipeline import (
    SEVEN_DEMOTED_FIELDS,
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
    InferredDefault,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
    VersionDefaultBasis,
)
from fmri_repro.spec.refs import AcquisitionEntities, AcquisitionRef

# --- Cho 2021 submission date ---
# Representative date for a 2021 paper that uses HCP-provided *_MSMAll.dtseries.nii
# data and cites the HCP minimal pipeline without pinning a HCPpipelines tag.
# Any 2021 date works for the mechanism: the latest HCPpipelines release prior
# to it is v4.1.3 (2020-02-12, first tag whose PostFreeSurferPipeline.sh
# defaults `--regname` to MSMSulc). Note that Cho's `*_MSMAll.dtseries.nii`
# describes the data file's post-FIX re-registration (an EXTRACTED filename
# fact) — not the minimal pipeline's base surface_registration default, which
# at v4.1.3 is `msm_sulc`.
# TODO: pin the actual submission date once the specific paper is identified.
CHO_2021_DATE = date(2021, 6, 1)


# --- helpers (mirror tests/spec/test_preprocessing.py patterns) ------------


def _span(text: str = "stub", start: int = 0) -> Span:
    return Span(start=start, end=start + len(text), text=text, section="Methods")


def _pf_missing(field_id: str, t: Any) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=["Methods"]),
        inference=LeftMissing(reason="awaiting KB"),
    )


def _pf_extracted(field_id: str, value: Any, t: Any, confidence: float = 0.95) -> ProvenancedField:
    return ProvenancedField[t](
        field_id=field_id,
        extraction=Extracted[t](
            value=value,
            spans=[_span(str(value))],
            confidence=confidence,
        ),
        inference=NotApplicable(),
    )


def _pf_deferred(field_id: str, t: Any, ref: str = "Glasser 2013") -> ProvenancedField:
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


def _temporal_filtering_missing() -> TemporalFiltering:
    return TemporalFiltering(
        effective_band_hz=_pf_missing("effective_band_hz", tuple[float | None, float | None]),
        method=_pf_missing("method", str),
        low_hz=_pf_missing("low_hz", float),
        high_hz=_pf_missing("high_hz", float),
        order=_pf_missing("order", int),
        cutoff=_pf_missing("cutoff", str),
        scale=_pf_missing("scale", int),
        nominal_band_hz=_pf_missing("nominal_band_hz", tuple[float, float]),
    )


def _intensity_normalization_missing() -> IntensityNormalization:
    return IntensityNormalization(
        scope=_pf_missing("scope", str),
        convention=_pf_missing("convention", str),
        value=_pf_missing("value", float),
    )


def _make_preprocessing(
    base_pipeline: ProvenancedField | NotApplicable,
    *,
    include_temporal_filtering: bool = True,
) -> Preprocessing:
    """Build a Preprocessing with the KB-targeted steps initialized missing.

    ``include_temporal_filtering`` toggles whether a ``TemporalFiltering`` step
    is in ``steps``. HCP minimal performs no temporal filtering at all, so its
    fixtures must omit the step (an absent step is the correct encoding —
    encoding it as a present step with all fields LeftMissing would falsely
    signal that filtering was attempted but unreported).
    """
    steps: list = [
        _spatial_normalization_missing(),
        _surface_projection_missing(),
    ]
    if include_temporal_filtering:
        steps.append(_temporal_filtering_missing())
    steps.append(_intensity_normalization_missing())
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=base_pipeline,
        steps=steps,
    )


def _extracted_hcp_minimal_with_version(version: str) -> ProvenancedField[PipelineRef]:
    """Outer Extracted PipelineRef whose inner version is also Extracted."""
    return ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=Extracted[PipelineRef](
            value=PipelineRef(
                name="HCP minimal preprocessing pipeline",
                version=_pf_extracted("version", version, str, confidence=1.0),
            ),
            spans=[_span(f"HCP MPP {version}")],
            confidence=1.0,
        ),
        inference=NotApplicable(),
    )


def _extracted_hcp_minimal_with_deferred_version() -> ProvenancedField[PipelineRef]:
    """Outer Extracted PipelineRef whose inner version is DeferredToCitation
    (the typical Cho 2021 case: paper names HCP minimal, cites Glasser 2013 for
    pipeline details, doesn't pin an HCPpipelines tag)."""
    return ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=Extracted[PipelineRef](
            value=PipelineRef(
                name="HCP minimal preprocessing pipeline",
                version=_pf_deferred("version", str, ref="Glasser et al. 2013"),
            ),
            spans=[_span("HCP minimal preprocessing pipeline")],
            confidence=1.0,
        ),
        inference=NotApplicable(),
    )


def _extracted_unknown_pipeline() -> ProvenancedField[PipelineRef]:
    """Bassett-style: extraction names something the KB doesn't recognize.
    Cross-check that recognize→None preserves the Extracted claim (no demote
    on Extracted) AND that get_param_defaults is not called."""
    return ProvenancedField[PipelineRef](
        field_id="base_pipeline",
        extraction=Extracted[PipelineRef](
            value=PipelineRef(
                name="hand-rolled FSL toolchain (Bassett-style)",
                version=_pf_missing("version", str),
            ),
            spans=[_span("FSL toolchain")],
            confidence=0.9,
        ),
        inference=NotApplicable(),
    )


# --- helpers for inspecting results ----------------------------------------


def _step_field(prep: Preprocessing, step_kind_cls: type, field_name: str) -> ProvenancedField:
    for s in prep.steps:
        if isinstance(s, step_kind_cls):
            # getattr() is typed Any; every step field is a ProvenancedField.
            return cast(ProvenancedField, getattr(s, field_name))
    raise AssertionError(f"no {step_kind_cls.__name__} step in fixture")


# ===========================================================================
# Test 1 — Branch (a): certain, synthetic Extracted version fires KB defaults
# ===========================================================================


def test_branch_a_certain_extracted_version_fires_kb_version_default():
    """SYNTHETIC fixture: paper Extracted base_pipeline name AND version
    (`HCPpipelines v4.1.3`). fill_dependent_defaults wraps the KB-documented
    fields as InferredDefault(version_default) with confidence ≤ 0.95.

    Six fields fire as version_default for HCP minimal v4.1.3:
    spatial_normalization x {target_space, resolution_mm},
    surface_projection x {target_surface, surface_registration},
    intensity_normalization x {convention, value}.

    The TemporalFiltering step is intentionally absent from the fixture
    because HCP minimal does not perform temporal filtering at all — an
    absent step is the correct encoding (per provenance.py:189-198,
    couple_stages forbids inference=NotApplicable on Missing/Deferred
    extraction, so a present-step-with-LeftMissing-fields encoding would
    falsely signal that filtering was attempted).
    """
    prep = _make_preprocessing(
        _extracted_hcp_minimal_with_version("v4.1.3"),
        include_temporal_filtering=False,
    )
    fill_dependent_defaults(prep, CHO_2021_DATE)

    # Concrete-value fields → InferredDefault(version_default) — six total
    for step_cls, field_name, expected_value in [
        (SpatialNormalization, "target_space", "MNI152NLin6Asym"),
        (SpatialNormalization, "resolution_mm", 2),
        (SurfaceProjection, "target_surface", "fsLR_32k"),
        (SurfaceProjection, "surface_registration", "msm_sulc"),
        (IntensityNormalization, "convention", "fsl_grand_mean_10000"),
        (IntensityNormalization, "value", 10000),
    ]:
        pf = _step_field(prep, step_cls, field_name)
        assert pf.inference.status == "INFERRED_DEFAULT", (
            f"{step_cls.__name__}.{field_name}: expected INFERRED_DEFAULT, "
            f"got {pf.inference.status}"
        )
        assert pf.inference.value == expected_value
        assert pf.inference.basis.basis_type == "version_default"
        assert pf.inference.basis.tool == "hcp_minimal"
        assert pf.inference.basis.version == "v4.1.3"
        assert pf.inference.confidence <= BASIS_CEILINGS["version_default"]

    # TemporalFiltering step is absent — the KB's not_applicable sentinel
    # for effective_band_hz cannot be filled because there is no step to
    # fill into. _find_step returns None → _apply_param_result early-returns.
    assert not any(isinstance(s, TemporalFiltering) for s in prep.steps)


# ===========================================================================
# Test 2 — Branch (b): uncertain Cho-2021-style, seven fields stay LeftMissing
# ===========================================================================


def test_branch_b_uncertain_cho2021_date_inferred_version_leaves_six_left_missing():
    """REALISTIC fixture: 2021 paper names HCP minimal preprocessing but
    cites Glasser 2013 instead of pinning an HCPpipelines tag. The Configurator:
    (1) infers version=v4.1.3 via date_inferred_version (latest tag ≤
        2021-06-01 in the seeded HCP timeline), then
    (2) fill_dependent_defaults' gate refuses to stack params on an inferred
        version, leaving the six KB-backed HCP-minimal fields as LeftMissing.

    The TemporalFiltering step is absent from the fixture (HCP minimal does
    not filter), so SEVEN_DEMOTED_FIELDS' temporal_filtering.effective_band_hz
    entry has no step to inspect — it is skipped in the assertion loop.
    """
    prep = _make_preprocessing(
        _extracted_hcp_minimal_with_deferred_version(),
        include_temporal_filtering=False,
    )

    # Step 1: infer version
    infer_base_pipeline_version(prep, CHO_2021_DATE)
    version_pf = prep.base_pipeline.extraction.value.version
    assert version_pf.inference.status == "INFERRED_DEFAULT"
    assert version_pf.inference.basis.basis_type == "date_inferred_version"
    assert version_pf.inference.value == "v4.1.3"

    # Step 2: gate refuses → present fields stay LeftMissing
    fill_dependent_defaults(prep, CHO_2021_DATE)
    assert not any(isinstance(s, TemporalFiltering) for s in prep.steps)
    for step_kind, field_name in SEVEN_DEMOTED_FIELDS:
        if step_kind == "temporal_filtering":
            continue  # step absent — nothing to assert
        step_cls = {
            "spatial_normalization": SpatialNormalization,
            "surface_projection": SurfaceProjection,
            "intensity_normalization": IntensityNormalization,
        }[step_kind]
        pf = _step_field(prep, step_cls, field_name)
        assert pf.inference.status == "LEFT_MISSING", (
            f"{step_kind}.{field_name}: should be LEFT_MISSING when version is "
            f"date_inferred_version, got {pf.inference.status}"
        )


# ===========================================================================
# Test 3 — Date→version SELECTION MECHANICS (not accuracy)
# ===========================================================================


def test_date_to_version_selection_mechanics_for_cho2021_lands_on_v413():
    """resolve_version for a 2021 paper date selects v4.1.3 — the latest
    HCPpipelines tag ≤ 2021-06-01 in the seeded timeline.

    This validates SELECTION MECHANICS, not date-inference accuracy. The HCP
    timeline as seeded contains only the registration-default boundary
    (v3.4.0 and v4.1.3); a 2021 date trivially resolves to v4.1.3 by
    "latest ≤ paper_date." Genuine date-inference accuracy validation lives
    on the fmriprep pipeline (20-release timeline). True HCP date→version
    validation would require a fuller HCP timeline reconciled against HCP
    *data*-release dates (S500/S900/S1200), which are a partly-orthogonal
    axis from the GitHub pipeline-tag timeline.

    Note also: Cho's data was `*_MSMAll.dtseries.nii`, which would be
    EXTRACTED from the filename — that deliberately differs from the
    date-inferred base-pipeline default of `msm_sulc` at v4.1.3. The
    branch-(b) gate (option-(a) gate) refuses to fill the seven fields on
    a date_inferred_version anyway, so the divergence stays harmless.
    """
    res = resolve_version("hcp_minimal", CHO_2021_DATE)
    assert res.basis_type == "date_inferred_version"
    assert res.resolved_version == "v4.1.3"
    # v3.4.0 (FS-era, first public release) is the adjacent-earlier alternative
    alt_versions = [c.version for c in res.alternative_candidates]
    assert "v3.4.0" in alt_versions


# ===========================================================================
# Test 4 — Ceiling clamp (both clamp arithmetic and provenance.py guard)
# ===========================================================================


def test_ceiling_clamp_caps_version_default_confidence_at_0_95():
    """Clamp arithmetic in fill_dependent_defaults: min(KB-proposed, ceiling)."""
    assert min(0.99, BASIS_CEILINGS["version_default"]) == 0.95
    assert min(0.50, BASIS_CEILINGS["version_default"]) == 0.50


def test_inferred_default_rejects_confidence_above_basis_ceiling():
    """provenance.py:_ceiling guards against the clamp being bypassed: an
    InferredDefault constructed with confidence > BASIS_CEILINGS[basis_type]
    must raise ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        InferredDefault[str](
            value="v4.1.3",
            basis=VersionDefaultBasis(tool="hcp_minimal", version="v4.1.3"),
            confidence=0.99,  # > 0.95 ceiling
            alternative_inferences=[],
        )


# ===========================================================================
# Test 5 — Basis-string-literal contract between KB and agent
# ===========================================================================


def test_basis_contract_kb_literals_subset_of_agent_ceiling_keys():
    """KB exports the basis-type strings it emits. Agent's BASIS_CEILINGS
    keys must cover all of them — otherwise a KB-emitted basis_type would
    crash InferredDefault._ceiling lookup."""
    assert KB_BASIS_LITERALS <= set(BASIS_CEILINGS.keys()), (
        f"KB literals not subset of agent ceilings: "
        f"missing {KB_BASIS_LITERALS - set(BASIS_CEILINGS.keys())}"
    )


# ===========================================================================
# Test 6 — Never-null (KB returns NotApplicable singleton, not None)
# ===========================================================================


def test_never_null_get_param_defaults_returns_not_applicable_singleton_not_none():
    """KB's contract: for explicitly-N/A fields, return the NotApplicable
    singleton, NEVER None or missing."""
    from fmri_defaults_kb import get_param_defaults

    out = get_param_defaults("hcp_minimal", "v4.1.3", ["temporal_filtering.effective_band_hz"])
    assert "temporal_filtering.effective_band_hz" in out
    result = out["temporal_filtering.effective_band_hz"]
    assert result.value is KbNotApplicable
    assert result.value is not None


# ===========================================================================
# Test 7 — Negative control: unknown pipeline → no get_param_defaults call
# ===========================================================================


def test_negative_control_unknown_pipeline_skips_kb_param_lookup():
    """Bassett-style: paper extracts a pipeline name the KB doesn't recognize.
    fill_dependent_defaults must NOT call get_param_defaults (no spurious
    lookups), and the seven fields stay as the Extractor left them."""
    prep = _make_preprocessing(_extracted_unknown_pipeline())

    with patch("fmri_repro.kb_client.base_pipeline.get_param_defaults") as mock_gpd:
        fill_dependent_defaults(prep, CHO_2021_DATE)
        mock_gpd.assert_not_called()

    # And the seven fields are untouched (still LeftMissing from _pf_missing).
    for step_kind, field_name in SEVEN_DEMOTED_FIELDS:
        step_cls = {
            "spatial_normalization": SpatialNormalization,
            "surface_projection": SurfaceProjection,
            "temporal_filtering": TemporalFiltering,
            "intensity_normalization": IntensityNormalization,
        }[step_kind]
        pf = _step_field(prep, step_cls, field_name)
        assert pf.inference.status == "LEFT_MISSING"

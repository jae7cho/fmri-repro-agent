"""Build ``examples/hcp_glasser_fieldmaps.json`` — the HCP S1200 / Glasser 2013
reference fixture.

Representative values from the HCP-S1200 / Glasser et al. 2013 protocol; this
is a **test/reference fixture** (every value tied to a synthetic ``Span``,
not extracted from a real PDF). The fixture exercises:

- Cross-arm ``intended_for``: the phasediff/magnitude pair points at the
  T1w/T2w anatomicals (B0 fieldmap intended for structural data), while the
  ``epi`` fieldmap points at the BOLD.
- Both fieldmap mechanisms in one ``ReplicationSpec``: a single ``epi``
  reverse-PE fmap plus the phasediff + magnitude1 + magnitude2 triple.
- ``DEFERRED_TO_CITATION`` on TR + multi-echo TE on the BOLD (Glasser cites
  Smith 2013 / Ugurbil 2013 for those acquisition details).

To regenerate: ``python scripts/make_glasser_fieldmap_example.py``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from fmri_repro.spec.core import (
    AcquisitionEntities,
    AcquisitionRef,
    AnatomicalAcquisition,
    AxisDirection,
    BrainCoverage,
    DatasetRef,
    FieldmapAcquisition,
    FirstLevelModel,
    FunctionalAcquisition,
    GroupLevelModel,
    ImagingType,
    MRAcquisitionType,
    PaperRef,
    ParallelTechnique,
    PulseSequenceType,
    ReplicationSpec,
    RunMeta,
    SliceOrderPattern,
    SliceOrientation,
    Thresholding,
)
from fmri_repro.spec.preprocessing import (
    NuisanceRegression,
    PipelineRef,
    Preprocessing,
    SpatialSmoothing,
    SurfaceProjection,
    TemporalFiltering,
)
from fmri_repro.spec.provenance import (
    DateInferredVersionBasis,
    Deferral,
    DeferredToCitation,
    Extracted,
    InferredDefault,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
)
from fmri_repro.spec.v0_4_0 import StudySpec  # current root; scripts emit 0.4.0 documents

_FIXED_RUN_ID = "00000000000000000000000000000002"
_FIXED_CREATED_AT = datetime(2026, 5, 21, 0, 0, 0, tzinfo=UTC)
_METHODS = "Methods"
_CITATION_REFS = ("Smith 2013", "Ugurbil 2013")


def _span(text: str, start: int) -> Span:
    return Span(start=start, end=start + len(text), text=text, section=_METHODS)


def _missing(field_id: str, t: type) -> ProvenancedField:
    """MISSING + LEFT_MISSING shorthand. Caller-supplied ``t`` is the element type."""
    return ProvenancedField[t](
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
        inference=LeftMissing(reason="not reported in paper"),
    )


def _common_missing_kwargs() -> dict[str, ProvenancedField]:
    """The 13 CommonAcquisitionParams fields, every one MISSING + LEFT_MISSING.

    Callers selectively overwrite specific entries with EXTRACTED / DEFERRED
    versions to model the Glasser HCP details."""
    return {
        "manufacturer": _missing("manufacturer", str),
        "scanner_model": _missing("scanner_model", str),
        "field_strength_t": _missing("field_strength_t", float),
        "receive_coil": _missing("receive_coil", str),
        "pulse_sequence_type": _missing("pulse_sequence_type", PulseSequenceType),
        "imaging_type": _missing("imaging_type", ImagingType),
        "mr_acquisition_type": _missing("mr_acquisition_type", MRAcquisitionType),
        "partial_fourier": _missing("partial_fourier", float),
        "repetition_time_s": _missing("repetition_time_s", float),
        "flip_angle_deg": _missing("flip_angle_deg", float),
        "voxel_size_mm": ProvenancedField[tuple[float, float, float]](
            field_id="voxel_size_mm",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
            inference=LeftMissing(reason="not reported in paper"),
        ),
        "matrix_size": ProvenancedField[tuple[int, ...]](
            field_id="matrix_size",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
            inference=LeftMissing(reason="not reported in paper"),
        ),
        "fov_mm": ProvenancedField[tuple[float, ...]](
            field_id="fov_mm",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
            inference=LeftMissing(reason="not reported in paper"),
        ),
    }


def _functional_missing_kwargs() -> dict[str, ProvenancedField]:
    """The 26 FunctionalAcquisition arm-specific fields, every one MISSING."""
    return {
        "echo_time_ms": ProvenancedField[list[float]](
            field_id="echo_time_ms",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
            inference=LeftMissing(reason="not reported in paper"),
        ),
        "n_echoes": _missing("n_echoes", int),
        "acquisition_time_s": _missing("acquisition_time_s", float),
        "n_volumes": _missing("n_volumes", int),
        "n_slices": _missing("n_slices", int),
        "slice_gap_mm": _missing("slice_gap_mm", float),
        "slice_orientation": _missing("slice_orientation", SliceOrientation),
        "slice_angulation_deg": _missing("slice_angulation_deg", float),
        "brain_coverage": _missing("brain_coverage", BrainCoverage),
        "slice_order_pattern": _missing("slice_order_pattern", SliceOrderPattern),
        "slice_timing_s": ProvenancedField[list[float]](
            field_id="slice_timing_s",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
            inference=LeftMissing(reason="not reported in paper"),
        ),
        "slice_encoding_direction": _missing("slice_encoding_direction", AxisDirection),
        "multiband_factor": _missing("multiband_factor", int),
        "parallel_technique": _missing("parallel_technique", ParallelTechnique),
        "parallel_factor": _missing("parallel_factor", float),
        "phase_encoding_reported": _missing("phase_encoding_reported", str),
        "phase_encoding_direction": _missing("phase_encoding_direction", AxisDirection),
        "pe_reversal": _missing("pe_reversal", bool),
        "effective_echo_spacing_s": _missing("effective_echo_spacing_s", float),
        "total_readout_time_s": _missing("total_readout_time_s", float),
        "prospective_motion_correction": _missing("prospective_motion_correction", bool),
        "signal_inhomogeneity_correction": _missing("signal_inhomogeneity_correction", bool),
        "distortion_correction_onscanner": _missing("distortion_correction_onscanner", bool),
        "recon_matrix_differs": _missing("recon_matrix_differs", bool),
        "shimming": _missing("shimming", str),
        "n_dummy_scanner": _missing("n_dummy_scanner", int),
    }


def _fieldmap_missing_kwargs() -> dict[str, ProvenancedField]:
    """The 4 FieldmapAcquisition arm-specific fields, every one MISSING."""
    return {
        "phase_encoding_direction": _missing("phase_encoding_direction", AxisDirection),
        "effective_echo_spacing_s": _missing("effective_echo_spacing_s", float),
        "total_readout_time_s": _missing("total_readout_time_s", float),
        "echo_times_ms": ProvenancedField[list[float]](
            field_id="echo_times_ms",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
            inference=LeftMissing(reason="not reported in paper"),
        ),
    }


# ---------------------------------------------------------------------------
# Acquisitions
# ---------------------------------------------------------------------------
def _t1w() -> AnatomicalAcquisition:
    common = _common_missing_kwargs()
    common["voxel_size_mm"] = ProvenancedField[tuple[float, float, float]](
        field_id="voxel_size_mm",
        extraction=Extracted[tuple[float, float, float]](
            value=(0.7, 0.7, 0.7),
            spans=[_span("T1w voxel size 0.7 mm isotropic", 100)],
            confidence=0.97,
        ),
        inference=NotApplicable(),
    )
    common["flip_angle_deg"] = ProvenancedField[float](
        field_id="flip_angle_deg",
        extraction=Extracted[float](
            value=8.0,
            spans=[_span("T1w flip angle 8°", 130)],
            confidence=0.95,
        ),
        inference=NotApplicable(),
    )
    return AnatomicalAcquisition(
        suffix="T1w",
        **common,
        echo_time_ms=ProvenancedField[float](
            field_id="echo_time_ms",
            extraction=Extracted[float](
                value=2.14,
                spans=[_span("T1w TE = 2.14 ms", 150)],
                confidence=0.95,
            ),
            inference=NotApplicable(),
        ),
    )


def _t2w() -> AnatomicalAcquisition:
    common = _common_missing_kwargs()
    common["voxel_size_mm"] = ProvenancedField[tuple[float, float, float]](
        field_id="voxel_size_mm",
        extraction=Extracted[tuple[float, float, float]](
            value=(0.7, 0.7, 0.7),
            spans=[_span("T2w voxel size 0.7 mm isotropic", 200)],
            confidence=0.97,
        ),
        inference=NotApplicable(),
    )
    return AnatomicalAcquisition(
        suffix="T2w",
        **common,
        echo_time_ms=_missing("echo_time_ms", float),
    )


def _bold_rest_lr() -> FunctionalAcquisition:
    common = _common_missing_kwargs()
    # Extracted common fields
    common["imaging_type"] = ProvenancedField[ImagingType](
        field_id="imaging_type",
        extraction=Extracted[ImagingType](
            value=ImagingType.EPI,
            spans=[_span("EPI", 300)],
            confidence=0.96,
        ),
        inference=NotApplicable(),
    )
    common["pulse_sequence_type"] = ProvenancedField[PulseSequenceType](
        field_id="pulse_sequence_type",
        extraction=Extracted[PulseSequenceType](
            value=PulseSequenceType.GRADIENT_ECHO,
            spans=[_span("gradient-echo EPI", 305)],
            confidence=0.96,
        ),
        inference=NotApplicable(),
    )
    common["mr_acquisition_type"] = ProvenancedField[MRAcquisitionType](
        field_id="mr_acquisition_type",
        extraction=Extracted[MRAcquisitionType](
            value=MRAcquisitionType.TWO_D,
            spans=[_span("2D EPI", 320)],
            confidence=0.94,
        ),
        inference=NotApplicable(),
    )
    common["voxel_size_mm"] = ProvenancedField[tuple[float, float, float]](
        field_id="voxel_size_mm",
        extraction=Extracted[tuple[float, float, float]](
            value=(2.0, 2.0, 2.0),
            spans=[_span("BOLD voxel size 2 mm isotropic", 340)],
            confidence=0.96,
        ),
        inference=NotApplicable(),
    )
    common["fov_mm"] = ProvenancedField[tuple[float, ...]](
        field_id="fov_mm",
        extraction=Extracted[tuple[float, ...]](
            value=(208.0, 180.0),
            spans=[_span("BOLD FOV 208 x 180 mm", 360)],
            confidence=0.95,
        ),
        inference=NotApplicable(),
    )
    # DEFERRED on TR (a Common field) — paper defers to Smith/Ugurbil 2013
    common["repetition_time_s"] = ProvenancedField[float](
        field_id="repetition_time_s",
        extraction=DeferredToCitation(
            deferrals=[
                Deferral(
                    ref=ref,
                    span=_span(f"BOLD TR — see {ref}", 380),
                    target_kind="paper",
                )
                for ref in _CITATION_REFS
            ],
            searched_terms=["repetition time", "TR"],
            sections_searched=[_METHODS],
        ),
        inference=LeftMissing(reason="paper defers to cited HCP methods"),
    )

    functional = _functional_missing_kwargs()
    # DEFERRED on echo_time_ms (multi-echo list) — paper defers to Smith/Ugurbil 2013
    functional["echo_time_ms"] = ProvenancedField[list[float]](
        field_id="echo_time_ms",
        extraction=DeferredToCitation(
            deferrals=[
                Deferral(
                    ref=ref,
                    span=_span(f"BOLD TE — see {ref}", 400),
                    target_kind="paper",
                )
                for ref in _CITATION_REFS
            ],
            searched_terms=["echo time", "TE"],
            sections_searched=[_METHODS],
        ),
        inference=LeftMissing(reason="paper defers to cited HCP methods"),
    )
    functional["effective_echo_spacing_s"] = ProvenancedField[float](
        field_id="effective_echo_spacing_s",
        extraction=Extracted[float](
            value=0.00058,
            spans=[_span("effective echo spacing 0.58 ms", 420)],
            confidence=0.94,
        ),
        inference=NotApplicable(),
    )
    functional["phase_encoding_direction"] = ProvenancedField[AxisDirection](
        field_id="phase_encoding_direction",
        extraction=Extracted[AxisDirection](
            value=AxisDirection.I_NEG,
            spans=[_span("phase encoding i- (LR)", 440)],
            confidence=0.93,
        ),
        inference=NotApplicable(),
    )

    return FunctionalAcquisition(
        entities=AcquisitionEntities(task="rest", dir="LR"),
        **common,
        **functional,
    )


def _epi_fmap_lr() -> FieldmapAcquisition:
    common = _common_missing_kwargs()
    common["voxel_size_mm"] = ProvenancedField[tuple[float, float, float]](
        field_id="voxel_size_mm",
        extraction=Extracted[tuple[float, float, float]](
            value=(2.0, 2.0, 2.0),
            spans=[_span("epi fmap voxel size 2 mm isotropic", 500)],
            confidence=0.96,
        ),
        inference=NotApplicable(),
    )
    common["fov_mm"] = ProvenancedField[tuple[float, ...]](
        field_id="fov_mm",
        extraction=Extracted[tuple[float, ...]](
            value=(208.0, 180.0),
            spans=[_span("epi fmap FOV 208 x 180 mm", 520)],
            confidence=0.95,
        ),
        inference=NotApplicable(),
    )

    fmap = _fieldmap_missing_kwargs()
    fmap["effective_echo_spacing_s"] = ProvenancedField[float](
        field_id="effective_echo_spacing_s",
        extraction=Extracted[float](
            value=0.00058,
            spans=[_span("effective echo spacing 0.58 ms (fmap)", 540)],
            confidence=0.94,
        ),
        inference=NotApplicable(),
    )
    fmap["phase_encoding_direction"] = ProvenancedField[AxisDirection](
        field_id="phase_encoding_direction",
        extraction=Extracted[AxisDirection](
            value=AxisDirection.I_NEG,
            spans=[_span("epi fmap phase encoding i- (LR)", 560)],
            confidence=0.93,
        ),
        inference=NotApplicable(),
    )

    return FieldmapAcquisition(
        suffix="epi",
        entities=AcquisitionEntities(dir="LR"),
        **common,
        **fmap,
        intended_for=[
            AcquisitionRef(
                suffix="bold",
                entities=AcquisitionEntities(task="rest", dir="LR"),
            ),
        ],
    )


def _two_mm_voxel_only_fmap(suffix: str, descriptor: str, start: int) -> FieldmapAcquisition:
    """phasediff / magnitude{1,2}: voxel EXTRACTED, every other fmap+common field MISSING.

    The paper gives ΔTE = 2.46 ms but no absolute TEs, so ``echo_times_ms`` stays MISSING.
    Each points (via ``intended_for``) at T1w and T2w — the B0 fieldmap is intended for
    structural unwarping in Glasser's pipeline."""
    common = _common_missing_kwargs()
    common["voxel_size_mm"] = ProvenancedField[tuple[float, float, float]](
        field_id="voxel_size_mm",
        extraction=Extracted[tuple[float, float, float]](
            value=(2.0, 2.0, 2.0),
            spans=[_span(f"{descriptor} voxel size 2 mm isotropic", start)],
            confidence=0.95,
        ),
        inference=NotApplicable(),
    )
    return FieldmapAcquisition(
        suffix=suffix,
        **common,
        **_fieldmap_missing_kwargs(),
        intended_for=[
            AcquisitionRef(suffix="T1w"),
            AcquisitionRef(suffix="T2w"),
        ],
    )


# ---------------------------------------------------------------------------
# Preprocessing — HCP Minimal Preprocessing Pipelines (Glasser 2013).
#
# Demonstrates:
#  - ``PipelineRef`` with version inferred via ``DateInferredVersionBasis``
#    (paper predates fixed S1200 release; Configurator narrows by date).
#  - A surface-aware chain: surface_projection (fsLR_32k / msm_all),
#    nuisance_regression (Friston-24 + WM + CSF), butterworth_bandpass
#    0.01-0.1 Hz, FWHM-6 smoothing on the template surface.
# ---------------------------------------------------------------------------


def _hcp_preprocessing() -> Preprocessing:
    """HCP MPP-style pipeline applied to the rest BOLD (LR run)."""
    bold_ref = AcquisitionRef(
        suffix="bold",
        entities=AcquisitionEntities(task="rest", dir="LR"),
    )
    inner_pipeline_ref = PipelineRef(
        name="HCP Minimal Preprocessing Pipelines",
        version=ProvenancedField[str](
            field_id="version",
            extraction=DeferredToCitation(
                deferrals=[
                    Deferral(
                        ref="Glasser 2013",
                        span=Span(
                            start=900,
                            end=940,
                            text="processed with the HCP MPP (Glasser 2013)",
                            section=_METHODS,
                        ),
                        target_kind="pipeline",
                    ),
                ],
                searched_terms=["HCP MPP version", "minimal preprocessing pipelines"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[str](
                value="2013-circa",
                basis=DateInferredVersionBasis(
                    tool="HCP MPP",
                    inferred_version="2013-circa",
                    paper_date=date(2013, 10, 15),
                    note="Configurator-inferred from paper date.",
                ),
                confidence=0.7,
                alternative_inferences=[],
            ),
        ),
    )
    return Preprocessing(
        applies_to=[bold_ref],
        # Outer DeferredToCitation(target_kind="pipeline") — the Glasser 2013
        # paper cites the HCP MPP but doesn't state a discrete pipeline version
        # itself; Configurator fills the inferred PipelineRef.
        base_pipeline=ProvenancedField[PipelineRef](
            field_id="base_pipeline",
            extraction=DeferredToCitation(
                deferrals=[
                    Deferral(
                        ref="Glasser 2013",
                        span=Span(
                            start=900,
                            end=920,
                            text="HCP minimal pipelines",
                            section=_METHODS,
                        ),
                        target_kind="pipeline",
                    ),
                ],
                searched_terms=["base pipeline", "HCP MPP"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[PipelineRef](
                value=inner_pipeline_ref,
                basis=DateInferredVersionBasis(
                    tool="HCP MPP",
                    inferred_version="2013-circa",
                    paper_date=date(2013, 10, 15),
                ),
                confidence=0.7,
                alternative_inferences=[],
            ),
        ),
        steps=[
            SurfaceProjection(
                target_surface=ProvenancedField[str](
                    field_id="target_surface",
                    extraction=Extracted[str](
                        value="fsLR_32k",
                        spans=[
                            Span(
                                start=1000,
                                end=1010,
                                text="fsLR_32k",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                vol2surf_sampling=ProvenancedField[str](
                    field_id="vol2surf_sampling",
                    extraction=MissingFromPaper(
                        searched_terms=["ribbon", "vol2surf"],
                        sections_searched=[_METHODS],
                    ),
                    inference=InferredDefault[str](
                        value="ribbon_constrained",
                        basis=DateInferredVersionBasis(
                            tool="HCP MPP",
                            inferred_version="2013-circa",
                            paper_date=date(2013, 10, 15),
                            note="HCP-MPP default sampling.",
                        ),
                        confidence=0.7,
                        alternative_inferences=[],
                    ),
                ),
                surface_registration=ProvenancedField[str](
                    field_id="surface_registration",
                    extraction=Extracted[str](
                        value="msm_all",
                        spans=[
                            Span(
                                start=1100,
                                end=1107,
                                text="MSMAll",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                cifti=ProvenancedField[bool](
                    field_id="cifti",
                    extraction=Extracted[bool](
                        value=True,
                        spans=[
                            Span(
                                start=1200,
                                end=1205,
                                text="CIFTI",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.9,
                    ),
                    inference=NotApplicable(),
                ),
            ),
            NuisanceRegression(
                motion_expansion=ProvenancedField[str](
                    field_id="motion_expansion",
                    extraction=Extracted[str](
                        value="friston24",
                        spans=[
                            Span(
                                start=1300,
                                end=1330,
                                text="24 Friston motion regressors",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.9,
                    ),
                    inference=NotApplicable(),
                ),
                tissue_regressors=ProvenancedField[list[str]](
                    field_id="tissue_regressors",
                    extraction=Extracted[list[str]](
                        value=["white_matter", "ventricles"],
                        spans=[
                            Span(
                                start=1340,
                                end=1360,
                                text="WM + CSF regression",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.9,
                    ),
                    inference=NotApplicable(),
                ),
                physio_regressors=ProvenancedField[str](
                    field_id="physio_regressors",
                    extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
                    inference=LeftMissing(reason="not reported"),
                ),
                physio_n_regressors=ProvenancedField[int](
                    field_id="physio_n_regressors",
                    extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
                    inference=LeftMissing(reason="not reported"),
                ),
                detrend=ProvenancedField[str](
                    field_id="detrend",
                    extraction=Extracted[str](
                        value="linear",
                        spans=[
                            Span(
                                start=1380,
                                end=1395,
                                text="linear detrend",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.9,
                    ),
                    inference=NotApplicable(),
                ),
                method=_missing("method", str),
                filtering_integrated=_missing("filtering_integrated", bool),
            ),
            TemporalFiltering(
                effective_band_hz=ProvenancedField[tuple[float | None, float | None]](
                    field_id="effective_band_hz",
                    extraction=Extracted[tuple[float | None, float | None]](
                        value=(0.01, 0.1),
                        spans=[
                            Span(
                                start=1400,
                                end=1420,
                                text="bandpass 0.01-0.1 Hz",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                method=ProvenancedField[str](
                    field_id="method",
                    extraction=Extracted[str](
                        value="butterworth_bandpass",
                        spans=[
                            Span(
                                start=1430,
                                end=1450,
                                text="Butterworth bandpass",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.92,
                    ),
                    inference=NotApplicable(),
                ),
                low_hz=ProvenancedField[float](
                    field_id="low_hz",
                    extraction=Extracted[float](
                        value=0.01,
                        spans=[
                            Span(
                                start=1460,
                                end=1470,
                                text="0.01 Hz",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                high_hz=ProvenancedField[float](
                    field_id="high_hz",
                    extraction=Extracted[float](
                        value=0.1,
                        spans=[
                            Span(
                                start=1480,
                                end=1490,
                                text="0.1 Hz",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                order=_missing("order", int),
                cutoff=_missing("cutoff", float),
                scale=_missing("scale", int),
                nominal_band_hz=_missing("nominal_band_hz", tuple),
            ),
            SpatialSmoothing(
                fwhm_mm=ProvenancedField[float](
                    field_id="fwhm_mm",
                    extraction=Extracted[float](
                        value=6.0,
                        spans=[
                            Span(
                                start=1500,
                                end=1520,
                                text="FWHM 6 mm on surface",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.92,
                    ),
                    inference=NotApplicable(),
                ),
                space=ProvenancedField[str](
                    field_id="space",
                    extraction=Extracted[str](
                        value="template_surface",
                        spans=[
                            Span(
                                start=1530,
                                end=1550,
                                text="smoothed on fsLR_32k surface",
                                section=_METHODS,
                            ),
                        ],
                        confidence=0.92,
                    ),
                    inference=NotApplicable(),
                ),
                kernel_type=ProvenancedField[str](
                    field_id="kernel_type",
                    extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
                    inference=LeftMissing(reason="kernel type not pinned"),
                ),
                approach=_missing("approach", str),
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def _build_study() -> StudySpec:
    spec = ReplicationSpec(
        dataset=DatasetRef(
            name="HCP S1200 (Glasser 2013 pipelines)",
            accession=None,
            source_url=None,
            site=None,
        ),
        acquisitions=[
            _t1w(),
            _t2w(),
            _bold_rest_lr(),
            _epi_fmap_lr(),
            _two_mm_voxel_only_fmap("phasediff", "phasediff fmap", 600),
            _two_mm_voxel_only_fmap("magnitude1", "magnitude1 fmap", 620),
            _two_mm_voxel_only_fmap("magnitude2", "magnitude2 fmap", 640),
        ],
        preprocessing=[_hcp_preprocessing()],
        first_level=FirstLevelModel(),
        group_level=GroupLevelModel(),
        thresholding=Thresholding(),
    )
    return StudySpec(
        run=RunMeta(
            run_id=_FIXED_RUN_ID,
            created_at=_FIXED_CREATED_AT,
            paper=PaperRef(source="10.1016/j.neuroimage.2013.05.041", sha256=None),
        ),
        specs=[spec],
        study_analysis=None,
    )


def main() -> Path:
    study = _build_study()
    out_path = Path("examples") / "hcp_glasser_fieldmaps.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(study.model_dump_json(indent=2) + "\n")
    print(out_path)
    return out_path


if __name__ == "__main__":
    main()

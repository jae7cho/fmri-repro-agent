"""Build the representative ``examples/spec.json`` fixture.

The fixture is a *generated artifact*: this script constructs a
:class:`StudySpec` in Python (mypy-checks every field; the model_validator
enforces every spec invariant at construction time) and serializes it. To
update the example, edit this script and re-run it.

Layout — one ``StudySpec`` wrapping two ``ReplicationSpec``s:

1. **HNU1** (no ``site`` set): a heterogeneous collection exercising all
   three acquisition arms in one dataset:
   - one :class:`AnatomicalAcquisition` (T1w)
   - one :class:`FunctionalAcquisition` (rest BOLD; carries the conv and
     derived ``INFERRED_DEFAULT`` fields and a ``DEFERRED_TO_CITATION`` on
     ``prospective_motion_correction``)
   - one :class:`FieldmapAcquisition` (epi, ``dir=PA``) whose ``intended_for``
     points at the BOLD.
2. **MSC** (``site="WUSTL"``): a single MSC-style BOLD acquisition,
   exercising the multi-spec / multi-site coverage at the study level.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fmri_repro.spec.preprocessing import (
    Despike,
    MotionCorrection,
    NonsteadystateRemoval,
    NuisanceRegression,
    PipelineRef,
    Preprocessing,
    SpatialSmoothing,
    TemporalFiltering,
)
from fmri_repro.spec.provenance import (
    Deferral,
    DeferredToCitation,
    DerivedBasis,
    Extracted,
    FieldConventionBasis,
    InferredDefault,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
    VersionDefaultBasis,
)
from fmri_repro.spec.v0_1_0 import (
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
    StudySpec,
    Thresholding,
)

# Pinned so successive runs produce byte-identical output.
_FIXED_RUN_ID = "00000000000000000000000000000001"
_FIXED_CREATED_AT = datetime(2026, 5, 20, 0, 0, 0, tzinfo=UTC)
_METHODS = "Methods"


def _span(text: str, start: int) -> Span:
    return Span(start=start, end=start + len(text), text=text, section=_METHODS)


def _missing(field_id: str, t: type) -> ProvenancedField:
    """LEFT_MISSING shorthand parameterized by element type. Returns the
    weakly-typed PF; call sites are typed by their containing model field."""
    return ProvenancedField[t](  # type: ignore[valid-type]
        field_id=field_id,
        extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
        inference=LeftMissing(reason="not reported in paper"),
    )


# ---------------------------------------------------------------------------
# Spec #1 — HNU1 (heterogeneous collection: T1w + bold + epi fieldmap)
# ---------------------------------------------------------------------------
def _hnu_common_kwargs() -> dict[str, ProvenancedField]:
    """The 13 CommonAcquisitionParams fields, shared by all HNU1 acquisitions
    (same scanner, same coil, same field strength, etc.)."""
    return {
        "manufacturer": ProvenancedField[str](
            field_id="manufacturer",
            extraction=Extracted[str](
                value="Siemens",
                spans=[_span("Siemens 3T Prisma scanner", 100)],
                confidence=0.98,
            ),
            inference=NotApplicable(),
        ),
        "scanner_model": ProvenancedField[str](
            field_id="scanner_model",
            extraction=Extracted[str](
                value="Prisma",
                spans=[_span("Siemens 3T Prisma scanner", 100)],
                confidence=0.96,
            ),
            inference=NotApplicable(),
        ),
        "field_strength_t": ProvenancedField[float](
            field_id="field_strength_t",
            extraction=Extracted[float](
                value=3.0,
                spans=[_span("3T", 107)],
                confidence=0.99,
            ),
            inference=NotApplicable(),
        ),
        "receive_coil": _missing("receive_coil", str),
        "pulse_sequence_type": ProvenancedField[PulseSequenceType](
            field_id="pulse_sequence_type",
            extraction=Extracted[PulseSequenceType](
                value=PulseSequenceType.GRADIENT_ECHO,
                spans=[_span("gradient-echo EPI", 200)],
                confidence=0.95,
            ),
            inference=NotApplicable(),
        ),
        "imaging_type": _missing("imaging_type", ImagingType),
        "mr_acquisition_type": ProvenancedField[MRAcquisitionType](
            field_id="mr_acquisition_type",
            extraction=Extracted[MRAcquisitionType](
                value=MRAcquisitionType.TWO_D,
                spans=[_span("2D EPI", 220)],
                confidence=0.93,
            ),
            inference=NotApplicable(),
        ),
        "partial_fourier": _missing("partial_fourier", float),
        "repetition_time_s": ProvenancedField[float](
            field_id="repetition_time_s",
            extraction=Extracted[float](
                value=2.0,
                spans=[_span("TR = 2.0 s", 300)],
                confidence=0.97,
            ),
            inference=NotApplicable(),
        ),
        "flip_angle_deg": ProvenancedField[float](
            field_id="flip_angle_deg",
            extraction=Extracted[float](
                value=80.0,
                spans=[_span("flip angle 80°", 340)],
                confidence=0.94,
            ),
            inference=NotApplicable(),
        ),
        "voxel_size_mm": ProvenancedField[tuple[float, float, float]](
            field_id="voxel_size_mm",
            extraction=Extracted[tuple[float, float, float]](
                value=(3.0, 3.0, 3.0),
                spans=[_span("3 x 3 x 3 mm voxels", 400)],
                confidence=0.96,
            ),
            inference=NotApplicable(),
        ),
        "matrix_size": ProvenancedField[tuple[int, ...]](
            field_id="matrix_size",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
            inference=LeftMissing(reason="not reported in paper"),
        ),
        "fov_mm": ProvenancedField[tuple[float, ...]](
            field_id="fov_mm",
            extraction=MissingFromPaper(
                searched_terms=["FOV", "field of view"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[tuple[float, ...]](
                value=(192.0, 192.0, 108.0),
                basis=DerivedBasis(
                    source_field_ids=["voxel_size_mm", "matrix_size"],
                    note="voxel_size_mm * matrix_size, per axis",
                ),
                confidence=0.55,
                alternative_inferences=[],
            ),
        ),
    }


def _hnu_t1w() -> AnatomicalAcquisition:
    return AnatomicalAcquisition(
        suffix="T1w",
        **_hnu_common_kwargs(),
        echo_time_ms=ProvenancedField[float](
            field_id="echo_time_ms",
            extraction=Extracted[float](
                value=2.34,
                spans=[_span("TE = 2.34 ms", 700)],
                confidence=0.95,
            ),
            inference=NotApplicable(),
        ),
    )


def _hnu_bold() -> FunctionalAcquisition:
    return FunctionalAcquisition(
        entities=AcquisitionEntities(task="rest"),
        **_hnu_common_kwargs(),
        echo_time_ms=ProvenancedField[list[float]](
            field_id="echo_time_ms",
            extraction=Extracted[list[float]](
                value=[30.0],
                spans=[_span("TE = 30 ms", 320)],
                confidence=0.95,
            ),
            inference=NotApplicable(),
        ),
        n_echoes=_missing("n_echoes", int),
        acquisition_time_s=ProvenancedField[float](
            field_id="acquisition_time_s",
            extraction=MissingFromPaper(
                searched_terms=["scan duration", "acquisition time"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[float](
                value=600.0,
                basis=DerivedBasis(
                    source_field_ids=["n_volumes", "repetition_time_s"],
                    note="n_volumes * repetition_time_s",
                ),
                confidence=0.65,
                alternative_inferences=[],
            ),
        ),
        n_volumes=ProvenancedField[int](
            field_id="n_volumes",
            extraction=Extracted[int](
                value=300,
                spans=[_span("300 volumes", 440)],
                confidence=0.95,
            ),
            inference=NotApplicable(),
        ),
        n_slices=ProvenancedField[int](
            field_id="n_slices",
            extraction=Extracted[int](
                value=36,
                spans=[_span("36 slices", 420)],
                confidence=0.95,
            ),
            inference=NotApplicable(),
        ),
        slice_gap_mm=_missing("slice_gap_mm", float),
        slice_orientation=_missing("slice_orientation", SliceOrientation),
        slice_angulation_deg=_missing("slice_angulation_deg", float),
        brain_coverage=_missing("brain_coverage", BrainCoverage),
        slice_order_pattern=ProvenancedField[SliceOrderPattern](
            field_id="slice_order_pattern",
            extraction=Extracted[SliceOrderPattern](
                value=SliceOrderPattern.INTERLEAVED_ASCENDING,
                spans=[_span("interleaved ascending slice order", 460)],
                confidence=0.90,
            ),
            inference=NotApplicable(),
        ),
        slice_timing_s=ProvenancedField[list[float]](
            field_id="slice_timing_s",
            extraction=MissingFromPaper(
                searched_terms=["slice timing", "SliceTiming"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[list[float]](
                value=[0.0, 1.0, 0.0556, 1.0556],
                basis=DerivedBasis(
                    source_field_ids=[
                        "slice_order_pattern",
                        "n_slices",
                        "repetition_time_s",
                    ],
                    note="reconstructed from slice_order_pattern + n_slices + TR",
                ),
                confidence=0.5,
                alternative_inferences=[],
            ),
        ),
        slice_encoding_direction=_missing("slice_encoding_direction", AxisDirection),
        multiband_factor=ProvenancedField[int](
            field_id="multiband_factor",
            extraction=Extracted[int](
                value=4,
                spans=[_span("multiband factor 4", 500)],
                confidence=0.92,
            ),
            inference=NotApplicable(),
        ),
        parallel_technique=ProvenancedField[ParallelTechnique](
            field_id="parallel_technique",
            extraction=MissingFromPaper(
                searched_terms=["GRAPPA", "SENSE", "parallel imaging"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[ParallelTechnique](
                value=ParallelTechnique.NONE,
                basis=FieldConventionBasis(
                    source="BIDS ParallelAcquisitionTechnique ∅ → 'none'",
                    note="convention: absence of mention defaults to no parallel technique",
                ),
                confidence=0.35,
                alternative_inferences=[],
            ),
        ),
        parallel_factor=_missing("parallel_factor", float),
        phase_encoding_reported=_missing("phase_encoding_reported", str),
        phase_encoding_direction=_missing("phase_encoding_direction", AxisDirection),
        pe_reversal=_missing("pe_reversal", bool),
        effective_echo_spacing_s=_missing("effective_echo_spacing_s", float),
        total_readout_time_s=_missing("total_readout_time_s", float),
        prospective_motion_correction=ProvenancedField[bool](
            field_id="prospective_motion_correction",
            extraction=DeferredToCitation(
                deferrals=[
                    Deferral(
                        ref="Gordon 2017",
                        span=_span(
                            "scanner-side motion handling as described in Gordon et al. (2017)",
                            550,
                        ),
                        target_kind="paper",
                    ),
                ],
                searched_terms=["prospective motion correction", "PMC"],
                sections_searched=[_METHODS],
            ),
            inference=LeftMissing(reason="paper defers to cited methods"),
        ),
        signal_inhomogeneity_correction=_missing("signal_inhomogeneity_correction", bool),
        distortion_correction_onscanner=_missing("distortion_correction_onscanner", bool),
        recon_matrix_differs=_missing("recon_matrix_differs", bool),
        shimming=ProvenancedField[str](
            field_id="shimming",
            extraction=MissingFromPaper(
                searched_terms=["shim", "shimming"],
                sections_searched=[_METHODS],
            ),
            inference=LeftMissing(reason="reporting-only; not modeled by pipeline in v0.1.0"),
        ),
        n_dummy_scanner=_missing("n_dummy_scanner", int),
    )


def _hnu_epi_fieldmap() -> FieldmapAcquisition:
    return FieldmapAcquisition(
        suffix="epi",
        entities=AcquisitionEntities(dir="PA"),
        **_hnu_common_kwargs(),
        phase_encoding_direction=ProvenancedField[AxisDirection](
            field_id="phase_encoding_direction",
            extraction=Extracted[AxisDirection](
                value=AxisDirection.J,
                spans=[_span("phase encoding j (PA)", 800)],
                confidence=0.9,
            ),
            inference=NotApplicable(),
        ),
        effective_echo_spacing_s=_missing("effective_echo_spacing_s", float),
        total_readout_time_s=_missing("total_readout_time_s", float),
        echo_times_ms=ProvenancedField[list[float]](
            field_id="echo_times_ms",
            extraction=Extracted[list[float]](
                value=[30.0],
                spans=[_span("TE = 30 ms (fieldmap)", 820)],
                confidence=0.9,
            ),
            inference=NotApplicable(),
        ),
        intended_for=[
            AcquisitionRef(
                suffix="bold",
                entities=AcquisitionEntities(task="rest"),
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Spec #2 — MSC (single BOLD; carries DatasetRef.site to exercise that field)
# ---------------------------------------------------------------------------
def _msc_common_kwargs() -> dict[str, ProvenancedField]:
    return {
        "manufacturer": ProvenancedField[str](
            field_id="manufacturer",
            extraction=Extracted[str](
                value="Siemens",
                spans=[_span("Siemens 3T Trio Tim", 100)],
                confidence=0.98,
            ),
            inference=NotApplicable(),
        ),
        "scanner_model": ProvenancedField[str](
            field_id="scanner_model",
            extraction=Extracted[str](
                value="Trio Tim",
                spans=[_span("Siemens 3T Trio Tim", 100)],
                confidence=0.95,
            ),
            inference=NotApplicable(),
        ),
        "field_strength_t": ProvenancedField[float](
            field_id="field_strength_t",
            extraction=Extracted[float](
                value=3.0,
                spans=[_span("3T", 107)],
                confidence=0.99,
            ),
            inference=NotApplicable(),
        ),
        "receive_coil": _missing("receive_coil", str),
        "pulse_sequence_type": ProvenancedField[PulseSequenceType](
            field_id="pulse_sequence_type",
            extraction=Extracted[PulseSequenceType](
                value=PulseSequenceType.GRADIENT_ECHO,
                spans=[_span("gradient-echo EPI", 200)],
                confidence=0.94,
            ),
            inference=NotApplicable(),
        ),
        "imaging_type": _missing("imaging_type", ImagingType),
        "mr_acquisition_type": ProvenancedField[MRAcquisitionType](
            field_id="mr_acquisition_type",
            extraction=Extracted[MRAcquisitionType](
                value=MRAcquisitionType.TWO_D,
                spans=[_span("2D EPI", 220)],
                confidence=0.92,
            ),
            inference=NotApplicable(),
        ),
        "partial_fourier": _missing("partial_fourier", float),
        "repetition_time_s": ProvenancedField[float](
            field_id="repetition_time_s",
            extraction=Extracted[float](
                value=2.2,
                spans=[_span("TR = 2.2 s", 300)],
                confidence=0.97,
            ),
            inference=NotApplicable(),
        ),
        "flip_angle_deg": ProvenancedField[float](
            field_id="flip_angle_deg",
            extraction=Extracted[float](
                value=80.0,
                spans=[_span("flip angle 80°", 340)],
                confidence=0.94,
            ),
            inference=NotApplicable(),
        ),
        "voxel_size_mm": ProvenancedField[tuple[float, float, float]](
            field_id="voxel_size_mm",
            extraction=Extracted[tuple[float, float, float]](
                value=(4.0, 4.0, 4.0),
                spans=[_span("4 x 4 x 4 mm voxels", 400)],
                confidence=0.96,
            ),
            inference=NotApplicable(),
        ),
        "matrix_size": ProvenancedField[tuple[int, ...]](
            field_id="matrix_size",
            extraction=MissingFromPaper(searched_terms=[], sections_searched=[_METHODS]),
            inference=LeftMissing(reason="not reported in paper"),
        ),
        "fov_mm": ProvenancedField[tuple[float, ...]](
            field_id="fov_mm",
            extraction=MissingFromPaper(
                searched_terms=["FOV", "field of view"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[tuple[float, ...]](
                value=(256.0, 256.0, 144.0),
                basis=DerivedBasis(
                    source_field_ids=["voxel_size_mm", "matrix_size"],
                    note="voxel_size_mm * matrix_size, per axis",
                ),
                confidence=0.55,
                alternative_inferences=[],
            ),
        ),
    }


def _msc_bold() -> FunctionalAcquisition:
    return FunctionalAcquisition(
        entities=AcquisitionEntities(task="rest"),
        **_msc_common_kwargs(),
        echo_time_ms=ProvenancedField[list[float]](
            field_id="echo_time_ms",
            extraction=Extracted[list[float]](
                value=[27.0],
                spans=[_span("TE = 27 ms", 320)],
                confidence=0.95,
            ),
            inference=NotApplicable(),
        ),
        n_echoes=_missing("n_echoes", int),
        acquisition_time_s=ProvenancedField[float](
            field_id="acquisition_time_s",
            extraction=MissingFromPaper(
                searched_terms=["scan duration", "acquisition time"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[float](
                value=1800.0,
                basis=DerivedBasis(
                    source_field_ids=["n_volumes", "repetition_time_s"],
                    note="n_volumes * repetition_time_s",
                ),
                confidence=0.65,
                alternative_inferences=[],
            ),
        ),
        n_volumes=ProvenancedField[int](
            field_id="n_volumes",
            extraction=Extracted[int](
                value=818,
                spans=[_span("818 volumes", 440)],
                confidence=0.94,
            ),
            inference=NotApplicable(),
        ),
        n_slices=ProvenancedField[int](
            field_id="n_slices",
            extraction=Extracted[int](
                value=36,
                spans=[_span("36 slices", 420)],
                confidence=0.94,
            ),
            inference=NotApplicable(),
        ),
        slice_gap_mm=_missing("slice_gap_mm", float),
        slice_orientation=_missing("slice_orientation", SliceOrientation),
        slice_angulation_deg=_missing("slice_angulation_deg", float),
        brain_coverage=_missing("brain_coverage", BrainCoverage),
        slice_order_pattern=ProvenancedField[SliceOrderPattern](
            field_id="slice_order_pattern",
            extraction=Extracted[SliceOrderPattern](
                value=SliceOrderPattern.INTERLEAVED_ASCENDING,
                spans=[_span("interleaved ascending slice order", 460)],
                confidence=0.88,
            ),
            inference=NotApplicable(),
        ),
        slice_timing_s=ProvenancedField[list[float]](
            field_id="slice_timing_s",
            extraction=MissingFromPaper(
                searched_terms=["slice timing", "SliceTiming"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[list[float]](
                value=[0.0, 1.1, 0.0611, 1.1611],
                basis=DerivedBasis(
                    source_field_ids=[
                        "slice_order_pattern",
                        "n_slices",
                        "repetition_time_s",
                    ],
                    note="reconstructed from slice_order_pattern + n_slices + TR",
                ),
                confidence=0.5,
                alternative_inferences=[],
            ),
        ),
        slice_encoding_direction=_missing("slice_encoding_direction", AxisDirection),
        multiband_factor=ProvenancedField[int](
            field_id="multiband_factor",
            extraction=MissingFromPaper(
                searched_terms=["multiband", "simultaneous multi-slice"],
                sections_searched=[_METHODS],
            ),
            inference=LeftMissing(reason="not reported; MSC Trio was single-band"),
        ),
        parallel_technique=ProvenancedField[ParallelTechnique](
            field_id="parallel_technique",
            extraction=MissingFromPaper(
                searched_terms=["GRAPPA", "SENSE", "parallel imaging"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[ParallelTechnique](
                value=ParallelTechnique.NONE,
                basis=FieldConventionBasis(
                    source="BIDS ParallelAcquisitionTechnique ∅ → 'none'",
                    note="convention: absence of mention defaults to no parallel technique",
                ),
                confidence=0.35,
                alternative_inferences=[],
            ),
        ),
        parallel_factor=_missing("parallel_factor", float),
        phase_encoding_reported=_missing("phase_encoding_reported", str),
        phase_encoding_direction=_missing("phase_encoding_direction", AxisDirection),
        pe_reversal=_missing("pe_reversal", bool),
        effective_echo_spacing_s=_missing("effective_echo_spacing_s", float),
        total_readout_time_s=_missing("total_readout_time_s", float),
        prospective_motion_correction=_missing("prospective_motion_correction", bool),
        signal_inhomogeneity_correction=_missing("signal_inhomogeneity_correction", bool),
        distortion_correction_onscanner=_missing("distortion_correction_onscanner", bool),
        recon_matrix_differs=_missing("recon_matrix_differs", bool),
        shimming=ProvenancedField[str](
            field_id="shimming",
            extraction=MissingFromPaper(
                searched_terms=["shim", "shimming"],
                sections_searched=[_METHODS],
            ),
            inference=LeftMissing(reason="reporting-only; not modeled by pipeline in v0.1.0"),
        ),
        n_dummy_scanner=_missing("n_dummy_scanner", int),
    )


# ---------------------------------------------------------------------------
# Preprocessing — Cho HNU (CCS base) and Cho MSC (minimal demo).
#
# Each Preprocessing exercises:
#  - ``base_pipeline``: ``PipelineRef`` with ``version`` carrying provenance
#    (deferred-to-pipeline for HNU; inferred-via-version_default for MSC), and
#    ``NotApplicable`` is exercised in the test fixtures (Bassett-style).
#  - Per-kind uniqueness via distinct ``kind`` discriminators.
#  - Conservative inference: ``inference_applicable=False`` fields use
#    MISSING + LEFT_MISSING; the few inference-applicable fields use
#    field-convention defaults under the basis ceiling.
# ---------------------------------------------------------------------------


def _hnu_preprocessing() -> Preprocessing:
    """CCS-style pipeline applied to the HNU1 rest BOLD.

    Demonstrates nested base_pipeline provenance: outer ``Extracted`` (paper
    named CCS) wrapping an inner ``PipelineRef.version`` that is itself
    ``DeferredToCitation`` (paper cites Xu 2015 without pinning a version).
    """
    inner_pipeline_ref = PipelineRef(
        name="CCS",
        version=ProvenancedField[str](
            field_id="version",
            extraction=DeferredToCitation(
                deferrals=[
                    Deferral(
                        ref="Xu 2015 - CCS",
                        span=_span("preprocessed with CCS (Xu et al., 2015)", 1000),
                        target_kind="pipeline",
                    ),
                ],
                searched_terms=["CCS", "Connectome Computation System"],
                sections_searched=[_METHODS],
            ),
            inference=LeftMissing(reason="pipeline version not pinned in paper"),
        ),
    )
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=ProvenancedField[PipelineRef](
            field_id="base_pipeline",
            extraction=Extracted[PipelineRef](
                value=inner_pipeline_ref,
                spans=[_span("CCS pipeline", 950)],
                confidence=0.93,
            ),
            inference=NotApplicable(),
        ),
        steps=[
            NonsteadystateRemoval(
                n_nonsteadystate_discarded=ProvenancedField[int](
                    field_id="n_nonsteadystate_discarded",
                    extraction=Extracted[int](
                        value=4,
                        spans=[_span("first 4 volumes discarded", 1100)],
                        confidence=0.92,
                    ),
                    inference=NotApplicable(),
                ),
            ),
            Despike(
                method=ProvenancedField[str](
                    field_id="method",
                    extraction=Extracted[str](
                        value="afni_3dDespike",
                        spans=[_span("AFNI 3dDespike", 1140)],
                        confidence=0.9,
                    ),
                    inference=NotApplicable(),
                ),
                threshold=_missing("threshold", float),
            ),
            MotionCorrection(
                method=ProvenancedField[str](
                    field_id="method",
                    extraction=Extracted[str](
                        value="mcflirt",
                        spans=[_span("FSL MCFLIRT", 1200)],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                reference_scan=_missing("reference_scan", str),
                similarity_metric=_missing("similarity_metric", str),
                interpolation=_missing("interpolation", str),
                nonrigid=_missing("nonrigid", bool),
                transform_type=_missing("transform_type", str),
                fieldmap_unwarping=_missing("fieldmap_unwarping", bool),
                unwarping_method=_missing("unwarping_method", str),
                slice_to_volume=_missing("slice_to_volume", bool),
            ),
            NuisanceRegression(
                motion_expansion=ProvenancedField[str](
                    field_id="motion_expansion",
                    extraction=Extracted[str](
                        value="friston24",
                        spans=[_span("24 motion regressors (Friston)", 1300)],
                        confidence=0.92,
                    ),
                    inference=NotApplicable(),
                ),
                tissue_regressors=ProvenancedField[list[str]](
                    field_id="tissue_regressors",
                    extraction=Extracted[list[str]](
                        value=["white_matter", "ventricles"],
                        spans=[_span("WM + CSF regression", 1340)],
                        confidence=0.9,
                    ),
                    inference=NotApplicable(),
                ),
                physio_regressors=_missing("physio_regressors", str),
                physio_n_regressors=_missing("physio_n_regressors", int),
                detrend=ProvenancedField[str](
                    field_id="detrend",
                    extraction=Extracted[str](
                        value="linear",
                        spans=[_span("linear detrend", 1380)],
                        confidence=0.9,
                    ),
                    inference=NotApplicable(),
                ),
            ),
            TemporalFiltering(
                effective_band_hz=ProvenancedField[tuple[float | None, float | None]](
                    field_id="effective_band_hz",
                    extraction=Extracted[tuple[float | None, float | None]](
                        value=(0.01, 0.1),
                        spans=[_span("bandpass 0.01-0.1 Hz", 1400)],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                method=ProvenancedField[str](
                    field_id="method",
                    extraction=Extracted[str](
                        value="butterworth_bandpass",
                        spans=[_span("Butterworth bandpass", 1420)],
                        confidence=0.93,
                    ),
                    inference=NotApplicable(),
                ),
                low_hz=ProvenancedField[float](
                    field_id="low_hz",
                    extraction=Extracted[float](
                        value=0.01,
                        spans=[_span("0.01 Hz", 1440)],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                high_hz=ProvenancedField[float](
                    field_id="high_hz",
                    extraction=Extracted[float](
                        value=0.1,
                        spans=[_span("0.1 Hz", 1460)],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                order=_missing("order", int),
                cutoff=_missing("cutoff", float),
                scale=_missing("scale", int),
                nominal_band_hz=_missing("nominal_band_hz", tuple),
            ),
        ],
    )


def _msc_preprocessing() -> Preprocessing:
    """Minimal demonstration pipeline applied to the MSC rest BOLD.

    Demonstrates outer Extracted (paper named fMRIPrep) with inner-version
    InferredDefault (Configurator backfilled the version via version_default)."""
    inner_pipeline_ref = PipelineRef(
        name="fMRIPrep",
        version=ProvenancedField[str](
            field_id="version",
            extraction=MissingFromPaper(
                searched_terms=["fMRIPrep version"],
                sections_searched=[_METHODS],
            ),
            inference=InferredDefault[str](
                value="23.2.1",
                basis=VersionDefaultBasis(
                    tool="fMRIPrep",
                    version="23.2.1",
                    note="MSC representative version for v0.1.0 fixture",
                ),
                confidence=0.9,
                alternative_inferences=[],
            ),
        ),
    )
    return Preprocessing(
        applies_to=[AcquisitionRef(suffix="bold", entities=AcquisitionEntities(task="rest"))],
        base_pipeline=ProvenancedField[PipelineRef](
            field_id="base_pipeline",
            extraction=Extracted[PipelineRef](
                value=inner_pipeline_ref,
                spans=[_span("fMRIPrep pipeline", 950)],
                confidence=0.95,
            ),
            inference=NotApplicable(),
        ),
        steps=[
            MotionCorrection(
                method=ProvenancedField[str](
                    field_id="method",
                    extraction=Extracted[str](
                        value="mcflirt",
                        spans=[_span("FSL MCFLIRT", 1500)],
                        confidence=0.95,
                    ),
                    inference=NotApplicable(),
                ),
                reference_scan=_missing("reference_scan", str),
                similarity_metric=_missing("similarity_metric", str),
                interpolation=_missing("interpolation", str),
                nonrigid=_missing("nonrigid", bool),
                transform_type=_missing("transform_type", str),
                fieldmap_unwarping=_missing("fieldmap_unwarping", bool),
                unwarping_method=_missing("unwarping_method", str),
                slice_to_volume=_missing("slice_to_volume", bool),
            ),
            SpatialSmoothing(
                fwhm_mm=ProvenancedField[float](
                    field_id="fwhm_mm",
                    extraction=Extracted[float](
                        value=6.0,
                        spans=[_span("FWHM 6 mm Gaussian", 1550)],
                        confidence=0.94,
                    ),
                    inference=NotApplicable(),
                ),
                space=ProvenancedField[str](
                    field_id="space",
                    extraction=Extracted[str](
                        value="mni_volume",
                        spans=[_span("smoothed in MNI volume", 1570)],
                        confidence=0.9,
                    ),
                    inference=NotApplicable(),
                ),
                kernel_type=_missing("kernel_type", str),
                approach=_missing("approach", str),
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def _empty_stubs() -> dict[str, object]:
    """Empty placeholders for the still-stub groups (first/group/thresholding)."""
    return {
        "first_level": FirstLevelModel(),
        "group_level": GroupLevelModel(),
        "thresholding": Thresholding(),
    }


def _build_study() -> StudySpec:
    hnu = ReplicationSpec(
        dataset=DatasetRef(
            name="HNU1",
            accession="HNU_1",
            source_url="http://fcon_1000.projects.nitrc.org/indi/CoRR/html/hnu_1.html",
        ),
        acquisitions=[_hnu_t1w(), _hnu_bold(), _hnu_epi_fieldmap()],
        preprocessing=[_hnu_preprocessing()],
        **_empty_stubs(),
    )
    msc = ReplicationSpec(
        dataset=DatasetRef(
            name="MSC",
            accession="ds000224",
            source_url="https://openneuro.org/datasets/ds000224",
            site="WUSTL",
        ),
        acquisitions=[_msc_bold()],
        preprocessing=[_msc_preprocessing()],
        **_empty_stubs(),
    )
    return StudySpec(
        run=RunMeta(
            run_id=_FIXED_RUN_ID,
            created_at=_FIXED_CREATED_AT,
            paper=PaperRef(source="10.1234/example", sha256=None),
        ),
        specs=[hnu, msc],
        study_analysis=None,
    )


def main() -> Path:
    study = _build_study()
    out_path = Path("examples") / "spec.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(study.model_dump_json(indent=2) + "\n")
    print(out_path)
    return out_path


if __name__ == "__main__":
    main()

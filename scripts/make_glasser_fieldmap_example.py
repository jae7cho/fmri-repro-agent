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

from datetime import UTC, datetime
from pathlib import Path

from fmri_repro.spec.provenance import (
    Deferral,
    DeferredToCitation,
    Extracted,
    LeftMissing,
    MissingFromPaper,
    NotApplicable,
    ProvenancedField,
    Span,
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
    Preprocessing,
    PulseSequenceType,
    ReplicationSpec,
    RunMeta,
    SliceOrderPattern,
    SliceOrientation,
    StudySpec,
    Thresholding,
)

_FIXED_RUN_ID = "00000000000000000000000000000002"
_FIXED_CREATED_AT = datetime(2026, 5, 21, 0, 0, 0, tzinfo=UTC)
_METHODS = "Methods"
_CITATION_REFS = ("Smith 2013", "Ugurbil 2013")


def _span(text: str, start: int) -> Span:
    return Span(start=start, end=start + len(text), text=text, section=_METHODS)


def _missing(field_id: str, t: type) -> ProvenancedField:
    """MISSING + LEFT_MISSING shorthand. Caller-supplied ``t`` is the element type."""
    return ProvenancedField[t](  # type: ignore[valid-type]
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
        preprocessing=Preprocessing(),
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

"""Versioned root for ReplicationSpec v0.1.0.

The spec is SemVer'd, with **one module per minor version** (this is the v0.1.0
module; a future v0.2.0 will live in a sibling ``v0_2_0.py`` and import the
same version-stable core types from :mod:`fmri_repro.spec.provenance`).

Between-version migrations are intended to be expressed as RFC 6902 JSON Patch
documents. **No migration engine is implemented in this chat** — that is
deferred to a later milestone, along with ``python-jsonpatch`` / ``bsmschema``
integration.

Acquisition is split into modality-typed arms — :class:`FunctionalAcquisition`,
:class:`AnatomicalAcquisition`, :class:`FieldmapAcquisition` — sharing the
13-field :class:`CommonAcquisitionParams` base. A :class:`ReplicationSpec`
carries ``acquisitions: list[Acquisition]`` (one entry per *protocol*, not per
run/session). The acquisitions in a single ReplicationSpec are within one
dataset (single site); multi-site or heterogeneous-protocol studies use
multiple ReplicationSpecs under one :class:`StudySpec`.

Per-field metadata (justification axis, source, BIDS key, unit, and whether
Configurator inference applies) lives in the per-arm registries
``COMMON_FIELD_META`` / ``FUNCTIONAL_FIELD_META`` / ``ANATOMICAL_FIELD_META``
/ ``FIELDMAP_FIELD_META``. Each registry is keyed by the **bare field name**
(``"repetition_time_s"``, not ``"acquisition.repetition_time_s"``) — the
report path is composed from :func:`bids_stem` + ``field_id``.

Data-recovery from headers/sidecars is deferred to v0.2+: in v0.1.0 the
Configurator may emit ``INFERRED_DEFAULT`` only on the 6 fields the catalog
marks ``conv`` (``multiband_factor``, ``parallel_technique``,
``parallel_factor``) or ``deriv`` (``fov_mm``, ``acquisition_time_s``,
``slice_timing_s``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, ClassVar, Literal, Self
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from fmri_repro.spec.provenance import ProvenancedField


# ---------------------------------------------------------------------------
# Run metadata
# ---------------------------------------------------------------------------
class PaperRef(BaseModel):
    source: str
    sha256: str | None = None


class RunMeta(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    paper: PaperRef


# ---------------------------------------------------------------------------
# Dataset & study-analysis surface (paper→specs layer)
# ---------------------------------------------------------------------------
class DatasetRef(BaseModel):
    """The context (dataset and/or site) this spec describes."""

    name: str
    accession: str | None = None
    source_url: str | None = None
    site: str | None = None


class StudyAnalysis(BaseModel):
    """TODO: cross-dataset analysis layer (concatenation, FC, reliability) —
    out of scope for v0.1.0."""


# ---------------------------------------------------------------------------
# Acquisition identity (BIDS entities + bids_stem path helper)
# ---------------------------------------------------------------------------
class AcquisitionEntities(BaseModel):
    """BIDS entities that together with the suffix identify an acquisition protocol."""

    task: str | None = None
    run: int | None = None
    dir: str | None = None  # phase-encoding entity, e.g. "LR" / "AP"
    acq: str | None = None


class AcquisitionRef(BaseModel):
    """Reference from a fieldmap's ``intended_for`` to another acquisition in the same spec."""

    suffix: str
    entities: AcquisitionEntities = AcquisitionEntities()


# Order in which BIDS composes entities into a filename stem (relevant subset).
_BIDS_ENTITY_ORDER: tuple[str, ...] = ("task", "acq", "dir", "run")


def bids_stem(suffix: str, entities: AcquisitionEntities) -> str:
    """Compose a BIDS filename stem like ``"task-rest_dir-LR_bold"`` (without
    file extension). Acquisitions without entities reduce to the bare suffix
    (e.g. ``"T1w"``)."""
    parts: list[str] = []
    for ent in _BIDS_ENTITY_ORDER:
        val = getattr(entities, ent)
        if val is not None:
            parts.append(f"{ent}-{val}")
    parts.append(suffix)
    return "_".join(parts)


# ---------------------------------------------------------------------------
# Enumerations (per catalog)
# ---------------------------------------------------------------------------
class PulseSequenceType(StrEnum):
    GRADIENT_ECHO = "gradient_echo"
    SPIN_ECHO = "spin_echo"
    OTHER = "other"


class ImagingType(StrEnum):
    EPI = "epi"
    SPIRAL = "spiral"
    OTHER = "other"


class MRAcquisitionType(StrEnum):
    TWO_D = "2D"
    THREE_D = "3D"


class SliceOrientation(StrEnum):
    AXIAL = "axial"
    SAGITTAL = "sagittal"
    CORONAL = "coronal"
    OBLIQUE = "oblique"


class SliceOrderPattern(StrEnum):
    ASCENDING = "ascending"
    DESCENDING = "descending"
    INTERLEAVED_ASCENDING = "interleaved_ascending"
    INTERLEAVED_DESCENDING = "interleaved_descending"
    UNKNOWN = "unknown"


class ParallelTechnique(StrEnum):
    GRAPPA = "GRAPPA"
    SENSE = "SENSE"
    MSENSE = "mSENSE"
    OTHER = "other"
    NONE = "none"


class AxisDirection(StrEnum):
    """BIDS-style i/j/k axis with optional sign reversal."""

    I = "i"  # noqa: E741  — member name mirrors BIDS axis label
    I_NEG = "i-"
    J = "j"
    J_NEG = "j-"
    K = "k"
    K_NEG = "k-"


# ---------------------------------------------------------------------------
# Structured sub-models
# ---------------------------------------------------------------------------
class BrainCoverage(BaseModel):
    whole_brain: bool
    cerebellum_included: bool
    brainstem_included: bool
    z_extent_mm: float | None = None


# ---------------------------------------------------------------------------
# Per-field metadata (registry — split per arm; see catalog v0.1.0)
# ---------------------------------------------------------------------------
class FieldMeta(BaseModel):
    justification_axis: Literal["cobidas", "pipeline", "both"]
    inference_applicable: bool
    source: Literal["sidecar", "header", "derived", "none"]
    bids_key: str | None = None
    unit: str | None = None


COMMON_FIELD_META: dict[str, FieldMeta] = {
    # MRI System
    "manufacturer": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="sidecar",
        bids_key="Manufacturer",
    ),
    "scanner_model": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="sidecar",
        bids_key="ManufacturersModelName",
    ),
    "field_strength_t": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="sidecar",
        bids_key="MagneticFieldStrength",
        unit="T",
    ),
    "receive_coil": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="sidecar",
        bids_key="ReceiveCoilName",
    ),
    # Sequence
    "pulse_sequence_type": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="sidecar",
        bids_key="PulseSequenceType",
    ),
    "imaging_type": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="sidecar",
        bids_key="ScanningSequence",
    ),
    "mr_acquisition_type": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="sidecar",
        bids_key="MRAcquisitionType",
    ),
    "partial_fourier": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="sidecar",
        bids_key="PartialFourier",
    ),
    # Timing & flip
    "repetition_time_s": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="sidecar",
        bids_key="RepetitionTime",
        unit="s",
    ),
    "flip_angle_deg": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="sidecar",
        bids_key="FlipAngle",
        unit="deg",
    ),
    # Geometry shared with all modalities — voxel/matrix/fov form a mutually
    # derivable triple (any one from the other two), so all three are
    # inference-applicable with a derived basis in v0.1.0.
    "voxel_size_mm": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
        unit="mm",
    ),
    "matrix_size": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=True,
        source="derived",
    ),
    "fov_mm": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=True,
        source="derived",
        unit="mm",
    ),
}


FUNCTIONAL_FIELD_META: dict[str, FieldMeta] = {
    # Timing & echo (multi-echo capable)
    "echo_time_ms": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="sidecar",
        bids_key="EchoTime",
        unit="ms",
    ),
    "n_echoes": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="none",
    ),
    "acquisition_time_s": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=True,
        source="derived",
        unit="s",
    ),
    "n_volumes": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="header",
    ),
    "n_slices": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="header",
    ),
    "slice_gap_mm": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="header",
        unit="mm",
    ),
    "slice_orientation": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="header",
    ),
    "slice_angulation_deg": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="header",
        unit="deg",
    ),
    "brain_coverage": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="none",
    ),
    "slice_order_pattern": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="none",
    ),
    "slice_timing_s": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="derived",
        bids_key="SliceTiming",
        unit="s",
    ),
    "slice_encoding_direction": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="sidecar",
        bids_key="SliceEncodingDirection",
    ),
    "multiband_factor": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="sidecar",
        bids_key="MultibandAccelerationFactor",
    ),
    "parallel_technique": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=True,
        source="sidecar",
        bids_key="ParallelAcquisitionTechnique",
    ),
    "parallel_factor": FieldMeta(
        justification_axis="both",
        inference_applicable=True,
        source="sidecar",
        bids_key="ParallelReductionFactorInPlane",
    ),
    "phase_encoding_reported": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="none",
    ),
    "phase_encoding_direction": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="sidecar",
        bids_key="PhaseEncodingDirection",
    ),
    "pe_reversal": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="sidecar",
    ),
    "effective_echo_spacing_s": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="sidecar",
        bids_key="EffectiveEchoSpacing",
        unit="s",
    ),
    "total_readout_time_s": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="sidecar",
        bids_key="TotalReadoutTime",
        unit="s",
    ),
    # Scanner-side preprocessing
    "prospective_motion_correction": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="none",
    ),
    "signal_inhomogeneity_correction": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="none",
    ),
    "distortion_correction_onscanner": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="none",
    ),
    "recon_matrix_differs": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="none",
    ),
    "shimming": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="none",
    ),
    "n_dummy_scanner": FieldMeta(
        justification_axis="cobidas",
        inference_applicable=False,
        source="none",
    ),
}


ANATOMICAL_FIELD_META: dict[str, FieldMeta] = {
    # Single-echo anatomical (T1w / T2w)
    "echo_time_ms": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="sidecar",
        bids_key="EchoTime",
        unit="ms",
    ),
}


FIELDMAP_FIELD_META: dict[str, FieldMeta] = {
    "phase_encoding_direction": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="sidecar",
        bids_key="PhaseEncodingDirection",
    ),
    "effective_echo_spacing_s": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="sidecar",
        bids_key="EffectiveEchoSpacing",
        unit="s",
    ),
    "total_readout_time_s": FieldMeta(
        justification_axis="pipeline",
        inference_applicable=False,
        source="sidecar",
        bids_key="TotalReadoutTime",
        unit="s",
    ),
    # 1 echo for direct fmaps; 2 for phasediff (TE1, TE2).
    "echo_times_ms": FieldMeta(
        justification_axis="both",
        inference_applicable=False,
        source="sidecar",
        bids_key="EchoTime",
        unit="ms",
    ),
}


# Names that exist on acquisition models but are NOT ProvenancedField wrappers
# (structural metadata — discriminator, identity, fmap linkage).
_STRUCTURAL_ACQ_FIELDS: frozenset[str] = frozenset({"suffix", "entities", "intended_for"})


def _check_arm_bijection(
    cls: type[BaseModel],
    arm_registry: dict[str, FieldMeta],
) -> None:
    """Each arm's provenanced fields must equal ``COMMON | arm_registry`` exactly.

    Module-level raising guard (not ``assert``: ``python -O`` strips asserts and
    would silently disable the check)."""
    provenanced = {n for n in cls.model_fields if n not in _STRUCTURAL_ACQ_FIELDS}
    expected = set(COMMON_FIELD_META) | set(arm_registry)
    if provenanced != expected:
        raise RuntimeError(
            f"{cls.__name__} registry/field mismatch: "
            f"missing_from_registry={provenanced - expected}, "
            f"extra_in_registry={expected - provenanced}"
        )


def _validate_arm_invariants(
    acq: CommonAcquisitionParams,
    arm_registry: dict[str, FieldMeta],
) -> None:
    """field_id↔name consistency + inference_applicable invariant for one arm.

    Raises ``ValueError`` on first violation; called from each arm subclass's
    ``model_validator(mode="after")``."""
    full = COMMON_FIELD_META | arm_registry
    for name in type(acq).model_fields:
        if name in _STRUCTURAL_ACQ_FIELDS:
            continue
        pf = getattr(acq, name)
        if pf.field_id != name:
            raise ValueError(
                f"field_id mismatch: attribute {name!r} has field_id {pf.field_id!r}, "
                f"expected {name!r}"
            )
        meta = full[name]
        if not meta.inference_applicable and pf.inference.status == "INFERRED_DEFAULT":
            raise ValueError(
                f"{name}: inference_applicable=False — "
                "INFERRED_DEFAULT not permitted; use LEFT_MISSING."
            )


# ---------------------------------------------------------------------------
# CommonAcquisitionParams + per-arm acquisitions
# ---------------------------------------------------------------------------
class CommonAcquisitionParams(BaseModel):
    """13 protocol-defining fields shared across all modalities.

    Not instantiated directly — always via one of the three arm subclasses.
    The base intentionally carries no discriminator / no validator; the arm
    subclasses each define ``suffix`` and a ``model_validator`` that checks
    field-id consistency and ``inference_applicable`` against
    :data:`COMMON_FIELD_META` ``|`` the arm's own registry.
    """

    # MRI System
    manufacturer: ProvenancedField[str]
    scanner_model: ProvenancedField[str]
    field_strength_t: ProvenancedField[float]
    receive_coil: ProvenancedField[str]
    # Sequence
    pulse_sequence_type: ProvenancedField[PulseSequenceType]
    imaging_type: ProvenancedField[ImagingType]
    mr_acquisition_type: ProvenancedField[MRAcquisitionType]
    partial_fourier: ProvenancedField[float]
    # Timing & flip
    repetition_time_s: ProvenancedField[float]
    flip_angle_deg: ProvenancedField[float]
    # Geometry (shared)
    voxel_size_mm: ProvenancedField[tuple[float, float, float]]
    matrix_size: ProvenancedField[tuple[int, ...]]
    fov_mm: ProvenancedField[tuple[float, ...]]


class FunctionalAcquisition(CommonAcquisitionParams):
    suffix: Literal["bold"] = "bold"
    entities: AcquisitionEntities = AcquisitionEntities()
    # --- Functional-only fields (26) ---
    echo_time_ms: ProvenancedField[list[float]]
    n_echoes: ProvenancedField[int]
    acquisition_time_s: ProvenancedField[float]
    n_volumes: ProvenancedField[int]
    n_slices: ProvenancedField[int]
    slice_gap_mm: ProvenancedField[float]
    slice_orientation: ProvenancedField[SliceOrientation]
    slice_angulation_deg: ProvenancedField[float]
    brain_coverage: ProvenancedField[BrainCoverage]
    slice_order_pattern: ProvenancedField[SliceOrderPattern]
    slice_timing_s: ProvenancedField[list[float]]
    slice_encoding_direction: ProvenancedField[AxisDirection]
    multiband_factor: ProvenancedField[int]
    parallel_technique: ProvenancedField[ParallelTechnique]
    parallel_factor: ProvenancedField[float]
    phase_encoding_reported: ProvenancedField[str]
    phase_encoding_direction: ProvenancedField[AxisDirection]
    pe_reversal: ProvenancedField[bool]
    effective_echo_spacing_s: ProvenancedField[float]
    total_readout_time_s: ProvenancedField[float]
    prospective_motion_correction: ProvenancedField[bool]
    signal_inhomogeneity_correction: ProvenancedField[bool]
    distortion_correction_onscanner: ProvenancedField[bool]
    recon_matrix_differs: ProvenancedField[bool]
    shimming: ProvenancedField[str]
    n_dummy_scanner: ProvenancedField[int]

    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = FUNCTIONAL_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_arm_invariants(self, FUNCTIONAL_FIELD_META)
        return self


class AnatomicalAcquisition(CommonAcquisitionParams):
    suffix: Literal["T1w", "T2w"]
    entities: AcquisitionEntities = AcquisitionEntities()
    echo_time_ms: ProvenancedField[float]  # single-echo (scalar)

    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = ANATOMICAL_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_arm_invariants(self, ANATOMICAL_FIELD_META)
        return self


class FieldmapAcquisition(CommonAcquisitionParams):
    suffix: Literal["epi", "phasediff", "magnitude1", "magnitude2", "fieldmap"]
    entities: AcquisitionEntities = AcquisitionEntities()
    phase_encoding_direction: ProvenancedField[AxisDirection]
    effective_echo_spacing_s: ProvenancedField[float]
    total_readout_time_s: ProvenancedField[float]
    echo_times_ms: ProvenancedField[list[float]]  # 1 (direct) or 2 (phasediff)
    intended_for: list[AcquisitionRef] = []

    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = FIELDMAP_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_arm_invariants(self, FIELDMAP_FIELD_META)
        return self


# Module-level bijection guards — raise on import if registry diverges from class.
_check_arm_bijection(FunctionalAcquisition, FUNCTIONAL_FIELD_META)
_check_arm_bijection(AnatomicalAcquisition, ANATOMICAL_FIELD_META)
_check_arm_bijection(FieldmapAcquisition, FIELDMAP_FIELD_META)


# Discriminated union over the three arms. ``suffix`` is the discriminator;
# multi-value Literals (Anatomical/Fieldmap) expand to multiple mapping entries.
Acquisition = Annotated[
    FunctionalAcquisition | AnatomicalAcquisition | FieldmapAcquisition,
    Field(discriminator="suffix"),
]


# ---------------------------------------------------------------------------
# Other groups (stubs, grown in later milestones)
# ---------------------------------------------------------------------------
class Preprocessing(BaseModel):
    """TODO: grow in a later chat."""


class FirstLevelModel(BaseModel):
    """TODO: grow in a later chat."""


class GroupLevelModel(BaseModel):
    """TODO: grow in a later chat."""


class Thresholding(BaseModel):
    """TODO: grow in a later chat."""


# ---------------------------------------------------------------------------
# Per-dataset replication unit
# ---------------------------------------------------------------------------
def _acquisition_key(
    a: FunctionalAcquisition | AnatomicalAcquisition | FieldmapAcquisition,
) -> tuple[str, str | None, int | None, str | None, str | None]:
    """Identity key for (suffix, entities) used by the uniqueness + intended_for checks."""
    e = a.entities
    return (a.suffix, e.task, e.run, e.dir, e.acq)


def _ref_key(
    ref: AcquisitionRef,
) -> tuple[str, str | None, int | None, str | None, str | None]:
    e = ref.entities
    return (ref.suffix, e.task, e.run, e.dir, e.acq)


class ReplicationSpec(BaseModel):
    """Per-dataset replication unit. Wrapped by :class:`StudySpec`."""

    dataset: DatasetRef
    acquisitions: list[Acquisition] = Field(min_length=1)
    preprocessing: Preprocessing
    first_level: FirstLevelModel
    group_level: GroupLevelModel
    thresholding: Thresholding

    @model_validator(mode="after")
    def _check_acquisition_collection(self) -> Self:
        # 1. (suffix, entities) uniqueness across the collection.
        keys = [_acquisition_key(a) for a in self.acquisitions]
        seen: set[tuple[str, str | None, int | None, str | None, str | None]] = set()
        for k in keys:
            if k in seen:
                raise ValueError(f"duplicate acquisition (suffix, entities): {k}")
            seen.add(k)

        # 2. intended_for referential integrity.
        all_keys = set(keys)
        for a in self.acquisitions:
            if not isinstance(a, FieldmapAcquisition):
                continue
            for ref in a.intended_for:
                rk = _ref_key(ref)
                if rk not in all_keys:
                    raise ValueError(
                        f"intended_for {rk} does not resolve to any acquisition in this spec"
                    )
        return self


# ---------------------------------------------------------------------------
# Study-level root — one paper → one or more per-dataset ReplicationSpecs
# ---------------------------------------------------------------------------
class StudySpec(BaseModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    run: RunMeta
    specs: list[ReplicationSpec] = Field(min_length=1)
    study_analysis: StudyAnalysis | None = None

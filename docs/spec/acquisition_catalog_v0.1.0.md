# Acquisition Field Catalog — ReplicationSpec v0.1.0

Authoritative field catalog for the `AcquisitionParams` group of the fMRI
Reproducibility Agent `ReplicationSpec`. Each field is a
`ProvenancedField[T]` (two-stage provenance chain, Option A).

Provenance of this catalog: field set traces to COBIDAS **Table D.2
(Acquisition Reporting)** [Nichols et al. 2017 committee report], which is
itself built from Ben Inglis's 2015 fMRI acquisition reporting checklist —
the same source BIDS organizes its acquisition metadata around. Exact BIDS
sidecar key names/types/units verified against the BIDS machine-readable
schema (`src/schema/objects/metadata.yaml`, BIDS 1.11.x).

## Conventions and decisions applied

1. **Two parallel provenance stages (Option A):** `extraction` (Methods
   Extractor, paper-only) + `inference` (Pipeline Configurator), coupled by a
   validator. Extraction is frozen; the Configurator only writes
   `inference` on `MISSING_FROM_PAPER` fields.
2. **Units — declared-unit-at-extraction, BIDS-seconds-at-emit:** each field
   declares one unit (suffix in name where applicable). Extraction normalizes
   the reported value into that unit (lossless; "2000 ms" -> `repetition_time_s`
   = 2.0); the span points at source text. The emitter converts field-unit ->
   BIDS canonical unit (seconds) at output.
3. **Dual-field convention** where the canonical machine value is
   underdetermined from prose: a `*_reported` descriptor (extractable) plus the
   BIDS-canonical value (often unresolved from the paper). Applied to slice
   order/timing and phase-encoding direction.
4. **Per-field metadata registry** (`ACQUISITION_FIELD_META`): each field tags
   `justification_axis` (cobidas | pipeline | both), `inference_applicable`,
   `bids_key`, `unit`, and `source` (sidecar | header | derived | none).
5. **`derived` basis (sixth basis type):** for values computed from other
   extracted fields. Ceiling 0.70. Carries `source_field_ids`.
6. **Data-recovery is OUT of v0.1.0:** fields authoritatively recoverable from
   the dataset's own NIfTI headers / BIDS sidecars (`source` = header/sidecar)
   are resolved by a separate reconciliation layer in a later version. Within
   v0.1.0 they are `EXTRACTED` or `LEFT_MISSING` and `inference_applicable=False`.

## Legend

- **Justify:** C = COBIDAS-mandatory; P = pipeline-input (fMRIPrep); C/P = both;
  C(o) = COBIDAS non-mandatory; (cond) = conditional.
- **Infer (in-spec):** N = no in-spec fill (-> `LEFT_MISSING` when absent);
  conv = field-convention default; deriv = `derived` basis.
- **Source:** how the value is ultimately resolvable — sidecar (BIDS `_bold.json`
  key), header (NIfTI), derived (computed), none (no machine source).
- field_id is the dotted path, e.g. `acquisition.repetition_time_s`.

## Catalog

### MRI system

| Field | Type | Unit | BIDS key | Source | Justify | Infer |
|---|---|---|---|---|---|---|
| manufacturer | str | — | Manufacturer | sidecar | C | N |
| scanner_model | str | — | ManufacturersModelName | sidecar | C | N |
| field_strength_t | float | T | MagneticFieldStrength | sidecar | C/P | N |
| receive_coil | str | — | ReceiveCoilName | sidecar | C | N |

### Sequence

| Field | Type | Unit | BIDS key | Source | Justify | Infer |
|---|---|---|---|---|---|---|
| pulse_sequence_type | enum | — | PulseSequenceType / ScanningSequence | sidecar | C/P | N |
| imaging_type | enum | — | ScanningSequence | sidecar | C | N |
| mr_acquisition_type | enum (2D/3D) | — | MRAcquisitionType | sidecar | C/P | N |
| partial_fourier | float | — | PartialFourier | sidecar | C | N |

### Timing & echo

| Field | Type | Unit | BIDS key | Source | Justify | Infer |
|---|---|---|---|---|---|---|
| repetition_time_s | float | s | RepetitionTime | sidecar | C/P | N |
| echo_time_ms | list[float] | ms | EchoTime (per `_echo-<n>`) | sidecar | C/P | N |
| n_echoes | int | — | (validates len) | none | P | N |
| flip_angle_deg | float | deg | FlipAngle | sidecar | C/P | N |
| acquisition_time_s | float | s | (no key) | derived | C | deriv |

`acquisition_time_s` derived from `[acquisition.n_volumes, acquisition.repetition_time_s]`.

### Geometry (NIfTI header — no sidecar key)

| Field | Type | Unit | BIDS key | Source | Justify | Infer |
|---|---|---|---|---|---|---|
| voxel_size_mm | tuple[float,float,float] | mm | — | derived | C/P | deriv |
| slice_gap_mm | float | mm | — | header | C | N |
| matrix_size | tuple[int, ...] | — | — | derived | C | deriv |
| fov_mm | tuple[float, ...] | mm | — | derived | C | deriv |
| n_slices | int | — | (len SliceTiming) | header | C | N |
| n_volumes | int | — | — | header | C | N |
| slice_orientation | enum | — | — | header | C | N |
| slice_angulation_deg | float | deg | — | header | C(cond) | N |
| brain_coverage | BrainCoverage | — | (no key) | none | C | N |

`voxel_size_mm` / `matrix_size` / `fov_mm` form a mutually derivable triple
(any one from the other two): `voxel = fov / matrix`, `fov = voxel × matrix`,
`matrix = fov / voxel`. All three are `inference_applicable=True` with a
`derived` basis whose `source_field_ids` cites the other two. In v0.2+ the
recovery layer prefers NIfTI-header values for `voxel_size_mm` / `matrix_size`
when the dataset is on disk.
`matrix_size` / `fov_mm` are length 2 (2D) or 3 (3D).

### Slice order & timing

| Field | Type | Unit | BIDS key | Source | Justify | Infer |
|---|---|---|---|---|---|---|
| slice_order_pattern | enum | — | (no key) | none | C | N |
| slice_timing_s | list[float] | s | SliceTiming | derived | C/P | deriv |
| slice_encoding_direction | enum (i/j/k±) | — | SliceEncodingDirection | sidecar | P | N |

`slice_timing_s` derived from `[acquisition.slice_order_pattern, acquisition.n_slices, acquisition.repetition_time_s]`; recovery from the dataset's `SliceTiming` sidecar is preferred when available (recovery layer, v0.2+).

### Acceleration & encoding

| Field | Type | Unit | BIDS key | Source | Justify | Infer |
|---|---|---|---|---|---|---|
| multiband_factor | int | — | MultibandAccelerationFactor | sidecar | C/P | conv (∅→1) |
| parallel_technique | enum | — | ParallelAcquisitionTechnique | sidecar | C | conv (∅→none) |
| parallel_factor | float | — | ParallelReductionFactorInPlane | sidecar | C/P | conv (∅→1.0) |
| phase_encoding_reported | str | — | (no key) | none | C | N |
| phase_encoding_direction | enum (i/j/k±) | — | PhaseEncodingDirection | sidecar | P | N |
| pe_reversal | bool | — | (fmap intent) | sidecar | C(cond) | N |
| effective_echo_spacing_s | float | s | EffectiveEchoSpacing | sidecar | P | N |
| total_readout_time_s | float | s | TotalReadoutTime | sidecar | P | N |

### Scanner-side preprocessing (already baked into the public data; matters for re-analysis)

| Field | Type | Unit | BIDS key | Source | Justify | Infer |
|---|---|---|---|---|---|---|
| prospective_motion_correction | bool | — | (no key) | none | C | N |
| signal_inhomogeneity_correction | bool | — | (no key) | none | C | N |
| distortion_correction_onscanner | bool | — | (no key) | none | C | N |
| recon_matrix_differs | bool | — | (no key) | none | C | N |
| shimming | str | — | (no key) | none | C | N |
| n_dummy_scanner | int | — | (no key) | none | C | N |

`n_nonsteadystate_discarded` (analysis-discarded dummies) belongs to the
**preprocessing** group, not here.

## Enumerations

- `pulse_sequence_type`: gradient_echo | spin_echo | other
- `imaging_type`: epi | spiral | other
- `mr_acquisition_type`: 2D | 3D
- `slice_orientation`: axial | sagittal | coronal | oblique
- `slice_order_pattern`: ascending | descending | interleaved_ascending | interleaved_descending | unknown
- `parallel_technique`: GRAPPA | SENSE | mSENSE | other | none
- `phase_encoding_direction`, `slice_encoding_direction`: i | i- | j | j- | k | k-

## Structs

- `BrainCoverage`: `whole_brain: bool`, `cerebellum_included: bool`,
  `brainstem_included: bool`, `z_extent_mm: float | None`

## Out of the acquisition group (do not lose; file elsewhere)

- Subject prep (mock scanning, special accommodations, experimenter personnel)
  -> participants/protocol group.
- Number of runs, run order, task/condition structure -> design group.
- `n_nonsteadystate_discarded`, slice-time correction -> preprocessing group.

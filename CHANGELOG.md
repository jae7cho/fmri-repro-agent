# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Vocabulary discipline.** Changes to spec `Literal` controlled vocabularies
> (or to KB schema enums) must be documented here, and marked **breaking** if a
> member is removed or renamed.

Nothing has been tagged yet, so all entries live under `[Unreleased]`.

## [Unreleased]

### Changed

- **(breaking, schema-vocab)** `IntensityNormalizationConvention`: renamed
  member `fsl_mode_10000` → `fsl_median_10000`. The old name was a misnomer —
  there is no FSL "mode-based 10000" convention; the real per-volume
  convention scales each volume so its **median** equals 10000. Renaming
  prevents the KB and Extractor from emitting a value that names a
  nonexistent normalization mode.

### Added

- `IntensityNormalizationConvention` extended with three new members verified
  against published practice (surfaced by the SfN batch extraction run; additive
  — no existing values invalidated):
  - `voxel_temporal_zscore` — per-voxel temporal z-score; no target magnitude (Liu 2013).
  - `global_median_1000` — scale so global median = 1000 (Mueller 2021).
  - `global_mode_1000` — scale so global mode = 1000 (Power 2014, Poldrack 2015;
    WashU/Petersen-lab convention).
  These use an operation-prefixed `<scope>_<statistic>_<target>` naming pattern,
  distinct from the tool-prefixed `fsl_*` / `spm_*` members (kept unchanged).
- Validator on `IntensityNormalization` enforcing `value` carries no concrete
  magnitude when `convention == "voxel_temporal_zscore"` (z-score is unitless).
- `IntensityNormalizationConvention` member `fsl_grand_mean_10000` — mean-based,
  single-factor 4D grand-mean scaling to 10000 (FSL `fslmaths -ing 10000` /
  FEAT default). Distinct from the per-volume `fsl_median_10000`.
- Per-member comments on `IntensityNormalizationConvention` documenting the
  mean / median / value distinction inline at the `Literal` definition.
- `inference_applicable=True` on the seven previously-demoted preprocessing
  fields: `spatial_normalization.{target_space, resolution_mm}`,
  `surface_projection.{target_surface, surface_registration}`,
  `temporal_filtering.effective_band_hz`,
  `intensity_normalization.{convention, value}`.
- `kb_client/base_pipeline.py` — `infer_base_pipeline_version` and
  `fill_dependent_defaults`: the Configurator-side wiring for
  `base_pipeline.version` inference and the option-(a) gate (params are only
  stacked on a *certain* version; a `date_inferred_version` leaves the fields
  `LeftMissing`).
- Vocab contract test (`tests/kb_client/test_vocab_contract.py`) — asserts the
  KB controlled vocabulary ⊆ spec `Literal` (one-way agent → KB), with an
  introspection-built `CONTRACTS` map and a derived-truth-set guard keeping
  `_STEP_CLASSES` in sync with the `PreprocStep` union.
- CCS gate tests (`tests/kb_client/test_ccs_base_pipeline.py`) — the option-(a)
  gate and version-certain fills exercised on a pipeline with no
  within-pipeline keying.

### Fixed

- Regenerated `schema/study_spec-0.1.0.schema.json` after the
  `IntensityNormalizationConvention` enum change.
- mypy (test surface): `_step_field` helpers now narrow the `getattr` result to
  `ProvenancedField` via `cast`; `_STEP_CLASSES` typed `tuple[type[BaseModel], ...]`
  so `.model_fields` resolves; added `types-PyYAML` dev dependency for the
  `yaml` import in the vocab contract test.

# Frozen specimens

Genuine artifacts from earlier schema versions, retained **unmigrated** so we can still
show what older AESPA output looked like — and so no current-schema file has to lie about
its own provenance by carrying a `0.1.0` label over `0.3.0`-shaped content.

These files are **intentionally not parseable by current code**. That is the point: the
version modules share one mutating `preprocessing` model, so `schema_version` is a
write-time label, not a promise that old data still parses. The supported reader for
archived artifacts is `fmri_repro.spec.migrations.parse_any_version` (migrate-then-parse).

## `preprocessing-v0.1.0.json`

A pre-0.2.0 `Preprocessing` artifact. Three properties mark it as genuine v0.1.0:

- no version stamp (`schema_version` was introduced in 0.3.0);
- `NuisanceRegression` has no `method` / `filtering_integrated` (added in 0.3.0);
- `intensity_normalization.convention` = `voxel_temporal_zscore`, which moved *out* of that
  enum into the `temporal_standardization` step in 0.2.0.

The last is the structural signature the migrator uses to place the document below the
0.2.0 migration floor. `parse_any_version()` **refuses it loudly** (`MigrationError`) rather
than guessing across the semantic 0.1.0→0.2.0 restructuring — see
`tests/spec/test_migrations.py`.

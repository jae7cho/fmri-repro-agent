# Design: `temporal_standardization` step — BUILD 1 (schema migration only)

**Scope of this doc:** Build 1 of a 2-build split. Build 1 is the **schema change +
member migration**, validated in isolation. Build 2 (separate doc, separate Claude
Code cycle) is the **extraction routing + prompt discrimination + dual-set tests**.
Build 1 does NOT touch the extraction prompt or the LLM path.

**Repo:** `fmri-repro-agent`. All line numbers are from the uploaded working tree
(`src/fmri_repro/spec/preprocessing.py`, 1137 lines).

---

## 0. What this build does, in one sentence

Move `voxel_temporal_zscore` OUT of the `IntensityNormalizationConvention` Literal
and INTO a new terminal `PreprocStep` kind `temporal_standardization`, so intensity
normalization becomes magnitude-scaling-only and z-scoring becomes an independently
representable preprocessing step (required for the PDF→replication-package goal:
a generated pipeline emits "z-score each voxel" as its own step, not as a mode of
intensity normalization).

**This is a MIGRATION, not an addition.** A member leaves one Literal and a new step
gains it as a method. That distinction drives the whole checklist below.

---

## 1. Decisions already locked (do NOT re-litigate)

- **One method, no scope field.** Method enum = `{voxel_temporal_zscore, other}`.
  Preprocessing operates per-run/session/4D-file, so per-voxel-across-time is the
  invariant; "per-segment vs whole-timeseries" (Cho vs Liu) is NOT a scope of this
  step — it's incidental to Cho's concatenation design. Liu and Cho are the SAME
  operation. No `scope` field. (Corpus-confirmed: standardization grep + Liu/Cho
  re-read.)
- **The step's object is the BOLD signal itself.** OUT: regressor standardization
  (Power), post-decomposition component standardization (Viduarre), connectivity
  transforms (Fisher r-to-z, ~14 papers), MVPA feature standardization (Cole/Greene),
  behavioral/phenotype z-scores, and QC metrics that lexically resemble it (DVARS,
  activation-map z). **This discrimination is BUILD 2's job (extraction prompt).**
  Build 1 only creates the schema container.
- **Terminal step**, mirrors `SpatialSmoothing` structurally (the last terminal step).

---

## 2. Pre-flight facts confirmed against the uploaded repo (do not re-verify, but know)

- `voxel_temporal_zscore` is currently a LIVE member of `IntensityNormalizationConvention`
  (preprocessing.py:964), WITH a dedicated validator `_zscore_has_no_magnitude`
  (preprocessing.py:999-1013) that forbids it carrying a `value`.
- **No example spec instantiates the z-score convention** (`examples/spec.json`,
  `examples/hcp_glasser_fieldmaps.json` — neither uses it). So the migration breaks
  no example instance. `scripts/make_example_spec.py` does not generate it.
- The string is baked into **~8 `$defs` blocks** in `schema/study_spec-0.1.0.schema.json`
  (Extracted/InferredDefault/AlternativeInference/ProvenancedField for the intensity
  convention Literal). These all change when the member moves → **schema regen required.**
- Consumers referencing it: `tests/spec/test_intensity_zscore.py` (the validator test —
  MOVES with the member), `tests/kb_client/test_vocab_contract.py:299` (pins
  `(intensity_normalization, convention)` — will need the new step's field added),
  the extractor prompt `extractor.py:182-195` (lists it as an intensity convention —
  **BUILD 2 changes this, NOT build 1**), and stale `results/batch_sfn_v2|v3/*.json`
  (historical run artifacts, gitignored, do NOT touch).

---

## 3. The exact edits (build 1)

### 3a. New step class — insert AFTER `SpatialSmoothing` (currently ends ~line 990),
so it's the last terminal step. Mirror `SpatialSmoothing` exactly.

```python
# 14. TemporalStandardization — per-voxel temporal standardization of the BOLD
# signal (z-score across time). Terminal conditioning before analysis. NOT
# intensity magnitude scaling (that's IntensityNormalization); NOT standardization
# of regressors/components/features/connectivity (those are analysis-stage). The
# object is the preprocessed BOLD signal itself. Liu 2013, Cho 2021.
TemporalStandardizationMethod = Literal["voxel_temporal_zscore", "other"]


TEMPORAL_STANDARDIZATION_FIELD_META: dict[str, FieldMeta] = {
    "method": FieldMeta(
        justification_axis="both",
        inference_applicable=False,   # do not infer a standardization method
        source="derived",
    ),
}


class TemporalStandardization(BaseModel):
    kind: Literal["temporal_standardization"] = "temporal_standardization"
    method: ProvenancedField[TemporalStandardizationMethod]

    cobidas_row: ClassVar[str] = "DIVERGENCE"   # see note 3f — no COBIDAS row exists
    STRUCTURAL_FIELDS: ClassVar[frozenset[str]] = frozenset({"kind"})
    ARM_REGISTRY: ClassVar[dict[str, FieldMeta]] = TEMPORAL_STANDARDIZATION_FIELD_META

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        _validate_step_invariants(self, TEMPORAL_STANDARDIZATION_FIELD_META)
        return self
```

Design notes on the class:
- **Single field `method`.** No `scope`, no `value` (z-score has no target magnitude —
  that was the whole point of `_zscore_has_no_magnitude`; by making this a step with
  no `value` field at all, the constraint becomes structural rather than a validator.
  The impossibility of a magnitude is now expressed by the ABSENCE of a value field,
  which is cleaner than a validator forbidding one.)
- `inference_applicable=False` on `method`: we do not want the configurator inferring
  "they probably z-scored" from a pipeline default. If a paper doesn't state it, it's
  LEFT_MISSING, not inferred. (Matches the conservative stance on other operation
  fields.)

### 3b. Remove `voxel_temporal_zscore` from `IntensityNormalizationConvention`
(preprocessing.py:952-967). Delete the member line (964) AND its comment block
(the `# New in v0.1.1 ... No target magnitude (Liu 2013).` lines, ~961-963). The
Literal becomes:

```python
IntensityNormalizationConvention = Literal[
    "spm_grand_mean_100",
    "fsl_grand_mean_10000",
    "fsl_median_10000",
    "global_median_1000",
    "global_mode_1000",
    "other",
]
```

### 3c. DELETE the `_zscore_has_no_magnitude` validator (preprocessing.py:999-1013)
entirely, AND delete the `_resolved_field_value` helper (preprocessing.py:973-980).
CONFIRMED: `_resolved_field_value` is used ONLY inside `_zscore_has_no_magnitude`
(lines 1005-1006) and nowhere else in the file — so once the validator is gone the
helper is dead code. Delete both. The validator's job (z-score carries no magnitude)
is now enforced structurally by `TemporalStandardization` having no `value` field.

### 3d. Register the bijection guard — add to the block at preprocessing.py:995-1010,
after the `SpatialSmoothing` line (1010):

```python
_check_step_bijection(TemporalStandardization, TEMPORAL_STANDARDIZATION_FIELD_META)
```

### 3e. Add to the `PreprocStep` union (preprocessing.py:1016-1033) — append after
`SpatialSmoothing`:

```python
PreprocStep = Annotated[
    NonsteadystateRemoval
    | ...
    | SpatialSmoothing
    | TemporalStandardization,
    Field(discriminator="kind"),
]
```

### 3f. COBIDAS row = `"DIVERGENCE"` (CONFIRMED, not a guess). There is no COBIDAS
D.3 row for temporal signal standardization. `"DIVERGENCE"` is the established
sentinel in this file — used by `SurfaceProjection` (line 733) and `TemporalFiltering`
(line 873), both "DIVERGENCE (added as a discrete step)", documented at line 556.
`TemporalStandardization` is exactly analogous. Use:
```python
    cobidas_row: ClassVar[str] = "DIVERGENCE"
```
Match the inline comment style of the other two: `# 14. TemporalStandardization —
DIVERGENCE (added as a discrete step)`.

---

## 4. Schema regeneration + versioning (REQUIRED — the biggest ripple)

**VERSION POLICY: new minor `v0_2_0.py` (DECIDED). This build is a complete 0.2.0
release with ONE focused change (the temporal_standardization step). 0.1.0 is frozen.**

Rationale locked with the human: the repo's convention is "one module per minor version"
(`v0_1_0.py` header: *a future v0.2.0 will live in a sibling `v0_2_0.py`*). Adding a
`PreprocStep` kind + narrowing a Literal is a minor change, not a patch — so it gets its
own minor module. The queued `(statistic,value)` intensity decomposition and
`EXCLUDED_BY_PAPER` state are LATER minors (0.3.0+), NOT part of this release.

**This is the one genuinely non-mechanical part of build 1. Follow the repo's existing
minor-module pattern; do NOT improvise it.**

### 4a. Understand the existing versioned-module structure FIRST (read-only).
- `src/fmri_repro/spec/v0_1_0.py` is the versioned root: it assembles `StudySpec`,
  holds `schema_version: Literal["0.1.0"] = "0.1.0"` (line 751), and imports
  version-stable core types from `provenance.py` / `refs.py`. Preprocessing step
  classes live in `preprocessing.py` (imported by `v0_1_0.py`).
- Read `v0_1_0.py` fully to see HOW it composes `StudySpec` from the group modules
  (acquisition arms, `preprocessing`, etc.) and what exactly the version bump touches.
- `scripts/export_schema.py` imports `from fmri_repro.spec.v0_1_0 import StudySpec` and
  writes a HARDCODED filename `study_spec-0.1.0.schema.json` (line 15).

### 4b. Create `v0_2_0.py` — the ONE remaining design decision (STOP and report).
`v0_1_0.py` is 754 lines assembling `StudySpec` → `ReplicationSpec` → acquisition arms
+ preprocessing. In 0.2.0, ONLY the preprocessing union changes (via the shared
`preprocessing.py`, §3); `StudySpec`, `ReplicationSpec`, the acquisition arms, and their
validators are IDENTICAL to 0.1.0.

**Do NOT blindly duplicate 754 lines to change one version string.** That establishes a
copy-paste-the-whole-root pattern that will rot. Report which approach the code supports
and RECOMMEND, but get the human's nod before implementing (this sets the pattern for
all future minors):

- **(A) Import-and-re-export.** `v0_2_0.py` imports the unchanged assembly from
  `v0_1_0.py` (or from wherever the shared pieces live) and re-declares ONLY what
  differs — the `StudySpec` subclass with `schema_version: Literal["0.2.0"] = "0.2.0"`.
  If `ReplicationSpec`/arms are unchanged and preprocessing is already shared via
  `preprocessing.py`, this may be a very small module. PROBLEM to check: `StudySpec` in
  `v0_1_0.py` hardcodes `schema_version="0.1.0"` — subclassing to override one Literal
  field is clean IF nothing else in the assembly pins 0.1.0.
- **(B) Extract shared core, then two thin version roots.** If `v0_1_0.py` mixes
  version-stable assembly with the version string such that (A) is awkward, refactor the
  shared assembly into a version-neutral module both `v0_1_0.py` and `v0_2_0.py` import,
  each supplying only its `schema_version`. Cleaner long-term, more work now.

**Recommendation to present:** (A) if `v0_1_0.py`'s structure allows a clean `StudySpec`
subclass/re-export; (B) only if (A) forces duplicating validators. Given "one focused
change, no audience," lean (A) — minimal new code. REPORT `v0_1_0.py`'s structure
(is `StudySpec` cleanly subclassable? do `ReplicationSpec`/arms reference the version?)
and the chosen approach BEFORE writing `v0_2_0.py`.

### 4c. **Frozen-0.1.0 handling — RESOLVED from repo structure.**
CONFIRMED by reading the module layout: `preprocessing.py`, `provenance.py`, `refs.py`
are **shared, UNVERSIONED group modules**; `v0_1_0.py` is the **versioned ROOT** that
imports them (line 43: `from fmri_repro.spec.preprocessing import Preprocessing`) and
assembles `StudySpec`/`ReplicationSpec`. So the repo's real pattern is: **one versioned
ROOT module per minor; the group modules evolve in place and are shared.**

Therefore:
- **`preprocessing.py` is edited in place** (§3 changes land here). It is shared and
  unversioned by design.
- **`v0_1_0.py` stays frozen** with `schema_version = "0.1.0"` — you simply STOP
  exporting from it. It is not deleted, not edited.
- **`study_spec-0.1.0.schema.json` is the frozen historical artifact ON DISK.** Do NOT
  regenerate it. "Frozen" means the FILE is frozen, which is the correct meaning given
  the group modules are shared. (Yes, `v0_1_0.py` would emit slightly different schema
  if re-run after §3 edits `preprocessing.py` — but you never re-run it. This latent
  inconsistency is harmless and is the intended consequence of shared group modules.)
- **`v0_2_0.py` is the new versioned root** with `schema_version = "0.2.0"`, importing
  the now-evolved `preprocessing.py`. The generator exports from `v0_2_0.py`.

This is NOT a stop condition — the structure decided it. The §3 in-place edits to
`preprocessing.py` are correct as written.

### 4d. Once 4c is decided: bump `schema_version` to `"0.2.0"` in the 0.2.0 root module,
and make `export_schema.py` write `study_spec-0.2.0.schema.json`. The generator
hardcodes the filename (line 15) — parametrize it off `StudySpec`'s `schema_version`
Literal (read it from the model) rather than hardcoding `0.2.0`, so future bumps don't
need a generator edit. If the generator is meant to export a SPECIFIC version, it may
need to import from `v0_2_0` instead of `v0_1_0` — report how you wire it.

### 4e. Regenerate and report the 0.1.0→0.2.0 schema diff at summary level: `$defs`
added (new `TemporalStandardization` + method Literal + union member), `$defs` changed
(intensity convention Literal variants — zscore removed). Confirm NO unrelated `$defs`
changed. LEAVE `study_spec-0.1.0.schema.json` untouched on disk.

---

## 5. Test changes (build 1)

### 5a. MOVE + REWRITE `tests/spec/test_intensity_zscore.py`.
The three current tests assert z-score-as-intensity-convention semantics
(`test_zscore_with_no_magnitude_is_accepted`, `test_zscore_with_concrete_value_is_rejected`,
`test_magnitude_conventions_still_accept_a_value`). After migration:
- `test_magnitude_conventions_still_accept_a_value` STAYS (tests `global_median_1000`
  with a value — still valid on `IntensityNormalization`). Keep it (maybe rename file).
- The two z-score-specific tests are OBSOLETE as written (the convention no longer
  exists on `IntensityNormalization`). REWRITE as `tests/spec/test_temporal_standardization.py`:
  - `test_temporal_standardization_accepts_voxel_temporal_zscore` — build a
    `TemporalStandardization(method=extracted("method", str, "voxel_temporal_zscore"))`,
    assert it validates and `.method.extraction.value == "voxel_temporal_zscore"`.
  - `test_temporal_standardization_has_no_value_field` — assert `TemporalStandardization`
    has no `value` attribute (the structural replacement for the old no-magnitude
    validator): `assert "value" not in TemporalStandardization.model_fields`.
  - `test_intensity_no_longer_accepts_zscore` — assert constructing an
    `IntensityNormalization` with `convention` extracted-value `"voxel_temporal_zscore"`
    raises ValidationError (it's no longer a valid Literal member).
  - `test_temporal_standardization_method_not_inferrable` — assert an INFERRED_DEFAULT
    on `method` is rejected (mirrors the `inference_applicable=False` invariant;
    see `test_preprocessing.py:705` pattern `test_inferred_default_on_non_flagged_field_rejected`).

### 5b. `tests/kb_client/test_vocab_contract.py:299` — it pins
`(intensity_normalization, convention)` as a vocab-carrying field. ADD
`(temporal_standardization, method)` to that list so the new step's method Literal is
covered by the contract. Read the test to see the exact structure of that list first;
it likely enumerates (step_kind, field) pairs whose Literals must round-trip. This
test is DESIGNED to catch vocab drift — it SHOULD require an update, and that update
is adding the new step's field, not removing the intensity one (intensity still has
`convention`, just with fewer members).

### 5c. `tests/spec/test_preprocessing.py` — the `_intensity_normalization()` builder
(line 318) constructs an IntensityNormalization. Confirm it does NOT use
`voxel_temporal_zscore` (grep it). If it uses a magnitude convention, no change. Add a
`_temporal_standardization()` builder mirroring the other step builders, and a test
that a `TemporalStandardization` step is accepted in a `Preprocessing.steps` list
(mirrors existing single-step acceptance tests). Also confirm the step-uniqueness
validator (line ~1107) treats it as a distinct kind (it will — different `kind`
string).

### 5d. Full suite must pass. Run:
- `tests/spec/` (preprocessing + the new temporal_standardization + the surviving
  intensity test)
- `tests/kb_client/` (vocab_contract especially)
- the root schema suite
- Report pass/fail counts. Any test that flips and is NOT in the expected-change set
  above → STOP and report, do not "fix" it.

---

## 6. Explicit STOP-and-report conditions (do not silently proceed)

**The ONE real decision that must stop for the human:**
1. **`v0_2_0.py` construction strategy (§4b): import-and-re-export (A) vs. extract-shared-core
   (B).** This sets the pattern for every future minor. Report `v0_1_0.py`'s structure
   (is `StudySpec` cleanly subclassable to override `schema_version`? do `ReplicationSpec`
   / acquisition arms pin the version anywhere?), recommend (A) unless it forces validator
   duplication, and get the nod BEFORE writing `v0_2_0.py`.

**Resolved (no longer stops — confirmed against the repo, listed so you know they were checked):**
- Frozen-0.1.0 handling (§4c): `preprocessing.py` is shared/unversioned, `v0_1_0.py` is the
  versioned root → edit `preprocessing.py` in place, freeze `v0_1_0.py` + the 0.1.0 schema
  FILE, export 0.2.0 from `v0_2_0.py`. Structure decided it.
- `_resolved_field_value` is used ONLY by the deleted validator → delete both (§3c).
- `"DIVERGENCE"` IS the established cobidas_row sentinel → use it (§3f).
- Schema generator IS `scripts/export_schema.py`, filename hardcoded (line 15) →
  parametrize off `schema_version`, import from `v0_2_0` (§4d).
- NO example spec instantiates `voxel_temporal_zscore` → migration breaks no instance.
- Version string lives at `v0_1_0.py:751` (`schema_version: Literal["0.1.0"]`) → the new
  root sets `"0.2.0"`; do NOT scatter-replace `0.1.0` (module NAME `v0_1_0.py` stays; the
  `v0_1_0.py` DOCSTRING "future v0.2.0 will live in v0_2_0.py" stays as-is).

**Still stop if these arise (they shouldn't, but guard):**
2. A test outside the section-5 expected-change set flips → STOP, do not "fix" it.
3. `scripts/export_schema.py` errors or produces a diff touching `$defs` UNRELATED to the
   intensity convention or the new step → STOP and report the diff before writing it.
4. `StudySpec` cannot be cleanly subclassed for (A) AND extracting shared core for (B)
   would touch acquisition-arm logic → STOP; that's larger than build 1.

---

## 7. What build 1 explicitly does NOT do (deferred to build 2)

- Does NOT change the extraction prompt (`extractor.py:182-195` still lists
  `voxel_temporal_zscore` as an intensity convention — build 2 removes it from there
  and adds the temporal_standardization extraction instruction).
- Does NOT add the signal-vs-derived-product discrimination.
- Does NOT add the Liu/Cho positive + Fisher-Z/Power/Viduarre/Cole negative dual-set
  extraction tests.
- Does NOT run any Bedrock/live extraction.

After build 1: the SCHEMA can represent temporal_standardization correctly and
intensity is magnitude-only, all validated by unit tests against constructed objects.
The EXTRACTOR still routes z-score to intensity (now-invalid) — which is fine because
build 2 fixes routing, and until then Liu's z-score simply lands as MISSING on
intensity (the honest interim state, since the convention member is gone). No live run
happens between build 1 and build 2.

---

## 8. Interaction with queued schema work (context, not build-1 scope)

Two other changes touch this same surface and should be sequenced deliberately AFTER
build 2:
- **`(statistic, value)` intensity decomposition** — collapses the value-in-name
  Literals (`fsl_grand_mean_10000` etc.) to `(statistic, value)`. Build 1 makes
  intensity magnitude-only, which is a prerequisite that HELPS this later work.
- **`EXCLUDED_BY_PAPER` reported-absence state** (provenance.py) — backlogged; the
  precision-imaging native-space paper is the exemplar. Separate provenance-core change.

Do NOT fold either into build 1 or build 2.

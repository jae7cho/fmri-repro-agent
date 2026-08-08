# Design: `temporal_standardization` step — BUILD 2 (extraction routing + prompt)

**Prerequisite:** BUILD 1 must be landed and green (schema has `TemporalStandardization`
with `method: ProvenancedField[TemporalStandardizationMethod]`,
`TemporalStandardizationMethod = Literal["voxel_temporal_zscore", "other"]`, and
`voxel_temporal_zscore` REMOVED from `IntensityNormalizationConvention`). Build 2 wires
the extractor to populate the new step.

**Repo:** `fmri-repro-agent`, extractor at
`extractor_mvp/src/extractor_mvp/extractor.py`. Line numbers are from the uploaded tree
and **MUST be re-verified against build 1's output** — build 1 edits `preprocessing.py`
(shared) and may shift nothing in `extractor.py`, but the schema types build 2 imports
(`TemporalStandardizationMethod`) only exist after build 1.

---

## ⚠️ 0. Build-1-dependency checklist — VERIFY before running build 2

Claude Code MUST confirm these against the actual build-1 result and STOP if any differ:
1. `from fmri_repro.spec.preprocessing import TemporalStandardization, TemporalStandardizationMethod`
   imports cleanly.
2. `IntensityNormalizationConvention` no longer contains `voxel_temporal_zscore`
   (build 1 §3b removed it).
3. `TemporalStandardization` has a single provenanced field `method` and NO `value` field.
4. The schema version root exporting is `v0_2_0.py` (build 1 §4). Build 2 does not touch
   versioning.

If the extractor currently still lists `voxel_temporal_zscore` in its prompt as an
intensity convention (`extractor.py` ~line 188) — it WILL, build 1 left the prompt
alone — that's the exact thing build 2 fixes. Expected, not an error.

---

## 1. What build 2 does, in one sentence

Teach the extractor to (a) STOP routing z-score into the intensity convention, and
(b) populate a new `temporal_standardization` step ONLY when the paper standardizes the
**preprocessed BOLD signal itself** (Liu, Cho) — NOT when it standardizes regressors,
post-decomposition components, connectivity values, features, or phenotypes, and NOT on
QC-metric / statistical-map lexical lookalikes (DVARS, activation-map z, Fisher r-to-z).

**The object-discrimination is an LLM semantic judgment in the prompt. The method stays
deterministically typed (one Literal). This preserves the two-stage firewall: LLM judges
WHAT is being standardized; the schema validates the typed method.**

---

## 2. Locked decisions carried from the design conversation (do NOT re-litigate)

- **Positive set (route INTO the step):** Liu 2013 ("for each voxel, the fMRI signal was
  temporally normalized by subtracting its mean and then dividing by its temporal SD");
  Cho 2021 ("z-scoring the segments" — SAME per-voxel-temporal operation, segmentation is
  incidental to concatenation). Both → `method = voxel_temporal_zscore`.
- **Negative set (must NOT route into the step) — from the corpus grep, verbatim:**
  - Fisher r-to-z of connectivity (~14 papers: Vanderwal, Gordon, Marek, Yang, Weber,
    Chen, Cole, Greene) — "correlations were Fisher z-transformed"
  - Regressor standardization (Power 2014: "regressors were standardized (zero-mean,
    unit variance)")
  - Post-decomposition component standardization (Viduarre 2017: "ICA-component time
    series standardized to mean 0 SD 1") — OUT per the lit-search boundary: components
    are analysis products, not the signal.
  - MVPA feature standardization (Cole 2013, Greene 2022: "across-feature normalization")
  - Behavioral/phenotype z-scores (DeRosa WBSI/PSWQ/RRS; Weber IQ)
  - QC/statistical lexical lookalikes (DVARS "standardized"; activation-map z-scores)
- **The boundary, stated as one rule for the prompt:** the object of standardization must
  be the BOLD signal itself. Anything DERIVED from it (components, regressors,
  correlations, features) or any METRIC describing it (DVARS, activation z) is OUT. The
  edge case that is IN: standardizing the signal *before* feeding a decomposition
  (stICA-style) — because at that point it is still the signal, not yet a component. The
  edge case that is OUT: standardizing components *after* decomposition (Viduarre).
- **No scope field** — per-run/session/4D-file is the invariant, not a parameter.

---

## 3. The exact edits (build 2)

### 3a. Add the LLM output field — `PreprocessingExtraction` (extractor.py:70-92).
Add a field for the new step's method, defaulted to `"missing"` so pre-existing fixtures
still construct (mirror how `base_pipeline_name` was added, lines 88-92):

```python
    temporal_standardization_method: FieldExtractionResult = Field(
        default_factory=lambda: FieldExtractionResult(status="missing")
    )  # voxel_temporal_zscore when the BOLD SIGNAL is z-scored (Liu/Cho); missing otherwise
```

### 3b. Rewrite the `intensity_convention` prompt block (extractor.py ~186-190).
REMOVE `voxel_temporal_zscore` from the canonical values list (build 1 removed it from
the Literal; the prompt must match or the LLM emits an invalid value). New canonical list:
`spm_grand_mean_100, fsl_grand_mean_10000, fsl_median_10000, global_median_1000,
global_mode_1000, other`. Update the block to be explicitly MAGNITUDE-ONLY:

```
intensity_convention: The global/grand-mean intensity MAGNITUDE-scaling convention
applied to the 4D BOLD series (scaling the signal so a summary statistic hits a target
number). Canonical values: spm_grand_mean_100, fsl_grand_mean_10000, fsl_median_10000,
global_median_1000, global_mode_1000, other.
  extracted: "scaled each run to a grand mean of 10000" -> value=fsl_grand_mean_10000
  missing: no magnitude scaling of the time series is described.
  NOT this field: per-voxel z-scoring / standardization to unit variance -> that is
    temporal_standardization_method, NOT an intensity convention. Fisher z-transform of
    correlations, DVARS, and statistical-map z-scores are NOT intensity conventions.
```

Also update the `intensity_value` block (~192): remove the "z-score conventions" mention
(z-score is no longer an intensity convention), keep it as the magnitude number.

### 3c. Add the `temporal_standardization` prompt block. Insert a NEW field description,
adjacent to the intensity block. **This is the load-bearing discrimination — write it
against the verbatim corpus phrasings.**

```
temporal_standardization_method: Whether the PREPROCESSED BOLD SIGNAL ITSELF was
temporally standardized per voxel (each voxel's time series transformed to zero mean and
unit variance across time, i.e. z-scored over time) as a preprocessing step before
analysis. Canonical values: voxel_temporal_zscore, other.
  extracted: "for each voxel, the signal was temporally normalized by subtracting its
    mean and dividing by its temporal standard deviation" -> value=voxel_temporal_zscore
  extracted: "the BOLD time series were z-scored" -> value=voxel_temporal_zscore
  missing: no per-voxel temporal standardization of the signal is described.

  CRITICAL — this field is ONLY for standardization of the BOLD SIGNAL ITSELF. It is
  "missing" (do NOT populate it) for ALL of the following, even though they use words
  like "standardized", "z-score", "unit variance", "zero mean":
    - Fisher r-to-z transform of CORRELATION / CONNECTIVITY values
      ("correlations were Fisher z-transformed") -> NOT this field.
    - Standardization of NUISANCE REGRESSORS / the design matrix
      ("regressors were standardized to zero-mean unit variance") -> NOT this field.
    - Standardization of ICA / PCA COMPONENTS after decomposition
      ("ICA component time series standardized to mean 0 SD 1") -> NOT this field
      (components are analysis products, not the signal).
    - Standardization of MVPA / classification FEATURES
      ("across-feature normalization") -> NOT this field.
    - Standardization of BEHAVIORAL / PHENOTYPE scores (IQ, symptom scales) -> NOT this
      field.
    - DVARS or other QC METRICS that are "standardized" -> NOT this field.
    - Z-scores in STATISTICAL MAPS / activation tables -> NOT this field.
  Ask: is the paper transforming the fMRI SIGNAL that carries forward into analysis, or
  is it transforming something DERIVED from the signal (a correlation, a regressor, a
  component, a feature, a metric)? Only the former is voxel_temporal_zscore.
```

### 3d. Add the `_FIELD_SPECS` entry (extractor.py:265-296). Append:

```python
    (
        "temporal_standardization_method",
        "method",
        "temporal_standardization.method",
        TemporalStandardizationMethod,
        TemporalStandardizationMethod,
    ),
```
This routes the LLM field through the same `_process_field` path (span resolution +
`resolve_to_literal`). **NOTE:** `temporal_standardization_method` takes NO
`value_context` (there is no sibling number — unlike intensity convention). Confirm the
loop at line ~635 only passes `value_context` for the intensity `convention` field and
leaves this one `None` (it should — the condition is `if field_id == "convention"`; the
new field's `field_id` is `"method"`, which would ALSO match that condition — **BUG RISK,
see 3f**).

### 3e. Wire the step into assembly (extractor.py:548-592). The assembly hardcodes
`steps=[spatial, surface, intensity]`. Add the new step:

```python
    temporal_standardization = TemporalStandardization(
        method=pf["temporal_standardization_method"],
    )
    ...
    return Preprocessing(
        ...
        steps=[spatial, surface, intensity, temporal_standardization],
    )
```
Import `TemporalStandardization` at the top of `extractor.py`.

### 3f. The `value_context` guard — CONFIRMED SAFE as specced, with a fragility note.
Verified against the real loop (extractor.py:634):
```python
value_context = intensity_value_ctx if field_id == "convention" else None
```
`field_id` is the bare step-attr (2nd `_FIELD_SPECS` element). The intensity convention's
is `"convention"`; the new `temporal_standardization_method`'s is `"method"`. Since
`"method" != "convention"`, the new field correctly receives `value_context=None`. **No
collision — the intensity number is NOT applied to temporal_standardization.** Safe.

**Latent fragility to be aware of (do NOT fix in build 2 — just don't make it worse):**
the guard matches on the bare attr name, which is not globally unique (several step
classes have a field named `method`). It's safe ONLY because exactly one `_FIELD_SPECS`
entry has `field_id == "convention"`. Do not add a second `_FIELD_SPECS` entry with
`field_id="convention"`, and do not broaden the guard to `field_id in (...)`. The new
entry uses `"method"`, which is fine. If a future change needs per-field value_context,
that guard should key on the LLM attr name (1st element, globally unique) not the bare
step-attr — but that's a separate refactor, not build 2.

---

## 4. The dual-set test suite (build 2's core validation — the LOAD-BEARING part)

Because build 2 relies on LLM semantic judgment for the object boundary (the one
discrimination the deterministic resolver provably cannot make — identical words,
different object), the negative set is the external check on that judgment (Huang et al.
self-correction limits: the LLM's call is not self-verifying; the test set verifies it).

**These are OFFLINE tests of the routing + resolver, NOT live Bedrock tests.** They test
that GIVEN an LLM extraction (simulated FieldExtractionResult), the field routes and
resolves correctly. A SEPARATE live-validation pass (build 3 / the delta batch) tests
whether the LLM actually makes the right call on real papers — that needs Bedrock and is
out of scope here.

### 4a. Resolver-level tests (no LLM) — `tests/test_synonym_resolver.py` or a new
`tests/test_temporal_standardization_routing.py`:
- `resolve_to_literal("voxel-wise temporal z-score", TS_METHOD_SYNONYMS, ...)` →
  resolved `voxel_temporal_zscore`. (Requires build 2 to add a synonym entry for the
  method — see 4c.)
- Confirm the method resolves from real phrasings: "z-scored over time", "temporal
  standardization per voxel".

### 4b. Routing/assembly tests (no LLM) — construct a `PreprocessingExtraction` with
`temporal_standardization_method` extracted = "voxel_temporal_zscore" and assert the
assembled `Preprocessing.steps` contains a `TemporalStandardization` with that method.
And the negative: construct one where it's "missing" and assert the step is present but
its method is MissingFromPaper (the step is always emitted, like the others; whether it
carries a value is what varies).

### 4c. Synonym entries for the METHOD (if the resolver is used for it). If
`temporal_standardization_method` routes through `resolve_to_literal`, it needs a synonym
table (like the intensity one). Add `TS_METHOD_SYNONYMS` mapping phrasings →
`voxel_temporal_zscore`:
  - "voxel temporal zscore", "per-voxel temporal z-score", "temporal z-score",
    "z-scored over time", "temporally normalized ... temporal standard deviation"
  Keep it TIGHT — the OBJECT discrimination is the LLM's job (prompt), the resolver only
  maps an already-signal-scoped phrase to the method Literal. Do NOT try to encode
  signal-vs-regressor in the synonym table (it can't — identical words).

### 4d. The negative-set is validated at the PROMPT level, which is not unit-testable
offline without an LLM. Document the negative set (§2) as the build-3 live-validation
spec: when the delta batch runs, Power/Gordon/Cole/Viduarre/DVARS papers must show
`temporal_standardization.method = MISSING` and must NOT show a spurious
`voxel_temporal_zscore`. Flag this as the acceptance criterion for build 3, NOT build 2.

### 4e. Full offline suite green. Run `-m "not live"`. Report counts.

---

## 5. STOP-and-report conditions

1. Build-1 types don't import (§0) → STOP, build 1 isn't landed.
2. The `value_context` guard at line 634 is NOT `field_id == "convention"` (i.e. build 1
   or some other change altered it to `field_id in (...)` or keyed it differently) → STOP;
   the safety argument in §3f depends on the guard being exactly `== "convention"`. If it
   changed, re-verify the new `"method"` field doesn't receive the intensity value_context.
3. Any existing test flips that isn't the intensity-prompt change → STOP.
4. `resolve_to_literal` signature or the `_process_field` path differs from what §3d/3f
   assume (re-verify against build 1's actual extractor state) → STOP and report the
   real signatures.

---

## 6. What build 2 does NOT do

- No Bedrock / live run. All tests are offline (simulated extractions).
- Does NOT validate the LLM's actual object-discrimination on real papers — that's the
  build-3 delta batch (Liu/Cho must populate; Power/Gordon/Cole/Viduarre/DVARS must not).
- Does NOT touch versioning (build 1 did that).
- Does NOT do the `(statistic, value)` intensity decomposition or `EXCLUDED_BY_PAPER`
  (later minors).

---

## 7. Sequencing after build 2

Build 3 = the live delta batch on 4.5 (`EXTRACTOR_MODEL` per-run override to match v5):
Liu + Cho (positive — must populate `temporal_standardization`) + Marek (false-fire
regression) + one version-pinned paper (KB) + Chen (machinery). The negative set
(Power/Gordon/Cole/Viduarre/DVARS) is checked for ABSENCE of spurious z-score. THEN
full-20 regenerated on the 0.2.0 schema. This is where the LLM's object-discrimination
is actually validated — the acceptance criterion is §4d.

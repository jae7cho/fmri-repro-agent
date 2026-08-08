# DESIGN — ReplicationSpec v0.3.0: anatomical-target steps + tool/method separation

*Grounded in the live tree. Catalog: `docs/spec/preprocessing_catalog_v0.1.0.md` (authoritative). Code: `src/fmri_repro/spec/preprocessing.py`, `v0_2_0.py`. Supersedes the earlier draft of this file.*

---

## 0. Organizing principle (already the schema's design, now made complete)

The catalog's legend: **"Canonical = method-independent param"**, and `method` is the **tool/implementation** discriminator (slice-timing: *"Method: software/tool (FSL slicetimer / SPM / AFNI 3dTshift)"*).

So each step captures two orthogonal facts:
- **`method`** — *what software did it* (`mcflirt`, `spm_realign`, `afni_3dvolreg`, `ants`, …)
- **Canonical fields** — *what operation was performed*, tool-independent (`cost_function`, `warp`, `transform`, …)

This is why OConnor's *"boundary-based registration [65]"* maps cleanly today: `coregistration.cost_function = boundary_based` (EXTRACTED), `coregistration.method` = MISSING (tool unstated). Algorithm reported, implementation not — an asymmetry the four-state model captures exactly.

**Justification for keeping the tool as a first-class field:** Bowring, Maumet & Nichols (2019, *HBM*; 2021 erratum) show analysis-package choice materially changes results. The implementation is a replication variable, not metadata.

v0.3.0 completes this pattern in the three places it is currently broken or absent.

---

## 1. Locked decisions

### D1 — Two new sibling step kinds: `brain_extraction`, `segmentation`
Catalog-sanctioned (lines 161–164, *"Anatomical-target (admit only if a functional pipeline depends on them)"*, both COBIDAS D.3 **mandatory**). Admission test passes: brain extraction feeds `coregistration`/`spatial_normalization`; segmentation produces the WM/CSF masks that `NuisanceRegression.tissue_regressors` and `CompCor` already consume — the schema modeled the consumers and omitted the producer.

```python
BrainExtractionMethod = Literal["bet","afni_3dskullstrip","freesurfer_recon_all","ants","synthstrip","other"]
SegmentationMethod    = Literal["fsl_fast","spm_segment","freesurfer_recon_all","ants_atropos","other"]
TissueClass           = Literal["gray_matter","white_matter","csf"]

class BrainExtraction:  # kind="brain_extraction", cobidas_row="brain_extraction"
    method: ProvenancedField[BrainExtractionMethod]        # TOOL
    manual_edits: ProvenancedField[bool]                   # canonical

class Segmentation:     # kind="segmentation", cobidas_row="segmentation"
    method: ProvenancedField[SegmentationMethod]           # TOOL
    tissue_classes: ProvenancedField[list[TissueClass]]    # canonical
```

`parameters` (catalog lists it for brain_extraction) is **deliberately omitted**: no canonical parameter is shared across BET / 3dSkullstrip / recon-all / SynthStrip (BET's `-f` has no analogue). Free-text would be unqueryable. Admit later only if a genuine cross-tool canonical param is identified.

`TissueClass` uses `csf`, deliberately distinct from `TissueRegressor.ventricles` (a regressor *mask*, narrower than the CSF tissue class).

`synthstrip` included (Hoopes et al. 2022, *NeuroImage* — **verify locator**); otherwise it silently falls to `other`.

### D2 — Schema version bump to v0.3.0
`preprocessing.py` is shared across version modules; the v0.2.0 docstring establishes that a step-kind addition *is* the version change, with the version module re-declaring `StudySpec` only to pin `schema_version`. Mirror exactly: new `v0_3_0.py`; `v0_1_0.py` / `v0_2_0.py` stay frozen. `fmri_repro` was contract-frozen for the emitter work; this is a deliberate, versioned unfreeze.

### D3 — Add `"ants"` to `SpatialNormalizationMethod`
Current literals (`fnirt`, `ants_syn`, `spm_normalise`, `dartel`) are the one place tool and algorithm are conflated: both sibling enums (`CoregistrationMethod`, `MotionCorrectionMethod`) already carry a plain `ants`. Without it, OConnor's *"non-rigid registration … using ANTs"* cannot record the tool without asserting SyN — an inference, not an extraction. With it: `method = ants` (tool, EXTRACTED), `warp = nonlinear` (canonical, EXTRACTED), algorithm honestly unstated. Additive Literal member; existing data still validates.

### D4 — `NuisanceRegression.method` (new; the tool gap)
`NuisanceRegression` is the only substantive step with **no tool field at all** (`motion_expansion`, `tissue_regressors`, `physio_regressors`, `physio_n_regressors`, `detrend`). Named `method`, not `software`, per the schema-wide convention that `method` = implementation.

```python
NuisanceRegressionMethod = Literal[
    "afni_3dtproject","afni_3dbandpass","afni_3ddeconvolve",
    "fsl_regfilt","spm","nilearn","custom","other",
]
```
`custom` is distinct from `other` on purpose: *"in-house MATLAB scripts"* is information (an unnamed bespoke implementation), not an unlisted named tool. **Verify each literal against the real program names before encoding.**

### D5 — `NuisanceRegression.filtering_integrated: ProvenancedField[bool]` (canonical)
Whether temporal bandpass filtering was applied **simultaneously within the same regression model** (one step) versus **sequentially** as a separate operation (multi-step).

Scientific grounding: Hallquist, Hwang & Luna (2013, *NeuroImage* 82:208–225) showed sequential bandpass-then-regression reintroduces nuisance variance; simultaneous regression+filtering (AFNI `3dTproject`) was the response. Many older studies filtered and regressed separately — so this is a real, high-impact, frequently-varying reporting dimension that must be **visible to users**, not inferred from a tool name.

**Canonical, not tool-derived:** a paper can describe simultaneous regression+filtering without naming `3dTproject`, and can name `3dTproject` while describing a separate bandpass. Tool and integration are orthogonal; folding integration into the tool literal would bury it.

Interaction with the `temporal_filtering` step: band edges stay on `temporal_filtering`; the *integration* fact lives here. Catalog divergence #1 already cites "order-sensitivity vs nuisance regression" as the reason `temporal_filtering` is a discrete step, so the two are complementary. A cross-step coherence validator (e.g. `filtering_integrated=True` implies a `temporal_filtering` step) is **deferred** — no coherence rules this round.

### D6 — `inference_applicable = False` on every new field
No KB records brain-extraction, segmentation, nuisance tool, or integration defaults. Mirrors the `intensity_normalization` precedent ("`inference_applicable=False` this round; flip when the KB lands").

### D7 — Pipeline-order placement: `brain_extraction`, then `segmentation`, immediately before `coregistration`
List position IS pipeline order (COBIDAS §4.3). Both are anatomical-target steps producing inputs that `coregistration` (skull-stripped T1, WM boundary) and `nuisance_regression` (tissue masks) consume. Segmentation operates on the extracted brain, so it follows brain_extraction.

### D8 — Amend the catalog in place
Promote the two "Anatomical-target" bullets to full numbered entries in the catalog's format (Prov / Canonical / Method / Infer), marked ADMITTED at v0.3.0; document the `parameters` deferral, the `ants` literal, and the two new `NuisanceRegression` fields. Single source of truth preserved.

---

## 2. Mechanical wiring (each has an import-time or test guard)

1. `BRAIN_EXTRACTION_FIELD_META` / `SEGMENTATION_FIELD_META`; extend `NUISANCE_REGRESSION_FIELD_META` with `method` + `filtering_integrated`. The import-time `_check_step_bijection` raises `RuntimeError` on any registry↔class divergence.
2. `STRUCTURAL_FIELDS = frozenset({"kind"})`, `ARM_REGISTRY`, and `@model_validator(mode="after")` → `_validate_step_invariants` on each new class.
3. Add both kinds to the `PreprocStep` `Annotated[..., Field(discriminator="kind")]` union.
4. `extractor_mvp._assemble`: construct both new steps, and the two new `NuisanceRegression` fields, as `_missing_pf(..., "not_targeted_by_mvp")` — schema-present, extractor-untargeted this change.
5. `preprocessing.py` docstring says "16-kind" (stale since v0.2.0 made it 17). Set to the true count (19).

---

## 3. Expected, intended consequence: `not covered by extractor` rises

~7 new untargeted fields per paper (5 from the new steps + 2 on NuisanceRegression). Chen's protocol header moves from `8 not covered by extractor` to ~15.

**Correct and honest** — these are real COBIDAS-mandatory items the extractor does not assess — but it is a visible number change:
- The chen reason-partition fixture asserting `"8 not covered by extractor"` will fail. **Update to the observed value; do not suppress.**
- `not_covered` remains excluded from every source-completeness figure (`_REASON_BUCKET`), so no source-gap claim shifts.
- Framing: the honest denominator is the COBIDAS checklist. A rising `not_covered` count means the extractor's gap *against the standard* is now more fully measured — not that the system regressed.

---

## 4. Out of scope

- **Extractor targeting** of any new field — separate change, separate commit, after this lands.
- `brain_extraction.parameters` (D1); cross-step coherence validators (D5); KB defaults for new steps (D6).
- Segmentation-derived masks as first-class provenance links into `nuisance_regression`/`compcor`.

---

## 5. Test plan

1. Import-time bijection passes for both new steps and the extended NuisanceRegression registry.
2. `_validate_step_invariants` fires on a deliberately mismatched `field_id` for each new class.
3. Discriminated-union round-trip: a `Preprocessing` containing both new kinds serializes and re-parses to the same types.
4. Per-kind uniqueness still rejects duplicate `brain_extraction` steps.
5. `SpatialNormalizationMethod` accepts `"ants"`; previously-valid values still validate (additive).
6. `NuisanceRegression` accepts `method` + `filtering_integrated`; `filtering_integrated` round-trips True/False.
7. `_assemble` emits both new steps and the two new fields fully untargeted.
8. `to_protocol` renders both steps with their `cobidas_row` tags and the "not assessed by current extractor" line (no emitter change — `flatten()` walks `steps` generically). **Confirm.**
9. `v0_3_0.StudySpec.schema_version == "0.3.0"`; `v0_1_0` / `v0_2_0` unchanged.
10. Chen fixture's `not covered by extractor` count updated to the newly observed value.

---

*Sequencing: this change first (spec + untargeted). Extractor targeting follows as its own commit — and now targets `method` AND the canonical fields per step, which is the "tool + method" output the user wants. The earlier "enum semantics fork" is resolved: no enum enrichment needed beyond D3, because `cost_function`/`warp`/`transform` already carry the method-independent facts.*

*Verification boundaries: COBIDAS PDFs in the project are zipped page images (no text layer), so Table D.3's exact row titles were NOT read directly — row names follow the repo catalog. Hoopes 2022 and Hallquist 2013 locators to be verified. `dartel`'s tool-vs-algorithm classification (unprefixed, unlike its siblings) is a pre-existing inconsistency, noted, not changed here.*

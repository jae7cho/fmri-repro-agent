# Preprocessing Step Catalog — ReplicationSpec v0.1.0 (DRAFT for review)

**Scope:** functional (resting + task) preprocessing as an *ordered process*. Anatomical-target
steps included only where a fMRI pipeline depends on them. DWI, perfusion, and resting-state
*feature* derivation (ALFF/fALFF/ReHo) are out of scope (routed to the deferred study-analysis layer).

**Grounding:** OHBM COBIDAS Report v1.0 (Nichols et al., 2016), **Table D.3 Preprocessing Reporting**
(pp. 53–58) and §4 General Principles. Each step records its COBIDAS provenance. Four rows are
explicit *divergences/extensions* beyond COBIDAS — flagged inline and listed at the end.

## Locked structural model
- `ReplicationSpec.preprocessing: list[Preprocessing]`; each `Preprocessing` has
  `applies_to: list[AcquisitionRef]` (referential integrity to present acquisitions; each functional
  acquisition covered exactly once). Handles rest/task sharing a pipeline (one entry, both refs) and
  the limited-FOV exception (its own entry).
- Each `Preprocessing` = `base_pipeline: ProvenancedField[PipelineRef] | NotApplicable`
  (2-arm union of *nested provenance over a PipelineRef* and an explicit NotApplicable arm
  for Bassett-style from-scratch pipelines). `PipelineRef(name: str, version: ProvenancedField[str])`:
  the name is plain (when a base pipeline is invoked the name is known) and the version carries
  its own provenance (Extracted / DeferredToCitation(target_kind="pipeline") / InferredDefault
  with `version_default` (0.95) or `date_inferred_version` (0.75) basis / MissingFromPaper).
  The outer ProvenancedField wraps the whole PipelineRef so the paper's claim about *whether
  there is a base pipeline* is itself provenanced. Configurator/KB role only — base pipelines
  are never expanded into stored steps.
  **+** `steps: list[PreprocStep]` (ordered; list position IS the order — COBIDAS §4.3
  *Ordering of steps*; may be empty for pipeline-as-is or unreported preprocessing).
- **Coupling rule:** exactly one combination is rejected — `base_pipeline = NotApplicable AND
  steps = []` (claims neither a base pipeline nor any preprocessing steps; incoherent for a
  spec with functional data). All other base_pipeline/steps combinations are valid, including
  pipeline-as-is (Extracted/Deferred + empty steps), honestly unreported (MissingFromPaper +
  empty steps), and Bassett (NotApplicable + non-empty steps).
- `PreprocStep` = `Annotated[Union[...], discriminator="kind"]`. **Plain per-kind uniqueness** within
  one pipeline, mirroring the acquisition collection validators. Operations that COBIDAS groups under
  one reporting row but that occur at *different pipeline stages* are modeled as **sibling kinds**
  (e.g. `despike` and `scrub`; `ica_denoise` / `compcor` / `nuisance_regression`) — so per-kind
  uniqueness alone lets them co-occur at separate ordered positions, with no composite key, no
  nested union, and no "may-repeat" exception. COBIDAS grouping is preserved as a queryable tag
  (`cobidas_row` class attr + `steps_in_group()` helper), not as an overloaded type.
- **Order is always extracted, never inferred.** No ordering prior (e.g. "ICA-FIX usually last") may
  enter the Extractor; the sequence is a property of the specific paper.
- Per-arm registry + import-time bijection + per-group `inference_applicable` invariant — mirror acquisition.
- `inference_applicable=True` only where a defensible default basis exists (conservative). Key reported
  params (FWHM, band edges, template space) default to **extracted** unless a base pipeline supplies them.

---

## Step catalog

Legend — Prov: COBIDAS D.3 row (or DIVERGENCE). Canonical = method-independent param. Infer = fields the
Pipeline Configurator may fill (basis in parens); all others are extracted-or-missing.

### 1. `nonsteadystate_removal`
- **Prov:** D.3 *T1 stabilization* (mandatory). Boundary: preprocessing-side dummy discard only
  ("if not already performed by scanner"); scanner dummies live in acquisition (`n_dummy_scanner`).
- **Canonical:** `n_nonsteadystate_discarded: int`
- **Method:** n/a
- **Infer:** none (study-specific; do not infer).

### 2. `slice_time_correction`
- **Prov:** D.3 *Slice time correction* (mandatory).
- **Canonical:** `reference: Literal["first","middle","specific_slice","specific_time"]`, `relative_to_motion_correction: Literal["before","after"]`
- **Method:** software/tool (FSL slicetimer / SPM / AFNI 3dTshift / …) + `interpolation: Literal["linear","spline","sinc"]` (+ order)
- **Infer:** interpolation (field_convention), reference (field_convention).

### 3. `motion_correction`
- **Prov:** D.3 *Motion correction* (mandatory).
- **Canonical:** `reference_scan: Literal["first","middle","mean","specific"]`
- **Method:** discriminator over `mcflirt` / `spm_realign` / `afni_3dvolreg` / `ants` / `other`; per-method:
  `similarity_metric` (normalized correlation / mutual information / …), `interpolation`,
  `nonrigid: bool` (+ transform type if true), `fieldmap_unwarping: bool` (+ method), `slice_to_volume: bool`
- **Infer:** similarity_metric (field_convention), interpolation (field_convention), reference_scan (field_convention).

### 4. `distortion_correction`
- **Prov:** D.3 *Gradient distortion correction* + *Distortion correction* (mandatory). Boundary:
  on-scanner / prospective correction stays in acquisition; reconstructed-image correction here.
- **Canonical:** `source: Literal["susceptibility_fieldmap","gradient_nonlinearity","fieldmap_less"]`
- **Method:** `topup` / `fugue` / `gradunwarp` / `sdc_fieldmapless` / `other`; `intended_fieldmap: AcquisitionRef|NotApplicable`
- **Infer:** none by default (method varies; do not infer).

### 5. `coregistration` (function ↔ structure, intra-subject)
- **Prov:** D.3 *Function-structure (intra-subject) coregistration* (mandatory).
- **Canonical:** `transform: Literal["rigid","affine","nonlinear"]`
- **Method:** `flirt_bbr` / `flirt` / `spm_coreg` / `bbregister` / `ants` / `other`; `cost_function`
  (correlation ratio / mutual information / boundary-based / SSD), `interpolation`
- **Infer:** cost_function (field_convention), interpolation (field_convention).

### 6. `intensity_correction`
- **Prov:** D.3 *Intensity correction* (mandatory). Bias-field (structural) + interleaved-EPI odd/even.
- **Canonical:** `target: Literal["bias_field","interleaved_slice"]`
- **Method:** software/tool (N4 / FAST bias / …)
- **Infer:** none by default.

### 7. `spatial_normalization` (intersubject, VOLUME)
- **Prov:** D.3 *Intersubject registration* (mandatory) — volume path only (surface split out → step 8).
- **Canonical:** `target_space: Literal["MNI152NLin6Asym","MNI152NLin2009cAsym","Talairach","native_volume","other"]`, `resolution_mm`
- **Method:** `fnirt` / `ants` / `ants_syn` / `spm_normalise` / `dartel` / `other`; `warp: Literal["rigid","affine","nonlinear"]` (+ transform type), `interpolation`, `regularization`. *(v0.3.0: plain `ants` added — lets "non-rigid registration using ANTs" record the tool without asserting SyN; mirrors coregistration / motion_correction.)*
- **Infer:** interpolation (field_convention). `target_space` / `resolution_mm` are
  version_default-only candidates — `inference_applicable=False` this round; flip when the
  KB lands and Configurator can defensibly pull base-pipeline defaults.

### 8. `surface_projection` — **DIVERGENCE (split from D.3 intersubject registration)**
- **Prov:** DIVERGENCE. COBIDAS folds surface into *Intersubject registration*; split out because
  target surface materially affects downstream results (per investigator: MNI152 vs MSM vs fsaverage vs native).
- **Canonical:** `target_surface: Literal["native","fsaverage","fsaverage5","fsaverage6","fsLR_32k","fsLR_164k","other"]`
- **Method:** `vol2surf_sampling: Literal["ribbon_constrained","trilinear","nearest"]`,
  `surface_registration: Literal["freesurfer_recon","msm_sulc","msm_all","other"]`, `cifti: bool`
- **Infer:** vol2surf_sampling (field_convention). `target_surface` and
  `surface_registration` are version_default-only candidates — `inference_applicable=False`
  this round; flip when the KB lands.

### 9. Structured noise removal — `cobidas_row="artifact_structured_noise_removal"` (3 SIBLING kinds)
- **Prov:** D.3 *Artifact and structured noise removal* (mandatory). COBIDAS groups these in one
  reporting row; modeled as sibling kinds so they co-occur at separate ordered positions (e.g. ICA-FIX
  then — separated by `temporal_filtering` — `nuisance_regression`). GSR = whole-brain tissue regressor
  inside `nuisance_regression`, not a step. Despike → `despike` (kind 10a).
- **kind `ica_denoise`:** `method: Literal["fix","aroma"]`; training set / threshold; AROMA aggressive vs non-aggressive.
- **kind `compcor`:** `variant: Literal["a","t"]`; n components or variance threshold; mask source.
- **kind `nuisance_regression`:**
  - motion `expansion: Literal["none","6param","friston24","volterra"]`
  - tissue: subset of {whole_brain(=GSR), gray_matter, white_matter, ventricles}; definition (seed / segmentation / aCompCor); signal (mean / first SV)
  - physio: `Literal["retroicor","rvt","none"]` + n regressors
  - detrend: `Literal["linear","quadratic","none"]`
  - **Method (v0.3.0):** `method: Literal["afni_3dtproject","afni_3dbandpass","afni_3ddeconvolve","fsl_regfilt","spm","nilearn","custom","other"]` — the tool discriminator this step previously lacked (`method` per schema-wide convention; `custom` = an author-written/in-house implementation, distinct from `other` = an unlisted named tool).
  - **Canonical (v0.3.0):** `filtering_integrated: bool` — True when temporal bandpass was applied *simultaneously within the same regression model* (one step, e.g. AFNI `3dTproject`) vs False = bandpass and regression as *separate sequential* operations. Tool-independent (a paper may describe simultaneous regression+filtering without naming `3dTproject`, or name it alongside a separate bandpass). Grounding: Hallquist, Hwang & Luna (2013, *NeuroImage* 82:208–225) — sequential bandpass-then-regression reintroduces nuisance variance. Band edges stay on `temporal_filtering`; only the integration fact lives here (no cross-step validator this round).
- **Infer:** none by default — motion expansion order is high-variance and prior-leaky; leave MISSING
  unless base pipeline supplies it (version_default). (Anti confirmation-bias: Extractor never infers these.)

### 10. Volume censoring — `cobidas_row="volume_censoring"` (2 SIBLING kinds)
- **Prov:** D.3 *Volume censoring* (mandatory). One COBIDAS row, two kinds because they occupy
  different pipeline stages (despike early; scrub late, FD-driven). Per-kind uniqueness lets both
  co-occur or either appear alone.
- **kind `despike`** (early per-voxel spike removal): tool/method (e.g. AFNI 3dDespike); optional threshold.
- **kind `scrub`** (motion-driven volume remediation): criterion (`fd_power` / `fd_jenkinson` / `dvars` / `bold_pct`) + threshold; `remediation: Literal["censor","interpolate"]` (+ interpolation method: spline / spectral if interpolate).
- **Infer:** none by default.

### 11. `temporal_filtering` — **DIVERGENCE (extension beyond D.3)**
- **Prov:** DIVERGENCE. Not a discrete D.3 row — COBIDAS files band edges under *RS feature* and
  high-pass/drift under D.4 (modeling). Added as a discrete step per RS-FC convention; order relative to
  nuisance is reproducibility-critical (Hallquist, Hwang & Luna, NeuroImage 2013 — verify exact cite).
- **Canonical:** `effective_band_hz: tuple[float|None, float|None]` (low, high) — method-independent.
  *Honest note:* for wavelet this is the scale's **nominal frequency support**, not a passband.
- **Method:** discriminator —
  - `butterworth_bandpass`: low_hz, high_hz, order
  - `highpass_only`: cutoff (s or Hz)
  - `wavelet_decomposition`: scale, nominal_band_hz (Bassett 2011: scale-two ≈ 0.06–0.12 Hz; *not* a filter)
- **Infer:** method=butterworth (field_convention), order (field_convention).
  `effective_band_hz` is a version_default-only candidate — `inference_applicable=False`
  this round (band edges must be Extracted or Missing); flip when the KB lands.

### 12. `intensity_normalization`
- **Prov:** D.3 *Intensity normalization* (NON-mandatory). Grand-mean / per-run scaling.
- **Canonical:** `scope: Literal["per_run","global"]`
- **Method:** convention (SPM grand-mean→100 [mean, single factor] / FSL grand-mean→10000 [mean, single factor, e.g. FEAT, fslmaths `-ing`] / FSL median→10000 [median, per-volume] / other) + value
- **Infer:** convention+value are version_default-only candidates — `inference_applicable=False`
  this round; flip when the KB lands.

### 13. `spatial_smoothing`
- **Prov:** D.3 *Spatial smoothing* (mandatory).
- **Canonical:** `fwhm_mm: float`, `space: Literal["native_volume","native_surface","mni_volume","template_surface"]`
- **Method:** kernel type (Gaussian); approach (fixed kernel / iterate-to-FWHM, e.g. AFNI 3dBlurToFWHM)
- **Infer:** kernel type (field_convention); fwhm_mm + space → extracted (key params).

### Anatomical-target (admit only if a functional pipeline depends on them) — **ADMITTED v0.3.0**
Both passed the admission test: brain extraction feeds `coregistration` / `spatial_normalization`
(skull-stripped T1); segmentation produces the WM/CSF masks that `nuisance_regression.tissue_regressors`
and `compcor` consume. List position places them just before `coregistration` (COBIDAS §4.3 order),
brain_extraction then segmentation. No KB defaults (`inference_applicable=False` on every field).

#### 4a. `brain_extraction` — **ADMITTED v0.3.0**
- **Prov:** D.3 *Brain extraction* (mandatory).
- **Canonical:** `manual_edits: bool`
- **Method:** `method: Literal["bet","afni_3dskullstrip","freesurfer_recon_all","ants","synthstrip","other"]`
- **Infer:** none (`inference_applicable=False`).
- **Deferral:** a `parameters` field is deliberately omitted — no canonical parameter is shared across
  BET / 3dSkullStrip / recon-all / SynthStrip (BET's `-f` has no cross-tool analogue), and free text
  would be unqueryable. Admit later only if a genuine cross-tool canonical param is identified.

#### 4b. `segmentation` — **ADMITTED v0.3.0**
- **Prov:** D.3 *Segmentation* (mandatory).
- **Canonical:** `tissue_classes: list[Literal["gray_matter","white_matter","csf"]]` — `csf` is the CSF
  tissue class, deliberately distinct from `nuisance_regression`'s `TissueRegressor.ventricles` (a
  narrower regressor mask).
- **Method:** `method: Literal["fsl_fast","spm_segment","freesurfer_recon_all","ants_atropos","other"]`
- **Infer:** none (`inference_applicable=False`).

---

## Divergences from COBIDAS D.3 (documented)
1. **`temporal_filtering`** added as a discrete step (COBIDAS files it under RS-feature / modeling). Justified: RS-FC convention + order-sensitivity vs nuisance regression.
2. **`surface_projection`** split out of *Intersubject registration*. Justified: target surface space is a high-impact, separately-reported decision in surface pipelines (HCP/CCS).
3. **RS features (ALFF/fALFF/ReHo)** — COBIDAS lists under D.3; we route to the study-analysis layer (derived measures, not transforms).
4. **`despike` and `scrub`** are sibling kinds under one COBIDAS *Volume censoring* group, separated
   because they occupy different pipeline stages (despike early, scrub late). COBIDAS reports them in
   one row; we keep the grouping as a tag while typing them distinctly.

## Out of scope (do not build here)
DWI (eddy/estimation/tractography), perfusion (ASL/DSC), RS feature derivation, citation resolution,
base-pipeline step expansion (KB manifest answers those at query time, not stored).

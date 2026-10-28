# DESIGN — coverage expansion: extraction for the eleven uncovered mandatory D.3 rows

**Design, written 2026-10-28 before the build, from the code at HEAD `88902fe`, the COBIDAS report
(`OHBM COBIDAS Report v1.0`, Table D.3 "Preprocessing Reporting", printed pp. 53–58) and the stored
results.** Part A is read-only fact with locators; Part B records the author's rulings of 2026-10-28
(R1–R8, sourced to their message of that day, quoted in §0) and the design built under them. The
three held-out papers (liu_2005, tang_2025, wheaton_2004) enter the run through the model only and
their reports are read as states and counts; no held-out text is read, by the author or by Claude
Code. No model call precedes Part D.

## 0. Rulings — 2026-10-28, by the author, recorded the day they were given

> **R1 Scope:** all 11 rows get extraction now, in two shared calls, each with its own pinned prompt:
> temporal/volume (T1 stabilization, slice time correction, volume censoring, artifact and structured
> noise removal) and spatial (brain extraction, segmentation, coregistration, distortion correction
> with gradient distortion folded in, intensity correction, spatial smoothing). Fields are D.3's
> items, granular: values, units, thresholds, tools, reference slices, regressor lists. Add fields
> where A1 found none.
>
> **R2** Every new step carries `performed` first: EXTRACTED yes or no with the quote, MISSING when the
> paper is silent. A stated negative is a report, not a gap. Parameters are asked only when performed
> is yes or unstated.
>
> **R3** Every field keeps the four-state model and the quote requirement, resolved through the same
> span path, with the value-support check by field type: alias table for Literals, digit-exact for
> numbers, the motion matcher for free text. Failures render unverifiable, never not-reported.
>
> **R4** Structured-noise tools (CompCor, ICA-AROMA, FIX) and nuisance regressors land on their own
> row here; the motion fallback keeps routing them off the motion method.
>
> **R5** Render: each row shows state, values and quote; a validation tag per row, "validated against
> labels" for Software, Intersubject registration and Motion correction, "unvalidated" for the rest;
> the coverage header counts over all 14 mandatory rows.
>
> **R6** Emission follows the existing convention: every kind emitted, fields carry states.
>
> **R7** No labels and no accuracy figures for the new rows; a later prereg picks rows to validate,
> smoothing and slice timing first. The KB's pipeline defaults for these rows are the next build, not
> this one.
>
> **R8** Vintage: the new calls are new hashes; the existing three hashes do not move (pin test).
> Cost recorded: two extra calls per paper.

---

## Part A — facts, read-only, at HEAD `88902fe`

### A1. The eleven uncovered mandatory rows: D.3's own items, and what the spec already has

D.3's "Notes" column is transcribed from the report's text layer (`COBIDASreport.pdf`, page indices
52–57; the layer's spacing artefacts such as "Nam e" are repaired, the wording is unchanged). The
spec's classes are in `src/fmri_repro/spec/preprocessing.py`; the row→kind mapping is
`extractor_mvp/src/extractor_mvp/cobidas.py:48-103`. "Has a field" / "no field" is read against the
class as declared at HEAD.

**1. T1 stabilization** (`cobidas.py:53`, kind `nonsteadystate_removal`) — D.3: *"Number of initial
'dummy' scans discarded as part of preprocessing (if not already performed by scanner)."* Class
`NonsteadystateRemoval` (`preprocessing.py:653-666`): `n_nonsteadystate_discarded: int`.
Has a field: the number. No field: whether the step was performed.

**2. Brain extraction** (`cobidas.py:54`, kind `brain_extraction`) — D.3: *"If performed, report:
Name of software/method (e.g., BET, recon-all in FreeSurfer, etc). Parameter choices (e.g. BET's
fractional intensity threshold). Any manual editing applied to the brain masks."* Class
`BrainExtraction` (`:753-766`): `method: Literal[bet, afni_3dskullstrip, freesurfer_recon_all, ants,
synthstrip, other]`, `manual_edits: bool`. Has a field: software/method; manual editing. No field:
parameter choices (the catalog `docs/spec/preprocessing_catalog_v0.1.0.md:171-176` deliberately
omitted it as unqueryable free text; R1 overrides: "add fields where A1 found none").

**3. Segmentation** (`cobidas.py:55`, kind `segmentation`) — D.3: *"For structural images, method
used to extract gray, white, CSF and other tissue classes."* Class `Segmentation` (`:777-790`):
`method: Literal[fsl_fast, spm_segment, freesurfer_recon_all, ants_atropos, other]`,
`tissue_classes: list[Literal[gray_matter, white_matter, csf]]`. Has a field: both items. No field:
performed.

**4. Slice time correction** (`cobidas.py:56-58`, kind `slice_time_correction`) — D.3: *"If
performed, report: Name of software/method. Whether performed after or before motion correction.
Reference slice. Interpolation type and order (e.g., 3rd order spline or sinc)."* Class
`SliceTimeCorrection` (`:673-687`): `reference: Literal[first, middle, specific_slice,
specific_time]`, `relative_to_motion_correction: Literal[before, after]`, `interpolation:
Literal[linear, spline, sinc]`. Has a field: before/after; reference slice; interpolation type. No
field: software/method; interpolation order; performed.

**5. Gradient distortion correction** (`cobidas.py:60-66`, kind `distortion_correction`) — D.3:
*"(If not already described as part of motion susceptibility correction.)"* — no items of its own;
the row shares the kind with row 6 (R1 folds it in). See 6.

**6. Distortion correction** (`cobidas.py:67-69`, kind `distortion_correction`) — D.3: *"Use of any
distortion correction due to field or gradient nonlinearity."* Class `DistortionCorrection`
(`:729-743`): `source: Literal[susceptibility_fieldmap, gradient_nonlinearity, fieldmap_less]`,
`method: Literal[topup, fugue, gradunwarp, sdc_fieldmapless, other]`, `intended_fieldmap`
(structural). Has a field: the source (which also tells gradient from field), the method. No field:
performed ("use of any").

**7. Function-structure (intra-subject) coregistration** (`cobidas.py:70-76`, kind `coregistration`)
— D.3: *"Report: Name of software/method. Type of transformation (rigid, nonlinear); if nonlinear,
type of transformation. Cost function (e.g., correlation ratio, mutual information, boundary-based
registration, etc). Interpolation method (e.g., spline, linear). Note this step might not be
necessary if direct T2\* to a functional template registration is used."* Class `Coregistration`
(`:801-816`): `transform: Literal[rigid, affine, nonlinear]`, `method: Literal[flirt_bbr, flirt,
spm_coreg, bbregister, ants, other]`, `cost_function: Literal[correlation_ratio, mutual_information,
boundary_based, ssd]`, `interpolation: Literal[linear, spline, sinc, other]`. Has a field: all four
named items. No field: the nonlinear transformation's type; performed.

**8. Intensity correction** (`cobidas.py:84-86`, kind `intensity_correction`) — D.3: *"Bias field
corrections for structural MRI, but also correction of odd versus even slice intensity differences
attributable to interleaved EPI acquisition without gaps."* Class `IntensityCorrection` (`:823-836`):
`target: Literal[bias_field, interleaved_slice]`, `method: Literal[n4, fast_bias, other]`. Has a
field: the target (both cases D.3 names), the method. No field: performed.

**9. Artifact and structured noise removal** (`cobidas.py:94-100`, kinds `ica_denoise`, `compcor`,
`nuisance_regression`) — D.3: *"Use of physiological noise correction method. Report: Name of
software/method used (e.g. CompCor, ICA-FIX, ICA-AROMA, etc.). If using a nuisance regression
method, specify regressors used; for each type, include key details, as follows: Motion parameters:
Expansion basis and order (e.g. 1st temporal derivatives; Volterra kernel expansion). Tissue
signals: Tissue type (e.g., whole brain, gray matter, white matter, ventricles). Tissue definition
(e.g., a priori seed, automatic segmentation, spatial regression). Signal definition (e.g., mean of
voxels, first singular vector, etc.). Physiological signals: e.g., heart rate variability,
respiration. Modeling choices (e.g. RETROICOR, cardiac and/or respiratory response functions) and
number of computed regressors."* Classes `ICADenoise` (`:914-928`: `method: Literal[fix, aroma]`,
`training_set: str`, `threshold: float`, `aggressive: bool`), `CompCor` (`:935-949`: `variant:
Literal[a, t]`, `n_components: int`, `variance_threshold: float`, `mask_source: str`),
`NuisanceRegression` (`:971-995`: `motion_expansion: Literal[none, 6param, friston24, volterra]`,
`tissue_regressors: list[Literal[whole_brain, gray_matter, white_matter, ventricles]]`,
`physio_regressors: Literal[retroicor, rvt, none]`, `physio_n_regressors: int`, `detrend:
Literal[linear, quadratic, none]`, `method: Literal[afni_3dtproject, …, custom, other]`,
`filtering_integrated: bool`). Has a field: the tool (ica method; nuisance method); motion expansion;
tissue type; physiological modelling choice and count. No field: the regressors "used" as a stated
list; tissue definition; signal definition; performed (per kind).

**10. Volume censoring** (`cobidas.py:101`, kinds `despike`, `scrub`) — D.3: *"Remediation of
problem scans, also known as 'scrubbing' or 'de-spiking'. Report: Name of software/method. Criteria
(e.g., frame-by-frame displacement threshold, percentage BOLD change). Use of censoring or
interpolation; if interpolation, method used (e.g., spline, spectral estimation)."* Classes `Despike`
(`:1002-1015`: `method: Literal[afni_3dDespike, other]`, `threshold: float`), `Scrub` (`:1023-1037`:
`criterion: Literal[fd_power, fd_jenkinson, dvars, bold_pct]`, `threshold: float`, `remediation:
Literal[censor, interpolate]`, `interpolation_method: Literal[spline, spectral, other]`). Has a
field: despike's tool; the criterion and threshold; censor/interpolate and the interpolation method.
No field: scrub's software/method; performed (per kind).

**11. Spatial smoothing** (`cobidas.py:102`, kind `spatial_smoothing`) — D.3: *"If this preprocessing
step is performed, report: Name of software/method. Size and type of smoothing kernel. Filtering
approach, e.g., fixed kernel or iterative smoothing until fixed FWHM. Space in which smoothing is
performed (i.e. native volume, native surface, MNI volume, template surface)."* Class
`SpatialSmoothing` (`:1158-1172`): `fwhm_mm: float`, `space: Literal[native_volume, native_surface,
mni_volume, template_surface]`, `kernel_type: Literal[gaussian, other]`, `approach:
Literal[fixed_kernel, iterate_to_fwhm]`. Has a field: size, type, approach, space. No field:
software/method; performed.

**Every class above carries no `performed` field.** The row→kind registry already maps all thirteen
kinds (`cobidas.py:50-103`); `nonsteadystate_removal`, `slice_time_correction`,
`distortion_correction`, `coregistration`, `intensity_correction`, `ica_denoise`, `compcor`,
`despike`, `scrub` and `spatial_smoothing` are **never emitted** by `_assemble` (`extractor.py:
1005-1016` lists eight kinds), so at HEAD their rows render "(no fields assessed by current
extractor)" on every report (`render.py:950-957`).

### A2. What a new targeted step kind touches, re-measured at HEAD

- **`_assemble`** (`extractor.py:906-1017`): a hardcoded list — `brain_extraction`, `segmentation`
  (`:921-928`), `spatial` (`:929-937`), `surface` (`:938-943`), `nuisance_regression` (`:948-956`),
  `intensity` (`:957-961`), `temporal_standardization` (`:962-964`), `motion_correction`
  (`:975-993`), `steps=[…]` (`:1005-1016`). Untargeted fields are `_missing_pf(name, type,
  "not_targeted_by_mvp")` (`:918`, `:451-456`). A new targeted kind is a new entry here and nowhere
  else in assembly.
- **The calls.** `extract_preprocessing` (`:1564-1601`) makes exactly two: the motion call first
  (`extract_motion_method`, `:1364-1473`, `client.chat.completions.create` at `:1392-1398`), then the
  shared call inside `_extract_from_prompt` (`:1474-1563`, `create` at `:1489-1495`), which builds
  the `pf` dict over `_FIELD_SPECS` (`:396`) and returns `_assemble(pf, base_pipeline,
  motion_method)` (`:1563`). The per-acquisition path (`extract_preprocessing_for_acquisition`,
  `:1603-1618`; `multi_acquisition_extractor.py:41-86`) calls `_extract_from_prompt` with no motion
  field, so `_assemble` marks `method` untargeted there (`:968-985`). One client serves both calls
  (`:1578-1585`); the test stub dispatches on `response_model` (`tests/conftest.py:95-146`).
- **Coverage.** `assess_coverage` (`cobidas.py:285-332`): per row, `mapped` = the flattened rows
  whose `group` is one of the row's `spec_kinds`; `addressed` iff any mapped field is `EXTRACTED` or
  `DEFERRED_TO_CITATION` (`_ADDRESSING_STATUSES`, `:120`); `covered_by_extractor` iff any mapped
  field's reason is not `not_targeted_by_mvp` (`_row_covered_by_extractor`, `:216-220`);
  `unverifiable` iff not addressed and some gap base is in `_UNVERIFIABLE_GAP_BASES`
  (`:150-180`). The Software row has its own rule (`:222-283`). Nothing here enumerates kinds; a
  new targeted kind is covered by construction once its fields carry a reason other than untargeted.
- **Render.** `flatten` (`render.py:245-290`) walks `model_fields` of every step and skips
  non-provenanced attributes (`:283-287`). `to_protocol` (`:720-812`) renders each step's rows
  generically (`:797-807`) with one special case, the motion line (`:802-803`). `to_cobidas_coverage`
  (`:855-1037`): the header (`:876-918`), the per-row tag (`:950-957`), the three lists
  (`:960-1030`). Gap wording comes from `_REASON_LINE` (`:514-569`) and buckets from
  `_REASON_BUCKET` (`:474-511`); `test_render.py:717-760` fails on any reason produced in
  `extractor.py`, `migrations.py` or `kb_client/base_pipeline.py` that is in neither table. **The
  scan does not read a new module**, so the new calls' reasons must be produced in `extractor.py`
  or the scan's source list must be widened (it is, in C).
- **Batch.** `_tally` (`batch.py:131-192`) walks every field of every step and assumes each attribute
  is a provenanced field (`pf.inference.status`, `:170`); `process_paper` (`:212-371`) stores
  `preprocessing.model_dump` and renders `to_report`. No wall-time field exists on the record
  (`:336-357`); the corpus run's timing came from the launcher manifest and file mtimes.
- **Other walkers that assume every step attribute is a `ProvenancedField`:**
  `_validate_step_invariants` (`preprocessing.py:610-633`, `pf.field_id`), `_check_step_bijection`
  (`:592-608`, names only), `citation_resolver._iter_fields` (`:51-58`, `pf.field_id`),
  `field_diff.py:45-49` (tolerant, `getattr(pf, "extraction", None)`), the KB fill
  (`kb_client/base_pipeline.py:64-79`, seven named fields only).
- **The routing gate** `_LAYER2_FIELD_IDS` (`extractor.py:1653-1664`) names six fields; a new step's
  `LEFT_MISSING` does not trigger the citation fallback. Unchanged by this build.
- **The pin.** `tests/test_prompt_pin.py:28-81` pins `EXTRACTION_PROMPT`
  (`31a050b291161c31d5b535b2411234df12b484039a436b7a85df6b4081b77535`),
  `PER_ACQUISITION_EXTRACTION_PROMPT`
  (`04ba3cb76b55342cee2ed2fd8b62fb515226fdb21511c6803f380d51913c4648`) and `MOTION_METHOD_PROMPT`
  (`b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837`);
  `test_both_model_facing_prompts_are_hash_pinned` (`:97-104`) loops exactly those three, and
  `:107-116` asserts the per-acquisition constant ends with the shared one. **Confirmed:** the three
  constants are untouched by this build (new prompts are new constants in a new module), so the
  three hashes cannot move; the pin test gains two entries (R8).
- **Schema.** `SCHEMA_VERSION = "0.5.1"` (`preprocessing.py:1269`; `Preprocessing.schema_version`
  `:1305`; the study root `v0_4_0.py:45`). Migration hops: `migrations.py:137-209` — 0.3.0 fills
  (`_ADDED_IN_0_3_0`), 0.4.1→0.5.0 lifts bare members to `SpecifiedTerm` (`_RETYPED_IN_0_5_0`,
  `:54-60`, `_lift_to_specified_term` `:117-135`), 0.5.0→0.5.1 re-stamps. The stored acceptance
  records are native 0.5.1 with seven kinds (`results/batch_a1_acceptance/papers/*.json`: no
  `motion_correction`), the corpus records native 0.5.1 with eight; `examples/spec.json` is native
  0.5.1 and carries **bare members** on `despike.method`, `nuisance_regression.motion_expansion /
  tissue_regressors / detrend`, `spatial_smoothing.space`.

---

## Part B — the design under R1–R8

### B1. Scope and the two calls (R1)

Two new model-facing constants in a new module `extractor_mvp/coverage_extractor.py`:
`TEMPORAL_VOLUME_PROMPT` with response model `TemporalVolumeExtraction`, and `SPATIAL_PROMPT` with
`SpatialExtraction`. Each response field is a `FieldExtractionResult` (the three-state schema every
call uses). The field inventory is D.3's items, granular; **new** marks a field A1 found missing.

**Call T — temporal/volume** (`TemporalVolumeExtraction`):

| kind | fields (new in bold) |
|---|---|
| `nonsteadystate_removal` | **performed**, n_nonsteadystate_discarded (int) |
| `slice_time_correction` | **performed**, **method** (tool), relative_to_motion_correction, reference, interpolation, **interpolation_order** (int) |
| `despike` | **performed**, method (tool), threshold (number) |
| `scrub` | **performed**, **method** (tool), criterion, threshold (number), remediation, interpolation_method |
| `ica_denoise` | **performed**, method, training_set (text), threshold (number), aggressive (bool) |
| `compcor` | **performed**, variant, n_components (int), variance_threshold (number), mask_source (text) |
| `nuisance_regression` | **performed**, method (tool), **regressor_list** (text: the regressors as the paper lists them), motion_expansion, tissue_regressors (list), **tissue_definition** (text), **tissue_signal_definition** (text), physio_regressors, physio_n_regressors (int), detrend, filtering_integrated (bool) |

**Call S — spatial** (`SpatialExtraction`):

| kind | fields (new in bold) |
|---|---|
| `brain_extraction` | **performed**, method (tool), **parameters** (text), manual_edits (bool) |
| `segmentation` | **performed**, method (tool), tissue_classes (list) |
| `coregistration` | **performed**, method (tool), transform, **nonlinear_transform_type** (text), cost_function, interpolation |
| `distortion_correction` | **performed**, source, method |
| `intensity_correction` | **performed**, target, method |
| `spatial_smoothing` | **performed**, **method** (tool), fwhm_mm (number), kernel_type, approach, space |

Thirty-eight fields on T, twenty-five on S. *(Erratum, 2026-10-28, at the build: the first
committed text of this line said thirty-nine; the table above sums to 2 + 6 + 3 + 6 + 5 + 5 + 11 =
38, which is what the response model carries.)* Gradient distortion correction is folded into
`distortion_correction` (R1): `source = gradient_nonlinearity` is the gradient case, and the
registry keeps both rows mapped to the one kind (`cobidas.py:60-69`), so a report on that kind
credits both rows — recorded, and the single-row credit test in C names this pair as the one
documented exception.

### B2. `performed` first (R2)

Each of the thirteen kinds gets `performed: ProvenancedField[bool]` as its first declared field.
The prompt asks it first for every step, with three outcomes: `extracted` with value `yes` or `no`
and the sentence that states it; `missing` when the text is silent; `deferred` when the text defers
the step (or its preprocessing as a whole) to a citation or a named pipeline and states nothing
about the step itself. A stated negative ("no slice-timing correction was applied") is EXTRACTED
`False` with its quote — a report, and it addresses the row (the predicate at `cobidas.py:120`
needs no change: EXTRACTED is EXTRACTED). The prompt asks for parameters only when `performed` is
`yes` or unstated; when the model returns `no`, the parameters are set `MissingFromPaper` with the
new reason **`step_not_performed`** regardless of what else it returned, rendered "not applicable —
the paper states this step was not performed" and bucketed under a new header segment
`not applicable (step stated as not performed)` that appears only when non-zero (so every stored
report is byte-identical). The reason is not a gap about the paper and not an extractor
limitation, so it joins neither `not_reported` nor `not_covered`.

### B3. States, quotes and support, by field type (R3)

Every field goes through `_process_field` (`extractor.py:487-618`): `missing` → `not_stated_in_text`;
`deferred` → `_process_deferred` (the deferral sentence resolved, `deferral_quote_unresolved:*`
otherwise); `extracted` → the quote resolved by `resolve_quote` (`extraction_quote_unresolved:*`
otherwise), then the value-support check **by field type**, run on the text the resolver located:

| field type | value shape | support check | source of the check |
|---|---|---|---|
| Literal-typed (term) — every closed vocabulary above, including tools | `SpecifiedTerm` (verbatim, resolved, resolution) | an alias of the value, taken whole, in the quote (`literal_value_supported`); the alias tables are new, one per field, keyed by dotted id | `quote_support.py:179-201`, extended |
| list of terms (`tissue_classes`, `tissue_regressors`) | `list[SpecifiedTerm]` | every item supported as above | new |
| number (`threshold`, `fwhm_mm`, `variance_threshold`) and integer (`n_nonsteadystate_discarded`, `interpolation_order`, `n_components`, `physio_n_regressors`) | float / int | the number in the quote, digit-exact (`number_in_quote`) | `quote_support.py:161-170` |
| free text (`parameters`, `regressor_list`, `tissue_definition`, `tissue_signal_definition`, `training_set`, `mask_source`, `nonlinear_transform_type`) | str | the motion matcher: the value's tokens as one contiguous run in the quote, word form tolerated, digits exact (`quote_supports_value_inflected`) | `motion_guard.py:103-119` |
| boolean (`performed`, `manual_edits`, `aggressive`, `filtering_integrated`) | bool | the quote must resolve; no token check (a yes/no has no token to find) — recorded as the one type without a value check | — |

A failed check is `MissingFromPaper` with reason `value_unsupported_by_quote` (already a member of
`_UNVERIFIABLE_GAP_BASES`, `cobidas.py:178`), so the row renders *examined; could not verify*, never
*not reported*. A value the resolver cannot coerce (a non-number for a number field, a non-yes/no
for a boolean) is `value_not_numeric` (existing) or the new `value_not_boolean` (bucket
`unmappable`). The `SpecifiedTerm` recording means a term the alias table does not know stays
EXTRACTED with `resolution = unrecognized` and the paper's words kept — the 0.5.0 rule
(`extractor.py:518-524`), which is why the Literal-typed fields of the thirteen kinds **retype** to
`SpecifiedTerm[X]` in this build (B9): `_process_field` produces a `SpecifiedTerm` for every
Literal-typed field and a bare-Literal field could not hold it.

Synonym resolution for the new fields is keyed by **dotted** id (new tables in
`coverage_fields.py`), never by the bare id (`extractor.py:526-537` records why: `method` is the bare
id of eleven fields now).

### B4. The artifact row (R4)

CompCor, ICA-AROMA and ICA-FIX land on `ica_denoise.method` / `compcor.*`; the regressors on
`nuisance_regression.*` — the row `artifact_structured_noise_removal` (`cobidas.py:94-100`). The
motion check is untouched: `motion_guard.structured_noise_tool` (`:122-134`) keeps routing those
tools off `motion_correction.method`, and the package fallback (`extractor.py:1444-1468`) stays.
Nothing in call T is read by the motion call or vice versa; both see the same slice.

### B5. Render (R5)

`to_cobidas_coverage` gains a per-row section, emitted **only when the record carries an expanded
step** (any of the thirteen kinds with `performed` present), so every stored report is byte-identical
(the same conditional-emission trade the unverifiable breakdown recorded at `render.py:900-911`):

- the header counts over all 14 mandatory rows: `Assessed by AESPA: N → addressed a · performed=no p
  · unverifiable u · not reported r` (`performed=no` and `unverifiable` segments only when non-zero);
- a `### Rows` list, one line per mandatory row in D.3 order: the aspect, the validation tag
  (`[validated against labels]` for Software, Intersubject registration and Motion correction —
  the three rows with a ground-truth protocol and a workbook; `[unvalidated]` for the rest), the row
  state (`reported` / `performed: no` / `deferred` / `unverifiable` / `not reported` / `not
  assessed`), then the row's values (`field = value`, the extracted and deferred fields only) and the
  first extracted field's quote, truncated as the step lines are (`_truncate_quote`, `:346-350`).

The step sections (`:797-807`) already show every field's state, value and quote and are unchanged.

### B6. Emission (R6)

`_assemble` emits all eighteen kinds, in catalog order with the existing eight kept in their
present relative order: `nonsteadystate_removal`, `slice_time_correction`, `brain_extraction`,
`segmentation`, `motion_correction`, `distortion_correction`, `coregistration`,
`intensity_correction`, `spatial_normalization`, `surface_projection`, `ica_denoise`, `compcor`,
`nuisance_regression`, `despike`, `scrub`, `intensity_normalization`, `spatial_smoothing`,
`temporal_standardization`. `temporal_filtering` is a DIVERGENCE kind with no D.3 row
(`cobidas.py:105-106`) and stays unemitted. On the per-acquisition path (no new calls, as for
motion) every field of the thirteen kinds, `performed` included, is `not_targeted_by_mvp` — the
extractor did not look, so no source-absence reason may stand there (the ruling-A reasoning at
`extractor.py:975-981`).

### B7. No labels, no accuracy (R7)

Nothing in this build is scored. The eleven rows carry the `[unvalidated]` tag; the run's table in
Part D is counts of papers by row state. A later pre-registration picks rows to validate, smoothing
and slice timing first. The KB's pipeline defaults for these rows are the next build: every new or
retyped field has `inference_applicable=False`.

### B8. Vintage and cost (R8)

`TEMPORAL_VOLUME_PROMPT` and `SPATIAL_PROMPT` are pinned in `test_prompt_pin.py` beside the three
existing hashes with a dated note; the three do not move (A2). Every call on the single-acquisition
path: four per paper (motion, temporal/volume, spatial, shared) — two more than before, each with
the same model, temperature 0.0 and `max_retries=2`, asserted by the stub test (C). The run's
`launcher_manifest.json` carries all five hashes. Wall time: `process_paper` records `wall_time_s`
(the four calls plus assembly, `time.perf_counter`) into the stored JSON — a new key, read by the
Part D table; stored records without it still load.

### B9. Schema 0.5.2 — the fork, recorded

Two schema changes are needed and one choice is open.

1. **The retype** (B3): the Literal-typed fields of the thirteen kinds become `SpecifiedTerm[X]`
   (lists: `list[SpecifiedTerm[X]]`). This is the 0.5.0/0.5.1 pattern with the same reason
   (`preprocessing.py:698-701`). A structural hop 0.5.1→0.5.2 lifts bare members on those fields
   (`_RETYPED_IN_0_5_2`, the existing `_lift_to_specified_term`, extended to lists); the stored
   records carry those fields only as `MissingFromPaper` fillers, so the lift is a no-op on them;
   `examples/spec.json` is re-stamped natively with its five bare members lifted by hand.
2. **The new fields** (`performed` and the nine D.3 items). Fork:
   - *(i) required, with the hop synthesising `field_not_in_schema_version` fillers* — the
     `_ADDED_IN_0_3_0` precedent (`migrations.py:97-105`). Cost: every stored report changes on
     re-render (three stored kinds gain rows: `brain_extraction` +2, `segmentation` +1,
     `nuisance_regression` +4), **and** `_row_covered_by_extractor` (`cobidas.py:216-220`) counts a
     `field_not_in_schema_version` field as targeted, which would flip those rows to "assessed → not
     reported" on old reports — a false claim about the paper (a latent defect: `cobidas.py:149-153`
     says the reason is the untargeted case, the predicate does not).
   - *(ii) optional (`ProvenancedField[...] | None = None`), with a re-stamp hop* — a 0.5.1 document
     parses with the fields absent; `written_under = 0.5.1` says why they are absent; a native 0.5.2
     document always carries them because `_assemble` sets every one (asserted in C). Cost: the
     walkers in A2 must skip `None` (`_validate_step_invariants`, `_iter_fields`, `_tally`).
   **Chosen: (ii)**, and **ratified by the author on 2026-10-28** ("Ratify the optional-fields fork
   as optional", their message of that evening, which also ordered the six follow-ups recorded in
   §B14). Chosen under the author's gate derivation ("stored JSONs have no new steps: 19
   identical") and the project's standing trade for the gate's attributability
   (`render.py:900-911`). The latent predicate defect under (i) is recorded here, not fixed: no
   migration synthesises fields in this build, so it cannot fire.

`SCHEMA_VERSION` → `0.5.2` (`preprocessing.py:1269`, the study root `v0_4_0.py:45`, the hop and its
tests, the example re-stamped).

### B10. The identity gate, derived before the run

The build changes code; the gate compares HEAD's render of the stored acceptance records with the
pre-build render (`scripts/rerender_reports.py --results-dir results/batch_a1_acceptance --against
<pre-build HEAD>`). Derived: **19 identical** — the stored records carry none of the thirteen kinds'
new fields (B9 (ii): absent, not synthesised), the three in-scope kinds they do carry render the
same rows with the same states, no retyped field in them holds a value, the per-row section and
the header segments are emitted only when an expanded step is present (B5, B2), and the step order
is read from the record, not from `_assemble`. Negative control: `--against d31e8b7` → 0 identical,
19 changed, as on every earlier run. Both are run after the build, before Part D.

### B11. Tests and mutations (Part C)

- The stub serves four response models by dispatch; `extract_preprocessing` makes exactly one of
  each per paper; the per-acquisition path makes none of the three extra calls (counter asserted).
- Each D.3 row maps to exactly one set of kinds; a synthetic record with one row's `performed`
  EXTRACTED credits only that row — except the gradient/distortion pair, which shares a kind and is
  asserted to move together.
- A `performed = no` record: the row addressed, the parameters `step_not_performed`, the header's
  segment present, the row line `performed: no`.
- Support failures by type: a term whose alias is not in the quote, a number not in the quote, free
  text not in the quote → `value_unsupported_by_quote`, row `unverifiable`.
- The pin: five hashes; the three old values unchanged (asserted against the literal strings).
- Mutations shown non-empty before each run: the `performed=no` override removed; the per-row
  section's condition inverted; one alias table emptied; the stub's dispatch collapsed.

### B12. Not built here

KB defaults for the eleven rows (R7); labels and scoring (R7); `temporal_filtering` emission (no
D.3 row); the Literal→SpecifiedTerm retype of kinds outside the thirteen; the `field_not_in_schema_
version` predicate defect (B9); the new calls on the per-acquisition path (same cost ruling A
recorded for motion).

### B13. Part D — the run

`configs/batch_coverage_v1_config.yaml`: the corpus config's nineteen papers and model, output
`results/batch_coverage_v1` (a new vintage directory, gitignored). The launcher writes
`launcher_manifest.json` (HEAD, the five prompt hashes, the config's sha256, model, start, end,
exit) beside the output before any result is read. Reported: the rendered reports of ciric_2017,
chen_2015 and poldrack_2015 in full (chat only); one table — per mandatory row, how many of the 16
contaminated papers are `addressed`, `performed=no`, `unverifiable`, `not reported` (exclusive, in
that order), the held-out three as counts only; wall time per paper from `wall_time_s`. Every field
this run writes is the new vintage `coverage_v1`; nothing is pooled with any earlier vintage.

### B14. The six follow-ups, ordered by the author on 2026-10-28 (after the coverage_v1 run)

Recorded verbatim from the author's message, each built in this order with tests, mutations and a
replay where no model call is needed; then the nineteen re-run as `coverage_v2`:

1. *Text-layer repair in the span resolver's repair pass: ligatures (ﬁ ﬂ, and binder's ª for fi),
   and single-glyph substitutions where the quote has a symbol and the text a letter or digit at
   that position (> as 4, < as o, × as /C2 already known), bounded to a small count per quote and
   reported as "matched after source-text repair" with the substitutions named. Replay over every
   stored result and every recorded motion draw: list each cell that moves from unresolved to
   resolved, by paper and field, and confirm nothing resolved before changes.*
2. *Boolean support: `performed` quotes must contain a phrase from a frozen per-step list; a miss
   renders unverifiable; `performed` can never be deferred (validator and prompt). Replay: which
   cells move.*
3. *Alias fixes: underscore, space and hyphen equal in alias matching; susceptibility_fieldmap gains
   "magnetic field inhomogeneit\*"; Volterra resolves to friston24; detrend takes the highest order
   named. Replay.*
4. *Coregistration field definitions in the spatial prompt: method = tool, cost_function = bbr |
   mutual_information | correlation_ratio | other. New hash, dated note.*
5. *A `multiple_pipelines` field on both coverage calls: whether the text describes more than one
   preprocessing variant, with quote and count; rendered as a header line on the steps section when
   true. New hashes, dated notes.*
6. *Kind-prefixed fields on rows with sibling kinds.*

Item 2 supersedes B2's third outcome (`performed` deferred) and B3's "no token check" for the
boolean `performed`; item 4 supersedes B1's coregistration vocabulary in the prompt (the spec's
Literal is unchanged: `bbr` resolves to `boundary_based`); item 6 supersedes B5's per-row value list
on rows mapped to more than one kind.

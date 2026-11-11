# applies_to Stage 2b: four variant papers re-run (2026-11-11)

**Run**
- `aespa-report` with default settings, from a worktree pinned at `1cb7383` (imports confirmed from
  it; schema 0.7.1), into `extractor_mvp/results/applies_to_v2`.
- fmri-defaults-kb at `12a82e3`; GROBID 0.9.1-crf on all four papers; under `caffeinate -i`;
  metered.
- The Stage 2 records (`applies_to_v1`, at `4786707`) are the comparison.

## Per paper

| paper | status | calls | retries | cost | time (s) | fields with a part | header (Stage 2b) |
|---|---|---|---|---|---|---|---|
| chen_2015 | success | 9 | 0 | $0.7071 | 202.5 | 6 (Stage 2: 0) | see below |
| gracia-tabuenca_2024 | success | 9 | 0 | $0.6401 | 760.9 | 0 (Stage 2: 0) | none |
| power_2014 | success | 9 | 0 | $0.7408 | 196.5 | 2 (Stage 2: 3) | see below |
| ciric_2017 | success | 17 | 1 | $1.1738 | 400.3 | 24 (Stage 2: 19) | see below |
| **total** | 4 of 4 | 44 | 1 | **$3.2618** | 1560.2 | | |

Header lines, verbatim:
- chen_2015: `> Values differ by: ReHo, global connectome metrics (DCw, ECw), SFC, ALFF and fALFF, global connectome (DCw and ECw) (temporal_filtering.performed, spatial_smoothing.performed, spatial_smoothing.fwhm_mm, spatial_smoothing.space, spatial_smoothing.kernel_type, spatial_smoothing.approach)`
- power_2014: `> Values differ by: historical lab practice, 24 motion-related regressors, 36 motion-related regressors (nuisance_regression.regressor_list, nuisance_regression.motion_expansion)`
- ciric_2017: `> Values differ by: Model 1, Model 2, Model 3, Model 4, Model 5, Model 6, Model 7, Model 8, Model 9, Model 10, Model 11, Model 12, Model 13, Model 14, all regressors, ICA-AROMA (models 13 and 14), models 1-12 (nuisance_regression.regressor_list, nuisance_regression.motion_expansion, nuisance_regression.tissue_regressors, nuisance_regression.tissue_signal_definition, temporal_filtering.relative_to_regression, temporal_filtering.applied_to, ica_denoise.performed, ica_denoise.method, compcor.performed, compcor.variant, compcor.n_components, compcor.mask_source, despike.performed, despike.method, scrub.performed, scrub.method, scrub.criterion, scrub.threshold, scrub.remediation, scrub.interpolation_method, spatial_smoothing.performed, spatial_smoothing.fwhm_mm, spatial_smoothing.kernel_type, spatial_smoothing.approach)`

Values returned per field with a part (dropped = the value or quote failed; unverified = the part's
words were found nowhere in the methods text):

| paper | field | returned | dropped | kept unverified |
|---|---|---|---|---|
| chen_2015 | temporal_filtering.performed | 3 | 0 | 0 |
| chen_2015 | spatial_smoothing.performed | 3 | 0 | 0 |
| chen_2015 | spatial_smoothing.fwhm_mm / space / kernel_type / approach | 1 each | 0 | 0 |
| power_2014 | nuisance_regression.regressor_list | 3 | 0 | 1 |
| power_2014 | nuisance_regression.motion_expansion | 3 | 0 | 1 |
| ciric_2017 | nuisance_regression.regressor_list | 14 | 0 | 0 |
| ciric_2017 | nuisance_regression.motion_expansion | 14 | 4 | 0 |
| ciric_2017 | nuisance_regression.tissue_regressors | 11 | 0 | 0 |
| ciric_2017 | nuisance_regression.tissue_signal_definition | 13 | 0 | 0 |
| ciric_2017 | temporal_filtering.relative_to_regression | 14 | 0 | 0 |
| ciric_2017 | temporal_filtering.applied_to | 1 | 0 | 0 |
| ciric_2017 | ica_denoise / compcor / despike / scrub .performed | 14 each | 0 | 0 |
| ciric_2017 | ica_denoise.method, compcor.variant / n_components / mask_source, despike.method, scrub.method / criterion / threshold / remediation | 2 each | 0 | 0 |
| ciric_2017 | scrub.interpolation_method | 1 | 0 | 0 |
| ciric_2017 | spatial_smoothing.performed | 2 | 0 | 1 |
| ciric_2017 | spatial_smoothing.fwhm_mm / kernel_type / approach | 1 each | 0 | 0 |

Kept unverified:
- Stage 2b: 3 values over the four papers.
- Stage 2, same four papers: 20 (chen 0, ciric 17, power 3, gracia-tabuenca 0); the other 30 of
  Stage 2's 50 were in tang_2025, silchenko_2023, greene_2022 and glasser2016_nature, not re-run.

No compared-models entry appeared. power_2014's parts are now named regressor sets
("historical lab practice", "24 motion-related regressors", "36 motion-related regressors").

## Smoothing and filtering against the label rows (with the classes)

Scored by `scripts/score_smoothing_filtering.py` on `ground_truth/smoothing_filtering_labels_v1.xlsx`.

Per label variant:

| sheet | paper | label variant | label state | Stage 1 (coverage_v4) | Stage 2 (applies_to_v1) | Stage 2b (applies_to_v2) |
|---|---|---|---|---|---|---|
| Smoothing | chen_2015 | ALFF and fALFF | reported | collapsed | collapsed | matched correct (values agree) |
| Smoothing | chen_2015 | ReHo and surface-based graphs | stated_not_performed | collapsed | collapsed | matched correct |
| Smoothing | ciric_2017 | ICA-AROMA models (input) | reported | collapsed | collapsed | matched correct (values agree) |
| Smoothing | ciric_2017 | other compared models | not_reported | collapsed | collapsed | missed |
| Smoothing | power_2014 | all (Parts I–III) | reported | reported, agree | reported, agree | reported, agree |
| Filtering | chen_2015 | ReHo and surface-based graphs | reported | collapsed | collapsed | missed |
| Filtering | chen_2015 | ALFF and fALFF | not_reported | collapsed | collapsed | missed |
| Filtering | ciric_2017 | all | partially_reported | reported (state disagrees) | reported (state disagrees) | split |
| Filtering | power_2014 | Parts I–II | reported | collapsed | collapsed | missed |
| Filtering | power_2014 | Part III | reported | collapsed | collapsed | missed |

Field level, Stage 2b:

| sheet | paper | outcome | matched correct | matched wrong | missed | spurious |
|---|---|---|---|---|---|---|
| Smoothing | chen_2015 | wrong | 2 | 0 | 0 | 1 |
| Smoothing | ciric_2017 | wrong | 1 | 0 | 1 | 1 |
| Filtering | chen_2015 | wrong | 0 | 0 | 2 | 3 |
| Filtering | ciric_2017 | split | 0 | 0 | 0 | 0 |
| Filtering | power_2014 | wrong | 0 | 0 | 2 | 1 |

Totals, Stage 2b, these four papers:
- label variants: 3 matched correct, 0 matched wrong, 5 missed;
- record parts: 5 spurious;
- collapsed: 0 (Stage 2: 8); split: 1 field.

What the Filtering rows record:
- **chen_2015.** The record's "ReHo" part has the band the label has (0.01–0.1 Hz, band-pass), from
  the label's own sentence.
  - The label quote begins with "…", so the overlap test does not match the two sentences, and
    under E2 the row is missed and the part spurious.
  - The ALFF/fALFF row carries no quote (not_reported), so no part can overlap it.
  - The record's other two parts, "global connectome metrics (DCw, ECw)" and "SFC", have no label
    row.
- **power_2014.** No parts on filtering. Every filtering field is "value present in source but span
  unresolved" in this draw (Stage 2: one band for all, collapsed).
- **ciric_2017.** `relative_to_regression` has one part per model, against a single "all" row.

## chen_2015's smoothing and filtering lines (`chen_2015.md`)

```
- performed: differs by what it applies to
    - ALFF and fALFF: performed   [from paper]  «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»   [check: supported]
    - ReHo: not performed   [from paper]  «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»   [check: supported]
    - global connectome (DCw and ECw): not performed   [from paper]  «This surface-based computation constructed weighted graphs for individual brain…»   [check: supported]
- method: not reported in source — you must specify   [check: supported]
- fwhm_mm: differs by what it applies to
    - ALFF and fALFF: 6.0   [from paper]  «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»   [check: supported]
    - ReHo: not performed   (the step is stated as not performed for this part)  «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»
    - global connectome (DCw and ECw): not performed   (the step is stated as not performed for this part)  «This surface-based computation constructed weighted graphs for individual brain…»
- space: differs by what it applies to
    - ⚑ ALFF and fALFF: native_surface   [from paper]  «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»   — checking pass: WRONG — The sentence does not state the space in which smoothing was performed.; should be: not reported «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»
    - ReHo: not performed   (the step is stated as not performed for this part)  «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»
    - global connectome (DCw and ECw): not performed   (the step is stated as not performed for this part)  «This surface-based computation constructed weighted graphs for individual brain…»
- kernel_type: differs by what it applies to
    - ALFF and fALFF: gaussian   [from paper]  «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»   [check: supported]
    - ReHo: not performed   (the step is stated as not performed for this part)  «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»
    - global connectome (DCw and ECw): not performed   (the step is stated as not performed for this part)  «This surface-based computation constructed weighted graphs for individual brain…»
- approach: differs by what it applies to
    - ALFF and fALFF: fixed_kernel   [from paper]  «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»   [check: supported]
    - ReHo: not performed   (the step is stated as not performed for this part)  «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»
    - global connectome (DCw and ECw): not performed   (the step is stated as not performed for this part)  «This surface-based computation constructed weighted graphs for individual brain…»
```

```
- performed: differs by what it applies to
    - ReHo: performed   [from paper]  «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»   [check: supported]
    - global connectome metrics (DCw, ECw): performed   [from paper]  «This surface-based computation constructed weighted graphs for individual brain…»   [check: supported]
    - SFC: performed   [from paper]  «Of note, this surface-based SFC was estimated using the same preprocessed rfMRI…»   [check: supported]
- filter_type: not reported in source — you must specify   [check: supported]
- pass_type = band_pass   [from paper]  «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»   [check: supported]
- ⚑ relative_to_regression = before   [from paper]  «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»   — checking pass: WRONG — The sentence describes filtering for ReHo computation, not the order relative to nuisance regression in the preprocessing pipeline.; should be: not reported «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»
- applied_to: not reported in source — you must specify   — checking pass: MISSED — the paper states: ReHo, SFC, global connectome metrics (DCw, ECw) «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»
- effective_band_hz = 0.01–0.1 Hz   [from paper]  «ALFF measures the strength or intensity of the low-frequency O = [0.01,0.1] (Hz…»   [check: supported]
- order: not reported in source — you must specify   [check: supported]
```

The same part is spelled two ways: "global connectome (DCw and ECw)" in smoothing and "global
connectome metrics (DCw, ECw)" in filtering. The same-string normalisation does not join them, so
the header lists both.

## ciric_2017: no compact table

The table needs more than four parts that differ ONLY on confound fields.
- ciric_2017 has 17 parts: Model 1 to Model 14, "all regressors", "ICA-AROMA (models 13 and 14)" and
  "models 1-12".
- Its differing fields include `spatial_smoothing` (performed, fwhm_mm, kernel_type, approach) and
  `temporal_filtering` (relative_to_regression, applied_to), which are not confound fields.
- So the pseudo-code is one block per part (17 blocks), with the note:

```
# note: values differ by what they apply to; one block per part, a field stated for all data appears in every block
```

The smoothing lines that stopped it (`ciric_2017.md`):

```
- performed: differs by what it applies to
    - ICA-AROMA (models 13 and 14): performed   [from paper]  «The input to ICA-AROMA is a voxelwise time series that has been smoothed at 6mm…»   [check: supported]
    - ⚑ models 1-12: not performed   [from paper]  «The input to ICA-AROMA is a voxelwise time series that has been smoothed at 6mm…»   (what it applies to was not found in the text, unverified)   — checking pass: WRONG — The sentence only states smoothing for ICA-AROMA input; it does not state smoothing was not performed for models 1-12.; should be: not reported «The input to ICA-AROMA is a voxelwise time series that has been smoothed at 6mm…»
- method: the extractor returned values for parts of the data and none of their quotes checked — check the source yourself   [check: supported]
- fwhm_mm: differs by what it applies to
    - ICA-AROMA (models 13 and 14): 6.0   [from paper]  «The input to ICA-AROMA is a voxelwise time series that has been smoothed at 6mm…»   [check: supported]
    - models 1-12: not performed   (the step is stated as not performed for this part)  «The input to ICA-AROMA is a voxelwise time series that has been smoothed at 6mm…»
- space: not reported in source — you must specify   [check: supported]
- kernel_type: differs by what it applies to
    - ICA-AROMA (models 13 and 14): gaussian   [from paper]  «The input to ICA-AROMA is a voxelwise time series that has been smoothed at 6mm…»   [check: supported]
    - models 1-12: not performed   (the step is stated as not performed for this part)  «The input to ICA-AROMA is a voxelwise time series that has been smoothed at 6mm…»
- approach: differs by what it applies to
    - ICA-AROMA (models 13 and 14): fixed_kernel   [from paper]  «The input to ICA-AROMA is a voxelwise time series that has been smoothed at 6mm…»   [check: supported]
    - models 1-12: not performed   (the step is stated as not performed for this part)  «The input to ICA-AROMA is a voxelwise time series that has been smoothed at 6mm…»
```

The table form exists and is tested (`tests/test_applies_to.py`). It rendered on the Stage 2 record
of ciric_2017, whose 14 parts differed only on confound fields, but that record is not this run's.

# applies_to Stage 2: the variant papers re-run (2026-11-11)

**Run**
- Nine papers, `aespa-report` with default settings, into `extractor_mvp/results/applies_to_v1`.
- Worktree pinned at `4786707`; imports confirmed from the worktree. fmri-defaults-kb at `12a82e3`.
- GROBID 0.9.1-crf text layer on all eight papers that reached text extraction; no fallback.
- Run under `caffeinate -i`, metered.
- tang_2025 is held out (prereg C11/C26): counts and classes only.

## 3. Per paper

Time is wall time.

| paper | status | calls | retries | parse errors | cost | time (s) | fields with a part | step-order parts |
|---|---|---|---|---|---|---|---|---|
| chen_2015 | success | 9 | 0 | 0 | $0.6871 | 193.3 | 0 | 0 |
| ciric_2017 | success | 17 | 1 | 0 | $1.0997 | 376.0 | 19 | 0 |
| power_2014 | success | 9 | 0 | 0 | $0.6739 | 163.0 | 3 | 0 |
| tang_2025 | success | 10 | 0 | 0 | $0.6094 | 154.0 | 5 | 2 |
| gracia-tabuenca_2024 | success | 9 | 0 | 0 | $0.6059 | 146.1 | 0 | 0 |
| silchenko_2023 | methods_not_found | 11 | 0 | 0 | $0.8372 | 204.3 | 2 | 0 |
| greene_2022 | success | 35 | 4 | 1 | $1.1213 | 284.5 | 9 | 0 |
| glasser2016_nature | success | 12 | 0 | 0 | $1.2184 | 235.4 | 1 | 1 |
| yang_2025 | extraction_failed | 6 | 1 | 2 | $0.4954 | 79.4 | — | — |
| **total** | 8 reports | 118 | 6 | 3 | **$7.3483** | 1836.0 | 39 | 3 |

yang_2025 failed in the main extraction call. All three attempts returned `base_pipeline_ref` as
`extracted` with value "(67)" and no quote, and the validator rejected each. No report was written.
The paper was not re-run.

Values per field with a part:
- returned = what the model gave;
- dropped = removed by the value or quote check;
- unverified = kept, but the part's words were not found in its sentences.

No value was dropped by the `applies_to` check: it keeps the value and marks it unverified.

| paper | field | returned | dropped | kept unverified |
|---|---|---|---|---|
| ciric_2017 | nuisance_regression.performed | 13 | 0 | 0 |
| ciric_2017 | nuisance_regression.regressor_list | 13 | 0 | 0 |
| ciric_2017 | nuisance_regression.motion_expansion | 11 | 0 | 0 |
| ciric_2017 | nuisance_regression.tissue_regressors | 11 | 0 | 0 |
| ciric_2017 | nuisance_regression.tissue_signal_definition | 11 | 0 | 8 |
| ciric_2017 | ica_denoise.performed | 2 | 0 | 0 |
| ciric_2017 | ica_denoise.method | 2 | 0 | 0 |
| ciric_2017 | compcor.performed | 2 | 0 | 0 |
| ciric_2017 | compcor.variant | 2 | 0 | 0 |
| ciric_2017 | compcor.n_components | 2 | 0 | 1 |
| ciric_2017 | compcor.mask_source | 2 | 0 | 2 |
| ciric_2017 | despike.performed | 2 | 0 | 0 |
| ciric_2017 | despike.method | 2 | 0 | 0 |
| ciric_2017 | scrub.performed | 2 | 0 | 0 |
| ciric_2017 | scrub.method | 2 | 0 | 0 |
| ciric_2017 | scrub.criterion | 2 | 0 | 2 |
| ciric_2017 | scrub.threshold | 2 | 0 | 2 |
| ciric_2017 | scrub.remediation | 2 | 0 | 1 |
| ciric_2017 | scrub.interpolation_method | 1 | 0 | 1 |
| power_2014 | nuisance_regression.regressor_list | 1 | 0 | 1 |
| power_2014 | nuisance_regression.motion_expansion | 1 | 0 | 1 |
| power_2014 | nuisance_regression.tissue_regressors | 1 | 0 | 1 |
| tang_2025 | 5 fields (counts only) | 2, 2, 2, 2, 2 | 0, 0, 0, 0, 0 | 0, 2, 2, 2, 0 |
| tang_2025 | 2 step-order parts | 1, 1 | 0, 0 | 1, 1 |
| silchenko_2023 | nuisance_regression.regressor_list | 3 | 0 | 3 |
| silchenko_2023 | nuisance_regression.tissue_regressors | 3 | 0 | 3 |
| greene_2022 | spatial_normalization.target_space | 3 | 0 | 3 |
| greene_2022 | nuisance_regression.performed | 3 | 1 | 2 |
| greene_2022 | nuisance_regression.regressor_list | 2 | 1 | 1 |
| greene_2022 | nuisance_regression.motion_expansion | 2 | 1 | 1 |
| greene_2022 | nuisance_regression.tissue_regressors | 2 | 1 | 1 |
| greene_2022 | nuisance_regression.tissue_signal_definition | 2 | 1 | 1 |
| greene_2022 | nuisance_regression.detrend | 2 | 1 | 1 |
| greene_2022 | temporal_filtering.filter_type | 3 | 1 | 2 |
| greene_2022 | temporal_filtering.pass_type | 3 | 1 | 2 |
| glasser2016_nature | temporal_filtering.performed | 2 | 0 | 1 |
| glasser2016_nature | step_order part | 1 | 0 | 1 |

"Values differ by:" header lines, verbatim:
- chen_2015: none.
- ciric_2017: `> Values differ by: Model 1, Model 2, Model 3, Model 4, Model 5, Model 6, Model 7, Model 8, Model 9, Model 11, Model 12, Model 13, Model 14, Model 10 (nuisance_regression.performed, nuisance_regression.regressor_list, nuisance_regression.motion_expansion, nuisance_regression.tissue_regressors, nuisance_regression.tissue_signal_definition, ica_denoise.performed, ica_denoise.method, compcor.performed, compcor.variant, compcor.n_components, compcor.mask_source, despike.performed, despike.method, scrub.performed, scrub.method, scrub.criterion, scrub.threshold, scrub.remediation, scrub.interpolation_method)`
- power_2014: `> Values differ by: varied across compared models (nuisance_regression.regressor_list, nuisance_regression.motion_expansion, nuisance_regression.tissue_regressors)`
- tang_2025: present; 2 parts, 6 fields (withheld).
- gracia-tabuenca_2024: none.
- silchenko_2023: `> Values differ by: WM-CSF-95%INDV, WM-CSF-50%TPM, GM-WM-CSF-70%TPM (nuisance_regression.regressor_list, nuisance_regression.tissue_regressors)`
- greene_2022: `> Values differ by: Yale dataset, CNP dataset, HCP dataset (spatial_normalization.target_space, nuisance_regression.performed, nuisance_regression.regressor_list, nuisance_regression.motion_expansion, nuisance_regression.tissue_regressors, nuisance_regression.tissue_signal_definition, nuisance_regression.detrend, temporal_filtering.filter_type, temporal_filtering.pass_type)`
- glasser2016_nature: `> Values differ by: resting state fMRI, task fMRI, functional preprocessing (temporal_filtering.performed, step order)`
- yang_2025: no report.

No new report carries the old "More than one preprocessing variant" line.

## 1. Smoothing and filtering against the label rows

Scored by `scripts/score_smoothing_filtering.py` on `ground_truth/smoothing_filtering_labels_v1.xlsx`.
The Stage 1 baseline is the same scorer on `batch_coverage_v4`. tang_2025's parts are given by row
order only.

Per label variant:

| sheet | paper | label variant | label state | coverage_v4 (Stage 1) | applies_to_v1 (Stage 2) |
|---|---|---|---|---|---|
| Smoothing | chen_2015 | ALFF and fALFF | reported | collapsed | collapsed |
| Smoothing | chen_2015 | ReHo and surface-based graphs | stated_not_performed | collapsed | collapsed |
| Smoothing | ciric_2017 | ICA-AROMA models (input) | reported | collapsed | collapsed |
| Smoothing | ciric_2017 | other compared models | not_reported | collapsed | collapsed |
| Smoothing | power_2014 | all (Parts I–III) | reported | reported, values agree | reported, values agree |
| Smoothing | tang_2025 | row 1 | reported | no record | matched correct |
| Smoothing | tang_2025 | row 2 | not_reported | no record | missed |
| Filtering | chen_2015 | ReHo and surface-based graphs | reported | collapsed | collapsed |
| Filtering | chen_2015 | ALFF and fALFF | not_reported | collapsed | collapsed |
| Filtering | ciric_2017 | all | partially_reported | reported (state disagrees) | reported (state disagrees) |
| Filtering | power_2014 | Parts I–II | reported | collapsed | collapsed |
| Filtering | power_2014 | Part III | reported | collapsed | collapsed |
| Filtering | tang_2025 | row 1 | reported | no record | matched correct |
| Filtering | tang_2025 | row 2 | reported | no record | matched correct |

Field level:

| sheet | paper | coverage_v4 | applies_to_v1 | matched correct | matched wrong | missed | spurious |
|---|---|---|---|---|---|---|---|
| Smoothing | chen_2015 | collapsed | collapsed | 0 | 0 | 0 | 0 |
| Smoothing | ciric_2017 | collapsed | collapsed | 0 | 0 | 0 | 0 |
| Smoothing | tang_2025 | no record | wrong | 1 | 0 | 1 | 1 |
| Filtering | chen_2015 | collapsed | collapsed | 0 | 0 | 0 | 0 |
| Filtering | power_2014 | collapsed | collapsed | 0 | 0 | 0 | 0 |
| Filtering | tang_2025 | no record | correct | 2 | 0 | 0 | 0 |

Totals, Stage 2:
- label variants: 3 matched correct, 0 matched wrong, 1 missed;
- record parts: 1 spurious;
- collapsed: 8 label variants over 4 fields; split: 0.

## 2. The lines

### chen_2015

No field has a part. Report lines (`chen_2015.md`), spatial smoothing and temporal filtering:

```
- ⚑ performed = True   [from paper]  «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»   — checking pass: WRONG — The sentence describes smoothing for ALFF/fALFF computation (analysis), not preprocessing of the BOLD data itself.; should be: not reported «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»
- ⚑ fwhm_mm = 6.0   [from paper]  «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»   — checking pass: WRONG — The sentence describes smoothing for ALFF/fALFF computation (analysis), not preprocessing of the BOLD data itself.; should be: not reported «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»
- ⚑ kernel_type = gaussian   [from paper]  «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»   — checking pass: WRONG — The sentence describes smoothing for ALFF/fALFF computation (analysis), not preprocessing of the BOLD data itself.; should be: not reported «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»
- ⚑ performed = True   [from paper]  «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»   — checking pass: WRONG — The sentence describes filtering for ReHo computation (analysis), not preprocessing of the BOLD data itself.; should be: not reported «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»
- ⚑ effective_band_hz = 0.01–0.1 Hz   [from paper]  «ALFF measures the strength or intensity of the low-frequency O = [0.01,0.1] (Hz…»   — checking pass: WRONG — The sentence describes the frequency band for ALFF computation (analysis), not preprocessing filtering of the BOLD data.; should be: not reported «ALFF measures the strength or intensity of the low-frequency O = [0.01,0.1] (Hz…»
```

Pseudo-code (`chen_2015.preproc.txt`), one block:

```
temporal_filtering(filter_type=? [?], pass_type="band_pass" [E], relative_to_regression="before" [E], applied_to=? [?], effective_band_hz=[0.01, 0.1] [E], order=? [?])  # «This surface-based ReHo was derived from the non-smoothed but temporally band-p…»
spatial_smoothing(method=? [?], fwhm_mm=6 [E], space="native_surface" [E], kernel_type="gaussian" [E], approach="fixed_kernel" [E])  # «Both ALFF and fALFF were derived from spatially smoothed rfMRI data (6 mm full-…»
```

### power_2014

There are no step-order parts; step order is `partial`.

Variant lines (`power_2014.md`):

```
- regressor_list: differs by what it applies to
    - ⚑ varied across compared models: varied across compared models   [from paper]  «Various combinations of nuisance regressors were used in the multiple regressio…»   (what it applies to was not found in the text, unverified)   — checking pass: WRONG — The paper states regressors varied but does not tie this to a named part; this should be a non-bracketed field with value describing the variation.; should be: not reported «Various combinations of nuisance regressors were used in the multiple regressio…»
- motion_expansion: differs by what it applies to
    - ⚑ varied across compared models: "varied across compared models"   [from paper]  «Various combinations of nuisance regressors were used in the multiple regressio…»   (what it applies to was not found in the text, unverified)   — checking pass: WRONG — The paper states motion expansions varied but does not tie this to a named part; this should be a non-bracketed field.; should be: not reported «Various combinations of nuisance regressors were used in the multiple regressio…»
- tissue_regressors: differs by what it applies to
    - ⚑ varied across compared models: "varied across compared models"   [from paper]  «Various combinations of nuisance regressors were used in the multiple regressio…»   (what it applies to was not found in the text, unverified)   — checking pass: WRONG — The paper states tissue regressors varied but does not tie this to a named part; this should be a non-bracketed field.; should be: not reported «Various combinations of nuisance regressors were used in the multiple regressio…»
```

These three entries carry the C2 phrase as their value, not a null value. The code reads an entry as
C2 only when its value is null, so they were processed as ordinary variants. That is why the value
repeats the phrase and the part is marked unverified.

Pseudo-code (`power_2014.preproc.txt`). One block: a compared-models entry is not a part.

```
nuisance_regression(regressor_list=varies(varied across compared models: "varied across compared models") [E], motion_expansion=varies(varied across compared models: "varied across compared models") [E], tissue_regressors=varies(varied across compared models: "varied across compared models") [E], tissue_definition="eroded ventricular mask for the CSF signal, eroded white matter mask for the white matter signal, and the whole-brain mask for the global signal" [E], tissue_signal_definition="average signal across voxels within a particular spatial mask" [E], physio_regressors="none" [E], physio_n_regressors=? [?], detrend="linear" [E], method=? [?], filtering_integrated=False [E])  # «Various combinations of nuisance regressors were used in the multiple regressio…»
```

### ciric_2017

The confound fields do not read "varied across compared models" (C2). They hold one variant per
model:
- nuisance regression: 13 or 11 variants per field;
- `ica_denoise`, `compcor`, `despike`, `scrub`: 2 each.

The header names Model 1 to Model 14, and the pseudo-code has 14 blocks (`# --- applies to: Model 1` …).

```
- regressor_list: differs by what it applies to
    - Model 1: 2 physiological time series: mean signal in WM and mean signal in CSF   [from paper]  «Model 1. (2P) Used only the 2 physiological time series: mean signal in WM and…»   [check: supported]
    - Model 2: 6 motion estimates derived from MCFLIRT realignment   [from paper]  «Model 2. (6P) Used only the 6 motion estimates derived from MCFLIRT realignment…»   [check: supported]
    - Model 3: 6 motion estimates and 2 physiological time series with global signal regression   [from paper]  «Model 3. (9P) Combined the 6 motion estimates and 2 physiological time series w…»   [check: supported]
```

Fields that stay "all" (EXTRACTED), by step:

| step | "all" | with parts |
|---|---|---|
| distortion_correction | performed, source, method, tool | — |
| nonsteadystate_removal | performed, n_nonsteadystate_discarded | — |
| motion_correction | method | — |
| slice_time_correction | performed | — |
| coregistration | performed, cost_function | — |
| brain_extraction | performed, method, parameters | — |
| segmentation | performed, method, tissue_classes | — |
| intensity_correction | performed, target | — |
| temporal_filtering | performed, filter_type, pass_type, relative_to_regression, effective_band_hz, order | — |
| spatial_smoothing | performed, fwhm_mm, kernel_type, approach | — |
| nuisance_regression | tissue_definition, physio_regressors, detrend, filtering_integrated | performed, regressor_list, motion_expansion, tissue_regressors, tissue_signal_definition |
| ica_denoise | — | performed, method |
| compcor | — | performed, variant, n_components, mask_source |
| despike | — | performed, method |
| scrub | — | performed, method, criterion, threshold, remediation, interpolation_method |

## Addendum (2026-11-11, later): yang_2025 re-run

Re-run at the author's instruction, from the same worktree pinned at `4786707`, into
`extractor_mvp/results/applies_to_v1_yang_rerun`. The failed attempt is kept in `applies_to_v1`.

| paper | status | calls | retries | parse errors | cost | time (s) | fields with a part | step-order parts |
|---|---|---|---|---|---|---|---|---|
| yang_2025 | success | 8 | 0 | 0 | $0.5723 | 119.7 | 0 | 0 |

Header line: none. Stage 2 total with the re-run: $7.9206 over 126 calls; 9 of 9 papers have a report.

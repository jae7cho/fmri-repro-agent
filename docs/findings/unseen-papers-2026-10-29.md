# Two papers the tool has never seen — aespa-report read against the methods text (2026-10-29)

**The input-a-paper, get-output check the author asked for.** Two recent-enough fMRI papers outside
the 19-paper corpus, supplied by the author: Gracia-Tabuenca et al. 2024 (ABCD data, task and rest)
and Shen et al. 2013 (the Shen 268 parcellation; Yale resting-state data). Each was run once through
`aespa-report` at HEAD `69a6152` plus the staged 2026-10-29 fixes (the five prompt hashes as
coverage_v2), model `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, four model calls per
paper, 56 s and 54 s. The reports are under `extractor_mvp/results/unseen_2026-10-29/` (gitignored).
Both methods sections were found by header (`2. Methods`, `3. Material and Methods`), not suspicious.
Each report was then read line by line against the paper's own preprocessing paragraph.

**Not an evaluation.** Two papers, one draw each, no labels; what follows is a list of what is wrong
or misleading in two reports, ranked by what it would cost a reader trying to replicate.

## What the reports get right

Both: the censoring line (Gracia-Tabuenca: FD above 0.9 mm, censored), the smoothing line (Shen:
6 mm Gaussian), the stated detrend order, initial-volume removal with the count correctly left
unstated, the tissue regressors and their signal definition (Shen), the deferral of the base
pipeline to Hagler et al. (2019) (Gracia-Tabuenca), and every "not reported" row I checked is in
fact silent in the text. The value-support check refused one guess it should refuse: Shen's
slice-timing order relative to motion correction, which the paper does not state.

## What is wrong, ranked

1. **Temporal filtering is invisible.** Both papers state a band-pass (Gracia-Tabuenca's rest-fMRI
   0.009–0.08 Hz and its motion-covariate filter; Shen's Butterworth 0.02–0.1 Hz). Neither report
   records it anywhere: `temporal_filtering` has no D.3 row, so it was never emitted or asked
   (DESIGN_coverage_expansion.md B6). For a resting-state replication this is the most consequential
   omission in both reports. The spec has the class; the coverage calls do not ask it.
2. **The step order is the template's, labelled as the paper's.** The section header reads
   "Preprocessing steps (pipeline order)", but `_assemble` emits a fixed catalog order. Shen's paper
   orders regression, then band-pass, then smoothing, then linear detrend "from all signals"; the
   report shows smoothing after regression and detrend inside regression. Order is reproducibility-
   critical (the catalog's own note on nuisance/filter order) and the header misstates it.
3. **The wrong subject's sentence fills a functional field.** Gracia-Tabuenca's report takes the
   *structural* MRI sentence for three functional rows: intersubject registration ("isotropic
   standard space" — the sMRI registration), distortion correction (source `gradient_nonlinearity`
   from the sMRI sentence, while the fMRI sentence states susceptibility AND gradient-nonlinearity
   correction; one Literal cannot hold both), and motion's neighbours. The motion stanza has a
   SUBJECT gate (functional-to-functional); the shared and coverage prompts do not.
4. **Analysis-stage regressors read as preprocessing.** Gracia-Tabuenca's nuisance regression row is
   filled from the *task first-level GLM* covariates (baseline, quadratic trends, motion estimates and
   derivatives) — COBIDAS D.4, not D.3 — while the rest-fMRI "regression" step it actually lists is
   left unspecified. Detrend = quadratic comes from the same GLM sentence.
5. **The `performed` phrase table misses a plain regression verb.** Shen regresses by
   *orthogonalizing* the gray-matter time courses against WM, CSF and six motion signals; the report's
   nuisance `performed`, `regressor_list` and `motion_expansion` all render unverifiable ("a value was
   returned but the quoted sentence does not state it"). "orthogonalized" is not in the frozen table;
   "six motion-related signals" matches no 6param alias. The row still reads reported only through
   the tissue regressors.
6. **The Software row ignores named, versioned software.** Gracia-Tabuenca names FreeSurfer v5.3;
   the report says "Version not reported; pipeline identity deferred to Hagler et al. (2019)" — the
   row reads only `base_pipeline`. D.3 asks for every software used. Shen names SPM5 (a fused version)
   and BioImage Suite (no version); the registration tool appears nowhere in the report
   (`spatial_normalization.method` is untargeted).
7. **Two over-resolutions.** "FD" alone resolves to `fd_power` (Gracia-Tabuenca does not say which
   FD); Shen's tissue masks "created in the common space" fill `segmentation` as performed with three
   tissue classes, though nothing says a structural image was segmented — an atlas mask is not D.3's
   segmentation.
8. **Task and rest preprocessing differ and the multi-pipeline header did not fire** on
   Gracia-Tabuenca (rest adds initial-volume removal, normalization, regression and filtering); on
   ciric's re-draw the same header fired with count 14 for denoising models. The question as worded
   does not separate "variants compared" from "per-modality branches".

## Where the next build should start (proposals, not decisions)

- Ask temporal filtering (band edges, filter type, order relative to regression) in the temporal
  call, rendered outside the D.3 rows as a divergence row it already is in the spec.
- Either record the paper's step order (a sequence field per step, from the sentence order) or
  rename the header to say the order is the template's.
- Give the shared and coverage prompts the motion stanza's subject gate: functional data only, a
  structural sentence never fills a functional field; let `distortion_correction.source` hold more
  than one source.
- Exclude first-level GLM covariates from `nuisance_regression` (a D.4 gate in the prompt).
- Widen the Software row to every named software with its stated version.
- The frozen phrase table and the motion-expansion aliases need "orthogonaliz*" and "six motion
  (-related) signals"; a frozen table changes only with a dated note.

Held for the author: which of these is the next build.

# coverage_v4: the scope rule restated and the checking pass's `unplaced` list (2026-11-02)

**What was asked (the author, 2026-11-02).**
1. Restate the scope rule in both coverage prompts and the software list. Structural steps that
   feed the fMRI analysis are in: brain extraction, segmentation used for masks or regressors,
   bias-field correction, and the structural target of registration. Structural-only analyses
   (morphometry, diffusion, tractography) and first-level covariates are out. The rule cites D.3's
   "For structural images".
2. Give the checking pass an `unplaced` list: preprocessing statements no field captured, each with
   its quote-checked sentence and its D.3 row or "no row". It is rendered as its own section and
   never changes a field.
3. Run coverage_v4 on the 16 contaminated papers and the two unseen ones. Report the per-row table
   beside coverage_v3, the author's key against v4 field by field, whether `unplaced` lists three
   named statements, and the wall time.
4. Check that `tested_lit/sfn_batch/Hagler_2019.pdf` exists.

## The build (`a3908c3`)

- **Scope rule.** `coverage_extractor.py` `_SHARED_RULES` now carries the restated paragraph, which
  quotes D.3's Segmentation row ("For structural images, method used to extract gray, white, CSF and
  other tissue classes"). A structural sentence fills only its own step's fields, never a field
  about the functional series itself. The software list now names software for any in-scope step.
- **The checking pass follows the same rule.** This is Claude's call, not in the order: left on the
  old rule, the checking pass would mark every in-scope structural field wrong. Its scope paragraph
  and its software question are restated to match.
- **`unplaced`.** `verifier.py` adds `UnplacedStatement`. Each item's sentence goes through
  `resolve_quote`. A row outside the D.3 ids is kept as `row_raw` and placed as "no row".
  `render._unplaced_section` emits the section between the steps and the coverage, and only when the
  record carries the list, so older records render unchanged.
- **Hashes, with dated notes in `tests/test_prompt_pin.py`:**

| prompt | before | after |
|---|---|---|
| TEMPORAL_VOLUME_PROMPT | `58328046…` | `a9230438…` |
| SPATIAL_PROMPT | `3c8d604b…` (never drawn) | `8b54be37…` |
| VERIFIER_PROMPT | `42cb343c…` | `f078f100…` |

- **Tests and mutations.** The scope test was rewritten to the restated rule. Two `unplaced` tests
  were added. Four mutations were run: one on the scope clause, three on `unplaced` (row
  normalisation, the old-record guard, the unverified marker). Each diff was shown non-empty first
  and each was killed. 596 extractor tests (not live) and 235 root tests pass; hooks are clean.
- **Identity gate, derived before running.** The acceptance batch, coverage_v2 and coverage_v3 are
  identical against HEAD (19, 19, 18). The negative control `d31e8b7` gives 0 of 19.

## The run

`extractor_mvp/results/batch_coverage_v4/launcher_manifest.json`:
- run from HEAD `a3908c3`, 2026-11-02 21:25:51 to 22:10:26 UTC;
- batch exit 0, 18 of 18 records `success`;
- five calls per paper; the model, config and the other three prompt hashes as coverage_v3.

**Per-row states over the 16 contaminated papers**, each vintage with its own checking pass applied:

| row | reported | partially | performed=no | deferred | unverifiable | not reported |
|---|---|---|---|---|---|---|
| Software | 1 → 1 | 5 → 5 | 0 → 0 | 1 → 1 | 0 → 0 | 9 → 9 |
| T1 stabilization | 5 → 4 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 11 → 12 |
| Brain extraction | 4 → 3 | 0 → 0 | 0 → 0 | 2 → 3 | 0 → 2 | 10 → 8 |
| Segmentation | 6 → 9 | 0 → 0 | 0 → 0 | 1 → 2 | 0 → 0 | 9 → 5 |
| Slice time correction | 5 → 5 | 0 → 0 | 2 → 2 | 0 → 0 | 0 → 0 | 9 → 9 |
| Motion correction | 12 → 12 | 0 → 0 | 0 → 0 | 4 → 4 | 0 → 0 | 0 → 0 |
| Gradient distortion correction | 3 → 2 | 0 → 0 | 0 → 0 | 1 → 2 | 0 → 1 | 12 → 11 |
| Distortion correction | 3 → 2 | 0 → 0 | 0 → 0 | 1 → 2 | 0 → 1 | 12 → 11 |
| Coregistration | 10 → 10 | 0 → 0 | 0 → 0 | 1 → 3 | 1 → 1 | 4 → 2 |
| Intersubject registration | 13 → 13 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 3 → 3 |
| Intensity correction | 2 → 3 | 0 → 0 | 0 → 0 | 1 → 2 | 1 → 1 | 12 → 10 |
| Artifact/noise removal | 14 → 14 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 | 2 → 2 |
| Volume censoring | 4 → 4 | 0 → 0 | 1 → 1 | 0 → 0 | 0 → 1 | 11 → 10 |
| Spatial smoothing | 11 → 12 | 0 → 0 | 1 → 1 | 0 → 1 | 1 → 0 | 3 → 2 |

**Which papers moved:**
- **braun_2015:** eight rows went from not reported to deferred: brain extraction, coregistration,
  both distortion rows, intensity correction, segmentation and smoothing.
- **Segmentation:** gordon_2014, liu_2013 and mueller_2021 went from not reported to reported.
- **chen_2015:** intensity correction went from not reported to reported.
- **vanderwal_2016:** brain extraction and coregistration went to deferred; volume censoring went
  from not reported to unverifiable.
- **Toward unverifiable:** ciric_2017's brain extraction (from deferred), oconnor_2017's brain
  extraction (from reported), and poldrack_2015's two distortion rows (from reported).
- **poldrack_2015:** smoothing went from unverifiable to reported; T1 stabilization went from
  reported to not reported.

Structural steps moved toward reported or deferred, as the restated rule intends. The four moves
toward unverifiable and poldrack's T1 move are one draw each; the run does not separate the rule's
effect from draw-to-draw variation.

**The checking pass, coverage_v4.** Counts are by `verifier.effective`. `unplaced` counts how many
statements were listed and how many of their sentences resolved.

| paper | supported | wrong | missed | unverified | unplaced (resolved) | checking-pass time (s) |
|---|---|---|---|---|---|---|
| agtzidis_2020 | 79 | 3 | 0 | 0 | 0 (0) | 72.4 |
| binder_1999 | 73 | 5 | 2 | 0 | 0 (0) | 42.0 |
| braun_2015 | 79 | 0 | 0 | 0 | 3 (3) | 50.8 |
| chen_2015 | 71 | 4 | 5 | 0 | 4 (4) | 60.6 |
| ciric_2017 | 48 | 21 | 11 | 0 | 5 (5) | 87.9 |
| cole_2013 | 75 | 0 | 5 | 0 | 3 (3) | 63.1 |
| derosa_2025 | 79 | 6 | 3 | 0 | 1 (1) | 58.0 |
| gordon_2014 | 68 | 7 | 3 | 4 | 2 (2) | 98.6 |
| liu_2013 | 77 | 2 | 4 | 0 | 1 (1) | 204.6 |
| mueller_2021 | 73 | 6 | 1 | 0 | 1 (1) | 64.5 |
| oconnor_2017 | 74 | 8 | 2 | 0 | 3 (3) | 101.3 |
| poldrack_2015 | 68 | 3 | 13 | 0 | 4 (4) | 69.6 |
| power_2014 | 62 | 2 | 11 | 5 | 6 (6) | 88.9 |
| vanderwal_2016 | 77 | 5 | 1 | 0 | 0 (0) | 77.4 |
| viduarre_2017 | 75 | 2 | 3 | 0 | 5 (5) | 50.5 |
| weber_2024 | 74 | 1 | 5 | 0 | 4 (4) | 60.7 |
| **16 contaminated** | **1,152** | **75** | **69** | **9** | **42 (42)** | |
| gracia-tabuenca_2024 | 77 | 4 | 0 | 0 | 2 (2) | 63.9 |
| shen_2013 | 81 | 1 | 0 | 0 | 0 (0) | 55.0 |

These counts are unvalidated. Every `unplaced` sentence resolved.

## The author's key against coverage_v4, field by field

The key, recorded on 2026-11-02 in `coverage-v3-results.md`. Sources: each paper's
`results/batch_coverage_v4/papers/<paper>.md` and `.json`.

**gracia-tabuenca_2024**

| key | v4 report | checking pass | against the key |
|---|---|---|---|
| Software row wrong; FreeSurfer, AtlasTrack, caret are not fMRI preprocessing; defer to Hagler et al. (2019) | caret no longer listed. AtlasTrack listed, excluded. The row reads "deferred: FreeSurfer 5.3 — Cortical surface and subcortical segmentations" and counts as addressed: no Software violation in the header | FreeSurfer: preprocessing. AtlasTrack: not, plus a wrong verdict | **still wrong**: FreeSurfer 5.3 is counted |
| Intensity correction wrong (structural sentence) | still filled from the sMRI sentence (bias field, "B1-bias field estimation") | supported (was wrong in v3) | **still wrong per the key**, and now supported |
| Intersubject registration wrong (structural sentence) | still "isotropic standard space" from the sMRI sentence | supported (was wrong in v3) | **still wrong per the key**, and now supported |
| Missed: two pipelines (task FD > 0.9 mm, rest FD > 0.2 mm) | no multi-pipeline header; multiple_pipelines not stated | the FD 0.2 mm rest rule is in `unplaced`, row Volume censoring | **half**: the rest rule surfaces, the two branches do not |
| Missed: the 0.31–0.43 Hz IIR filter on motion estimates | the drafter put `temporal_filtering.filter_type = iir` from that sentence | that field marked wrong; the filter is in `unplaced`, "no D.3 row" | **surfaces**, in `unplaced` and as a flag |
| Correct: base pipeline deferral | deferred to Hagler et al. (2019) | supported | as the key |
| Correct: distortion sources | susceptibility_fieldmap, gradient_nonlinearity; method now deferred to Hagler | supported | as the key |
| Correct: motion | "corrected for motion" | supported | as the key |
| Correct: rest filtering 0.009–0.08 Hz | 0.009–0.08 Hz | supported | as the key |
| Correct: initial-volume removal | performed, count not stated | supported | as the key |
| Correct: rest regression | performed, from the rest sentence | supported | as the key, **but** see below |

- **A regression on the rest-regression row.** `motion_expansion` and `detrend` are again filled from
  the task first-level GLM sentence, which coverage_v3 had left empty. The checking pass marks both
  wrong. The restated rule still names first-level covariates as out.
- **Not in the key.** Segmentation is filled from the FreeSurfer structural sentence and now
  supported (wrong in v3). The convention reads "names the operation but no convention", the
  2026-11-02 fix working live.
- **The key and the restated rule disagree on two items.** The rule puts "bias-field correction" and
  "the structural target of registration" in scope. Under it, both the drafter and the checking pass
  now accept Gracia-Tabuenca's sMRI sentence for intensity correction and intersubject
  registration, which the key calls wrong. Whether that sMRI sentence describes a step that feeds
  the fMRI analysis is a ruling for the author.

**shen_2013**

| key | v4 report | checking pass | against the key |
|---|---|---|---|
| Correct overall, in order | order stated in full, seven steps | `step_order` wrong ("the draft lists many steps not performed"), proposing the same seven in the same order | as the key; the checking pass's objection repeats from v3 |
| Wrong: SPM5 shown as "no version" | "SPM5 (major version only)"; the base pipeline is now SPM5, version not reported (v3: no base pipeline named) | SPM5: preprocessing | **fixed** |
| Missed: six-parameter motion expansion | `motion_expansion` still unverifiable | supported; not in `unplaced` (Shen's list is empty) | **still missed** |
| Nuisance `performed` unverifiable ("orthogonalized") | performed = True | supported | **fixed** (the phrase-table change, live) |

**The three `unplaced` questions:**
- **Gracia-Tabuenca's motion filter:** listed, "no D.3 row".
- **Gracia-Tabuenca's FD 0.2 mm rest rule:** listed, row Volume censoring.
- **Shen's six motion parameters: not listed.** The list asks only for statements no draft line
  captures. Shen's sentence is already the quote of the unverifiable `motion_expansion` line, so by
  that rule it is captured.

## Wall time per paper (seconds)

| paper | v3 total | v4 total | v4 checking pass |
|---|---|---|---|
| binder_1999 | 93.5 | 93.5 | 42.0 |
| viduarre_2017 | 104.7 | 106.2 | 50.5 |
| shen_2013 | 118.6 | 111.4 | 55.0 |
| braun_2015 | 93.3 | 113.6 | 50.8 |
| cole_2013 | 142.3 | 123.2 | 63.1 |
| gracia-tabuenca_2024 | 122.2 | 123.2 | 63.9 |
| mueller_2021 | 125.8 | 125.5 | 64.5 |
| weber_2024 | 126.6 | 131.2 | 60.7 |
| agtzidis_2020 | 112.8 | 131.4 | 72.4 |
| vanderwal_2016 | 133.5 | 138.0 | 77.4 |
| derosa_2025 | 131.1 | 143.8 | 58.0 |
| chen_2015 | 158.9 | 154.3 | 60.6 |
| poldrack_2015 | 191.0 | 167.1 | 69.6 |
| oconnor_2017 | 290.8 | 172.9 | 101.3 |
| gordon_2014 | 143.1 | 181.3 | 98.6 |
| ciric_2017 | 200.9 | 185.1 | 87.9 |
| power_2014 | 177.0 | 200.2 | 88.9 |
| liu_2013 | 274.2 | 268.9 | 204.6 |
| **all 18** | **2,740.4** | **2,670.9** | |

The launcher ran 44 min 35 s.

## Hagler_2019.pdf

`/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch/Hagler_2019.pdf` exists: 3,382,421 bytes.
The path is the parent `neurorepro` folder's `tested_lit`, not the repository's. Not opened.

## Open, for the author

- **Two rulings on Gracia-Tabuenca's sMRI sentence.** Do its intensity correction and its
  registration to standard space count as structural steps that feed the fMRI analysis? The key
  says no and the restated rule reads yes.
- **FreeSurfer 5.3 on Gracia-Tabuenca.** Its segmentations are used for the structural analyses.
  The key puts it out, while the drafter and the checking pass read it as segmentation and keep it.
- **A deferred base pipeline plus one versioned mention makes the Software row addressed.** On
  Gracia-Tabuenca that silences the unconditional violation while the row reads "deferred".
- **First-level covariates filled `motion_expansion` and `detrend` again** on Gracia-Tabuenca. The
  checking pass caught both.
- **Shen's six motion parameters stay unverifiable**, and `unplaced` cannot list them by its own rule.

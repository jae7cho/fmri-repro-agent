# Report v2 run — coverage_v3: 16 contaminated papers and two unseen papers (2026-10-29)

**DIAGNOSTIC. Not an evaluation.** The first run of report v2 (`DESIGN_report_v2.md`, ratified by the
author on 2026-10-29): schema 0.6.0 and the list fields, `software_mentions` and the rebuilt Software
row, temporal filtering, the scope paragraph, step order from the paper, and the checking pass. Run on
the 16 contaminated corpus papers and the two unseen papers (Gracia-Tabuenca 2024, Shen 2013); the
held-out three were not run. Counts only.

**The unseen papers' checking-pass verdicts are withheld** — from this document, from chat and from the
DEVLOG — until the author confirms their own reading of the two papers is recorded (the evaluation
plan, §4). Their reports were shown in the session rendered with the checking pass hidden
(`<id>.hidden.md`); their stored `.md` and `.json` carry the verdicts and have not been printed.

- **Vintage** `coverage_v3` — `extractor_mvp/results/batch_coverage_v3/` (gitignored): 2026-10-29,
  14:44:57–15:30:42 UTC. **Code:** the report-v2 build *staged, not yet committed* (the commit hook
  blocks 09:00–17:00 ET); the manifest records HEAD `c220315` and the staged tree `1e46ed66`, which is
  the build plus this config. Config `configs/batch_coverage_v3_config.yaml` (sha256 `04e4d9be…`).
  **Gate:** the manifest carries six prompt hashes — the three unchanged (`31a050b2…`, `04ba3cb7…`,
  `b0093774…`), `TEMPORAL_VOLUME_PROMPT` `58328046…`, `SPATIAL_PROMPT` `697c868b…`,
  `VERIFIER_PROMPT` `42cb343c…` — and the phrase table; exit 0. **18 of 18 success**; the checking pass
  `ok` on all 18 (none unavailable).
- **Five calls per paper.**

## The per-row table — the 16 contaminated papers, coverage_v2 beside coverage_v3

Row states exclusive (`partially reported` new in v3). v3 rows read with the checking pass's software
exclusion (F1d); the row states are the drafting pass's, not the checking pass's (flags are shown at
field level and as "flagged" rows in the reports).

| row | reported | partially | performed=no | deferred | unverifiable | not reported |
|---|---|---|---|---|---|---|
| Software | 3 → 1 | 0 → 5 | — | 0 → 1 | 2 → 0 | 11 → 9 |
| T1 stabilization | 5 → 5 | — | 0 → 0 | 0 → 0 | 0 → 0 | 11 → 11 |
| Brain extraction | 4 → 4 | — | 0 → 0 | 2 → 2 | 0 → 0 | 10 → 10 |
| Segmentation | 7 → 6 | — | 0 → 0 | 1 → 1 | 0 → 0 | 8 → 9 |
| Slice time correction | 5 → 5 | — | 2 → 2 | 0 → 0 | 0 → 0 | 9 → 9 |
| Motion correction | 12 → 12 | — | — | 4 → 4 | 0 → 0 | 0 → 0 |
| Gradient distortion correction | 3 → 3 | — | 0 → 0 | 1 → 1 | 0 → 0 | 12 → 12 |
| Distortion correction | 3 → 3 | — | 0 → 0 | 1 → 1 | 0 → 0 | 12 → 12 |
| Function-structure (intra-subject) coregistration | 9 → 10 | — | 0 → 0 | 1 → 1 | 1 → 1 | 5 → 4 |
| Intersubject registration | 13 → 13 | — | — | 0 → 0 | 0 → 0 | 3 → 3 |
| Intensity correction | 2 → 2 | — | 0 → 0 | 1 → 1 | 1 → 1 | 12 → 12 |
| Artifact and structured noise removal | 14 → 14 | — | 0 → 0 | 0 → 0 | 0 → 0 | 2 → 2 |
| Volume censoring | 4 → 4 | — | 1 → 1 | 0 → 0 | 1 → 0 | 10 → 11 |
| Spatial smoothing | 10 → 11 | — | 1 → 1 | 0 → 0 | 1 → 1 | 4 → 3 |

The Software row moved most: read over every named software, **5 of the 16 are now partially
reported** (some software versioned, some not), and 1 reported where coverage_v2 had 3 — a paper that
versioned its base pipeline but named other software without a version is no longer counted as
compliant.

## The checking pass on the 16 contaminated papers (counts per paper)

| paper | supported | wrong | missed | unverified | not checked | verifier s |
|---|---|---|---|---|---|---|
| agtzidis_2020 | 83 | 3 | 0 | 0 | 0 | 50.4 |
| binder_1999 | 73 | 5 | 2 | 0 | 0 | 40.8 |
| braun_2015 | 77 | 2 | 0 | 0 | 0 | 36.7 |
| chen_2015 | 68 | 6 | 7 | 0 | 0 | 64.7 |
| ciric_2017 | 64 | 23 | 5 | 1 | 0 | 95.8 |
| cole_2013 | 77 | 3 | 5 | 0 | 0 | 76.0 |
| derosa_2025 | 73 | 4 | 3 | 0 | 9 | 44.2 |
| gordon_2014 | 70 | 6 | 1 | 3 | 3 | 58.4 |
| liu_2013 | 80 | 2 | 1 | 1 | 0 | 206.1 |
| mueller_2021 | 73 | 7 | 0 | 0 | 6 | 58.8 |
| oconnor_2017 | 72 | 13 | 0 | 1 | 0 | 210.1 |
| poldrack_2015 | 64 | 3 | 12 | 0 | 22 | 78.2 |
| power_2014 | 66 | 2 | 6 | 6 | 0 | 63.8 |
| vanderwal_2016 | 76 | 3 | 1 | 0 | 4 | 72.9 |
| viduarre_2017 | 77 | 1 | 1 | 0 | 3 | 44.9 |
| weber_2024 | 71 | 6 | 3 | 0 | 8 | 53.3 |
| **total** | **1,164** | **89** | **47** | **12** | **55** | |

**Unvalidated.** These verdicts are a second draw from the same model family; none is trusted before the
author's spot check (§4). Controls the design named, read on the contaminated papers:
- **chen_2015 slice-timing `performed`: supported** — the author's 2026-10-29 correction says it is
  right; a false "wrong" here would have been a verifier error. It did not make one.
- **poldrack_2015 `scrub.threshold`: extracted 0.25 and supported** — the repaired-text support fix
  of 2026-10-29 working on a live draw (it failed in coverage_v2).
- **ciric_2017 `multiple_pipelines`: still "yes"**, despite the re-worded question excluding
  benchmarks of denoising strategies. The re-wording did not fix it. liu_2013 and weber_2024, "yes" in
  coverage_v2, are now missing.
- **ciric_2017: 23 wrong**, most of them the benchmark again ("14 different models... not a single
  list"), which is right about the paper and the reason the draft cannot hold one configuration.
- **One self-contradictory verdict seen:** ciric's `brain_extraction.performed` is marked wrong with the
  reason "Brain extraction was performed on the structural image, which is in scope for this field" —
  a reason that supports the draft. Verifier errors of this kind are what the spot check is for.

## Wall time per paper (seconds; total, with the checking pass's share)

| paper | v2 | v3 | of which checking pass |
|---|---|---|---|
| braun_2015 | 56.8 | 93.3 | 36.7 |
| binder_1999 | 47.9 | 93.5 | 40.8 |
| viduarre_2017 | 71.8 | 104.7 | 44.9 |
| agtzidis_2020 | 54.2 | 112.8 | 50.4 |
| shen_2013 | — | 118.6 | 61.3 |
| gracia-tabuenca_2024 | — | 122.2 | 59.9 |
| mueller_2021 | 49.8 | 125.8 | 58.8 |
| weber_2024 | 64.0 | 126.6 | 53.3 |
| derosa_2025 | 67.2 | 131.1 | 44.2 |
| vanderwal_2016 | 47.4 | 133.5 | 72.9 |
| cole_2013 | 60.1 | 142.3 | 76.0 |
| gordon_2014 | 73.1 | 143.1 | 58.4 |
| chen_2015 | 75.5 | 158.9 | 64.7 |
| power_2014 | 65.0 | 177.0 | 63.8 |
| poldrack_2015 | 82.2 | 191.0 | 78.2 |
| ciric_2017 | 85.0 | 200.9 | 95.8 |
| liu_2013 | 79.0 | 274.2 | 206.1 |
| oconnor_2017 | 68.5 | 290.8 | 210.1 |

All 18: 2,740.4 s summed, 45 min 45 s launcher. The design's guess (+40–90 s per paper) holds for 16
of 18; liu_2013 and oconnor_2017 took over 200 s in the checking pass alone (the longest methods
slices). Calls T and S also grew (temporal filtering, software, order): v3 minus the checking pass is
above v2 on every paper.

## Defects found in the two hidden-verdict reports (the report itself, not the verdicts)

- **The band renders two ways**: "0.02, 0.1" in the step section, "0.02–0.1 Hz" in the rows section
  (`_fmt_band` is used only in the rows line).
- **The header names the Software violation under "not reported"** when the Software row is partially
  reported (Gracia-Tabuenca: "partially reported 1 · ... not reported 4 (incl. Software — unconditional
  violation)").
- **Shen's nuisance `performed` is still unverifiable**: "orthogonalized" is not in the frozen phrase
  table. By the ratified design the tables stay and the checking pass is the second line; whether it
  caught this is among the withheld verdicts.
- **Step order works on both**: Shen's is stated in full (motion, slice timing, normalization,
  segmentation, regression, filtering, smoothing); Gracia-Tabuenca's partially.

## Status (2026-10-29)

- Waiting on the author: their reading of Gracia-Tabuenca 2024 and Shen 2013, recorded before the
  verifier's verdicts on them are shown; then the three-reader comparison (§4).
- The report-v2 build is committed after 17:00 ET as seven commits (the ratified design, then steps
  1–6); this document and the config after them; the DEVLOG last.
  Done: `edaea4c`..`03fa079`, DEVLOG `06a560c` (see the 2026-11-02 sections below).

## The author's reading of the two unseen papers (recorded 2026-11-02, before the verdicts were shown)

Recorded verbatim as the author wrote it. This is the answer key for the three-reader comparison below.

```
My reading of the two unseen papers, recorded as the answer key (dated 2026-11-02,
author alone, written before seeing the checking pass):
- gracia-tabuenca_2024: Software row wrong (FreeSurfer, AtlasTrack, caret are not fMRI
  preprocessing; the row should defer to Hagler et al. 2019). Intensity correction and
  intersubject registration wrong (structural sentence). Missed: two pipelines (task
  censors FD > 0.9 mm, rest correlation excludes FD > 0.2 mm); the 0.31–0.43 Hz IIR
  filter on motion estimates. Correct: base pipeline deferral, distortion sources,
  motion, rest filtering 0.009–0.08 Hz, initial-volume removal, rest regression.
- shen_2013: correct overall, in order. Wrong: SPM5 shown as "no version" (major version
  only). Missed: six-parameter motion expansion; nuisance performed unverifiable because
  "orthogonalized" is not in the phrase table.
```

## The checking pass on the two unseen papers (opened 2026-11-02, after the reading above was recorded)

Read from `extractor_mvp/results/batch_coverage_v3/papers/<paper>.json`, key `verifier`; counts are
by `verifier.effective` (an unresolved sentence has no effect; none occurred on these two).

| paper | supported | wrong | missed | unverified | multiple_pipelines | checking-pass time |
|---|---|---|---|---|---|---|
| gracia-tabuenca_2024 | 73 | 6 | 0 | 0 | not stated | 59.9 s |
| shen_2013 | 75 | 5 | 1 | 0 | not stated | 61.3 s |

Every verdict that is not "supported", with the value it proposes:

- **gracia-tabuenca_2024**
  - `segmentation.performed`, `segmentation.method` — wrong, should be "not reported": the sentence
    is structural MRI segmentation.
  - `intensity_correction.performed`, `.target`, `.method` — wrong, should be "not reported": the
    sMRI sentence.
  - `spatial_normalization.target_space` — wrong, should be "not reported": the sMRI sentence.
  - Software: FreeSurfer, AtlasTrack and caret all marked not used for preprocessing, so the row
    excludes them and falls back to the base-pipeline deferral to Hagler et al. (2019).
- **shen_2013**
  - `slice_time_correction.method` — wrong, should be "SPM5" (the paper names the package, not the
    SPM function).
  - `slice_time_correction.relative_to_motion_correction` — wrong, should be "after" (the field was
    already unverifiable; the verdict reads order from "motion corrected and slice-time corrected").
  - `nuisance_regression.performed` — wrong, should be True (orthogonalisation is regression).
  - `nuisance_regression.method` — missed: orthogonalization.
  - `temporal_filtering.relative_to_regression` — wrong, should be "after".
  - `step_order` — wrong: "the draft lists many steps that were not performed". The proposed order
    is the paper's seven steps, which is the order the report already gives them.
  - Software: SPM5 and BioImage Suite both marked used for preprocessing. No verdict on SPM5's version.
  - `nuisance_regression.motion_expansion` — supported, with the reason that the paper does not say
    whether the six signals are the basic parameters or an expansion.

## Three readers, by counts (2026-11-02)

The author's reading is the key. "Claude's review" is the review written on 2026-10-29 before any
verdict existed: `docs/findings/unseen-papers-2026-10-29.md` (items 1–8, read against the
**coverage_v2-era** report) and the "Defects found in the two hidden-verdict reports" section above
(read against the coverage_v3 report). **Mapping those items onto the key was done on 2026-11-02,
after the verdicts were open**, so that column is not blind in its mapping, only in its content.

Per key item (✓ caught, ✗ not, ⊘ contradicted):

| paper | key item | checking pass | Claude's review |
|---|---|---|---|
| gracia | Software row: FreeSurfer, AtlasTrack, caret are not fMRI preprocessing | ✓ all three excluded | ⊘ item 6 argued FreeSurfer v5.3 belonged in the row |
| gracia | Intensity correction from the structural sentence | ✓ three fields wrong | ✗ item 3 named other rows, not this one |
| gracia | Intersubject registration from the structural sentence | ✓ | ✓ item 3 |
| gracia | Missed: two pipelines (task FD > 0.9 mm, rest FD > 0.2 mm) | ✗ multiple_pipelines not stated | ✓ item 8 (on the rest-only steps, not the FD thresholds) |
| gracia | Missed: 0.31–0.43 Hz IIR filter on motion estimates | ✗ | ✓ item 1 ("its motion-covariate filter") |
| shen | SPM5 shown as "no version" (major version only) | ✗ | ✗ not flagged on the v3 report (item 6 had called SPM5 "a fused version") |
| shen | Missed: six-parameter motion expansion | ✗ marked supported | ✓ item 5 |
| shen | Nuisance `performed` unverifiable ("orthogonalized") | ✓ | ✓ item 5 and the v3 defect list |

| count | checking pass | Claude's review |
|---|---|---|
| key items wrong or missed (8) caught | 4 | 5 |
| caught by this reader only | 2 | 3 |
| caught by both | 2 | 2 |
| caught by neither | 1 | 1 |
| contradicted the key | 0 | 1 |
| key's "correct" items on Gracia-Tabuenca (6) agreed | 6 | not assessable (v2-era report) |
| key's "correct, in order" on Shen disputed | 1 (step_order) | 0 |
| flags on fields the key does not mention | 6 field verdicts | 0 |

The six flags outside the key: gracia's two segmentation fields; shen's slice-timing method, slice
order, filter order and the missed regression method. Whether those are right is the author's call;
the key neither confirms nor contradicts them. No rate is computed: two papers, one draw, one key.

## The six queued fixes (built 2026-11-02, no model calls)

| fix | what changed | test | mutations killed | replay (no model call) |
|---|---|---|---|---|
| Software version "major only" (COBIDAS §4.3) | a name with a fused SPM major version reads "(major version only)" and is named on its own in the detail line; it still does not address the row | `test_a_fused_major_version_is_major_only_not_no_version` | 2 | coverage_v3 re-render: 5 Software rows change (below) |
| Scope rule on software_mentions | call S lists only software used to preprocess the functional data; SPATIAL_PROMPT `697c868b…` → `3c8d604b…`, dated note | `test_the_scope_rule_applies_to_software_mentions` | 1 | not replayable without a draw; the population it targets: 58 of 98 v3 mentions the checking pass marked not preprocessing |
| "orthogonalized" and "regressed out" families | added to `nuisance_regression` in the frozen phrase table, **declared fitted** (shen_2013 is now contaminated for it); table `02acd07d…` → `f77f032b…` | `test_orthogonalized_and_regressed_out_name_nuisance_regression` | 1 | stored unverifiable `performed` cells re-checked: v1 0, v2 0 of 4, v3 1 of 5 move (shen_2013 nuisance_regression); old table on v3: 0 move |
| An operation word is not a convention value | a convention made only of operation words ("normalization", "intensity normalized") becomes unverifiable, reason `operation_word_not_value` | `test_an_operation_word_is_not_a_convention_value` | 2 | v3: 2 of 6 extracted conventions move (gracia-tabuenca_2024, weber_2024); v1 1 of 5, v2 1 of 5, motion_corpus_v1 1 of 5 (weber each time); v7_full and sfn_v5 0 |
| One band format | every surface renders a band as "0.02–0.1 Hz" | the band test, extended to the step section | 1 | coverage_v3 re-render: 11 band lines change |
| The Software header label | a partially reported Software row carries its label on the partial segment, never under "not reported" | the partial-row test, extended | 2 | coverage_v3 re-render: 11 header lines change |

- **The "regressed out" family already matched** through the existing "regressed"; the entries make
  it explicit and move nothing. "orthogonalized" also covers "orthogonalised" and "orthogonalization";
  a bare "orthogonal" stays unmatched (tested).
- **weber_2024's "intensity normalization" moves too.** It was not in the key; it is the same shape.
- **The scope rule's target list includes doubtful checking-pass calls** (oconnor's FSL and ANTs,
  derosa's SPM12 and FEAT marked not preprocessing). The new prompt line keeps software whose output
  the functional preprocessing uses, so it is not meant to drop those; the next draw will show it.
- **Not addressed by these fixes**, from the key: the structural-sentence fields (the checking pass
  flags them; the scope paragraph did not stop them), Gracia-Tabuenca's two pipelines and motion
  filter, Shen's six-parameter expansion.

**Identity gate, derived before each run** (render-only effects; the processed-layer fixes change no
stored record):

| results | against | derived | got |
|---|---|---|---|
| batch_a1_acceptance | HEAD | 19 identical | 19 identical |
| batch_a1_acceptance | `d31e8b7` (negative control) | 0 identical | 0 identical, 19 changed |
| batch_coverage_v2 | HEAD | 19 identical | 19 identical |
| batch_coverage_v3 | HEAD | 16 changed; binder_1999, viduarre_2017 identical | the same |

Every changed v3 line is one of four kinds: band line 11, header line 11, Software row values 5,
Software detail line 5. No other line moved.

Tests: 594 extractor (not live), 235 root.

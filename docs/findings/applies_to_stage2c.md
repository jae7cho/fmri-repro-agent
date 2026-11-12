# applies_to Stage 2c: scorer, tables, part joins, two diagnoses (2026-11-11)

**Run: no model call.** The four Stage 2b records (`extractor_mvp/results/applies_to_v2`, drawn at
`1cb7383`) were re-rendered with the Stage 2c code by `extractor_mvp/scripts/rerender_records.py`
into `extractor_mvp/results/applies_to_v2c` and re-scored with
`extractor_mvp/scripts/score_smoothing_filtering.py`.

**Control on the render path.** The same render calls (`full_report.render_record`,
`pseudocode.render_pseudocode`) run from a worktree at `755508c` reproduce all 8 stored Stage 2b files
(4 reports, 4 pseudo-code files) byte for byte. A difference below is therefore the Stage 2c code's
doing, not the render path's.

## Scoring, Stage 2b vs Stage 2c (same records)

| sheet | paper | Stage 2b | Stage 2c | matched by quote / name |
|---|---|---|---|---|
| Smoothing | chen_2015 | 2 matched correct, 1 spurious | unchanged | 2 / 0 |
| Smoothing | ciric_2017 | 1 matched correct, 1 missed, 1 spurious | unchanged | 1 / 0 |
| Filtering | chen_2015 | 2 missed, 3 spurious | **1 matched correct**, 1 missed, 2 spurious | 1 / 0 |
| Filtering | ciric_2017 | split | split | — |
| Filtering | power_2014 | 2 missed, 1 spurious | unchanged | 0 / 0 |

- **chen_2015 Filtering, ReHo row:** matched once the label quote's leading "…" is stripped. State
  reported vs reported; band agree; pass type agree. This is the only row of either sheet whose
  outcome moved (the full score reports differ only there and in the two new scope columns).
- **chen_2015 Filtering, ALFF/fALFF row:** still missed. The label has no quote, and the record has
  no ALFF/fALFF part for filtering at all: its filtering parts are ReHo, global connectome metrics
  (DCw, ECw) and SFC. Nothing exists to match by name, so this miss is an extraction gap.
- **The name fallback matched nothing on these four papers.** ciric_2017's unquoted label "other
  compared models" has content words {other, compared, models}; the record's nearest part is
  "models 1-12". power_2014's filtering record has no parts (below).

## Part joins

One join across the four records, logged in `papers/chen_2015.json` under `part_joins`, none
refused:

`global connectome (DCw and ECw)` → `global connectome metrics (DCw, ECw)` (content words
{connectome, dcw, ecw, global} ⊂ {connectome, dcw, ecw, global, metrics}).

chen_2015's header line, verbatim:

`> Values differ by: ReHo, global connectome metrics (DCw, ECw) (joined: global connectome (DCw and ECw)), SFC, ALFF and fALFF (temporal_filtering.performed, spatial_smoothing.performed, spatial_smoothing.fwhm_mm, spatial_smoothing.space, spatial_smoothing.kernel_type, spatial_smoothing.approach)`

In the pseudo-code the two blocks are now one. Its smoothing line went from `spatial_smoothing(...)
[?]` to `spatial_smoothing()  [x]`, the not-performed statement the other spelling carried.

## ciric_2017's table

The record has 17 parts, so the pseudo-code prints each step once and the differing fields as
tables by step: 155 lines, against 368 for the 17 blocks in Stage 2b. The smoothing table,
verbatim:

```text
# spatial_smoothing
# | part | performed | fwhm_mm | kernel_type | approach |
# |---|---|---|---|---|
# | ICA-AROMA (models 13 and 14) | True | 6 | "gaussian" | "fixed_kernel" |
# | models 1-12 | False | ? | ? | ? |
# (15 other parts state none of these fields)
```

There are also tables for nuisance regression (14 parts), temporal filtering (15), ICA denoising,
CompCor, despiking and scrubbing (14 each). In the temporal filtering table, one of the 17 parts is
"all regressors": the record gives `temporal_filtering.applied_to` = "all regressors" as a part of
its own. That is the extraction treating the value as a part, not a part of the paper's data.
"ICA-AROMA (models 13 and 14)" and "Model 13" were not joined: "models" and "model" are different
words, so neither name is a subset of the other.

## Diagnosis 1: power_2014's filtering quotes (diagnosis only)

- **Which check failed:** the quote resolver (`span_resolver.resolve_quote`), `quote_not_found`.
  There are 6 diagnostics `extraction_quote_unresolved:quote_not_found`: performed, effective band,
  filter type, pass type, order and relative_to_regression. All six became MISSING_FROM_PAPER.
- **Why:** in the Stage 2b draw, the TemporalVolumeExtraction call gave each filtering field one
  quote that starts at "After fMRI pre-processing, further steps were taken … (Figure 1). These steps
  included …". In the text, those two sentences have a third sentence between them ("Data from
  various steps in processing will be illustrated in the paper."). The quote leaves it out, so no
  contiguous span exists. The Stage 2 draw quoted from "These steps included" (performed,
  relative_to_regression) or from "frequency filtering of the data" (the others), which resolved.
- **Text layer: the same as Stage 2.** Both records have text source grobid-0.9.1-crf and methods
  offsets 6911–21598. Rebuilt today, the text gives the same slice. Against it, the Stage 2 quotes
  resolve at the offsets stored in the Stage 2 record (3971–4275 and 4158–4275), and the Stage 2b
  quotes resolve nowhere.
- **The checking pass:** MISSED on each of the six fields, with the right values (pass band 0.009 to
  0.08 Hz, Butterworth, 2nd order, after regression).
- **Values:** the dropped values were correct: 0.009–0.08 Hz, band-pass, Butterworth, order 2,
  after regression. The loss is the quote, not the reading.

## Diagnosis 2: gracia-tabuenca_2024 has no parts (diagnosis only)

- **The scrub sentence:** "Also, time points with a framewise displacement (FD) above 0.9 mm were
  censored." It sits at full-paper offset 9407–9487, at the end of the task-fMRI description.
  `scrub.performed`, `criterion` (fd_power), `threshold` (0.9) and `remediation` (censor) all quote
  it, as values for all data.
- **The rest-fMRI paragraph is in the methods slice.** The slice runs from 5764 to 19738 (header
  "Methods", ending at "Results"). The very next sentence, at 9488, begins "Rest-fMRI underwent
  additional preprocessing steps including removal of initial volumes, normalization, regression,
  temporal filtering (0.009-0.08 Hz)…". Two sentences later, rest-fMRI's own censoring rule follows:
  time points with FD above 0.2 mm were left out of the correlation.
- **What the extraction did:** the TemporalVolumeExtraction call returned no field as varied. No
  call's raw output contains "applies_to" or "varied". It gave filtering, non-steady-state removal and
  nuisance regression as performed for all data, quoting the sentence that begins "Rest-fMRI
  underwent". So the part's name was in the quote, and the part rules added in Stage 2b did not change
  the answer.
- **What the checking pass said:** MISSED, with values per part, on:
  - `scrub.performed`: "True for task-fMRI with FD > 0.9 mm; True for rest-fMRI with FD > 0.2 mm";
  - `scrub.threshold`: "0.9 mm for task-fMRI; 0.2 mm for rest-fMRI";
  - `temporal_filtering.performed`, `pass_type` and `effective_band_hz`: "… for rest-fMRI";
  - `nonsteadystate_removal.performed` and `nuisance_regression.performed`: "True for rest-fMRI".

  It marked `scrub.remediation` supported. The Stage 2 checking pass gave the same reading, with
  per-part better values.
- **Reading:** the information reaches the checking pass and is in the slice; the extraction call
  does not turn it into variants. The checking pass's per-part values are not converted into
  variants, by design (the checking pass does not change the extraction arms).

## Checks

- 16 mutations, each with a non-empty diff against the pre-mutation file before its run, all killed.
- Identity gate vs HEAD (`755508c`): 68/68 (a1 19, coverage_v4 18, stress_v1 12, corpus_grobid_v1 19)
  plus 8/8 `applies_to_v1`, all identical. The gate renders the report without the pseudo-code and
  without a join on those records, so nothing there moves. Positive control: a temporary title edit
  changed 12/12 on stress_v1, and after the restore they were 12 identical again.
- Suites: extractor_mvp 1061 passed, root 318 passed.

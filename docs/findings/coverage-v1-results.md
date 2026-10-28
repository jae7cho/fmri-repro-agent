# The eleven uncovered D.3 rows — the first run of the two coverage calls: nineteen papers, results (2026-10-28)

**DIAGNOSTIC. Not an evaluation.** The run `DESIGN_coverage_expansion.md` Part D specified, under the
author's rulings R1–R8 of 2026-10-28: the batch over all 19 papers with four model calls each (the
frozen motion stanza, the two new coverage calls, the shared call), into a new vintage directory.
**No labels and no accuracy figure for the eleven rows (R7)**; every number is a count of papers or of
field cells; nothing is pooled with any earlier vintage. The three held-out papers entered through the
model only and are read as states and counts (never a field, offset or text).

- **Vintage** `coverage_v1` — `extractor_mvp/results/batch_coverage_v1/` (gitignored, as results/
  always is): 2026-10-28, 22:26:59–22:47:00 UTC, HEAD `86cba81`, config
  `configs/batch_coverage_v1_config.yaml` (sha256 `f2ad9975…`), model
  `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2` on all
  four calls. **Gate:** `launcher_manifest.json` carries the five prompt hashes — `EXTRACTION_PROMPT`
  `31a050b2…`, `PER_ACQUISITION_EXTRACTION_PROMPT` `04ba3cb7…`, `MOTION_METHOD_PROMPT` `b0093774…`,
  `TEMPORAL_VOLUME_PROMPT` `9e523824…`, `SPATIAL_PROMPT` `17742cbb…` — the HEAD, the config's sha256,
  start, end and exit 0; checked before any record was read. 19 `.json` + 19 `.md`; `status` success
  18, `methods_not_found` 1 (liu_2005, the same text-layer status as the corpus run); `render_error` 0.
- **Every field this run wrote is the vintage `coverage_v1`**, the motion and shared fields included
  (re-drawn under their unchanged hashes on a different day); this document reports the eleven rows
  and the 14-row header. The motion and target_space columns exist and are not compared with any
  earlier run here.

## The table — per mandatory row, the 16 contaminated papers

Row state per paper from `cobidas.row_state` over the stored record, exclusive in this order:
`performed=no` (every EXTRACTED `performed` on the row is False and nothing else on it reports),
`addressed` (an EXTRACTED field), `deferred` (addressed by deferral only), `unverifiable` (a quote
resolved and the value was not in it, or a quote did not resolve), `not reported` (targeted, nothing
reported), `not assessed` (never targeted — 0 everywhere: every row is targeted now). Every row sums
to 16.

| row | addressed | performed=no | deferred | unverifiable | not reported |
|---|---|---|---|---|---|
| Software | 3 | — | 0 | 0 | 13 |
| T1 stabilization | 5 | 0 | 0 | 0 | 11 |
| Brain extraction | 4 | 0 | 3 | 0 | 9 |
| Segmentation | 7 | 0 | 1 | 0 | 8 |
| Slice time correction | 5 | 1 | 0 | 1 | 9 |
| Motion correction | 11 | — | 4 | 0 | 1 |
| Gradient distortion correction | 3 | 0 | 1 | 0 | 12 |
| Distortion correction | 3 | 0 | 1 | 0 | 12 |
| Function-structure (intra-subject) coregistration | 10 | 0 | 1 | 1 | 4 |
| Intersubject registration | 11 | — | 1 | 1 | 3 |
| Intensity correction | 3 | 0 | 1 | 0 | 12 |
| Artifact and structured noise removal | 14 | 0 | 0 | 0 | 2 |
| Volume censoring | 3 | 1 | 0 | 1 | 11 |
| Spatial smoothing | 10 | 1 | 1 | 2 | 2 |

(Software, Motion correction and Intersubject registration carry no `performed`; the dash marks a
state they cannot take. Gradient and field distortion share the folded kind, R1, and move together.)

**The held-out three, counts only** (3 papers × 14 mandatory rows = 42 row-cells, summed, never per
paper): addressed **10**, performed=no **2**, deferred **1**, unverifiable **7**, not reported **22**.

## Named lines — the 63 coverage fields

- **16 contaminated papers × 63 fields = 1,008 cells:** extracted 175; deferred 10; `not_stated_in_text`
  738; `step_not_performed` 25 (the parameters behind the 4 stated negatives); `value_unsupported_by_quote`
  38; `extraction_quote_unresolved` 22 (agtzidis 2, binder 4, gordon 1, poldrack 9, power 6); no other
  reason occurred (`value_not_numeric`, `value_not_boolean`, `value_not_in_literal`: 0 each).
- **`performed`, 13 kinds × 16 = 208 cells:** yes 68, no 4, deferred 8, not stated 121, quote unresolved 7.
- **The held-out three, 3 × 63 = 189 cells:** extracted 22; `not_stated_in_text` 146; `step_not_performed`
  10; `value_unsupported_by_quote` 2; `extraction_quote_unresolved` 9; deferred 0. `performed` over 39:
  yes 7, no 2, not stated 26, unresolved 4.
- **Reasks and errors:** none recorded by the batch (`error_message` 0, `render_error` 0); the batch
  does not count instructor reasks.

## Wall time per paper (seconds; `wall_time_s`, the four calls plus assembly and deferral resolution)

| paper | s | | paper | s |
|---|---|---|---|---|
| viduarre_2017 | 50.03 | | derosa_2025 | 67.82 |
| binder_1999 | 51.36 | | chen_2015 | 73.18 |
| vanderwal_2016 | 53.87 | | gordon_2014 | 74.77 |
| mueller_2021 | 55.70 | | ciric_2017 | 77.50 |
| weber_2024 | 58.97 | | poldrack_2015 | 84.43 |
| cole_2013 | 59.22 | | held-out three, as one group | 176.32 total, 58.77 mean |
| oconnor_2017 | 59.31 | | **all 19** | **1,196.85 total** |
| liu_2013 | 60.39 | | | |
| agtzidis_2020 | 61.71 | | | |
| braun_2015 | 66.01 | | | |
| power_2014 | 66.28 | | | |

The corpus run's batch (two calls per paper) did not record per-paper wall time; its 19 papers took
8 min 35 s of launcher wall clock against this run's 20 min 1 s.

## What was found that was not pre-declared (from the three reports pasted in the session: ciric, chen, poldrack)

- **A boolean's quote need not be about the step.** B3 recorded that `performed` has no token check;
  chen_2015's `slice_time_correction.performed = True` quotes the de-spiking sentence ("removed and
  interpolated temporal spikes"), a real sentence of the paper about a different step. The row reads
  "reported" on a quote that does not state it. Held for the author: a rule for the boolean's quote
  (the sentence must name the step), which would move such cells to *unverifiable*.
- **An alias miss by spelling:** chen's `segmentation.tissue_classes` carries one item
  `"cerebrospinal_fluid"` unrecognized beside `white_matter` and `gray_matter` resolved — the table's
  alias is "cerebrospinal fluid" with a space and the model wrote an underscore. The item stays EXTRACTED
  with the paper's words (the 0.5.0 rule); the resolver's substring match does not fold underscores.
- **Sibling kinds on one row list their fields without the kind's name:** the artifact row's line
  reads "performed = True; method = aroma; performed = True; variant = a; …" for ica_denoise, compcor and
  nuisance_regression in turn; the censoring row likewise for despike and scrub. The step sections
  above the coverage block carry the kind. A wording item for the author, not changed after the run.
- **The text layer again:** poldrack's 9 unresolved quotes on these fields (and power's 6, binder's 4)
  are the long-quote and hyphenation shapes the resolver already names; poldrack's scrub and smoothing
  rows read *examined; could not verify* for that reason, not because the paper is silent.
- **A cost-function token in the method slot:** ciric's `coregistration.method = "boundary_based"`
  (verbatim, unrecognized) while `cost_function` is not stated — the model answered the method
  question with BBR; both tokens are in the alias tables and the record keeps what was returned.
- **Every stated negative was caught by the override:** 4 (contaminated) + 2 (held-out) `performed = no`
  cells, and the 25 + 10 `step_not_performed` parameters behind them, with 0 parameter cells extracted
  on a step stated as not performed.

## The identity gate

Derived before the run as 19 identical (the stored acceptance records carry none of the thirteen
kinds' new fields) and run after the build, before the run: `--against 9c5359d` (the pre-build code)
→ 19 identical, 0 changed; the negative control `--against d31e8b7` → 0 identical, 19 changed. The
run changes no code and writes only under its own output_dir; the newest stored acceptance JSON's
mtime is 2026-09-07.

## Status

- No labels for the eleven rows; no accuracy figure; nothing here may be read as one. A later
  pre-registration picks rows to validate, smoothing and slice timing first (R7).
- The KB's pipeline defaults for these rows are the next build (R7); every new or retyped field has
  `inference_applicable=False`.
- Held for the author: the boolean's quote rule; the sibling-kind wording on the per-row line;
  whether the underscore spelling joins the alias tables.

# corpus_full_v3: the 45 papers re-run after the pre-rerun bundle (2026-11-11), INCOMPLETE

Code `80f0c63` (items 1-5: `bf05d8b`, `4873f67`, `d411763`, `fe1f0e5`, `80f0c63`), KB `12a82e3`,
aespa-report, default text source (GROBID 0.9.1-crf), metered, under `caffeinate -i`, from a worktree
pinned at `80f0c63`, three papers at a time, into `extractor_mvp/results/corpus_full_v3` (gitignored).
Each paper's reconstructed preprocessing is in `<paper>.preproc.txt` there and the 38 together in
`preproc_all_45.txt` there (not committed: it carries the held-out papers' values). Rows of liu_2005,
tang_2025 and wheaton_2004 below give ids and states only.

**This run is not the finished re-run. Two defects, one of them mine, leave 16 of 45 papers to be run
again:**

1. **The Bedrock daily token limit** ("Too many tokens per day, please wait before trying again") was
   reached at 21:33. Five papers failed with no record: viduarre_2017, weber_2024, wheaton_2004,
   yang_2025, yassa_2010. Two finished papers lost their last two calls (the resolution call and
   the data-release call) to the same limit: smith_2013_rest_in_hcp and vanderwal_2016.
2. **The runner passed no `--corpus`.** corpus_full_v2's runner passed every `tested_lit` folder; this
   one did not, so each paper's citation hop looked for cited PDFs only in the citing paper's own
   folder. Hagler_2019.pdf, Glasser_2013_HCP_pipelines.pdf and the rest sit in other folders. Every
   hop-dependent result is therefore wrong for the 10 papers with a hop or a deferral to a paper:
   braun_2015, cattarinussi_2026, cho_2021, derosa_2025, gracia-tabuenca_2024, mueller_2021,
   silchenko_2023, sims_2021, smith_2013_rest_in_hcp, tang_2025. That covers the hop records, item 4's
   "source could not be opened" marks, and the resolution call that reads the hop's answers.
   - Of the 15 hop records, 14 report `not_retrievable` / `no_local_pdf`. In v2,
     cattarinussi_2026 → Hagler 2019 and gracia-tabuenca_2024 → Hagler 2019 opened `Hagler_2019.pdf`.
   - Reproduced offline: `resolve_local_pdf` finds Hagler 2019 with `sfn_batch` among the folders, and
     not with gracia-tabuenca's own folder (`~/Downloads`) alone.

The extraction, the checking pass, the checker-supplied values, the parts, the quotes and the
extraction-side scorers never read the corpus folders. Those sections below stand for the 40 papers
with a record. Sections that depend on the hop are marked.

## The run

- **Records:** 40 of 45. 33 success, 5 `methods_not_found` (glasser_2013_hcp_pipelines, liu_2005,
  silchenko_2023, smith_2013, smith_2013_rest_in_hcp) and 2 not-fMRI stops (cabral_2017, gao_2026).
  Five failed on the token limit.
- **Cost:** $31.6542 metered over 525 calls, the failed papers' partial calls included. Wall time
  7,628 s summed over papers (about 43 minutes elapsed, three at a time).

## Fields, v2 against v3, the same 40 papers

Counted on the stored fields of every step:

| field state | v2 | v3 |
|---|---|---|
| extracted | 815 | 716 |
| extracted, checker-supplied (item 2) | 0 | 26 |
| varied (values by part) | 0 | 113 |
| deferred | 24 | 29 |
| deferred, source could not be opened (item 4; hop-dependent, see above) | 0 | 14 |
| missing from paper | 3036 | 2978 |
| missing, inferred default | 1 | 0 |

The extracted count fell because 113 fields now give values by part instead of one value for all.
Values stated, all forms together: 815 in v2 against 855 in v3.

**Unverifiable fields** (counted as in corpus_full_v2.md): 62 → 47 on the same 40, the 2026-11-09
checker-supplied beside-the-field values included in v2's count (60 less them).

**Pseudo-code tags.** Not comparable this time. A record with parts now prints one block per part, or
tables, so every tag on a shared step is printed once per part. The counts are kept for the record:
[E] 614 → 916, [E†] 0 → 33, [D] 60 → 118, [M] 75 → 87, [C] 26 → 40, [?] 1023 → 1491, [x] 13 → 35.

## Item 1: quotes as 1-3 spans

- 55 values carry more than one span, in 19 papers (ciric_2017 7, glasser2016_nature 7,
  glasser_2013_hcp_pipelines 8, hagler_2019 5, poldrack_2015 5; one held-out paper 1).
- `extraction_quote_unresolved` diagnostics: 40 → 31 on the same 40 papers. The question this item was
  built for, power_2014's stitched filtering quote, did not recur this draw: power_2014's filtering
  fields are extracted.

## Item 2: checker-supplied values

- **Verdicts:** the checking pass returned 131 MISSED or WRONG verdicts with a value and a sentence;
  26 filled a field and 105 stayed flags.
- **Why the 105 stayed flags:** the field was already extracted 42 (never overridden); not a field
  the extraction path checks 20; the sentence did not resolve 9; value not in the sentence 5; value not
  numeric 5; quote unresolved 3; value not yes/no 2.
- **No verdict created parts.** gracia-tabuenca_2024's per-part scrub verdict is on a field the
  extraction filled for all data, so it stayed a flag, as the rule says.
- **The checks let some values through that are wrong in kind.** These are observations, not fixed:
  - derosa_2025 `temporal_filtering.filter_type` = "Butterworth or not reported";
  - bakker_2012 `segmentation.tissue_classes` = a list of medial temporal regions (anatomical ROIs,
    not tissue classes);
  - power_2014 `nonsteadystate_removal.n_nonsteadystate_discarded` = "15 TRs at beginning and end of
    each run after filtering", which is frames removed after filtering, not T1-stabilization volumes.

  Each value is in its sentence, so the value-in-quote check passes. The check tests where a value is
  written, not what it means.

## Parts (Stage 2c and items 2-3)

14 of 38 papers with a preprocessing record have parts:

| paper | fields with parts | part names | step-order parts | joins | refused joins | checker-supplied parts |
|---|---|---|---|---|---|---|
| chen_2015 | 8 | 5 | 0 | 1 | 0 | 0 |
| cho_2021 | 24 | 5 | 2 | 2 | 0 | 0 |
| ciric_2017 | 24 | 15 | 0 | 0 | 0 | 0 |
| glasser2016_nature | 2 | 2 | 2 | 0 | 0 | 0 |
| glasser_2013_hcp_pipelines | 1 | 2 | 0 | 0 | 0 | 0 |
| gracia-tabuenca_2024 | 8 | 5 | 2 | 0 | 1 | 0 |
| greene_2022 | 17 | 3 | 1 | 0 | 0 | 0 |
| hagler_2019 | 8 | 2 | 2 | 0 | 0 | 0 |
| hermans_2024 | 1 | 2 | 0 | 0 | 0 | 0 |
| li_2024 | 3 | 2 | 0 | 0 | 0 | 0 |
| power_2014 | 2 | 3 | 0 | 0 | 0 | 0 |
| silchenko_2023 | 3 | 3 | 0 | 0 | 0 | 0 |
| smith_2013 | 1 | 3 | 0 | 0 | 0 | 0 |
| tang_2025 | 11 | 3 | 2 | 1 | 0 | 0 |

Joins: chen_2015 "global connectome (DCw and ECw)" into "DCw and ECw"; cho_2021 "HNU" into "HNU
dataset", "MSC" into "MSC dataset"; one in tang_2025 (held out).
- **gracia-tabuenca_2024 has parts this draw:** 8 fields, 5 part names. In Stage 2b it had none.
- **ciric_2017 has no "all regressors" part** (item 3): 15 part names, against 17 in Stage 2b.
- **`varied_variant_without_value`:** 17 diagnostics. A variant with no value that is not the
  compared-models entry is dropped.

## The scorers, the 16 labelled papers with a v3 record

v2 is scored on the same 16 papers (`corpus_full_v2`), so the two columns compare. wheaton_2004,
viduarre_2017 and weber_2024 have no v3 record. Both columns are scored with the current code.

| scorer | v2 | v3 |
|---|---|---|
| motion, bullet 1 (agree / disagree) | 5 / 11 | 4 / 12 |
| motion resolved, KB-confirmed (agree / disagree) | 11 / 1 | 11 / 0 |
| smoothing: papers scored | 13 | 16 |
| filtering: papers scored | 13 | 15 |

- **Motion bullet 1:** gordon_2014 went from named_tool (agree) to described_only (disagree). This is
  the extraction, not the hop.
- **Motion resolved** reads the resolution call, which is hop-dependent for 4 of the 16 (braun_2015,
  derosa_2025, mueller_2021, tang_2025) and failed for vanderwal_2016. Rows that moved:
  - derosa_2025: disagree → agree;
  - poldrack_2015: model-only disagree → KB-confirmed agree;
  - liu_2005 (held out): agree → disagree;
  - vanderwal_2016: no resolution.
- **Smoothing:** chen_2015, ciric_2017 and tang_2025 are no longer collapsed.
  - chen_2015: both rows agree.
  - ciric_2017: "ICA-AROMA models (input)" agrees; "other compared models" is missed.
  - tang_2025 (held out): one row agrees, one is missed.
- **Filtering:**
  - chen_2015's ReHo row agrees; its ALFF/fALFF row reads stated_not_performed against the label's
    not_reported.
  - tang_2025: both rows agree.
  - ciric_2017 is no longer split (one "all" value, state partially_reported → reported, disagree).
  - power_2014 is collapsed again: its filtering values resolved this draw, as one value for all.
- **The 16 row scorers:** no labels exist on any of their sheets; each printed its expected schema and
  exited 0.

## Item 5: reference lists

The hop's reference list was found by heading in 32 papers and by the numbered-run fallback in 4 (not held out; the two not-fMRI stops have none)
(bassett_2011, braun_2015, greene_2022, marek_2022). braun_2015's "refs. 47 and 48" now reaches its
entries (Cao 2014, Plichta 2012). Neither has a PDF in braun's folder. Whether one exists in another
folder is unknown until the hop is re-run with `--corpus` (defect 2).

## What is needed to finish

Re-run 16 papers at `80f0c63` with every `tested_lit` folder passed as `--corpus`, once the token
limit allows: the 5 that failed, smith_2013_rest_in_hcp and vanderwal_2016, and the hop-dependent 10
(one of which, smith_2013_rest_in_hcp, is in both lists). Estimated from this run's per-paper costs:
about $13. Then rebuild the motion row for all 45, the hop table and the scorers on the 19, and redo
this document's hop-dependent sections. The motion row table is left out here because 10 of its rows
are hop-dependent and 5 have no record.

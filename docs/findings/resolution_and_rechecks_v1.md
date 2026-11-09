# The resolution call, value checks, glyphs and the GROBID hop (2026-11-09)

Code: `9badfb8` (items 1 to 4) and `971b2b5` (KB id mapping, motion re-check, the re-check
script), with the render fix in this document's commit. KB: fmri-defaults-kb `263e461` (CONN in
`kb/pipelines`), pinned in CI at `5df094f`. Papers other than achuthan_2023 are reported as held
out: statuses, counts, provenance and cost only.

## 1. Unverifiable fields, 45 stored records, before and after (items 2 and 3, no model call)

`scripts/recheck_records.py --in results/corpus_full_v1 --out results/corpus_full_v1_rechecked`.
A field counts as unverifiable when the extraction left it MISSING with an unverifiable reason
(`cobidas._UNVERIFIABLE_GAP_BASES`). The re-check re-runs `_process_field` (and, for the motion
method, `motion_post_check`) on every field left MISSING for a quote reason, against the same
methods slice of the same text layer. Two rules bound it:
- A value item 2 now leaves to the checking pass is not restored where the stored checking pass
  judged the field `supported` (it endorsed the gap) or `wrong` with its own value. No model call
  is made to judge the restored value.
- "Checker-supplied" counts the fields where the checking pass said WRONG and gave a value from the
  extraction's own quote. They render as `[checker-supplied]` and are not counted.

| paper | before | after the re-check | checker-supplied | after |
|---|---|---|---|---|
| achuthan_2023 | 5 | 5 | 2 | 3 |
| agtzidis_2020 | 5 | 1 | 0 | 1 |
| bakker_2012 | 4 | 4 | 0 | 4 |
| bassett_2011 | 1 | 1 | 0 | 1 |
| binder_1999 | 1 | 0 | 0 | 0 |
| braun_2015 | 1 | 1 | 0 | 1 |
| cabral_2017 | not-fMRI stop | | | |
| cattarinussi_2026 | 3 | 1 | 0 | 1 |
| chen_2015 | 5 | 5 | 0 | 5 |
| cho_2021 | 3 | 2 | 0 | 2 |
| ciric_2017 | 10 | 4 | 1 | 3 |
| cole_2013 | 3 | 1 | 0 | 1 |
| derosa_2025 | 5 | 4 | 1 | 3 |
| dimitrova_2002 | 6 | 0 | 0 | 0 |
| gao_2026 | not-fMRI stop | | | |
| glasser2016_nature | 7 | 4 | 0 | 4 |
| glasser_2013_hcp_pipelines | 12 | 8 | 0 | 8 |
| gordon_2014 | 2 | 0 | 0 | 0 |
| gracia-tabuenca_2024 | 4 | 3 | 0 | 3 |
| greene_2022 | 7 | 7 | 1 | 6 |
| hagler_2019 | 8 | 8 | 0 | 8 |
| hermans_2024 | 3 | 3 | 0 | 3 |
| ladouceur_2023 | 11 | 7 | 0 | 7 |
| li_2024 | 6 | 5 | 3 | 2 |
| liu_2005 | 12 | 12 | 1 | 11 |
| liu_2013 | 2 | 2 | 0 | 2 |
| maheu_2011 | 2 | 2 | 0 | 2 |
| marek_2022 | 6 | 0 | 0 | 0 |
| mueller_2021 | 2 | 2 | 0 | 2 |
| oconnor_2017 | 5 | 3 | 0 | 3 |
| poldrack_2015 | 9 | 6 | 0 | 6 |
| power_2014 | 11 | 4 | 0 | 4 |
| schwartz_2018 | 2 | 2 | 0 | 2 |
| shen_2013 | 3 | 3 | 0 | 3 |
| silchenko_2023 | 3 | 3 | 1 | 2 |
| sims_2021 | 12 | 11 | 0 | 11 |
| smith_2013 | 4 | 2 | 0 | 2 |
| smith_2013_rest_in_hcp | 9 | 6 | 0 | 6 |
| tang_2025 | 5 | 5 | 0 | 5 |
| vanderwal_2016 | 4 | 2 | 0 | 2 |
| viduarre_2017 | 5 | 4 | 0 | 4 |
| weber_2024 | 5 | 1 | 0 | 1 |
| wheaton_2004 | 1 | 1 | 0 | 1 |
| yang_2025 | 5 | 5 | 0 | 5 |
| yassa_2010 | 3 | 0 | 0 | 0 |
| **total, 45 records** | **222** | **150** | **10** | **140** |

All 45 text layers matched the stored text source, so no record was copied unchanged for a
text-source change. The record-level step order is not re-checked. The D.3 coverage section still
counts a checker-supplied field as unverifiable, because the provenance contract has no arm for it.

**The two named cases.**
- **dimitrova_2002:** 6 to 0. The smoothing quotes resolve once U+03EB folds to x.
- **agtzidis_2020:** of its 7 quote failures, 5 fields are restored: every field-level quote that
  failed on the multiplication sign, the motion method among them. The sixth such quote is the
  record-level step order, which is not re-checked.
  `nuisance_regression.motion_expansion` stays as stored, because the checking pass endorsed the gap.

## 2. Items 1 and 4 on seven papers (metered, pinned at `971b2b5`, under `caffeinate -i`)

| paper | method field | resolved pipeline in KB | realignment tool | sub-items (EXTRACTED / MODEL / UNKNOWN) | hops (path) | cost |
|---|---|---|---|---|---|---|
| achuthan_2023 | EXTRACTED | yes (conn) | INFERRED_DEFAULT: spm → Realign, named in the paper | 1 / 3 / 0 | 1 (marker_text, not retrievable) | $0.0124 |
| cattarinussi_2026 | DEFERRED, left missing | no (free text) | UNKNOWN | 0 / 0 / 4 | 2 (grobid_ref_target, not retrievable) | $0.0113 |
| li_2024 | EXTRACTED | yes | INFERRED_DEFAULT, named | 0 / 3 / 1 | 0 | $0.0126 |
| schwartz_2018 | EXTRACTED | yes | INFERRED_DEFAULT, named | 0 / 3 / 1 | 0 | $0.0139 |
| bassett_2011 | EXTRACTED | no | INFERRED_DEFAULT, named | 0 / 3 / 1 | 0 | $0.0118 |
| dimitrova_2002 | EXTRACTED | no | INFERRED_DEFAULT, named | 1 / 2 / 1 | 0 | $0.0126 |
| yassa_2010 | MISSING, arm filled (KB-confirmed) | no | INFERRED_DEFAULT, named | 0 / 0 / 4 | 0 | $0.0113 |

The seven calls cost $0.0859 and took 34.6 s. A first run at `9badfb8` ($0.0855) is superseded,
for two reasons:
- The model echoed the KB index prefix ("tool spm"), so no answer matched a KB id. `971b2b5` maps
  answers through the KB's recognisers.
- The harness ran from the worktree, whose default GROBID cache is empty, so the supplement's TEI
  was not found. The re-run points `AESPA_GROBID_CACHE` at the repository's cache.

Total for both runs: $0.1714.

**achuthan_2023 (labelled, so values are shown):**
- The method stays the paper's phrase, "realigned and unwarped" (EXTRACTED).
- The resolution gives pipeline conn (KB) and tool spm → Realign, KB-confirmed (SPM is named in the
  paper).
- Susceptibility correction is stated (unwarping), from the method's own sentence.
- Reference scan, interpolation and similarity metric are each inferred by the model, unconfirmed.

**The cattarinussi hop does not find hagler_2019, and the expectation does not hold.**
- The "[3,][4]" deferral sentence is in the supplement, not the paper. Through the supplement's TEI
  its targets are b2 and b3 (printed entries 3 and 4).
- Hagler 2019 is the supplement's b1 (printed 2) and the paper's b33. Neither b2 nor b3 has Hagler
  as first author with year 2019.
- Both entries resolve through targets; neither has a local PDF.
- The stored hop (marker text against the paper's pypdf list) matched "3" in the wrong list.
- Checked twice, by the subagent that built item 4 and independently (ids only).

**yang_2025's "67"** resolves through its target to b66 (sentence found verbatim), with no local
PDF. This was checked without a model call; yang was not in the metered seven.

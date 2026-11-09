# Freeze report (2026-11-08)

Code at `50551fc` (no library change since); the tag `sfn2026-freeze` marks the DEVLOG commit that
follows this report. Counts only; held-out papers (liu_2005, tang_2025, wheaton_2004) by
id. The text-source comparison is `text_source_ab_v1.md`; its 18-paper view (liu_2005 left out)
is section 6 there.

## 0. Footprint after corpus_full_v1 (2026-11-08)

Every paper PDF in scope not extracted at or after `4c3b4b4` was run through aespa-report with the
default text source (GROBID CRF), metered, under `caffeinate -i`, from a worktree pinned at
`50551fc`, into `extractor_mvp/results/corpus_full_v1`: the 25 of section 2, and gao_2026, whose
only current-render report (section 1) was a 2026-11-05 not-fMRI stop. The folder also links the
19 labelled papers' current records (corpus_grobid_v2: corpus_grobid_v1's 18 and liu_2005's
fallback re-run). Every paper in the run is treated as held out: statuses, counts, cost and time
only. No labels exist for them, so nothing is scored.

| group | distinct papers in scope | current-code report before the run | current-code report now |
|---|---|---|---|
| labelled corpus | 19 | 19 | 19 |
| stress_v1 | 12 | 0 | 12 |
| sfn_batch, unlabelled | 3 | 0 | 3 |
| hop cases | 2 | 1 | 2 |
| other in scope | 10 | 0 | 10 |
| **total, de-duplicated by DOI** | **45** | **19** | **45** |

"Current-code report" here is the strict tier of section 1: extracted at or after `4c3b4b4`, and
re-rendering byte for byte with the current code (all 26 new reports do). The 45 records of
corpus_full_v1 map to 45 distinct DOI keys, covering every key in scope (cho_2021 and weber_2024
once each). poldrack_2015 is counted in both the labelled corpus and hop case 2.

**The run.** 26 of 26 wrote a record and a report on the first attempt; the watchdog killed
nothing; no failure. 20 full reports, 4 `methods_not_found`
(each still a report, sliced from the full text), 2 not-fMRI stops. Every paper
was read by GROBID (`grobid-0.9.1-crf`); the plausibility check fired on none. Checking-pass counts
are the verifier's raw verdicts per field, and the number of statements it could not place on a
row.

| paper | group | status | text source | fallback | calls | cost | wall (s) | checking pass: supported / wrong / missed / unplaced | unverifiable D.3 rows |
|---|---|---|---|---|---|---|---|---|---|
| achuthan_2023 | stress_v1 | full report | grobid-0.9.1-crf | none | 11 | $0.5451 | 169.4 | 79 / 5 / 0 / 3 | 0 |
| bakker_2012 | stress_v1 | full report | grobid-0.9.1-crf | none | 7 | $0.4945 | 145.2 | 67 / 5 / 10 / 6 | 0 |
| cattarinussi_2026 | stress_v1 | full report | grobid-0.9.1-crf | none | 9 | $0.6002 | 178.5 | 73 / 8 / 3 / 8 | 1 |
| dimitrova_2002 | stress_v1 | full report | grobid-0.9.1-crf | none | 10 | $0.4826 | 124.3 | 74 / 2 / 6 / 0 | 2 |
| hermans_2024 | stress_v1 | full report | grobid-0.9.1-crf | none | 9 | $0.6163 | 184.4 | 68 / 11 / 3 / 19 | 0 |
| ladouceur_2023 | stress_v1 | full report | grobid-0.9.1-crf | none | 8 | $0.7038 | 201.3 | 65 / 7 / 9 / 3 | 0 |
| li_2024 | stress_v1 | full report | grobid-0.9.1-crf | none | 13 | $0.4945 | 144.5 | 78 / 6 / 0 / 1 | 0 |
| maheu_2011 | stress_v1 | full report | grobid-0.9.1-crf | none | 11 | $0.5549 | 157.3 | 79 / 6 / 0 / 3 | 1 |
| silchenko_2023 | stress_v1 | methods_not_found | grobid-0.9.1-crf | none | 11 | $0.7504 | 174.6 | 73 / 12 / 0 / 0 | 1 |
| sims_2021 | stress_v1 | full report | grobid-0.9.1-crf | none | 16 | $0.6626 | 213.2 | 80 / 5 / 1 / 3 | 3 |
| yassa_2010 | stress_v1 | full report | grobid-0.9.1-crf | none | 11 | $0.5562 | 148.1 | 78 / 2 / 4 / 3 | 0 |
| gracia-tabuenca_2024 | hop case 1 | full report | grobid-0.9.1-crf | none | 8 | $0.5413 | 160.3 | 71 / 11 / 1 / 2 | 1 |
| shen_2013 | other in scope | full report | grobid-0.9.1-crf | none | 9 | $0.5089 | 138.1 | 82 / 1 / 0 / 0 | 0 |
| cabral_2017 | sfn_batch, unlabelled | not-fMRI stop | grobid-0.9.1-crf | none | 1 | $0.0557 | 7.1 | not run (stopped) | n/a |
| hagler_2019 (pipeline description) | sfn_batch, unlabelled | full report | grobid-0.9.1-crf | none | 32 | $1.0255 | 299.3 | 58 / 21 / 3 / 8 | 1 |
| smith_2013 (pipeline description) | sfn_batch, unlabelled | methods_not_found | grobid-0.9.1-crf | none | 69 | $1.9035 | 434.0 | 75 / 7 / 5 / 3 | 1 |
| cho_2021 | other in scope | full report | grobid-0.9.1-crf | none | 7 | $0.6709 | 198.1 | 68 / 11 / 2 / 20 | 0 |
| schwartz_2018 | other in scope | full report | grobid-0.9.1-crf | none | 15 | $0.7728 | 248.4 | 81 / 3 / 0 / 0 | 0 |
| marek_2022 | other in scope | full report | grobid-0.9.1-crf | none | 12 | $0.7605 | 252.4 | 80 / 2 / 8 / 13 | 0 |
| bassett_2011 | other in scope | full report | grobid-0.9.1-crf | none | 9 | $0.3976 | 99.1 | 82 / 0 / 2 / 0 | 1 |
| glasser_2013_hcp_pipelines (pipeline description) | other in scope | methods_not_found | grobid-0.9.1-crf | none | 54 | $1.3722 | 406.2 | 72 / 7 / 11 / 4 | 0 |
| smith_2013_rest_in_hcp | other in scope | methods_not_found | grobid-0.9.1-crf | none | 19 | $1.4509 | 280.6 | 77 / 0 / 12 / 5 | 1 |
| glasser2016_nature | other in scope | full report | grobid-0.9.1-crf | none | 11 | $0.5883 | 165.4 | 61 / 10 / 9 / 1 | 2 |
| greene_2022 | other in scope | full report | grobid-0.9.1-crf | none | 19 | $0.8041 | 217.7 | 72 / 14 / 0 / 5 | 0 |
| yang_2025 | other in scope | full report | grobid-0.9.1-crf | none | 7 | $0.5635 | 160.7 | 82 / 2 / 0 / 1 | 0 |
| gao_2026 | stress_v1 | not-fMRI stop | grobid-0.9.1-crf | none | 1 | $0.0566 | 7.2 | not run (stopped) | n/a |
| **total** | | | | | 389 | $17.9334 | 4915.4 | | |

**Cost.**
- This run: **$17.9334** metered, 389 calls, 4915.4 s.
- The 19 labelled papers' current records (corpus_grobid_v2): $11.5141, 187 calls.
- The current-code footprint, 45 papers: **$29.4475**.
- Not in the footprint: the same-code pypdf control (corpus_pypdf_v1, $12.1298), liu_2005's
  superseded GROBID record ($0.3649), and the attempts interrupted on 2026-11-06 (unmetered).

Sections 1 and 2 below are the census before this run.

## 1. Papers with a current-code report

**Definition.** A paper counts when at least one stored per-paper report under
`extractor_mvp/results/` (any vintage) re-renders byte for byte from its stored record with the
current code. `tested_lit/` holds PDFs and a DOI cache, no reports; no other folder in
`neurorepro/` holds one.

**Method** (scratch script, no model calls):
- Every `.md` under `results/` whose first line is `# Replication Protocol`: 267 reports.
- Its record: `papers/<id>.json`, `<id>.json` or `<id>.record.json` beside it; for a `_rerender`
  folder, the same in the folder without the suffix. For a hop-case report with no record beside it,
  every stored record with that paper id is tried, with the hop files beside the report merged in.
- Renderers: `full_report.render_record` (the batch and aespa-report paths) and, for hop cases, the
  `scripts/run_citation_hop.py` assembly.
- Outcome: 77 identical, 188 differ, 2 with no record (`unseen_2026-10-29`).

**Controls.**
- A one-character change to `render.to_report` turns all 41 identical protocol reports in the
  folders tried (corpus_pypdf_v1, heldout_sf_v1, batch_motion_corpus_v1) to "differs".
- The same change to `fmri_gate.to_not_fmri_report` turns gao_2026's 2 identical reports to
  "differs".

**De-duplication by DOI.**
- Key: the first DOI on page 1 (`doi_date_resolver._page1_dois`); else the first DOI in the first
  10,000 characters; else the PDF's sha256 (binder_1999, gao_2026, schwartz_2018).
- DOIs are compared in memory only and are not reproduced here.
- 47 paper PDFs in scope (macOS `._` metadata files excluded) are 45 distinct papers: cho_2021
  (`tested_lit/` and `multi_batch/`) and weber_2024 (`sfn_batch/` and `multi_batch/`) are one paper
  each.
- No two of the 20 counted papers share a DOI.

**Two tiers.** An identical re-render shows that the current renderer prints the stored record the
same way. It does not show that the record was extracted by the current code: the
batch_motion_corpus_v1 records (2026-10-27) carry no checking pass, fMRI gate or supplement record,
and render identically because the renderer prints nothing for absent sections. The second column
counts only records extracted at or after `4c3b4b4` (the last change to extraction before the
plausibility check `45a1878`, which alters only liu_2005's input).

| group | distinct papers in scope | current-code report (identical re-render) | extracted at or after `4c3b4b4` |
|---|---|---|---|
| labelled corpus | 19 | 19 | 19 |
| stress_v1 | 12 | 1 | 0 |
| sfn_batch, unlabelled | 3 | 0 | 0 |
| hop cases | 2 | 1 | 1 |
| other in scope | 10 | 0 | 0 |
| **total, de-duplicated by DOI** | **45** | **20** | **19** |

The groups overlap: poldrack_2015 is in the labelled corpus and is hop case 2, and the copy of
weber_2024 in `multi_batch/` is the labelled paper. Each is counted once in the total.

### Per group, with the vintages that re-render identically

**Labelled corpus (19 of 19).** In each case corpus_grobid_v1 (`4c3b4b4`) and corpus_pypdf_v1
(`cdca5c9`); also batch_motion_corpus_v1 and / or batch_motion_corpus_v1_inferred where noted (m),
heldout_sf_v1 (`35e4081`) where noted (h), corpus_grobid_v2 (`45a1878`) where noted (g2).
agtzidis_2020 (m), binder_1999 (m), braun_2015, chen_2015 (m), ciric_2017 (m), cole_2013 (m),
derosa_2025 (m), gordon_2014 (m), liu_2005 (m, h, g2), liu_2013 (m), mueller_2021 (m),
oconnor_2017 (m), poldrack_2015 (m), power_2014 (m), tang_2025 (m, h), vanderwal_2016 (m),
viduarre_2017, weber_2024 (m), wheaton_2004 (m, h).
liu_2005's corpus_grobid_v1 record (GROBID text before the plausibility check) also re-renders
identically; corpus_grobid_v2 replaces it.

**stress_v1 (1 of 12).** gao_2026: its not-fMRI stop report, stress_v1_fix1b and stress_v2
(2026-11-05).

**sfn_batch, unlabelled (0 of 3).** cabral_2017, hagler_2019, smith_2013 (the record's path is in
`sfn_batch/`; the PDF is now at `tested_lit/Smith_2013.pdf`).

**Hop cases (1 of 2).**
- Case 2, poldrack_2015: corpus_pypdf_v1's record ran the hop (1 hop, reference resolved, local
  PDF) and re-renders identically. corpus_grobid_v1's poldrack record has no deferral, so no hop.
  `hop_case2`'s own report differs.
- Case 1, gracia-tabuenca_2024: every stored report differs (hop_case1 to hop_case1_v11, their
  rerenders, batch_coverage_v3 and v4).

## 2. Papers in scope with no current-code report

What a "processed" count of 20 leaves out (25 distinct papers):

| folder | paper | what is stored |
|---|---|---|
| tested_lit/stress_v1 | achuthan_2023, bakker_2012, cattarinussi_2026, dimitrova_2002, hermans_2024, ladouceur_2023, li_2024, maheu_2011, silchenko_2023, sims_2021, yassa_2010 | reports that differ (stress_v1, stress_v1_rerun, stress_v1_fix*, stress_v2, stress_v3; 2026-11-05 code) |
| ~/Downloads (hop case 1) | gracia-tabuenca_2024 | reports that differ |
| ~/Downloads | shen_2013 | reports that differ (batch_coverage_v3 and v4); `unseen_2026-10-29` report has no record |
| tested_lit/sfn_batch | cabral_2017 | records, no per-paper report (batch_sfn to batch_sfn_v4) |
| tested_lit/sfn_batch | hagler_2019 | no record (read only as hop case 1's cited paper) |
| tested_lit (top level) | smith_2013 | records, no per-paper report (batch_sfn to batch_sfn_v3, fork_b_partA_probe) |
| tested_lit (top level) | cho_2021 (also in multi_batch) | records, no per-paper report (batch_smoke, batch_v6_delta) |
| tested_lit (top level) | schwartz_2018 | record, no per-paper report (batch_smoke) |
| tested_lit (top level) | bassett_2011, glasser_2013_hcp_pipelines, smith_2013_rest_in_hcp | no record |
| tested_lit/glasser2016 | glasser2016_nature | no record |
| tested_lit/multi_batch | marek_2022 | record, no per-paper report (batch_v6_delta) |
| tested_lit/multi_batch | greene_2022, yang_2025 | no record |

Of the 25: 13 have stored reports that differ, 5 have records but no stored per-paper report
(cabral_2017, smith_2013, cho_2021, schwartz_2018, marek_2022), and 7 have no record.

"Other in scope" (10): shen_2013, cho_2021, schwartz_2018, bassett_2011,
glasser_2013_hcp_pipelines, smith_2013_rest_in_hcp, glasser2016_nature, marek_2022, greene_2022,
yang_2025. Each column's group rows sum to one more than its total (46, 21, 20), because poldrack_2015 is
counted in both the labelled corpus and hop case 2; the 45 is 19 labelled + 12 stress_v1 + 3 sfn_batch unlabelled + gracia-tabuenca_2024 + these 10.

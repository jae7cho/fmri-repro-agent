# GROBID as a text source: the gate (2026-11-06)

Built in `84154b8` (`extractor_mvp/src/extractor_mvp/grobid_source.py`, `batch.load_text`). It is
flag-gated, and pypdf stays the default. No model calls were made.
- **The default layer is pypdf.** The default text layer is pypdf (`pdf_loader.load_pdf_text`), not
  pdftotext, so records name it `pypdf`.
- **What "pypdf text" means here:** the current loader with reflow. "GROBID text" is the TEI
  `<body>` flattened, as follows.
  - Each `<head>` and `<p>` goes on its own line.
  - `<ref type="bibr">` becomes `[n]`, n being the entry's position in the reference list (GROBID's
    `#b0` is 1), or the ref's own text when it has no target.
  - `<figure>`, `<table>` and `<back>` are excluded.
- **Quotes** are resolved with `span_resolver.resolve_quote` against each paper's whole text.

## Images

| image | version (`/api/version`) | architecture | size | used for |
|---|---|---|---|---|
| `lfoppiano/grobid:0.9.1-full` | 0.9.1 (revision 0.9.1) | amd64, `--platform linux/amd64` | 37.4 GB | everything below, except §5 |
| `lfoppiano/grobid:0.9.1-crf` | 0.9.1 (revision 0.9.1) | arm64, native | 1.7 GB | §5 |

- **Processing time:** the 33 PDFs behind the stored records went through the full image in 122.5
  s in all, with no fallback. The two PDFs already cached took 0 s; the rest took at most 5.2 s
  each.
- **Memory:** starting the CRF container beside the full one killed the full one (`OOMKilled`, exit
  137; Docker's VM has 8.3 GB). It was restarted after §5 and is running.

## 2. Citation test: cattarinussi_2026's 11 quotes on the bracketed flattening

All 11 resolve (`nuisance_regression` performed, regressor_list, tissue_regressors,
physio_regressors, detrend, filtering_integrated; `temporal_filtering` performed,
effective_band_hz, pass_type, relative_to_regression; `record.step_order`). The resolver's tolerant
tier already skips a bracketed marker. Nothing was stripped.

gordon_2014's 3 filtering quotes do not resolve on the bracketed flattening.
- The sentence comes out whole, with no page header, but each quote ends with the paper's
  author-year citation, which the flattening renders as `[5]`.
- Each quote up to its citation resolves.
- These 3 were not found on pypdf either, so they are in no "lost" count below.

## 3. Quote regression gate

- **Stored quotes:** every stored span's text in each record (found when the record was made), and
  every raw quote in its diagnostics that failed to resolve (not found then).
- **Label quotes:** every quote or verbatim cell of three or more words in the two workbooks.
- **Held-out papers:** counts only.
- **Lost:** found on pypdf and not on GROBID.
- **Cause:**
  - **A:** found on GROBID's body once a citation keeps its own text (i.e., lost to the `[n]`
    rendering, mostly author-year citations inside the quote).
  - **B:** found elsewhere in the TEI (outside `<body>`, or in a figure, table or note).
  - **C:** found nowhere in the TEI.
- Every loss failed as `quote_not_found`.

### batch_coverage_v4

| paper | quotes | found on pypdf | found on GROBID | lost | gained | lost by cause (A/B/C) |
|---|---|---|---|---|---|---|
| agtzidis_2020 | 16 | 16 | 9 | 7 | 0 | 0/0/7 |
| binder_1999 | 8 | 8 | 0 | 8 | 0 | 8/0/0 |
| braun_2015 | 21 | 21 | 21 | 0 | 0 |  |
| chen_2015 | 32 | 31 | 24 | 8 | 1 | 8/0/0 |
| ciric_2017 | 48 | 46 | 21 | 25 | 0 | 25/0/0 |
| cole_2013 | 15 | 14 | 7 | 7 | 0 | 7/0/0 |
| derosa_2025 | 23 | 23 | 21 | 2 | 0 | 2/0/0 |
| gordon_2014 | 22 | 16 | 14 | 2 | 0 | 2/0/0 |
| gracia-tabuenca_2024 | 27 | 27 | 25 | 2 | 0 | 2/0/0 |
| liu_2013 | 25 | 25 | 20 | 5 | 0 | 5/0/0 |
| mueller_2021 | 28 | 28 | 28 | 0 | 0 |  |
| oconnor_2017 | 17 | 17 | 17 | 0 | 0 |  |
| poldrack_2015 | 36 | 29 | 35 | 1 | 7 | 1/0/0 |
| power_2014 | 31 | 26 | 26 | 3 | 3 | 3/0/0 |
| shen_2013 | 23 | 23 | 23 | 0 | 0 |  |
| vanderwal_2016 | 26 | 26 | 2 | 24 | 0 | 24/0/0 |
| viduarre_2017 | 21 | 21 | 0 | 21 | 0 | 0/0/21 |
| weber_2024 | 31 | 31 | 31 | 0 | 0 |  |
| **total** | 450 | 428 | 324 | 115 | 11 | 87/0/28 |

### stress_v1

| paper | quotes | found on pypdf | found on GROBID | lost | gained | lost by cause (A/B/C) |
|---|---|---|---|---|---|---|
| Achuthan_2023 | 25 | 25 | 14 | 11 | 0 | 11/0/0 |
| Bakker_2012 | 5 | 5 | 4 | 1 | 0 | 1/0/0 |
| Cattarinussi_2026 | 0 | 0 | 0 | 0 | 0 |  |
| Dimitrova_2002 | 15 | 10 | 7 | 3 | 0 | 3/0/0 |
| Gao_2026 | 19 | 19 | 19 | 0 | 0 |  |
| Hermans_2024 | 37 | 37 | 13 | 24 | 0 | 2/0/22 |
| Ladouceur_2023 | 37 | 37 | 3 | 34 | 0 | 34/0/0 |
| Li_2024 | 23 | 20 | 19 | 4 | 3 | 4/0/0 |
| Maheu_2011 | 15 | 10 | 9 | 1 | 0 | 1/0/0 |
| Silchenko_2023 | 8 | 8 | 2 | 6 | 0 | 0/6/0 |
| Sims_2021 | 39 | 33 | 13 | 20 | 0 | 16/0/4 |
| Yassa_2010 | 18 | 18 | 10 | 8 | 0 | 8/0/0 |
| **total** | 241 | 222 | 113 | 112 | 3 | 80/6/26 |

### heldout_sf_v1 (held out: counts only)

| paper | quotes | found on pypdf | found on GROBID | lost | gained | lost by cause (A/B/C) |
|---|---|---|---|---|---|---|
| liu_2005 (held out) | 16 | 1 | 0 | 1 | 0 | 0/0/1 |
| tang_2025 (held out) | 26 | 25 | 21 | 4 | 0 | 4/0/0 |
| wheaton_2004 (held out) | 14 | 14 | 14 | 0 | 0 |  |
| **total** | 56 | 40 | 35 | 5 | 0 | 4/0/1 |

### motion_correction_labels_v1.xlsx

| paper | quotes | found on pypdf | found on GROBID | lost | gained | lost by cause (A/B/C) |
|---|---|---|---|---|---|---|
| agtzidis_2020 | 2 | 1 | 1 | 0 | 0 |  |
| binder_1999 | 2 | 2 | 1 | 1 | 0 | 1/0/0 |
| braun_2015 | 1 | 0 | 0 | 0 | 0 |  |
| chen_2015 | 1 | 1 | 0 | 1 | 0 | 1/0/0 |
| ciric_2017 | 3 | 3 | 2 | 1 | 0 | 1/0/0 |
| cole_2013 | 2 | 1 | 0 | 1 | 0 | 1/0/0 |
| derosa_2025 | 1 | 1 | 1 | 0 | 0 |  |
| gordon_2014 | 3 | 3 | 3 | 0 | 0 |  |
| liu_2005 (held out) | 1 | 0 | 0 | 0 | 0 |  |
| liu_2013 | 1 | 1 | 0 | 1 | 0 | 1/0/0 |
| mueller_2021 | 2 | 2 | 2 | 0 | 0 |  |
| oconnor_2017 | 1 | 1 | 1 | 0 | 0 |  |
| poldrack_2015 | 3 | 2 | 2 | 0 | 0 |  |
| power_2014 | 3 | 3 | 2 | 1 | 0 | 1/0/0 |
| tang_2025 (held out) | 1 | 1 | 0 | 1 | 0 | 1/0/0 |
| vanderwal_2016 | 1 | 1 | 0 | 1 | 0 | 1/0/0 |
| viduarre_2017 | 1 | 1 | 0 | 1 | 0 | 0/0/1 |
| wheaton_2004 (held out) | 1 | 1 | 1 | 0 | 0 |  |
| **total** | 30 | 25 | 16 | 9 | 0 | 8/0/1 |

### smoothing_filtering_labels_v1.xlsx

| paper | quotes | found on pypdf | found on GROBID | lost | gained | lost by cause (A/B/C) |
|---|---|---|---|---|---|---|
| agtzidis_2020 | 1 | 1 | 1 | 0 | 0 |  |
| binder_1999 | 1 | 1 | 0 | 1 | 0 | 1/0/0 |
| braun_2015 | 2 | 2 | 2 | 0 | 0 |  |
| chen_2015 | 3 | 2 | 2 | 0 | 0 |  |
| ciric_2017 | 2 | 1 | 1 | 0 | 0 |  |
| cole_2013 | 2 | 0 | 0 | 0 | 0 |  |
| derosa_2025 | 2 | 2 | 2 | 0 | 0 |  |
| gordon_2014 | 2 | 1 | 1 | 0 | 0 |  |
| liu_2005 (held out) | 2 | 1 | 0 | 1 | 0 | 0/0/1 |
| liu_2013 | 2 | 0 | 0 | 0 | 0 |  |
| mueller_2021 | 2 | 2 | 2 | 0 | 0 |  |
| poldrack_2015 | 2 | 1 | 1 | 0 | 0 |  |
| power_2014 | 3 | 1 | 1 | 0 | 0 |  |
| tang_2025 (held out) | 3 | 3 | 3 | 0 | 0 |  |
| vanderwal_2016 | 2 | 2 | 1 | 1 | 0 | 1/0/0 |
| viduarre_2017 | 2 | 2 | 0 | 2 | 0 | 0/0/2 |
| weber_2024 | 2 | 0 | 0 | 0 | 0 |  |
| wheaton_2004 (held out) | 2 | 2 | 2 | 0 | 0 |  |
| **total** | 37 | 24 | 19 | 5 | 0 | 2/0/3 |


Totals over the three record sets: 747 quotes, 690 found on pypdf, 472 on GROBID; 232 lost
(A 171, B 6, C 55) and 14 gained. Over the two label workbooks: 67 quotes, 49 on pypdf, 35 on
GROBID; 14 lost (A 10, C 4), none gained.

The C losses concentrate in a few papers:
- **viduarre_2017:** none of its 74 pypdf methods sentences (eight words or more) is in GROBID's
  body, and 25 are anywhere in its TEI.
- **Hermans_2024:** 22 C losses. 53 of its 69 methods sentences are in the body, and 62 anywhere in
  the TEI.
- **agtzidis_2020:** 7 C losses. 73 of 106 sentences are in the body, and 98 anywhere.
- **Sims_2021:** 4 C losses. 51 of 83 sentences are in the body, and 74 anywhere.
- **liu_2005 (held out):** 2 C losses (1 record, 1 label). Its GROBID body is 2,601 characters.

The 6 B losses are all Silchenko_2023's.

The list below identifies each lost quote by its record field or label column; quote text is not
reproduced here. Held-out papers' 7 losses are in the counts above only.
### Every quote found on pypdf and not on GROBID (co-adjudicated papers; by record field or label column)


**batch_coverage_v4 / agtzidis_2020**

- `steps[0].method.extraction.spans[0]` (C)
- `steps[1].performed.extraction.spans[0]` (C)
- `steps[2].target_space.extraction.spans[0]` (C)
- `steps[2].resolution_mm.extraction.spans[0]` (C)
- `steps[3].space.extraction.spans[0]` (C)
- `steps[5].performed.extraction.spans[0]` (C)
- `step_order_spans[0]` (C)

**batch_coverage_v4 / binder_1999**

- `steps[4].method.extraction.spans[0]` (A)
- `steps[6].performed.extraction.spans[0]` (A)
- `steps[6].cost_function.extraction.spans[0]` (A)
- `steps[8].target_space.extraction.spans[0]` (A)
- `steps[17].performed.extraction.spans[0]` (A)
- `steps[17].fwhm_mm.extraction.spans[0]` (A)
- `steps[17].kernel_type.extraction.spans[0]` (A)
- `software_mentions[0].extraction.spans[0]` (A)

**batch_coverage_v4 / chen_2015**

- `steps[0].performed.extraction.spans[0]` (A)
- `steps[0].n_nonsteadystate_discarded.extraction.spans[0]` (A)
- `steps[1].performed.extraction.spans[0]` (A)
- `steps[2].performed.extraction.spans[0]` (A)
- `steps[3].method.extraction.spans[0]` (A)
- `steps[9].method.extraction.spans[0]` (A)
- `steps[14].effective_band_hz.extraction.spans[0]` (A)
- `step_order_spans[0]` (A)

**batch_coverage_v4 / ciric_2017**

- `steps[2].method.extraction.spans[0]` (A)
- `steps[3].performed.extraction.spans[0]` (A)
- `steps[3].cost_function.extraction.spans[0]` (A)
- `steps[5].motion_expansion.extraction.spans[0]` (A)
- `steps[5].tissue_definition.extraction.spans[0]` (A)
- `steps[5].filtering_integrated.extraction.spans[0]` (A)
- `steps[6].performed.extraction.spans[0]` (A)
- `steps[8].performed.extraction.spans[0]` (A)
- `steps[9].performed.extraction.spans[0]` (A)
- `steps[9].target.extraction.spans[0]` (A)
- `steps[12].performed.extraction.spans[0]` (A)
- `steps[12].method.extraction.spans[0]` (A)
- `steps[13].performed.extraction.spans[0]` (A)
- `steps[13].n_components.extraction.spans[0]` (A)
- `steps[14].performed.extraction.spans[0]` (A)
- `steps[14].method.extraction.spans[0]` (A)
- `steps[15].performed.extraction.spans[0]` (A)
- `steps[15].criterion.extraction.spans[0]` (A)
- `software_mentions[0].extraction.spans[0]` (A)
- `software_mentions[1].extraction.spans[0]` (A)
- `software_mentions[4].extraction.spans[0]` (A)
- `software_mentions[5].extraction.spans[0]` (A)
- `software_mentions[7].extraction.spans[0]` (A)
- `software_mentions[9].extraction.spans[0]` (A)
- `step_order_spans[0]` (A)

**batch_coverage_v4 / cole_2013**

- `steps[0].performed.extraction.spans[0]` (A)
- `steps[1].method.extraction.spans[0]` (A)
- `steps[2].target_space.extraction.spans[0]` (A)
- `steps[3].performed.extraction.spans[0]` (A)
- `steps[14].performed.extraction.spans[0]` (A)
- `software_mentions[0].extraction.spans[0]` (A)
- `step_order_spans[0]` (A)

**batch_coverage_v4 / derosa_2025**

- `software_mentions[5].extraction.spans[0]` (A)
- `software_mentions[6].extraction.spans[0]` (A)

**batch_coverage_v4 / gordon_2014**

- `steps[12].tissue_regressors.extraction.spans[0]` (A)
- `steps[12].tissue_definition.extraction.spans[0]` (A)

**batch_coverage_v4 / gracia-tabuenca_2024**

- `base_pipeline.extraction.deferrals[0].span` (A)
- `steps[1].method.extraction.deferrals[0].span` (A)

**batch_coverage_v4 / liu_2013**

- `base_pipeline.extraction.value.version.extraction.spans[0]` (A)
- `base_pipeline.extraction.spans[0]` (A)
- `software_mentions[0].extraction.spans[0]` (A)
- `software_mentions[1].extraction.spans[0]` (A)
- `software_mentions[2].extraction.spans[0]` (A)

**batch_coverage_v4 / poldrack_2015**

- `steps[4].method.extraction.deferrals[0].span` (A)

**batch_coverage_v4 / power_2014**

- `steps[3].target_space.extraction.spans[0]` (A)
- `steps[3].resolution_mm.extraction.spans[0]` (A)
- `steps[4].motion_expansion.extraction.spans[0]` (A)

**batch_coverage_v4 / vanderwal_2016**

- `base_pipeline.extraction.spans[0]` (A)
- `steps[0].method.extraction.deferrals[0].span` (A)
- `steps[1].target_space.extraction.spans[0]` (A)
- `steps[2].performed.extraction.spans[0]` (A)
- `steps[2].regressor_list.extraction.spans[0]` (A)
- `steps[2].detrend.extraction.spans[0]` (A)
- `steps[2].filtering_integrated.extraction.spans[0]` (A)
- `steps[3].performed.extraction.spans[0]` (A)
- `steps[3].effective_band_hz.extraction.spans[0]` (A)
- `steps[6].method.extraction.deferrals[0].span` (A)
- `steps[6].parameters.extraction.deferrals[0].span` (A)
- `steps[6].manual_edits.extraction.deferrals[0].span` (A)
- `steps[9].transform.extraction.deferrals[0].span` (A)
- `steps[9].nonlinear_transform_type.extraction.deferrals[0].span` (A)
- `steps[9].method.extraction.deferrals[0].span` (A)
- `steps[9].cost_function.extraction.deferrals[0].span` (A)
- `steps[9].interpolation.extraction.deferrals[0].span` (A)
- `steps[13].performed.extraction.spans[0]` (A)
- `steps[13].n_components.extraction.spans[0]` (A)
- `software_mentions[0].extraction.spans[0]` (A)
- `software_mentions[1].extraction.spans[0]` (A)
- `software_mentions[2].extraction.spans[0]` (A)
- `step_order_spans[0]` (A)
- `step_order_spans[1]` (A)

**batch_coverage_v4 / viduarre_2017**

- `base_pipeline.extraction.deferrals[0].span` (C)
- `steps[0].performed.extraction.spans[0]` (C)
- `steps[0].method.extraction.spans[0]` (C)
- `steps[4].method.extraction.deferrals[0].span` (C)
- `steps[4].parameters.extraction.deferrals[0].span` (C)
- `steps[4].manual_edits.extraction.deferrals[0].span` (C)
- `steps[5].method.extraction.deferrals[0].span` (C)
- `steps[5].tissue_classes.extraction.deferrals[0].span` (C)
- `steps[6].method.extraction.deferrals[0].span` (C)
- `steps[7].source.extraction.deferrals[0].span` (C)
- `steps[7].method.extraction.deferrals[0].span` (C)
- `steps[8].transform.extraction.deferrals[0].span` (C)
- `steps[8].nonlinear_transform_type.extraction.deferrals[0].span` (C)
- `steps[8].method.extraction.deferrals[0].span` (C)
- `steps[8].cost_function.extraction.deferrals[0].span` (C)
- `steps[8].interpolation.extraction.deferrals[0].span` (C)
- `steps[9].target.extraction.deferrals[0].span` (C)
- `steps[9].method.extraction.deferrals[0].span` (C)
- `steps[12].performed.extraction.spans[0]` (C)
- `software_mentions[0].extraction.spans[0]` (C)
- `step_order_spans[0]` (C)

**stress_v1 / Achuthan_2023**

- `steps[1].target_space.extraction.spans[0]` (A)
- `steps[2].performed.extraction.spans[0]` (A)
- `steps[2].tissue_classes.extraction.spans[0]` (A)
- `steps[3].space.extraction.spans[0]` (A)
- `steps[5].performed.extraction.spans[0]` (A)
- `steps[5].tissue_regressors.extraction.spans[0]` (A)
- `steps[14].mask_source.extraction.spans[0]` (A)
- `steps[16].performed.extraction.spans[0]` (A)
- `software_mentions[0].extraction.spans[0]` (A)
- `software_mentions[1].extraction.spans[0]` (A)
- `step_order_spans[1]` (A)

**stress_v1 / Bakker_2012**

- `software_mentions[0].extraction.spans[0]` (A)

**stress_v1 / Dimitrova_2002**

- `steps[8].target_space.extraction.spans[0]` (A)
- `steps[13].performed.extraction.spans[0]` (A)
- `steps[16].convention.extraction.spans[0]` (A)

**stress_v1 / Hermans_2024**

- `base_pipeline.extraction.value.version.extraction.spans[0]` (C)
- `base_pipeline.extraction.spans[0]` (C)
- `steps[0].method.extraction.deferrals[0].span` (C)
- `steps[0].reference.extraction.deferrals[0].span` (C)
- `steps[0].interpolation.extraction.deferrals[0].span` (C)
- `steps[0].interpolation_order.extraction.deferrals[0].span` (C)
- `steps[1].transform.extraction.deferrals[0].span` (C)
- `steps[1].nonlinear_transform_type.extraction.deferrals[0].span` (C)
- `steps[1].method.extraction.deferrals[0].span` (C)
- `steps[1].cost_function.extraction.deferrals[0].span` (C)
- `steps[1].interpolation.extraction.deferrals[0].span` (C)
- `steps[3].source.extraction.deferrals[0].span` (C)
- `steps[3].method.extraction.deferrals[0].span` (C)
- `steps[3].tool.extraction.deferrals[0].span` (C)
- `steps[7].method.extraction.deferrals[0].span` (C)
- `steps[7].parameters.extraction.deferrals[0].span` (C)
- `steps[7].manual_edits.extraction.deferrals[0].span` (C)
- `steps[8].method.extraction.deferrals[0].span` (C)
- `steps[8].tissue_classes.extraction.deferrals[0].span` (C)
- `steps[9].target.extraction.deferrals[0].span` (C)
- `steps[9].method.extraction.deferrals[0].span` (C)
- `steps[10].target_space.extraction.spans[0]` (A)
- `software_mentions[0].extraction.spans[0]` (C)
- `software_mentions[1].extraction.spans[0]` (A)

**stress_v1 / Ladouceur_2023**

- `base_pipeline.extraction.value.version.extraction.spans[0]` (A)
- `base_pipeline.extraction.spans[0]` (A)
- `steps[0].method.extraction.spans[0]` (A)
- `steps[1].performed.extraction.spans[0]` (A)
- `steps[1].transform.extraction.deferrals[0].span` (A)
- `steps[1].nonlinear_transform_type.extraction.deferrals[0].span` (A)
- `steps[1].method.extraction.deferrals[0].span` (A)
- `steps[1].cost_function.extraction.deferrals[0].span` (A)
- `steps[1].interpolation.extraction.deferrals[0].span` (A)
- `steps[2].performed.extraction.spans[0]` (A)
- `steps[2].tool.extraction.deferrals[0].span` (A)
- `steps[3].target_space.extraction.spans[0]` (A)
- `steps[4].performed.extraction.spans[0]` (A)
- `steps[4].regressor_list.extraction.spans[0]` (A)
- `steps[4].tissue_regressors.extraction.spans[0]` (A)
- `steps[4].detrend.extraction.spans[0]` (A)
- `steps[4].filtering_integrated.extraction.spans[0]` (A)
- `steps[5].performed.extraction.spans[0]` (A)
- `steps[5].applied_to.extraction.spans[0]` (A)
- `steps[5].effective_band_hz.extraction.spans[0]` (A)
- `steps[6].criterion.extraction.spans[0]` (A)
- `steps[6].remediation.extraction.spans[0]` (A)
- `steps[6].interpolation_method.extraction.spans[0]` (A)
- `steps[9].method.extraction.deferrals[0].span` (A)
- `steps[9].parameters.extraction.deferrals[0].span` (A)
- `steps[10].method.extraction.deferrals[0].span` (A)
- `steps[11].target.extraction.deferrals[0].span` (A)
- `steps[11].method.extraction.deferrals[0].span` (A)
- `software_mentions[0].extraction.spans[0]` (A)
- `software_mentions[1].extraction.spans[0]` (A)
- `software_mentions[2].extraction.spans[0]` (A)
- `step_order_spans[0]` (A)
- `step_order_spans[1]` (A)
- `step_order_spans[2]` (A)

**stress_v1 / Li_2024**

- `steps[12].performed.extraction.spans[0]` (A)
- `steps[12].motion_expansion.extraction.spans[0]` (A)
- `steps[12].tissue_regressors.extraction.spans[0]` (A)
- `software_mentions[1].extraction.spans[0]` (A)

**stress_v1 / Maheu_2011**

- `steps[16].convention.extraction.spans[0]` (A)

**stress_v1 / Silchenko_2023**

- `steps[3].performed.extraction.spans[0]` (B)
- `steps[3].method.extraction.spans[0]` (B)
- `steps[3].tissue_classes.extraction.spans[0]` (B)
- `steps[12].performed.extraction.spans[0]` (B)
- `steps[12].tissue_regressors.extraction.spans[0]` (B)
- `software_mentions[0].extraction.spans[0]` (B)

**stress_v1 / Sims_2021**

- `base_pipeline.extraction.spans[0]` (A)
- `steps[0].method.extraction.deferrals[0].span` (A)
- `steps[1].performed.extraction.spans[0]` (A)
- `steps[1].criterion.extraction.spans[0]` (A)
- `steps[6].method.extraction.deferrals[0].span` (A)
- `steps[6].parameters.extraction.deferrals[0].span` (A)
- `steps[6].manual_edits.extraction.deferrals[0].span` (A)
- `steps[7].method.extraction.deferrals[0].span` (A)
- `steps[8].performed.extraction.spans[0]` (C)
- `steps[8].source.extraction.spans[0]` (C)
- `steps[9].transform.extraction.deferrals[0].span` (A)
- `steps[9].nonlinear_transform_type.extraction.deferrals[0].span` (A)
- `steps[9].method.extraction.deferrals[0].span` (A)
- `steps[9].cost_function.extraction.deferrals[0].span` (A)
- `steps[9].interpolation.extraction.deferrals[0].span` (A)
- `steps[10].target.extraction.deferrals[0].span` (A)
- `steps[10].method.extraction.deferrals[0].span` (A)
- `steps[12].target_surface.extraction.spans[0]` (C)
- `software_mentions[3].extraction.spans[0]` (C)
- `step_order_spans[0]` (A)

**stress_v1 / Yassa_2010**

- `base_pipeline.extraction.value.version.extraction.spans[0]` (A)
- `base_pipeline.extraction.spans[0]` (A)
- `steps[2].target_space.extraction.spans[0]` (A)
- `steps[3].performed.extraction.spans[0]` (A)
- `software_mentions[0].extraction.spans[0]` (A)
- `software_mentions[1].extraction.spans[0]` (A)
- `step_order_spans[1]` (A)
- `step_order_spans[2]` (A)

**motion_correction_labels_v1.xlsx / binder_1999**

- `Labels.method_quote` (A)

**motion_correction_labels_v1.xlsx / chen_2015**

- `Labels.method_quote` (A)

**motion_correction_labels_v1.xlsx / ciric_2017**

- `Labels.method_quote` (A)

**motion_correction_labels_v1.xlsx / cole_2013**

- `Labels.nonrigid_transform_verbatim` (A)

**motion_correction_labels_v1.xlsx / liu_2013**

- `Labels.method_quote` (A)

**motion_correction_labels_v1.xlsx / power_2014**

- `Labels.interpolation_combined_verbatim` (A)

**motion_correction_labels_v1.xlsx / vanderwal_2016**

- `Labels.method_quote` (A)

**motion_correction_labels_v1.xlsx / viduarre_2017**

- `Labels.method_quote` (C)

**smoothing_filtering_labels_v1.xlsx / binder_1999**

- `Smoothing.quote` (A)

**smoothing_filtering_labels_v1.xlsx / vanderwal_2016**

- `Filtering.quote` (A)

**smoothing_filtering_labels_v1.xlsx / viduarre_2017**

- `Smoothing.quote` (C)
- `Filtering.quote` (C)


## 4. Methods slice on GROBID text, 19 corpus papers

`find_methods_section` on each text. A changed end heading is marked when the slice source changed
(header vs full-text fallback) or the end heading differs once section numbers are set aside.
Held-out rows give numbers only, with "changed" computed on the real headings.

| paper | pypdf: header → end | chars | share | GROBID: header → end | chars | share | end changed |
|---|---|---|---|---|---|---|---|
| agtzidis_2020 | 2. Methods → 3. Results | 16,141 | 0.240 | Methods → Results | 14,633 | 0.371 | no |
| binder_1999 | Processing → Acknowledgments | 13,914 | 0.187 | methods_not_found (full text) | 48,768 | 1.000 | **yes** |
| braun_2015 | Methods → end_of_text | 14,354 | 0.296 | Methods → end_of_text | 3,407 | 0.104 | no |
| chen_2015 | Methods and Analysis → Results | 16,075 | 0.210 | methods_not_found (full text) | 38,684 | 1.000 | **yes** |
| ciric_2017 | Materials and methods → Results | 25,824 | 0.278 | Materials and methods → Results | 23,411 | 0.384 | no |
| cole_2013 | ONLINE METHODS → Supplementary Material | 18,626 | 0.235 | ONLINE METHODS → end_of_text | 23,077 | 0.386 | **yes** |
| derosa_2025 | 2. Methods → 3. Results | 45,407 | 0.426 | Methods → Results | 35,043 | 0.493 | no |
| gordon_2014 | METHODS → DISCUSSION | 25,592 | 0.425 | METHODS → RESULTS | 13,635 | 0.347 | **yes** |
| liu_2005 (held out) | fallback_full_text | 50,672 | 1.000 | fallback_full_text | 2,601 | 1.000 | no |
| liu_2013 | METHODS → RESULTS | 9,920 | 0.184 | methods_not_found (full text) | 36,776 | 1.000 | **yes** |
| mueller_2021 | METHODS → ACKNOWLEDGMENTS | 8,815 | 0.117 | methods_not_found (full text) | 42,549 | 1.000 | **yes** |
| oconnor_2017 | Methods → Availability of supporting data | 29,769 | 0.560 | Methods → end_of_text | 23,076 | 0.848 | **yes** |
| poldrack_2015 | Methods → References | 42,806 | 0.407 | Methods → end_of_text | 42,025 | 0.559 | **yes** |
| power_2014 | Methods → Results | 15,444 | 0.122 | Methods → Results | 14,426 | 0.154 | no |
| tang_2025 (held out) | header_match | 9,072 | 0.168 | header_match | 8,769 | 0.344 | no |
| vanderwal_2016 | 2. Materials and Methods → 3. Results | 14,615 | 0.218 | Materials and Methods → Results | 12,246 | 0.318 | no |
| viduarre_2017 | Methods → end_of_text | 11,013 | 0.234 | methods_not_found (full text) | 32,409 | 1.000 | **yes** |
| weber_2024 | Methods → Results | 11,650 | 0.153 | Methods → Results | 8,658 | 0.236 | no |
| wheaton_2004 (held out) | header_match | 8,743 | 0.153 | header_match | 7,571 | 0.211 | no |

End heading changed (section numbers aside): 9 of 19.

On GROBID text, binder_1999, chen_2015, liu_2013, mueller_2021 and viduarre_2017 are
methods_not_found, for two reasons:
- **binder_1999, chen_2015, liu_2013, mueller_2021:** GROBID's body has a heading that runs the
  section name into the first subsection's ("Methods and Analysis Participants", "METHODS ANALYSIS
  APPROACH", "METHODS 28andMe Experimental Protocol", "METHOD Pilot Study: Task-Unrelated
  Thought"). The finder's heading pattern must match a whole line.
- **viduarre_2017:** no heading in its body names methods, analysis, processing or procedures.

Other changes:
- poldrack_2015 and oconnor_2017 now end at the end of the text: their end headings (References;
  Availability of supporting data) are outside `<body>`.
- cole_2013 no longer ends at "Supplementary Material".
- gordon_2014 ends at RESULTS (13,635 characters) where pypdf ran to DISCUSSION (25,592).

## 5. CRF against full, on three papers

| paper | full | CRF | identical | where they differ |
|---|---|---|---|---|
| gordon_2014 | 39,263 chars, 66 lines | 39,262 chars, 66 lines | no | 78 runs, 87 characters of full replaced or removed, 86 of CRF replaced or added, in 8 line blocks; all 78 inside a `[..]` citation marker |
| cattarinussi_2026 | 39,236 chars | 39,236 chars | yes | — |
| power_2014 | 93,440 chars, 158 lines | 93,393 chars, 158 lines | no | 86 runs, 162 characters of full replaced or removed, 115 of CRF replaced or added, in 23 line blocks; all 86 inside a `[..]` citation marker |

With every `[..]` marker emptied, gordon_2014 and power_2014 are identical between the two images.
CRF times: gordon_2014 9.6 s, cattarinussi_2026 1.9 s, power_2014 2.2 s.

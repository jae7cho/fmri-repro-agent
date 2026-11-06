# GROBID as a text source: the gate after three flattening fixes (2026-11-06)

Follows `docs/findings/grobid_gate.md` (v1). Built in `e157475`. The fixes are flag-gated, and pypdf stays the default
text source. No model calls were made.

The three fixes:
1. **Citations as printed:** a `<ref type="bibr">` becomes its own text, verbatim. It is bracketed as
   `[..]` only when that text is bare numerals (digits, ranges, comma lists, with an optional
   trailing comma). The reference index is never used.
2. **Back matter read:** `<back>` is flattened after `<body>`. Only `<listBibl>` is excluded, along
   with `<figure>` and `<table>` as before.
3. **Merged methods headings (GROBID text only):** a heading line whose first words are a top-level
   methods keyword opens the methods section.

Unchanged from v1:
- **Text compared:** "pypdf text" is the current loader with reflow. Quotes are resolved with
  `span_resolver.resolve_quote` against each paper's whole text.
- **Image:** `lfoppiano/grobid:0.9.1-full`, with the TEI cache from v1. The full container is
  running.

## 1. Diagnosis before the inclusion: where the cause-B and cause-C text sits

These are the 65 quotes v1 lost to causes B and C: 61 in records, 4 in the label workbooks. Each
was searched in one TEI region at a time, with citations as their own text. The regions were:
- the `<body>`;
- `<back>`, split into `<div type="annex">` and the other prose divs;
- `<figure>` captions, `<table>`s and `<note>`s;
- the `<teiHeader>`;
- the `<listBibl>`.

A quote found in no region is "absent". For those, the longest leading run of its words found
anywhere in the TEI is given.

| paper | quotes | `<back>` annex div | other `<back>` div | `<figure>` | `<table>` | `<note>` | absent from the TEI as a run |
|---|---|---|---|---|---|---|---|
| viduarre_2017 | 24 | 24 | 0 | 0 | 0 | 0 | 0 |
| Silchenko_2023 | 6 | 0 | 0 | 6 | 0 | 0 | 0 |
| Hermans_2024 | 22 | 0 | 0 | 0 | 0 | 0 | 22 (leading 23 of 28 or 50 words) |
| agtzidis_2020 | 7 | 0 | 0 | 0 | 0 | 0 | 7 (leading 11 to 36 of 18 to 60 words) |
| Sims_2021 | 4 | 0 | 0 | 0 | 0 | 0 | 4 (leading 26 to 51 of 29 to 54 words) |
| liu_2005 (held out) | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| **total** | 65 | 24 | 0 | 6 | 0 | 0 | 35 |

**viduarre_2017 (PNAS):** all 24 quotes sit in `<back>`. GROBID's `<back>` holds, in order:
1. the acknowledgements;
2. a funding `<listOrg>`;
3. a `<div type="annex">` headed "Methods" and "Estimation and Statistical Testing";
4. the references.

**The v1 cause-C tally was wrong for viduarre.** v1's whole-TEI search text repeated each `<div>`'s
text ahead of its paragraphs. Each viduarre quote therefore matched twice, and `resolve_quote`
returned `quote_ambiguous`, which v1 counted as not found. Re-running v1's search on the 59 cause-C
quotes gives:
- viduarre: `quote_ambiguous` for 24;
- every other paper: `quote_not_found` for 35.

The searches in this report join each region's blocks once.

**Silchenko_2023:** the 6 quotes sit in a single 2,034-character `<figure>`.
- Its only child is a `<figDesc>`: no `<head>`, no `<label>`, no `<graphic>`.
- It opens like prose, not with "Fig", and pypdf has its opening words in the running text.
- So GROBID has filed a prose paragraph as a figure. Figures stay excluded, so these 6 stay lost
  (cause F below).

**The 35 "absent" quotes begin in the body and diverge partway through.** For each, the words up to
the divergence point resolve in the body:
- **Hermans_2024 (22) and Sims_2021 (4): GROBID rewrites the ref text of a same-author year list.**
  - The paper prints a list such as "(Author et al., 2019, 2020)". GROBID splits it into two refs,
    and the second ref's own text repeats the author: `(Author et al., , 2020`.
  - Sims_2021's three divergences are the same pattern, in lists of two and three years.
  - The text GROBID gives is not the paper's, so emitting refs verbatim cannot recover these
    (cause R below).
- **agtzidis_2020 (7): the multiplication sign.**
  - pypdf reads "×" as the glyph name `/C2`, and the stored quotes carry `/C2`.
  - GROBID reads it as `Â`.
  - `span_resolver` already documents the `/C2` mangle as unhandled (cause G below).
- **liu_2005 (held out, 2):** counts only.

Of the 65:
- 24 are recoverable by reading `<back>`, and all 24 are recovered (§3).
- None sits in a `<note>` or `<table>`, in a non-annex `<back>` div, in the `<teiHeader>` or in the
  `<listBibl>`.

## 2. The fixes as built

**Fix 1: citations (`grobid_source._ref_marker`).**
- A ref's own text is emitted verbatim.
- It is bracketed only when it fully matches bare numerals: `\d+` or a range `\d+ - \d+` (hyphen, en
  dash or em dash, spaces allowed), in a comma list, with an optional trailing comma. Examples:
  cattarinussi_2026's "4 , 5" and "5 -7"; cole_2013's "1,".
- **One addition beyond the request: a numeral inside a bracket the paper already opened stays as
  printed.**
  - weber_2024 prints "[5, 25, 35]", and GROBID splits it into refs reading "[5,", "25," and "35]".
  - Bracketing the middle ref would print "[5,[25,]35]".
  - A bracket counts as open when the paragraph's text so far has an unclosed `[`.

**Fix 2: back matter (`grobid_source.flatten_tei`).**
- `<body>` then `<back>` are walked in document order.
- `<head>` and `<p>` become lines.
- `<figure>`, `<table>` and `<listBibl>` are skipped.
- A funding `<listOrg>` yields nothing, since it holds no `<head>` or `<p>`.

**Fix 3: the methods finder (`methods_finder.find_methods_section(text, text_source=...)`).**
- With `text_source="grobid"`, a line also opens the methods section when all three hold:
  - its first words are a top-level methods keyword (the same vocabulary as the whole-line pattern:
    "Methods", "X and Methods", "Methods and X", "Online Methods", "Experimental Procedures");
  - it has at most 8 words;
  - it does not end with a period.
- The earliest candidate still wins.
- `batch.process_paper` passes the parser (`"grobid"` or `"pypdf"`).
- `full_report` passes it on to `citation_hop.extract_data_release` for call R's methods slice.
- On pypdf text, behaviour is unchanged.

**Tests (all synthetic prose):**
- `tests/test_grobid_source.py`: 22 tests. The fixtures are:
  - the gordon_2014 and cattarinussi_2026 structures (cattarinussi gains a pair ref and a range
    ref);
  - a new `viduarre_2017_structure.tei.xml` with the annex methods in `<back>`;
  - inline TEI for the weber, cole and `listBibl`-heading shapes.
- `tests/test_methods_finder.py`: 9 new cases.
- `tests/test_full_report.py`: 2 new cases. The slice and call R are told the source.

**Checks:**
- **Suite:** 799 passed, 2 skipped (live). `ruff`, `ruff format` and `mypy` are clean.
- **Render identity gate (stored records rendered by `render.to_report`, working tree vs HEAD
  `4c14054`):**
  - Derived first: no change, since the pypdf path passes `text_source="pypdf"` and nothing in
    `render.py` changed.
  - Run: `batch_a1_acceptance` 19 identical, `batch_coverage_v4` 18 identical, `stress_v1` 12
    identical, so 49/49.
  - **Positive control:** wrapping `render.to_report` to append one character gave `stress_v1: 0
    identical, 12 changed`; the file was then restored and checked against its copy. A first
    attempt perturbed `full_report.render_record`, which the gate does not call, and it gave 12
    identical. It is reported here and does not count as a control.
- **Mutations: 18, each diff shown non-empty before its run, all killed.**
  - Fix 1 (8): never bracket; ignore an open bracket; always bracket; index from the target; no comma
    lists; no ranges; no trailing comma; a bracket never closes.
  - Fix 2 (3): `listBibl` read; body only; back first.
  - Fix 3 (4): the prefix rule on every source; no word cap; no period guard; a later prefix match
    wins.
  - Threading (3): the batch slice not told; call R not told; the data-release slice ignoring the
    source.
  - `listBibl` read, the period guard and the later-prefix mutant survived the first pass. Three
    tests were added and the three were re-run killed.
  - The `listBibl` mutant is equivalent on the corpus: none of the 36 cached TEIs has a `<head>` or
    `<p>` inside `<listBibl>`. Its test uses a schema-legal synthetic `<head>`.

## 3. Citation test

**cattarinussi_2026:** the 11 quotes that fail on pypdf (record `stress_v3/fix1_893c3f6`) all
resolve on the v2 flattening, through `batch.load_text` with source `grobid-0.9.1-full`:
- `nuisance_regression`: performed, regressor_list, tissue_regressors, physio_regressors, detrend,
  filtering_integrated;
- `temporal_filtering`: performed, effective_band_hz, pass_type, relative_to_regression;
- `record.step_order`.

**gordon_2014:** the three `temporal_filtering` quotes all resolve: performed, effective_band_hz,
relative_to_regression.
- Each had failed `extraction_quote_unresolved:quote_not_found` in `batch_coverage_v4`.
- Each still fails on pypdf.
- On GROBID each now resolves through its closing author-year citation, which is printed as the
  paper prints it.

## 4. Quote regression gate

The sources are the same as in v1: stored spans and unresolved diagnostic quotes in the three record
sets, and quote cells of three or more words in the two workbooks.
- **Lost:** found on pypdf and not on GROBID.
- **Gained:** the reverse.
- **v1 columns:** repeated from `grobid_gate.md` for comparison.

Every remaining loss fails as `quote_not_found`. By cause:
- **N** (bare numerals bracketed): the paper prints superscript or bare reference numbers, pypdf
  puts them inline unbracketed, and the stored quote carries them (in the shape "networks1,2 were"). Fix 1
  bracketing them, e.g. `[1,][2]`, is what loses these. They resolve on the same flattening with the
  numerals left unbracketed.
- **R:** GROBID's ref text for a same-author year list (§1).
- **G:** the multiplication sign (§1).
- **F:** prose filed as a `<figure>` (§1).
- **X:** held out, absent from the TEI as a run. Counts only.

**Totals, three record sets:**
- 747 quotes, 690 found on pypdf.
- On GROBID, 472 found in v1 and 663 in v2.
- **Lost: 232 in v1, 52 in v2.** By cause: N 12, R 26, G 7, F 6, X 1.
- Gained: 14 in v1, 25 in v2.

**Totals, two label workbooks:**
- 67 quotes, 49 found on pypdf.
- On GROBID, 35 found in v1 and 46 in v2.
- **Lost: 14 in v1, 3 in v2.** By cause: N 2, X 1.
- Gained: none.

Of the 55 losses, 7 are on held-out papers (counts only):
- tang_2025: 5, all N (4 in heldout_sf_v1, 1 label).
- liu_2005: 2 X (1 record, 1 label).

### batch_coverage_v4

| paper | quotes | found on pypdf | found on GROBID v1 | found on GROBID v2 | lost v1 | lost v2 | gained v2 | lost v2 by cause (N/R/G/F/X) |
|---|---|---|---|---|---|---|---|---|
| agtzidis_2020 | 16 | 16 | 9 | 9 | 7 | 7 | 0 | 0/0/7/0/0 |
| binder_1999 | 8 | 8 | 0 | 8 | 8 | 0 | 0 |  |
| braun_2015 | 21 | 21 | 21 | 21 | 0 | 0 | 0 |  |
| chen_2015 | 32 | 31 | 24 | 32 | 8 | 0 | 1 |  |
| ciric_2017 | 48 | 46 | 21 | 46 | 25 | 0 | 0 |  |
| cole_2013 | 15 | 14 | 7 | 7 | 7 | 7 | 0 | 7/0/0/0/0 |
| derosa_2025 | 23 | 23 | 21 | 23 | 2 | 0 | 0 |  |
| gordon_2014 | 22 | 16 | 14 | 21 | 2 | 0 | 5 |  |
| gracia-tabuenca_2024 | 27 | 27 | 25 | 27 | 2 | 0 | 0 |  |
| liu_2013 | 25 | 25 | 20 | 25 | 5 | 0 | 0 |  |
| mueller_2021 | 28 | 28 | 28 | 28 | 0 | 0 | 0 |  |
| oconnor_2017 | 17 | 17 | 17 | 17 | 0 | 0 | 0 |  |
| poldrack_2015 | 36 | 29 | 35 | 35 | 1 | 1 | 7 | 1/0/0/0/0 |
| power_2014 | 31 | 26 | 26 | 29 | 3 | 0 | 3 |  |
| shen_2013 | 23 | 23 | 23 | 23 | 0 | 0 | 0 |  |
| vanderwal_2016 | 26 | 26 | 2 | 26 | 24 | 0 | 0 |  |
| viduarre_2017 | 21 | 21 | 0 | 21 | 21 | 0 | 0 |  |
| weber_2024 | 31 | 31 | 31 | 31 | 0 | 0 | 0 |  |
| **total** | 450 | 428 | 324 | 429 | 115 | 15 | 16 | 8/0/7/0/0 |

### stress_v1

| paper | quotes | found on pypdf | found on GROBID v1 | found on GROBID v2 | lost v1 | lost v2 | gained v2 | lost v2 by cause (N/R/G/F/X) |
|---|---|---|---|---|---|---|---|---|
| Achuthan_2023 | 25 | 25 | 14 | 25 | 11 | 0 | 0 |  |
| Bakker_2012 | 5 | 5 | 4 | 5 | 1 | 0 | 0 |  |
| Cattarinussi_2026 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| Dimitrova_2002 | 15 | 10 | 7 | 10 | 3 | 0 | 0 |  |
| Gao_2026 | 19 | 19 | 19 | 19 | 0 | 0 | 0 |  |
| Hermans_2024 | 37 | 37 | 13 | 15 | 24 | 22 | 0 | 0/22/0/0/0 |
| Ladouceur_2023 | 37 | 37 | 3 | 37 | 34 | 0 | 0 |  |
| Li_2024 | 23 | 20 | 19 | 23 | 4 | 0 | 3 |  |
| Maheu_2011 | 15 | 10 | 9 | 15 | 1 | 0 | 5 |  |
| Silchenko_2023 | 8 | 8 | 2 | 2 | 6 | 6 | 0 | 0/0/0/6/0 |
| Sims_2021 | 39 | 33 | 13 | 30 | 20 | 4 | 1 | 0/4/0/0/0 |
| Yassa_2010 | 18 | 18 | 10 | 18 | 8 | 0 | 0 |  |
| **total** | 241 | 222 | 113 | 199 | 112 | 32 | 9 | 0/26/0/6/0 |

### heldout_sf_v1 (held out: counts only)

| paper | quotes | found on pypdf | found on GROBID v1 | found on GROBID v2 | lost v1 | lost v2 | gained v2 | lost v2 by cause (N/R/G/F/X) |
|---|---|---|---|---|---|---|---|---|
| **total** | 56 | 40 | 35 | 35 | 5 | 5 | 0 | 4/0/0/0/1 |

### motion_correction_labels_v1.xlsx

| paper | quotes | found on pypdf | found on GROBID v1 | found on GROBID v2 | lost v1 | lost v2 | gained v2 | lost v2 by cause (N/R/G/F/X) |
|---|---|---|---|---|---|---|---|---|
| agtzidis_2020 | 2 | 1 | 1 | 1 | 0 | 0 | 0 |  |
| binder_1999 | 2 | 2 | 1 | 2 | 1 | 0 | 0 |  |
| braun_2015 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| chen_2015 | 1 | 1 | 0 | 1 | 1 | 0 | 0 |  |
| ciric_2017 | 3 | 3 | 2 | 3 | 1 | 0 | 0 |  |
| cole_2013 | 2 | 1 | 0 | 0 | 1 | 1 | 0 | 1/0/0/0/0 |
| derosa_2025 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |  |
| gordon_2014 | 3 | 3 | 3 | 3 | 0 | 0 | 0 |  |
| liu_2005 (held out) | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| liu_2013 | 1 | 1 | 0 | 1 | 1 | 0 | 0 |  |
| mueller_2021 | 2 | 2 | 2 | 2 | 0 | 0 | 0 |  |
| oconnor_2017 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |  |
| poldrack_2015 | 3 | 2 | 2 | 2 | 0 | 0 | 0 |  |
| power_2014 | 3 | 3 | 2 | 3 | 1 | 0 | 0 |  |
| tang_2025 (held out) | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 1/0/0/0/0 |
| vanderwal_2016 | 1 | 1 | 0 | 1 | 1 | 0 | 0 |  |
| viduarre_2017 | 1 | 1 | 0 | 1 | 1 | 0 | 0 |  |
| wheaton_2004 (held out) | 1 | 1 | 1 | 1 | 0 | 0 | 0 |  |
| **total** | 30 | 25 | 16 | 23 | 9 | 2 | 0 | 2/0/0/0/0 |

### smoothing_filtering_labels_v1.xlsx

| paper | quotes | found on pypdf | found on GROBID v1 | found on GROBID v2 | lost v1 | lost v2 | gained v2 | lost v2 by cause (N/R/G/F/X) |
|---|---|---|---|---|---|---|---|---|
| agtzidis_2020 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |  |
| binder_1999 | 1 | 1 | 0 | 1 | 1 | 0 | 0 |  |
| braun_2015 | 2 | 2 | 2 | 2 | 0 | 0 | 0 |  |
| chen_2015 | 3 | 2 | 2 | 2 | 0 | 0 | 0 |  |
| ciric_2017 | 2 | 1 | 1 | 1 | 0 | 0 | 0 |  |
| cole_2013 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| derosa_2025 | 2 | 2 | 2 | 2 | 0 | 0 | 0 |  |
| gordon_2014 | 2 | 1 | 1 | 1 | 0 | 0 | 0 |  |
| liu_2005 (held out) | 2 | 1 | 0 | 0 | 1 | 1 | 0 | 0/0/0/0/1 |
| liu_2013 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| mueller_2021 | 2 | 2 | 2 | 2 | 0 | 0 | 0 |  |
| poldrack_2015 | 2 | 1 | 1 | 1 | 0 | 0 | 0 |  |
| power_2014 | 3 | 1 | 1 | 1 | 0 | 0 | 0 |  |
| tang_2025 (held out) | 3 | 3 | 3 | 3 | 0 | 0 | 0 |  |
| vanderwal_2016 | 2 | 2 | 1 | 2 | 1 | 0 | 0 |  |
| viduarre_2017 | 2 | 2 | 0 | 2 | 2 | 0 | 0 |  |
| weber_2024 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| wheaton_2004 (held out) | 2 | 2 | 2 | 2 | 0 | 0 | 0 |  |
| **total** | 37 | 24 | 19 | 23 | 5 | 1 | 0 | 0/0/0/0/1 |

Held-out papers' 7 losses are in the counts above only. Quote text is not reproduced.

### Every quote still lost (co-adjudicated papers; by record field or label column)

**batch_coverage_v4 / agtzidis_2020**

- `steps[0].method.extraction.spans[0]` (G)
- `steps[1].performed.extraction.spans[0]` (G)
- `steps[2].target_space.extraction.spans[0]` (G)
- `steps[2].resolution_mm.extraction.spans[0]` (G)
- `steps[3].space.extraction.spans[0]` (G)
- `steps[5].performed.extraction.spans[0]` (G)
- `step_order_spans[0]` (G)

**batch_coverage_v4 / cole_2013**

- `steps[0].performed.extraction.spans[0]` (N)
- `steps[1].method.extraction.spans[0]` (N)
- `steps[2].target_space.extraction.spans[0]` (N)
- `steps[3].performed.extraction.spans[0]` (N)
- `steps[14].performed.extraction.spans[0]` (N)
- `software_mentions[0].extraction.spans[0]` (N)
- `step_order_spans[0]` (N)

**batch_coverage_v4 / poldrack_2015**

- `steps[4].method.extraction.deferrals[0].span` (N)

**stress_v1 / Hermans_2024**

- `base_pipeline.extraction.value.version.extraction.spans[0]` (R)
- `base_pipeline.extraction.spans[0]` (R)
- `steps[0].method.extraction.deferrals[0].span` (R)
- `steps[0].reference.extraction.deferrals[0].span` (R)
- `steps[0].interpolation.extraction.deferrals[0].span` (R)
- `steps[0].interpolation_order.extraction.deferrals[0].span` (R)
- `steps[1].transform.extraction.deferrals[0].span` (R)
- `steps[1].nonlinear_transform_type.extraction.deferrals[0].span` (R)
- `steps[1].method.extraction.deferrals[0].span` (R)
- `steps[1].cost_function.extraction.deferrals[0].span` (R)
- `steps[1].interpolation.extraction.deferrals[0].span` (R)
- `steps[3].source.extraction.deferrals[0].span` (R)
- `steps[3].method.extraction.deferrals[0].span` (R)
- `steps[3].tool.extraction.deferrals[0].span` (R)
- `steps[7].method.extraction.deferrals[0].span` (R)
- `steps[7].parameters.extraction.deferrals[0].span` (R)
- `steps[7].manual_edits.extraction.deferrals[0].span` (R)
- `steps[8].method.extraction.deferrals[0].span` (R)
- `steps[8].tissue_classes.extraction.deferrals[0].span` (R)
- `steps[9].target.extraction.deferrals[0].span` (R)
- `steps[9].method.extraction.deferrals[0].span` (R)
- `software_mentions[0].extraction.spans[0]` (R)

**stress_v1 / Silchenko_2023**

- `steps[3].performed.extraction.spans[0]` (F)
- `steps[3].method.extraction.spans[0]` (F)
- `steps[3].tissue_classes.extraction.spans[0]` (F)
- `steps[12].performed.extraction.spans[0]` (F)
- `steps[12].tissue_regressors.extraction.spans[0]` (F)
- `software_mentions[0].extraction.spans[0]` (F)

**stress_v1 / Sims_2021**

- `steps[8].performed.extraction.spans[0]` (R)
- `steps[8].source.extraction.spans[0]` (R)
- `steps[12].target_surface.extraction.spans[0]` (R)
- `software_mentions[3].extraction.spans[0]` (R)

**motion_correction_labels_v1.xlsx / cole_2013**

- `Labels.nonrigid_transform_verbatim` (N)

## 5. Methods slice, 19 papers

`find_methods_section` was run on pypdf text, and on GROBID v2 text with `text_source="grobid"`.
- **End changed:** the found/not-found state or the end heading differs from the pypdf run, with
  section numbers ignored ("3. Results" = "Results").
- **Held-out papers:** headings are withheld.
- **v1's last column:** its `methods_not_found` came from a heading GROBID had merged, or, for
  viduarre, from a methods section filed in `<back>`.

| paper | pypdf: header | ends at | characters | share | GROBID v2: header | ends at | characters | share | GROBID v1 ended at | end changed from pypdf |
|---|---|---|---|---|---|---|---|---|---|---|
| agtzidis_2020 | `2. Methods` | 3. Results | 16,141 | 0.240 | `Methods` | Results | 14,894 | 0.361 | Results | no |
| binder_1999 | `Processing` | Acknowledgments | 13,914 | 0.187 | `METHOD Pilot Study: Task-Unrelated Thought` | end_of_text | 11,474 | 0.221 | methods_not_found | **yes** |
| braun_2015 | `Methods` | end_of_text | 14,354 | 0.296 | `Methods` | end_of_text | 5,684 | 0.163 | end_of_text | no |
| chen_2015 | `Methods and Analysis` | Results | 16,075 | 0.210 | `Methods and Analysis Participants` | Results | 13,571 | 0.329 | methods_not_found | no |
| ciric_2017 | `Materials and methods` | Results | 25,824 | 0.278 | `Materials and methods` | Results | 24,437 | 0.376 | Results | no |
| cole_2013 | `ONLINE METHODS` | Supplementary Material | 18,626 | 0.235 | `ONLINE METHODS` | ACKNOWLEDGEMENTS | 23,079 | 0.382 | end_of_text | **yes** |
| derosa_2025 | `2. Methods` | 3. Results | 45,407 | 0.426 | `Methods` | Results | 35,637 | 0.484 | Results | no |
| gordon_2014 | `METHODS` | DISCUSSION | 25,592 | 0.425 | `METHODS` | RESULTS | 13,759 | 0.333 | RESULTS | **yes** |
| liu_2005 (held out) | methods_not_found | (withheld) | 50,672 | 1.000 | methods_not_found | (withheld) | 3,068 | 1.000 | (withheld) | no |
| liu_2013 | `METHODS` | RESULTS | 9,920 | 0.184 | `METHODS ANALYSIS APPROACH` | RESULTS | 9,477 | 0.247 | methods_not_found | no |
| mueller_2021 | `METHODS` | ACKNOWLEDGMENTS | 8,815 | 0.117 | `METHODS 28andMe Experimental Protocol` | ACKNOWLEDGMENTS | 8,506 | 0.185 | methods_not_found | no |
| oconnor_2017 | `Methods` | Availability of supporting data | 29,769 | 0.560 | `Methods` | Funding | 23,074 | 0.765 | end_of_text | **yes** |
| poldrack_2015 | `Methods` | References | 42,806 | 0.407 | `Methods` | Acknowledgements | 42,026 | 0.533 | end_of_text | **yes** |
| power_2014 | `Methods` | Results | 15,444 | 0.122 | `Methods` | Results | 14,657 | 0.149 | Results | no |
| tang_2025 (held out) | (withheld) | (withheld) | 9,072 | 0.168 | (withheld) | (withheld) | 8,768 | 0.318 | (withheld) | no |
| vanderwal_2016 | `2. Materials and Methods` | 3. Results | 14,615 | 0.218 | `Materials and Methods` | Results | 12,518 | 0.304 | Results | no |
| viduarre_2017 | `Methods` | end_of_text | 11,013 | 0.234 | `Methods` | end_of_text | 2,987 | 0.082 | methods_not_found | no |
| weber_2024 | `Methods` | Results | 11,650 | 0.153 | `Methods` | Results | 8,649 | 0.218 | Results | no |
| wheaton_2004 (held out) | (withheld) | (withheld) | 8,743 | 0.153 | (withheld) | (withheld) | 7,600 | 0.200 | (withheld) | no |

**Every paper with a methods slice on pypdf still has one on GROBID.** That is 16 of 16; liu_2005
is `methods_not_found` on both. In v1, 5 of the 16 had none.

The end heading changed on 5 of 19, against 9 in v1. These five are the papers whose slice ends at a
heading that GROBID places differently:
- **gordon_2014:** on pypdf no line after METHODS matches the end-heading pattern before
  DISCUSSION, so the slice runs on to DISCUSSION. GROBID
  has RESULTS as a `<head>`, so the slice ends there, 13,759 characters long against 25,592.
- **poldrack_2015:** GROBID has no "References" heading, since the reference list is `<listBibl>`
  with no `<head>`. The `<back>` acknowledgements follow the methods directly, so the slice ends at
  "Acknowledgements": 42,026 characters against 42,806.
- **oconnor_2017:** GROBID's `<back>` puts the funding div before the availability div. The slice
  ends at "Funding", one heading earlier: 23,074 characters against 29,769.
- **cole_2013:** GROBID puts "ACKNOWLEDGEMENTS" before the "Supplementary Material" line. The slice ends at the acknowledgements: 23,079 characters against 18,626.
- **binder_1999:** GROBID's text has no "Acknowledgments" heading line after the methods, so the
  slice runs to the end of the text: 11,474 characters, share 0.221. On pypdf it is 13,914
  characters, ending at "Acknowledgments". binder also opens differently:
  - on GROBID, at the merged "METHOD Pilot Study: Task-Unrelated Thought";
  - on pypdf, which has no whole-line METHOD heading, at the subsection heading "Processing".

Fix 3 restored four slices:
- chen_2015, liu_2013 and mueller_2021 now end at the same heading as on pypdf.
- binder_1999 has a slice again, with the changed end above.

Fix 2 restored viduarre_2017:
- Its slice starts at the annex "Methods" heading and runs to the end of the text.
- It is 2,987 characters (share 0.082). On pypdf, the slice also runs from "Methods" to the end of the
  text: 11,013 characters.

## 6. CRF vs full, after fix 1

Both images report version 0.9.1, revision 0.9.1, from `/api/version` on 2026-11-06 (§5 of v1).
- **Inputs:** the cached TEIs from that run (`extractor_mvp/.grobid_cache/<sha256>.<image>.0.9.1.tei.xml`),
  flattened with the v2 code. The CRF container was not started again.
- **Image versions:** `lfoppiano/grobid:0.9.1-full` reports 0.9.1, and `lfoppiano/grobid:0.9.1-crf`
  reports 0.9.1.

| paper | full | CRF | result |
|---|---|---|---|
| gordon_2014 | 41,346 characters | 41,346 characters | identical |
| cattarinussi_2026 | 41,081 characters | 41,081 characters | identical |
| power_2014 | 98,151 characters | 98,098 characters | differs: one run, 53 characters, line 161 of 168 |

**Gordon and Power no longer differ in their citations.** In v1 they differed only inside citation
markers (78 and 86 runs). With each ref printed as its own text, none of those differences
remains.

**power_2014's remaining difference is one 9-word paragraph in `<back>`.** The full TEI has a
`<div type="conflict">` (a competing-interests statement) that the CRF TEI does not contain
anywhere. The body, the annex and every citation are identical.

## 7. Memory

Docker Desktop's VM still has 8.3 GB. Its memory setting was not changed, and this task started no
second container. The full container (`grobid`, port 8070) is running.

## 8. Against the flip criterion

- **Lost quotes at or near zero: not met.** 52 of the 690 quotes found on pypdf are lost in the
  record sets, and 3 of 49 in the label workbooks. The 55 have four causes:
  - N, 14: fix 1's bracketing of bare numerals that pypdf prints inline;
  - R, 26: GROBID's own ref text for same-author year lists;
  - G, 7: the multiplication sign;
  - F, 6: prose filed as a figure;
  - X, 2: held out, absent from the TEI as a run.
- **Every paper with a methods slice on pypdf still has one: met** (16 of 16).
- **gordon_2014's three filtering quotes found: met.**

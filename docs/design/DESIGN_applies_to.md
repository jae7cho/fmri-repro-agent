# DESIGN: `applies_to` on first-hop values

Status: designed 2026-11-05 (the author's request of that date). Stage 1 built 2026-11-11 with the
author's forks A1, B1 (with the normalized same-string rule), C2, D1, E2 and F1, no re-run (§8).
Stage 2, the re-run of the variant papers from a pinned worktree, follows.

## 1. What changes

The citation hop already records, for each field of a cited paper, a list of
`(value, verbatim_quote, applies_to)` entries, where `applies_to` is the cited paper's own words for
the variant and "all" is the ordinary case (`DESIGN_citation_hop.md` §3;
`extractor_mvp/src/extractor_mvp/citation_hop.py:526-532` `HopVariant`, the prompt at
`citation_hop.py:539-543`, the render at `render.py:1053-1058`). This design gives the first hop
(i.e., the paper's own report) the same structure. Any step value may carry `applies_to`. That is the
paper's own words for what the value applies to:
- a derived measure (e.g., ALFF, ReHo)
- an analysis or part of the paper (e.g., Part III)
- a data type (e.g., task-fMRI, rest-fMRI)
- a scanner or site
- a named preprocessing variant (e.g., one of a paper's regression combinations)

A value that applies to all of the paper's data has `applies_to` = "all", which is what every value
is today.

It replaces `multiple_pipelines` as a separate flag. Whether a paper preprocesses its data in more
than one way is no longer asked as its own question; it is read off the values (a paper has
variants when any value has `applies_to` other than "all").

**Why the flag goes.** `multiple_pipelines` is one record-level yes/missing answer, asked of the
checking pass (`verifier.py:80-87`) and rendered as one warning line above the steps
(`render.py:802-823`, stored at `batch.py:466` and `batch.py:517`). It says that variants exist,
not which values differ or what each applies to, so a reader still cannot reproduce either branch.
On the stored records it is also unreliable in both directions:
- ciric_2017 (`batch_coverage_v4`): "yes", count 14. The prompt itself says a benchmark of
  strategies applied to the same data, studied as the object of the paper, is not this.
- power_2014: "yes", no count.
- chen_2015, gracia-tabuenca_2024 (`batch_coverage_v4`) and Silchenko_2023 (`stress_v2`):
  missing, though each states different preprocessing for different parts of its data (§3).

The value-level structure carries what the flag was asking about, and a value that is wrong for part
of the data becomes visible where it sits.

## 2. The structure

Each first-hop field keeps its `ProvenancedField` and its two arms. What the extraction arm can
hold when the paper states different values for different parts of its data is fork A (§5). Under
either branch, every value the paper states carries:

- `value` (the field's type, as now)
- `spans` (the quote, resolved as now)
- `applies_to: str`, the paper's own words, default "all"
- `applies_to_spans`, the sentence that ties the value to that part, when it is not the value's own
  sentence (chen_2015 names ReHo and its unsmoothed input in one sentence; gracia-tabuenca_2024's
  censoring sentence is the task-fMRI paragraph's, and its rest-fMRI steps are a separate sentence).

`applies_to` is quote-checked like the value: its words must appear in the quote or in
`applies_to_spans`. A label that does not resolve is shown as unverified. It is never dropped, and
never replaced with "all".

The same applies to `record.step_order`. An order the paper states for one part of its work only
(power_2014) carries that part's words. `step_order_source` stays as it is for an order that holds
throughout.

The extraction prompts gain one paragraph, the hop's own wording for the first hop:
- When the text gives different values for a field for different measures, analyses, data types,
  scanners or named variants, return each value with its `applies_to`.
- Never choose one value.
- Never write "all" for a value the text ties to a part of its data.

Every prompt that changes is re-pinned (the extraction, temporal/volume, spatial and checking-pass
hashes).

## 3. The cases

Each is described from the stored record and the paper's methods. The labels to score against are
the author's to key (§6), not this design's.

- **chen_2015 (ALFF/fALFF vs ReHo), a derived measure.** The paper smooths for its amplitude
  measures (ALFF and fALFF, 6 mm Gaussian). It derives ReHo, and its vertex-wise connectivity graphs,
  from data that were band-pass filtered but not smoothed.
  - The stored record (`batch_coverage_v4/papers/chen_2015.json`) has `spatial_smoothing.performed`
    true, `fwhm_mm` 6.0 and `kernel_type` gaussian, all as "all". That is wrong for ReHo, and nothing
    on the report says so.
  - Under this design, `spatial_smoothing` carries two entries: performed true, 6 mm Gaussian,
    applies_to "ALFF and fALFF"; and performed false, applies_to "ReHo".
  - `temporal_filtering.effective_band_hz` (0.01 to 0.1 Hz) holds for all three measures and stays
    "all".
- **gracia-tabuenca_2024 (task vs rest censoring), a data type.** The paper preprocesses task-fMRI
  and rest-fMRI separately.
  - Its FD censoring threshold of 0.9 mm sits in the task-fMRI description. Rest-fMRI is described as
    having additional steps (initial volumes removed, normalization, regression, its own filter band)
    in a separate sentence.
  - The stored record has `scrub.threshold` 0.9 and `remediation` censor as "all", which is the task
    value given to rest.
  - Under this design the scrub fields carry applies_to "task-fMRI". Rest-fMRI's censoring is either
    stated in this paper under "rest-fMRI" or deferred (this paper defers to Hagler et al. 2019, and
    the hop's own variants then apply on the second hop).
- **power_2014 (Parts I to II vs III order of operations), an analysis.** The order of processing
  operations is not the same throughout the paper.
  - Part III replaces censored frames after nuisance regression and before frequency filtering.
  - The paper also states that the regression/filtering order changed from the authors' earlier
    report.
  - The stored record's step order is `partial`, with 3 spans and no part named.
  - Under this design `record.step_order` carries one entry per stated order, each with the part it
    holds for, in the paper's words ("Part III", and the words the paper uses for the processing of
    Parts I and II).
- **Silchenko_2023 (regression variants), named variants.** The paper computes tissue-specific signal
  regressors three ways, as three named combinations of WM/CSF signals from different whole-brain
  masks, and reports results under each.
  - The stored record (`stress_v2`) has one `tissue_regressors` value and the flag missing.
  - Under this design `nuisance_regression.tissue_regressors` and `tissue_definition` carry one
    entry per combination, `applies_to` the paper's own name for it. One name ties the two fields of
    a variant together (fork B).
- **ciric_2017 (14 benchmark models), fork C.** The paper's object of study is a comparison of 14
  participant-level confound regression models on the same data.
  - The stored record flattens them into one set of "all" values: `nuisance_regression`
    friston24, `compcor` with variant and 10 components, `ica_denoise` AROMA, `despike` 3dDespike,
    `scrub` FD 0.2 with spectral interpolation.
  - No single model uses all of these, so the record describes a pipeline the paper never ran.
  - Either answer under fork C ends that.

## 4. Render

A field whose values are all "all" renders exactly as now. A field with variants renders the hop's
shape (`render.py:1053-1058`) on the first hop:

    - fwhm_mm: differs by what it applies to
        - ALFF and fALFF: 6.0   [from paper]  «…»   [check: supported]
        - ReHo: not performed   [from paper]  «…»   [check: supported]

- **Each variant line carries its own state, quote and checking-pass verdict.** An `applies_to`
  whose words did not resolve adds "(what it applies to was not found in the text, unverified)".
- **Header line.** The `> ⚠ More than one preprocessing variant is described` line
  (`render.py:823`) is replaced by one line derived from the values. It names each part a value is
  tied to and the fields that differ, e.g., "Values differ by: task-fMRI, rest-fMRI (scrub)". It
  appears only when some value is not "all".
- **Step order.** Each order is shown under "Order stated in:" with its part.
- **Completeness and the COBIDAS rows.** A field with variants is counted once, under the weakest
  state among its variants (fork D's default). A COBIDAS row is addressed only when each of its
  variants is.
- **Stored records.** A record written before this carries no `applies_to` and keeps its stored
  `multiple_pipelines` answer. It renders as it did, old warning line included, so the identity gate
  over a1, coverage_v4 and stress_v1 stays 49/49 (ciric_2017's and power_2014's stored "yes" lines
  included).

## 5. Scoring against labels that carry `applies_to`

The label files today hold one value per paper per field (e.g.,
`ground_truth/base_pipeline_labels_v1.csv`, `target_space_labels_v1.csv`), and the scorers compare
one prediction to one label (`extractor_mvp/score_target_space.py:179`). Labels gain an `applies_to`
column, default "all", with one row per variant.

- **Matching a predicted variant to a label variant.** The model's words and the labeler's will not
  be the same string. A predicted variant matches a label variant when its value quote, or its
  `applies_to_spans`, overlaps the label's supporting quote in the paper (span overlap after
  resolution, the resolver the scorer already trusts). Failing that, the labeler's `applies_to`
  aliases are used (fork E).
- **Per label variant.** Each label variant is one of:
  - matched, value correct
  - matched, value wrong
  - missed (no predicted variant matches it)
- **Per predicted variant.** One that matches no label variant is spurious.
- **Two scope errors, each its own class, not mixed into value errors:**
  - **Collapsed:** the prediction has one "all" value equal to one label variant's value.
    gracia-tabuenca_2024's 0.9 mm and chen_2015's 6 mm are this shape today. It is scored wrong, not
    correct: the reader would apply it to data it does not describe.
  - **Split:** the prediction has variants where the label says "all".
- **Field correct.** A field is correct only when every label variant is matched with the correct
  value and no predicted variant is spurious. Variant-level counts are reported beside the
  field-level ones, never instead of them.
- **Existing labels.** A label with no `applies_to` is "all". Against it, a predicted variant set is
  a split unless the labeler re-keys the paper. The five case papers are re-keyed before any score
  that includes them is reported.
- **Step order.** A label order carries its part too. A predicted order with no part, against a
  label with parts, is collapsed.

## 6. Forks for the author

- **A. How a field with variants is held.**
  - (A1) A new extraction arm, `Varied[T]`: two or more `(value, spans, applies_to)` entries and no
    single value. Recommended: the field records what the paper states, and no code that reads
    `Extracted.value` can silently take one variant as the paper's.
  - (A2) The hop's convention as is: the field's own value is the one that holds for all data, else
    MISSING_FROM_PAPER, with the variants beside it. This matches the hop exactly. However, it records
    a stated field as missing from the paper, the false-missing that 0.5.0's `SpecifiedTerm` retype
    removed (`src/fmri_repro/spec/preprocessing.py:75-87`).
- **B. Whether variants are named once per record.**
  - (B1) Free text per value.
  - (B2) A record-level list of variants (each with the paper's words and the sentence that
    introduces it), referenced by id from each value. B2 ties Silchenko_2023's two regression fields
    of one combination together, and gives the header line one name per variant. B1 is simpler and
    is the hop's shape.
- **C. ciric_2017's 14 models.**
  - (C1) One `applies_to` per model. This is faithful, and a reader can rebuild any one model.
    However, it is about 14 entries on each of 5 or more fields, and the output grows with it (the
    checking pass already reached 6,727 to 10,110 output tokens on Ladouceur_2023). Its labels need
    the same 14 rows.
  - (C2) A single entry, `applies_to` "varied across compared models", with the sentence that states
    the comparison and no value. The report says the paper compares models and does not describe
    one, and every confound field reads so. This is cheap and true, but does not let a reader rebuild
    a model.
  - Under either, the flattened "all" set the record holds today is gone.
- **D. How a field with variants counts toward completeness.**
  - (D1) Under its weakest variant (default above).
  - (D2) As specified if any variant is specified.
  - (D3) Counted once per variant. D3 inflates the denominators of papers with variants.
- **E. Matching `applies_to` words when quotes do not overlap.**
  - (E1) A labeler-written alias list per paper.
  - (E2) Unmatched, counted as a miss plus a spurious entry.
  - E1 costs labeling time; E2 counts a wording difference as two errors.
- **F. What the checking pass judges.**
  - (F1) It judges `applies_to` as part of the value: "wrong" when the value does not hold for the
    part named, "missed" when the paper ties a value to a part the draft gave as "all". This replaces
    the `multiple_pipelines` question.
  - (F2) A separate per-field scope verdict beside the value verdict.
  - F1 keeps one verdict per line; F2 says which half was wrong.

## 7. What it touches when built

- **Schema:** a minor version bump. A migration gives every stored value `applies_to` "all"; fork A
  decides the arm.
- **Prompts:** the extraction, temporal/volume and spatial prompts, and the checking-pass prompt
  (the `multiple_pipelines` question removed, fork F's wording added), all re-pinned.
- **Code:**
  - `coverage_fields.py:825`'s `multiple_pipelines` spec
  - the verifier's record field (`verifier.py:145`, `:386-402`)
  - `batch.py:466` and `:517`
  - the render's header line and variant lines
  - the scorers, and the label CSVs' `applies_to` column
- **Gate:** identity over a1 (19), coverage_v4 (18) and stress_v1 (12) holds by the stored-records
  rule in §4. The five case papers are re-run from a pinned worktree after the labels are re-keyed.

## 8. Stage 1 as built (2026-11-11)

The forks the author chose: A1, B1 with a normalized match (the prompt also tells the model to reuse
the identical phrase for a part across fields), C2, D1, E2, F1. No model call was made.

- **Schema 0.7.0** (additive, a pure re-stamp hop). `Varied[T]` holds one or more `Variant[T]`
  entries (value, spans, `applies_to`, `applies_to_spans`, `applies_to_verified`) and
  `variants_dropped`. No variant is "all", and no two share an `applies_to` under
  `provenance.normalize_applies_to` (case, dashes, "&", punctuation, spacing, a leading "the"). A
  value-less entry is only the single "varied across compared models" entry (C2). The inference arm
  of a varied field is `NOT_APPLICABLE`, as for an extracted one, and every inference writer skips it.
  `step_order_source` gains "by_part", with `step_order_parts` (kinds, part, sentences).
- **The model's output.** `StepFieldResult` adds a "varied" status to the extraction call's six
  Layer-2 fields and temporal standardization, and to every field of calls T and S. The base-pipeline
  fields, the motion call, the hop and the checking pass keep `FieldExtractionResult`, so their
  schemas do not change. Each variant goes through `_process_field` as an extracted field would. One
  whose value or quote fails is dropped and counted, never shown. One surviving variant stays varied
  and is never collapsed to "all".
- **Prompts.** One paragraph (`prompt_rules.VARIANT_RULES`) in the extraction, temporal/volume and
  spatial prompts. It takes no example from a corpus paper, because §3's case papers are scored
  against it in Stage 2. Call T asks `step_order_parts`. The checking pass judges a `<field>[<part>]`
  line for its part. "Missed" now also covers a value the paper ties to a part the draft gives for
  all, and the `multiple_pipelines` question is gone (`RECORD_SPECS` removed). All five prompt
  hashes are re-pinned with dated notes.
- **Render.** The variant lines and the "Values differ by" header are as in §4. A parameter of a step
  whose `performed` varies is shown "not performed" for the parts that say so. Completeness and the
  COBIDAS rows count a varied field under its weakest variant (`FieldRow.coverage_status`):
  - an unverified part is the unverifiable gap `applies_to_unverified`;
  - C2 has its own bucket, "varied across compared models".

  Not in §4: the pseudo-code shows one block per part, each varied field at that part's value, and
  `?` where a field states nothing for the part.
- **Scoring** (`applies_to_scoring.py`). The classes are those of §5. "Overlap" is tested by resolving
  each sentence against the other (span_resolver), so no paper text is needed. On
  `ground_truth/smoothing_filtering_labels_v1.xlsx` against the stored `batch_coverage_v4`, these come
  out collapsed: chen_2015 and ciric_2017 (smoothing), and chen_2015 and power_2014 (filtering).
  tang_2025 has no record in that vintage. One comparison rule was added: equality skips a value the
  record's schema did not have (`pass_type` before 0.6.3), which is no evidence either way.
- **Labels.** The smoothing/filtering workbook already carries `applies_to`. The label CSVs
  (`base_pipeline_labels_v1.csv`, `target_space_labels_v1.csv`) gain no column here: none of §3's
  cases varies in those fields, and the files are being edited elsewhere. The scrub, nuisance and
  step-order labels of the case papers are the author's to key (§6) before Stage 2 scores them.
- **Gate.** 68 of 68 stored reports are identical against `868ec27`: a1 19, coverage_v4 18,
  stress_v1 12 (the 49 of §7) and corpus_grobid_v1 19. A positive control changed 12 of 12.

## 9. Stage 2b (2026-11-11, from Stage 2's findings)

The author's items, as built. No re-run of the 45.

1. **Compared models** (supersedes fork C2 as first built).
   - When each model is described: one variant per model, `applies_to` the model's name.
   - Only when the variation is stated without description: the null "varied across compared
     models" entry.
   - The phrase is recognised in `value` or in `applies_to`, and normalised to the null form.
   - A compared-models entry beside described variants is dropped, with the reason
     `varied_compared_entry_beside_described_variants`.
   - **Pseudo-code:** with more than four parts that differ only on confound fields (nuisance
     regression, CompCor, ICA denoising, despiking, scrubbing), the common steps are printed once
     and the parts follow as a table, one row per part and one column per differing field.
2. **The part rules,** in `PREPROCESSING_RULES` and so in the extraction prompts and the checking pass.
   - Preprocessing applied before a derived measure (ALFF, fALFF, ReHo, FC), or for one data type or
     dataset, is that part's preprocessing, not analysis.
   - "Not applied to one part" is a value: performed = no for that part.
3. **Finding a part's words.** `applies_to` is looked for in the value's sentence, then its
   `applies_to_quote`, then anywhere in the methods text, headings included
   (`quote_support.locate_phrase`).
   - The location is kept in `applies_to_spans`, and for a step-order part in its new
     `applies_to_spans` (schema 0.7.1, an additive patch).
   - A part is unverified only when its words are found nowhere.
4. **`base_pipeline_ref` as a bare citation marker with no quote** (yang_2025's "(67)").
   - It becomes a deferral to that marker, grounded on the sentence of the methods text that carries
     it, and the hop resolves it.
   - Anything else extracted without a quote becomes missing.
   - Neither is a validation failure any more.
5. **`merge_labels.py` fails closed.** For a held-out paper, every column outside the known label
   columns is withheld.

Variant and part spans now get `span_in_slice` / `span_in_full_paper` like extracted spans.

## 10. Stage 2c (2026-11-11, from Stage 2b's findings)

The author's items, as built. No model call: the four Stage 2b records were re-rendered and
re-scored (`extractor_mvp/scripts/rerender_records.py`).

1. **Scorer** (`applies_to_scoring.py`; supersedes fork E2's "no alias fallback").
   - Leading and trailing ellipses ("…", "...") and quote marks are stripped from both quotes
     before the overlap test (`clean_quote`).
   - A label variant with no quote, or whose quote overlapped nothing, is then matched by part name
     (`names_match`): the same words under the same-string rule, or the same content words.
   - Quote overlap runs over every label variant before any name match, so a name never takes the
     part another label's quote overlaps. A label variant matched by neither is missed.
   - `FieldScore.routes` records "quote" or "name" per label variant; the scope table reports both.
2. **Pseudo-code tables for more than four parts, whatever fields differ.** Every step is printed
   once, a differing field as `by_part`. Below, one table per step whose fields differ, in step
   order: a row per part that states one of those fields, a column per field, then how many parts
   state none of them. `CONFOUND_KINDS` is no longer a condition.
3. **Joining two spellings of one part** (`part_names.py`).
   - Two names join when one name's content words (punctuation, parentheses and stopwords dropped)
     are a subset of the other's.
   - Not joined: two names one field carries side by side (the extractor gave each its own value);
     a group in which some pair is not a subset (ambiguous); the compared-models entry; a name with
     no content words.
   - "a" is not a stopword: it is also a part label ("Model A"), and dropping it would join "Model A"
     into "Model B".
   - The spelling kept is the first met in render order. The paper's words stay on every value.
   - Every join and every refused group is logged in the record (`part_joins`, written by
     `batch.py`). The report header shows a join as `kept (joined: other)`; the pseudo-code notes it.
   - The scorer's streams, the pseudo-code's parts and the header all group by the joined key.

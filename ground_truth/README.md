# `base_pipeline` ground-truth labels

Ground truth for the `base_pipeline` field across the 20-paper `tested_lit/sfn_batch` corpus
(analysed denominator 19; cabral_2017 excluded). Single-rater, **author-labeled** (Jae Wook Cho)
strictly against [`docs/ground-truth-protocol.md`](../docs/ground-truth-protocol.md) at **v1.2**
(HEAD `e0eb09d`); every rule the labels follow lives in that protocol, which was pre-registered
before any label was written.

## Files

- **`base_pipeline_labels_v1.csv`** — **canonical for scoring.** Machine-readable, diff-able,
  self-describing (each row carries `labeler` and `protocol_version`). `value` and `specificity` are
  semicolon-separated lists (split on `"; "`). Derived from the xlsx, never hand-typed — the two
  cannot drift.
- **`base_pipeline_labels_v1.xlsx`** — the **human-editable source** (the labeling workbook: Labels /
  Glossary / Start-here sheets). Edit labels here, then re-derive the CSV.
- **`base_pipeline_labels_v1.1-snapshot.xlsx`** — provenance snapshot of the **pre-v1.2-correction**
  state, so the label history (the six v1.2 corrections to vanderwal/power/tang/liu_2005/cole/ciric)
  is inspectable. Not for scoring.

## Caveat (standing)

These labels are **single-rater** and produced by the developer of the system under evaluation, so
they are **not independent** of it: any metric computed against them is **indicative, not an
independent benchmark**. A second/panel rater and inter-rater reliability are **deferred, conditional
on publication** (see the protocol's rater-scope section). Do not cite a hallucination rate from these
labels as an external benchmark.

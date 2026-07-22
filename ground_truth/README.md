# `base_pipeline` ground-truth labels

Ground truth for the `base_pipeline` field across the 20-paper `tested_lit/sfn_batch` corpus
(analysed denominator 19; cabral_2017 excluded). Single-rater, **author-labeled** (Jae Wook Cho)
strictly against [`docs/ground-truth-protocol.md`](../docs/ground-truth-protocol.md), which was
pre-registered before any label was written.

## Protocol version (set-level)

**Protocol version (set-level): v1.3.** These labels conform to
[`docs/ground-truth-protocol.md`](../docs/ground-truth-protocol.md) v1.3 (HEAD at finalization). The
protocol evolved v1 → v1.3 during labeling; v1.3 is the version all 19 labels conform to. Which rule
governs a given paper is recorded in the protocol's changelog and decision sections, **not per-row**.
The version is a **set-level** fact and lives here (README) — derivable and stable — not as a CSV
column that regeneration from the xlsx cannot reproduce. Canonical scored artifact = the CSV; human
source = the xlsx.

## Files

- **`base_pipeline_labels_v1.csv`** — **canonical for scoring.** Machine-readable, diff-able; each row
  carries `labeler`. `value` and `specificity` are semicolon-separated lists (split on `"; "`).
  **Derived from the xlsx by `derive_labels_csv.py`, never hand-typed** — regenerating from the source
  reproduces it exactly, so the two cannot drift. (Protocol version is set-level, above — not a
  column.)
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

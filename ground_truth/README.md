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

## Coverage & denominator (name the omissions)

The corpus is **19 analysable papers** (20 minus cabral_2017). The label set covers **18** distinct
paper_ids; the blind Tier-A/B rate is **N=17**. Two coverage facts a cited number must state on its
face — "82.4% on 17 of 19 corpus papers" wants its omissions named, not discovered:

- **binder_1999 is in the corpus but has NO ground-truth label** (it is not in the protocol's paper
  list; `stage_partition.py:51` maps it). It is not an easy one: `stage-partition.md:66` flags that
  binder's **"(SPMs)"** (plural) sits exactly on a status-rule boundary — does "(SPMs)" *name* SPM
  when a trailing-letter rule forbids matching `SPM`? That is a v1.2/v1.3 status-rule question and
  should be labeled before the number is cited.
- **chen_2015 appears twice in the workbook** — as the pre-filled *example* row and as its own
  labeled row. The blind N=17 counts **chen's own row**, whose label was inherited from the example
  above it (so it is **not independent**). chen → CCS is unambiguous, so it does not move the number,
  but the denominator note records which chen row counted and that its label is non-independent.

## Caveat (standing)

These labels are **single-rater** and produced by the developer of the system under evaluation, so
they are **not independent** of it: any metric computed against them is **indicative, not an
independent benchmark**. A second/panel rater and inter-rater reliability are **deferred, conditional
on publication** (see the protocol's rater-scope section). Do not cite a hallucination rate from these
labels as an external benchmark.

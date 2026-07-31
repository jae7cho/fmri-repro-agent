# `spatial_normalization.target_space` ground-truth labels

Ground truth for the `target_space` field across the 20-paper `tested_lit/sfn_batch` corpus (analysed
denominator 19; cabral excluded). Single-rater, **author-labeled** (Jae Wook Cho) strictly against
[`docs/ground-truth-protocol-target_space.md`](../docs/ground-truth-protocol-target_space.md), which was
pre-registered before any label was written (commit `65e7d91` blank instrument; `305bcb6`/`bc28f12` v1.2
+ labels).

## Protocol version (set-level)

**Protocol version (set-level): v1.2.** These labels conform to
[`docs/ground-truth-protocol-target_space.md`](../docs/ground-truth-protocol-target_space.md) v1.2 (HEAD
at finalization). The protocol evolved v1 → v1.2 during labeling (CALL 6 composed chains, CALL 7 terminal
volumetric state, the six-state vocabulary, Talairach → family_specified); which rule governs a given
paper is in the protocol's changelog, **not per-row**. Set-level fact — lives here, not as a CSV column
regeneration can't reproduce.

## Files

- **`target_space_labels_v1.csv`** — **canonical for scoring.** Derived from the xlsx by
  `derive_target_space_csv.py`, never hand-typed. Columns: `paper_id, target_space_state, value,
  supporting_quote, notes, labeler`. 19 rows (the 2 worked "(EXAMPLE)" rows are skipped — they duplicate
  their own real rows).
- **`target_space_labels_v1.xlsx`** — the human-editable source (Labels / Glossary / Start-here sheets).
- **`target_space_scoring_map.csv`** — **the PRE-REGISTERED extractor-state → label-state mapping.**
  Committed with the labels, BEFORE the scorer is run, so the mapping cannot be tuned after seeing the
  number (same discipline as `tier_b_aliases.csv`). Principle-derived (label-state definitions + protocol
  v1.2's Talairach ruling + base_pipeline's MISSING→honest-nothing convention), not fit to an outcome.
- **`target_space_predictions_v040_frozen.csv`** — frozen K=3 extractor predictions (results/ is
  gitignored + non-stationary), the durable record the score is computed against.

## The two vocabularies (why a mapping table is needed at all)

The extractor's `TargetSpace` enum names **which resolved space** (`MNI152NLin6Asym`,
`MNI152NLin2009cAsym`, `Talairach`, `native_volume`, `study_specific`, `other`); the labels grade **how
completely specified** (canonical / family_specified / study_specific / native_volume / deferred /
absent). These are different axes and both can be true at once. The mapping table
(`target_space_scoring_map.csv`) is the explicit bridge; its load-bearing row is
**EXTRACTED+Talairach → family_specified** (per protocol v1.2: Talairach is a coordinate system realized
by many digital templates, so it names the family, not a resolvable variant).

## Capability findings (structural, established BEFORE scoring)

Two vocabulary GAPS mean some labels are not reachable by the extractor as currently built — these score
as "errors" for a **capability** reason, not an **accuracy** reason, and must be reported as such:

1. **`family_specified` is enum-UNREACHABLE (the dominant gap).** The enum has resolved-variant slots
   and `native_volume`/`study_specific`/`other`, but **no family-level / bare-"MNI" value**. Every paper
   that named the family without a resolvable variant flattens to `MISSING` (raw_diagnostic shows the
   grabbed-then-discarded "MNI"/"MNI-152"/"MNI152"/"EPI template"). On this corpus that is **9 of the 10
   `family_specified` labels** — the largest tier — so the headline is NOT an accuracy rate; it is a
   capability finding that the enum lacks a family tier.
2. **Deferral is PARTIAL + unstable.** target_space extraction CAN emit `DEFERRED_TO_CITATION` (braun
   does, on an explicit "described in refs. 47 and 48"), so deferred is not structurally unreachable —
   but the detector misses the provenance-named ("a pipeline developed at Washington University" —
   poldrack) and "technique-of" (viduarre) forms, which emit `MISSING`. braun itself is **K=3-unstable**
   (DEFERRED/MISSING/DEFERRED). So 1 of 3 deferred labels is reachable-and-correct, 2 are missed.

## Coverage & denominator (name the omissions)

- **binder_1999 has NO extractor prediction** — it was added as the 19th label AFTER `batch_v040_labelset`
  (an 18-paper batch), so the extractor never ran on it. It is unscoreable from the frozen audit; it needs
  an extractor run before any complete number is cited. (Its label is `native_volume`, CALL 7(a).)
- **oconnor and mueller are NOT blind.** Both appear as the pre-filled worked-example rows in the xlsx
  AND as their own labeled rows, so the author saw the answer. They count in the 19-label set but are
  **non-independent**; the blind denominator is **N=17**.
- So: 19 labels · 18 with a prediction · 17 blind.

## Predicted decomposition (pre-scoring; grounded in the frozen predictions + the pre-registered map)

Applying the committed map to the frozen predictions, over the 18 papers that have a prediction:

- **Correct (3):** cole (EXTRACTED Talairach → family_specified ✓ — the map's Talairach row), power
  (MISSING → absent ✓, genuine gesture), braun (DEFERRED → deferred ✓, majority 2/3).
- **`family_specified` flattening — enum gap (9):** agtzidis, derosa, gordon, liu_2005, liu_2013, tang,
  vanderwal, weber, wheaton. All bare family terms → MISSING → absent, vs `family_specified`.
- **`study_specific` missed (2):** ciric, mueller — a study-CONSTRUCTED template the detector didn't
  capture → MISSING, vs `study_specific` (the enum HAS study_specific, so this is accuracy, not capability).
- **deferral-miss (2):** poldrack, viduarre — MISSING vs `deferred` (see capability finding 2).
- **specificity-flatten (1):** oconnor — a resolvable FSL file grabbed as bare "MNI" → MISSING vs
  `canonical` (the extraction-accuracy divergence, docs/findings/extraction-specificity-flattening.md).
- **cross-axis leak (1):** chen — the surface template's MNI frame grabbed for the volumetric field →
  MISSING vs `native_volume` (CALL 1).

The RESULT is this decomposition, not an aggregate rate: the extractor scores correct on only the resolved
(Talairach), the genuinely-absent, and one explicit deferral, and the rest partitions into named error
classes — each generalizable beyond its paper (an enum lacking a family tier; a deferral detector blind to
provenance/technique-of forms; specificity flattening; cross-axis leakage). That decomposition is the
finding.

## Caveat (standing)

These labels are **single-rater** and produced by the developer of the system under evaluation, so they
are **not independent** of it: any metric against them is **indicative, not an independent benchmark**. A
second/panel rater and inter-rater reliability are **deferred, conditional on publication**.

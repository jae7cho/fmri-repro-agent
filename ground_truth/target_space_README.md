# `spatial_normalization.target_space` ground-truth labels

Ground truth for the `target_space` field across the 20-paper `tested_lit/sfn_batch` corpus (analysed
denominator 19; cabral excluded). Single-rater, **author-labeled** (Jae Wook Cho) strictly against
[`docs/ground-truth-protocol-target_space.md`](../docs/ground-truth-protocol-target_space.md), which was
pre-registered before any label was written (blank instrument `65e7d91`; v1.2 + labels `305bcb6`/`bc28f12`).

## Protocol version (set-level)

**Protocol version (set-level): v1.2.** These labels conform to
[`docs/ground-truth-protocol-target_space.md`](../docs/ground-truth-protocol-target_space.md) v1.2 (HEAD
at finalization). Set-level fact — lives here, not as a CSV column regeneration can't reproduce.

## Files

- **`target_space_labels_v1.csv`** — canonical for scoring. Derived from the xlsx by
  `derive_target_space_csv.py` (examples skipped -> 19 rows).
- **`target_space_labels_v1.xlsx`** — the human-editable source.
- **`target_space_scoring_map.csv`** — the PRE-REGISTERED extractor → label mapping, keyed on
  `(status, failure_reason, raw_diagnostic)`. Committed before the scorer runs so it can't be tuned to a
  number. **v2** (see "Map correction" below): v1 keyed on status alone and was lossy.
- **`target_space_predictions_v040_frozen.csv`** — frozen K=3 predictions incl. `failure_reason`, the
  durable record the score is computed against (results/ is gitignored + non-stationary).
- Scorer: `extractor_mvp/score_target_space.py` (report-only).

## The two vocabularies (why a mapping table is needed)

The extractor's `TargetSpace` enum names **which resolved space**; the labels grade **how completely
specified**. Different axes, both can be true at once. The map is the bridge; two load-bearing rows:
**EXTRACTED+Talairach → family_specified** (Talairach is a coordinate system, not a resolvable variant),
and **MISSING+value_not_in_literal:underspecified[MNI] → family_specified** (the extractor grabbed a bare
MNI-family term it couldn't resolve — "said MNI, no variant" — mirroring generate_sfn_review's
`value_not_in_literal → Family-specified`).

## Map correction (transparency)

**Map v1 (committed `7bca618`) was lossy and produced a spurious result; it is superseded here.** v1 keyed
on `status` alone (MISSING → absent), so the 9 papers where the extractor GRABBED a bare MNI-family term
but relabeled `status→MISSING` (value_not_in_literal) scored as `absent` — yielding a false "9-paper
family_specified is enum-UNREACHABLE" capability class. That was a **scoring artifact**: the extractor DOES
capture those targets (the raw term is in the diagnostic, and the reporting layer already reads it). v2
keys on `failure_reason`; the correction was author-identified and is justified by faithfulness to the
extractor's actual output (a factual criterion), not by the resulting number — both numbers are reported.
The v1 map/number stand in git history as the record.

**Why v2 is a correction, not a tune — the prediction came out WRONG in a checkable direction.** The
collapse was predicted *before* the map was changed, with a mechanism (value_not_in_literal captures the
family term) and a magnitude (**9** papers). The magnitude came out wrong: **8** collapsed. liu_2005
deviated — its `failure_reason=None` (nothing captured) makes it a genuine miss, not a value_not_in_literal
artifact — and the deviation was *investigated* (below), not absorbed. A post-hoc change that produced
exactly the predicted nicer number would be weak evidence of honesty; one that deviates in a checkable
direction, with the deviation run down, is strong evidence the map tracks the extractor's actual behavior
rather than a target number.

## The real defect (this survives the correction)

The extractor's SPEC records `extraction.status = MissingFromPaper` for 9 papers that **stated "MNI"**
(the value_not_in_literal relabeling). The core model therefore asserts *absence* where there is
*presence* — a **false provenance claim inside the system whose entire thesis is distinguishing absence
from presence.** The reporting layer papers over it with the reason code; the spec itself is untrue. This
is a correctness defect in the core model, not a vocabulary gap, and has its own note:
[`docs/findings/target_space-false-missing.md`](../docs/findings/target_space-false-missing.md).

## Capability finding (deferral)

Deferral IS reachable (braun emits `DEFERRED_TO_CITATION` on an explicit "described in refs. 47 and 48"),
but **partial + unstable**: the detector misses provenance-named (poldrack) and "technique-of" (viduarre)
forms → MISSING; braun itself is K=3-unstable. 1 of 3 deferred labels reachable-and-correct, 2 missed.

## Coverage & denominator (name the omissions)

- **binder_1999** was run separately (2026-07-31, same model pin) and now HAS a prediction — the denominator
  is closed at **19 scored**.
- **oconnor and mueller are non-blind** (appear as the worked-example rows AND their own rows). The rate is
  quoted over the **BLIND set of 17** (19 scored − 2 non-blind).

## Score (report-only; map + predictions both committed)

Over all **19** papers: **11 correct / 8 error**. Blind set: **11 of 17 correct** (6 error). The 8 errors
partition four ways — the honest headline is this split, not a raw rate:
**5 model-accuracy · 2 capability-limited · 1 demonstrated-input-corruption**.
- **2 capability-limited** (chen, binder): CALL 7 `native_volume` is unreachable by construction (the
  value-support guard forbids an absence-evidenced value; `target_space-call7-unreachable.md`) — a cited
  accuracy number should not charge these.
- **1 demonstrated-input-corruption** (liu_2005): a clean de-interleaved slice recovers Talairach 3/3
  (BrainVoyager 3/3 validates the slice) vs MISSING 3/3 on the corrupted PDF — upstream slicing, not a model
  error (`target_space-pending-runs.md`).
So the **model-accuracy denominator is 5 errors**, on the papers the extractor could reach with clean input.
The finding is the decomposition:

- **Correct (11):** the 8 bare-MNI-family papers (agtzidis, derosa, gordon, liu_2013, tang, vanderwal,
  weber, wheaton) + cole (Talairach) + power (absent) + braun (deferred, K=3-unstable).
- **study_specific missed (2):** ciric, mueller — constructed template not captured (MISSING, no raw). New
  model-side class (the enum HAS study_specific; the detector didn't fire on an explicit construction phrase).
  The two `deferred`-labelled misses are **two distinct mechanisms wearing one label** (checked
  deterministically, K=3-stable), so they are counted separately:
- **extract-over-defer (1):** poldrack — `status=extracted, value="3-mm isotropic atlas space"`
  (value_not_in_literal): the model grabbed an inadequate noun phrase instead of deferring. **VERIFIED not
  the base_pipeline `_parse_attribution_ref` [45] bug** — target_space deferral is model-driven
  (`_process_deferred` consumes the model's `status="deferred"`; no attribution parser in this path); the
  hypothesized cross-field reuse did not hold. (poldrack does the same extract-over-defer in base_pipeline
  — "Washington University pipeline" — so it is a two-field, single-paper observation to WATCH, not yet a
  generalizable class.)
- **deferral not recognized (1):** viduarre — `status=MISSING`, `failure_reason=None`, raw=None, no
  fabrication (unlike its base_pipeline behaviour): a silent miss on the "technique of Smith et al."
  form. Distinct from poldrack (which grabbed a phrase); they do NOT share a mechanism.
- **cross-axis leak (1) — CAPABILITY-LIMITED:** chen — surface template's MNI frame grabbed as a volumetric
  family target. The cross-axis leak is real and fixable, but chen's `native_volume` is a CALL 7 reading
  (unreachable by construction), so a perfect cross-axis firewall yields MISSING → absent, still ≠
  native_volume — **the cross-axis fix buys no scoring improvement on this row** (`target_space-call7-unreachable.md`).
- **results-space leak (1) — CAPABILITY-LIMITED:** binder — `EXTRACTED Talairach` 3/3 (2026-07-31 run),
  pulled from the SPM statmap-projection sentence (Talairach applied to DERIVED maps) — the first LIVE
  CALL 7(a) instance. Scores `family_specified` vs `native_volume`. Also CALL 7-unreachable (native_volume
  has no quote), so like chen the leak-fix is scoring-neutral; two mechanisms on one unreachable row.
- **demonstrated-input-corruption (1):** liu_2005 — batch MISSING (Talairach not captured); the two-column
  layout interleaves methods with the reference list (`pdf-glue-false-missing.md`). **CONFIRMED causal
  (2026-07-31):** a clean de-interleaved slice recovers Talairach 3/3 (BrainVoyager 3/3 validates the slice)
  vs MISSING 3/3 on the corrupted PDF — on clean input it maps to `family_specified` = its label = correct.
  An upstream PDF failure, NOT a model error. cole's opposite (there glue looked causal, tested → refuted).
- **specificity flattening (1):** oconnor — resolvable FSL file grabbed as bare "MNI".

**Both pending runs are DONE (2026-07-31, bedrock sonnet-4-5, `run_pending_target_space.py`):** liu_2005 →
Talairach 3/3 on the clean slice (input-corruption confirmed causal); binder → Talairach 3/3 (results-space
leak confirmed, denominator closed). Outcomes were pre-committed before the run:
`docs/findings/target_space-pending-runs.md`.

## Caveat (standing)

Single-rater, produced by the developer of the system under evaluation → **indicative, not an independent
benchmark**. Second/panel rater + inter-rater reliability **deferred, conditional on publication**.

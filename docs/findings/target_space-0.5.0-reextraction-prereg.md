# Pre-registration: 0.5.0 re-extraction of the target_space corpus

**Committed BEFORE the run (2026-08-06, ET), so the falsifiability is on record, not in conversation.**
Retype commit: `382795a`. Run this against that HEAD.

## Why

The v0.5.0 retype is mechanism-fixed but **not yet demonstrated end-to-end**: no committed spec document
has been written by the retyped extractor, and map v3 currently scores against the *pre-retype* frozen
predictions by TRANSLATING their columns (`reconstruct_struct`). This run produces genuine 0.5.0 output
and scores v3 against it. Two things it buys: (1) demonstrates the false-missing fix on the corpus;
(2) if v3's numbers hold against *real* output, the translation was faithful and the score is grounded —
if they don't, the disagreement is between real extraction and the translation, which is the more
interesting result.

## Run

- `extractor_mvp/batch.py --config <draw{1,2,3}>`, K=3, model `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`
  (identical pin to the frozen `batch_v040_labelset`), 19 papers (18-paper sfn_batch + binder_1999;
  cabral excluded). ~57 calls. New output dir `results/batch_v050_labelset/` (frozen dir untouched).
- The retype changes ONLY post-resolution recording in `_process_field` — it does NOT touch the model
  call, the prompt, or `fe.value`. So the extracted **verbatim is model-determined and should match the
  frozen diagnostic's raw_value** (modulo model non-stationarity across a fresh K=3).

## Expected outcome (success case)

The 12 papers the pre-retype extractor recorded as `value_not_in_literal` -> `MISSING_FROM_PAPER` (the
false-missings) become **EXTRACTED** with `resolved=None` and the verbatim preserved:

| paper | frozen raw_value | expected 0.5.0 | resolution | v3 grade (unchanged) |
|---|---|---|---|---|
| agtzidis_2020 | MNI | EXTRACTED, verbatim≈"MNI" | underspecified | family_specified ✓ |
| chen_2015 | MNI | EXTRACTED, verbatim≈"MNI" | underspecified | family_specified (ERR vs native_volume, unreachable) |
| derosa_2025 | MNI-152 | EXTRACTED, verbatim≈"MNI-152" | underspecified | family_specified ✓ |
| liu_2013 | MNI | EXTRACTED, verbatim≈"MNI" | underspecified | family_specified ✓ |
| oconnor_2017 | MNI | EXTRACTED, verbatim≈"MNI" | underspecified | family_specified (ERR vs canonical) |
| tang_2025 | MNI | EXTRACTED, verbatim≈"MNI" | underspecified | family_specified ✓ |
| vanderwal_2016 | MNI | EXTRACTED, verbatim≈"MNI" | underspecified | family_specified ✓ |
| weber_2024 | MNI152 | EXTRACTED, verbatim≈"MNI152" | underspecified | family_specified ✓ |
| wheaton_2004 | MNI | EXTRACTED, verbatim≈"MNI" | underspecified | family_specified ✓ |
| gordon_2014 | EPI template | EXTRACTED, verbatim≈"EPI template" | unrecognized | family_specified ✓ (named, not gesture) |
| poldrack_2015 | 3-mm isotropic atlas space | EXTRACTED, verbatim≈"…atlas space" | unrecognized | absent (ERR vs deferred) |
| power_2014 | atlas space | EXTRACTED, verbatim≈"atlas space" | unrecognized | absent ✓ |

Unchanged from frozen:
- **cole_2013**, **binder_1999**: stay EXTRACTED (Talairach), now as `SpecifiedTerm(resolved="Talairach")`.
- **braun_2015**: stays DEFERRED (may be K=3-unstable, as before).
- **ciric_2017, mueller_2021, viduarre_2017**: stay MISSING (nothing captured — genuine absence / study_specific miss / deferral-not-recognized).
- **liu_2005**: stays MISSING (corrupted two-column PDF; the retype does NOT fix upstream corruption — that is `demonstrated-input-corruption`, excluded).

**Headline falsifiable claim:** v3 scored against this REAL 0.5.0 output reproduces the translated-legacy
score — **11 correct / 8 error**, same partition, blind **11/17 = 64.7%**, reachable-only **11/14 = 78.6%**.

## Failure modes (pre-committed — any of these is STOP-and-investigate, not a silent pass)

1. **Different verbatim than the diagnostic held.** If a paper flips to EXTRACTED but with a verbatim
   that is *not* the frozen raw_value (beyond trivial whitespace/case), the extraction path changed, not
   just the recording — which the retype provably should NOT do (it never touches `fe.value`). Distinguish
   non-stationarity (a fresh draw grabbed different words) from a retype-induced change: a MAJORITY-of-K=3
   difference points at a bug or a real model shift; a single-draw difference is likely variance. Either
   way, stop and name which.
2. **A currently-CORRECT row moves.** If any of the 11 correct rows changes grade under real output, the
   retype (or the model on a fresh run) has a scoring consequence the translation hid. Stop; the
   disagreement between real extraction and the `reconstruct_struct` translation is the finding.
3. **Non-stationarity is data, not noise.** This is a fresh K=3. The earlier target_space runs were
   stable (most 3/3), but base_pipeline's were not. Record per-draw status; a flip across draws is
   recorded and reasoned about, not averaged away. The K=3 majority is the reported state; instability is
   flagged (as braun already is).

## What would make this MORE interesting than the retype

If the numbers do NOT hold against real output, the translation (`reconstruct_struct`) and the real
extractor disagree about at least one row. That disagreement — not the retype — becomes the result to
run down: which row, and whether the translation over-simplified the frozen columns or the model shifted.

## Outcome

_To be filled in after the run (per-draw states, K=3 majority, verbatim vs frozen raw, v3 score,
which failure modes fired if any)._

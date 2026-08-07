# Pre-registration: 0.5.0 re-extraction of the target_space corpus

**Committed BEFORE the run (2026-08-06, ET), so the falsifiability is on record, not in conversation.**
Retype commit: `382795a`. Run this against that HEAD. **AMENDED 2026-08-06** after a 1-paper smoke + a
free proxy but BEFORE the full run — the original expectation was known-wrong for agtzidis (see below).

## AMENDMENT (after the smoke + free proxy, before the full run)

The original expectation below ("all 12 flip to EXTRACTED") was **already known to be wrong for agtzidis**
— the pre-reg failed to consult a committed finding.
[`span-resolution-hard-drop.md`](span-resolution-hard-drop.md) (Phase 1) recorded **target_space ×2**
silent span-drops and named **agtzidis target_space** specifically as a recoverable *pypdf-mangle* case:
pypdf renders `×` as the literal `/C2`, so agtzidis's slice carries `3 /C2 3 /C2 3m m 3` where the model
regularized `3 × 3 × 3 mm3`. Phase 2 (the fixes) was measured but never run. So this is a committed
latent defect, not a discovery — the artifact/conversation gap in a new direction.

**Why the retype surfaced it.** The `value_not_in_literal` short-circuit was HIDING the hard-drop: the old
flow returned MISSING at the value check, *before* quote resolution ran, so the span-drop could never fire
for these papers. Removing the short-circuit lets the value reach quote resolution, and a known latent
defect surfaces. The **root cause is pypdf, not the retype**, and the **value-support guard is working as
designed** — it correctly refuses to ground a quote that does not match the (mangled) source. agtzidis
belongs to the same family as cole's AFNI-glue and liu_2005's column interleaving: different mechanism,
same origin (source corruption).

**Restated claim (narrower, and true).** NOT "the spec no longer records `MissingFromPaper` for a stated
term" — now known false for agtzidis. The accurate claim: **the retype closes the `value_not_in_literal`
path to false-missing; the `quote_not_found` path remains open and is a separate, previously-documented
defect** (`span-resolution-hard-drop.md`, Phase 2 unbuilt).

**Do not let the score launder this.** If agtzidis's v3 grade holds at `family_specified`, that is NOT
evidence the fix works there: `reconstruct_struct` falls back to the diagnostic's `raw="MNI"` for a
`quote_not_found` row — the exact diagnostic-side-channel workaround the retype was meant to retire. So
agtzidis is still scored by the OLD mechanism; "numbers unchanged" is honest ONLY if this is stated.

**Amended expectation (this is what the run tests):**
- **~11/12** of the value_not_in_literal papers flip to **EXTRACTED** with the verbatim preserved
  (`resolution="underspecified"` for the 9 bare-MNI; `"unrecognized"` for gordon/poldrack/power).
- **agtzidis: `quote_not_found` → stays `MissingFromPaper`** (documented pypdf-mangle). It MAY flip on a
  cleaner draw — fresh K=3, the model's quote varies run to run; its core phrase resolves, only the
  garbled `/C2` tail breaks the full quote.
- **Any currently-CORRECT row that moves** means the retype has a scoring consequence the translation hid.
- **A verbatim differing from the diagnostic's raw** means EXTRACTION behavior changed, not just recording
  (the retype provably does not touch `fe.value`, so this would be a bug or a real model shift).

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

## Expected outcome (per the amendment above)

Of the 12 papers the pre-retype extractor recorded as `value_not_in_literal` -> `MISSING_FROM_PAPER`,
**~11 become EXTRACTED** with `resolved=None` and the verbatim preserved; **agtzidis stays
`MissingFromPaper` via `quote_not_found`** (pypdf-mangle, may flip on a cleaner draw):

| paper | frozen raw_value | expected 0.5.0 | resolution | v3 grade (unchanged) |
|---|---|---|---|---|
| agtzidis_2020 | MNI | **quote_not_found -> MISSING** (pypdf `/C2` mangle) | n/a | family_specified ✓ (scored via diagnostic raw — old mechanism, NOT the fix) |
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

## Outcome (2026-08-06, after the full K=3 run)

Run: `results/batch_v050_labelset/` draws 1-3, 19 papers each, **0 failed** (no partial output — the
miss/harness-failure ambiguity is cleared). Every draw: **0 value_not_in_literal** (the path is
eliminated on real output) + 3 quote-unresolved. Durable real-shape record:
`ground_truth/target_space_predictions_v050.csv`; scorer: `extractor_mvp/score_v050_reextraction.py`.

**The fix is demonstrated.** **11/12** value_not_in_literal false-missings now record the term — EXTRACTED,
**K=3-stable (all 3/3)**, verbatim preserved and **matching the frozen raw** (chen "MNI", derosa "MNI-152",
gordon "EPI template", poldrack "3-mm isotropic atlas space", power "atlas space", weber "MNI152", …). The
verbatim-match confirms the retype changed only recording, not extraction — **failure mode #1 did not
fire**.

**agtzidis: exactly as amended-predicted.** Stayed `MissingFromPaper` via `quote_not_found` on **all 3
draws** (did NOT flip on a cleaner draw). Graded `family_specified` via the diagnostic raw — the OLD
side-channel, **NOT the fix**. The documented pypdf-mangle (`span-resolution-hard-drop.md`, Phase 2
unbuilt) stands.

**Two NON-STATIONARITY movers (orthogonal to the retype), both stable 3/3 this run:**
- **braun** deferred → absent: fresh K=3 gave MISS/MISS/MISS; deferral detection dropped (frozen was
  DEFERRED/MISS/DEFERRED, already K=3-unstable). A currently-correct row moved (**failure mode #2 fired**);
  investigation → non-stationarity (#3), not a translation flaw.
- **mueller** absent → study_specific: fresh K=3 gave EXTR/EXTR/EXTR; the construction phrase was newly
  captured (frozen was MISS/MISS/MISS). An improvement, also non-stationarity.

**Score.** Total **11/8** (matches frozen total, different composition). **Blind moved 11/17 → 10/17
(64.7% → 58.8%)**, reachable 78.6% → 71.4% — driven entirely by braun (blind, correct→error); mueller's
offsetting improvement is non-blind so it does not lift the blind rate. The v3 **translation was faithful
for the retype's target population** (every value_not_in_literal paper grades identically real-vs-translated);
the blind-rate drop is **model non-stationarity on braun, not a translation error and not the retype**.

**Verdict on the pre-reg's question** ("if the numbers hold, the translation was faithful"): for the
retype's target population they held exactly (11/12 flipped verbatim-faithful; agtzidis as documented). The
blind-rate drop is a separate, orthogonal non-stationarity signal on braun — recorded as data, not
attributable to the fix.

**Phase 2 (span-resolution) — open.** agtzidis is the lone target_space `quote_not_found`; the broader
hard-drop is corpus-wide across 6 fields (`span-resolution-hard-drop.md`). Whether to build Fix A/B is a
separate decision; the retype (commit `382795a`) is demonstrated as far as it claims.

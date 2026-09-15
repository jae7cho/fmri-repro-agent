> **Moved from `extractor_mvp/results/VARIANCE_FINDINGS.md` on 2026-09-14.** That directory is ignored by a
> bare `*`, so this analysis had no tracked home and appears in no backup archive. Of 20 distinctive sentences here, **none** appears in any tracked file.
> The run artifacts it was computed from stay ignored — only the prose moved.
>
> Companion to [`variance.md`](variance.md), which states the finding; this is the N=15 analysis
> under it. The raw per-run table `VARIANCE_PROBE.md` stays ignored and regenerates from the harness.

# Variance harness — findings (N=15, temp 0, byte-identical input)

Raw per-field table: `VARIANCE_PROBE.md`. Instrument: `scripts/variance_probe.py`.
Slice computed once per paper and reused for all 15 runs, so the ONLY variable between
runs is the Bedrock call. Model, temperature (0.0), and input bytes are held fixed.

## Verdict: temp 0 is NOT deterministic in this stack

3 of the 24 field-cells flipped across byte-identical input. All three are on chen (the
paper whose extraction the whole thesis leans on):

| paper | field | outcome across 15 identical runs | kind of flip |
|---|---|---|---|
| chen | temporal_standardization.method | EXTRACTED x10 / **MISSING x5** | **state flip — 33% false-absence** |
| chen | base_pipeline | CCS-with-"(CCS)" x8 / CCS-without x7 | value-string flip (both → CCS) |
| chen | surface_projection.surface_registration | MISSING **15/15** | STABLE |

Everything on oconnor and weber was 15/15 stable.

## The PI's two questions, answered

**1. "What does chen's surface_registration do across 15 identical runs?"**
Rock stable: MISSING 15/15. So the v6→v7 loss (EXTRACTED on whole-doc input →
MISSING on the tighter slice) is a REAL context-sensitivity effect, not draw noise.
The ATTRIBUTION_DIFF canary reading stands: a correct, verified slice reliably fails
to yield this field. It is a property of the input, reproducible, not sampling.

**2. The caching/false-stability caution is discharged.**
The runs did NOT come back identical — we observe 10/5 and 8/7 splits on fixed bytes.
That is direct proof that no Bedrock prompt caching or fixed seed is pinning outputs;
if it were, every cell would be N/N. Temp is genuinely 0 at the API layer AND the
stack is still nondeterministic. Both halves of the caution resolve.

## What this means for every extraction number

- **The unit of an AESPA extraction is a draw, not a fact.** chen's
  temporal_standardization is MISSING one run in three on identical input. Any single
  corpus run's MISSING count is partly a coin-flip; corpus statistics reported from one
  run carry uncharacterized variance. The honest unit is a per-field flip-rate over K
  runs, not a state.
- **The C-PAC false negative is DETERMINISTIC, not noise.** oconnor and weber
  base_pipeline are MISSING 15/15 with C-PAC verified present in the slice. This is a
  stable model failure, not a bad draw. That is good news for fixing it: a prompt change
  can be measured against a fixed 0/15 baseline — any nonzero recovery is signal.
- **State flips and value flips are different failures.** base_pipeline's 8/7 is
  cosmetic (both decode to CCS; only the "(CCS)" parenthetical varies) — a normalization
  wobble, not a recall failure. temporal_standardization's 10/5 crosses the
  EXTRACTED/MISSING boundary — that is the one that corrupts a corpus count.

## Immediate consequences

1. No corpus number should be reported from a single run again. Any headline (KB
   intersection, recall) needs K≥10 repeats and a flip-rate / modal-state with a count.
2. The v6-vs-v7 diff is only trustworthy for fields that are per-run STABLE on both
   inputs. chen temporal_standardization changed MISSING→EXTRACTED in that diff, but it
   is a 10/5 coin on the v7 slice — that "gain" is inside the noise band and must not be
   read as a slice improvement.
3. Before the C-PAC prompt investigation: its target (0/15 base_pipeline) is a clean,
   stable baseline, so that work is well-posed. Proceed there — but score any prompt
   change over K runs, not one.

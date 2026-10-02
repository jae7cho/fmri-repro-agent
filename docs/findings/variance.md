# Finding: the extractor is not run-to-run deterministic at temperature 0

**Harness:** `extractor_mvp/scripts/variance_probe.py`
**Model (pinned):** `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`
**Run:** N=15 repeats per paper, input held BYTE-IDENTICAL (methods slice computed once, reused
every run), on chen_2015 + oconnor_2017 + weber_2024. Raw per-run table:
`extractor_mvp/results/VARIANCE_PROBE.md` (gitignored — regenerate with the harness).

## Claim

With the input to the LLM call held byte-identical, the same field's four-state outcome can
change from run to run. Temperature 0 is **not** effectively deterministic in this stack
(litellm → Bedrock → Claude). Therefore a single extraction run is one draw from a distribution,
and any corpus statistic reported from one run carries uncharacterized run-to-run variance.

## Evidence (N=15)

3 of 24 field-cells flipped across identical input; all three were on chen:

> **CORRECTION, 2026-10-01 — the count is 2, not 3.** The sentence above and "the other 21 cells" below
> are retained as written and are both off by one. Counted from the raw table this file points at
> (`extractor_mvp/results/VARIANCE_PROBE.md`, gitignored): chen has exactly **two** fields marked
> unstable — `base_pipeline` (2 distinct outcomes) and `temporal_standardization.method` (2) — and
> oconnor and weber have **none**. So **2 of 24 flipped and 22 were stable**. The summary table below
> lists `surface_projection.surface_registration` as a third chen row, but marks it `stable` ×15; it
> looks like the third flip and is not one.
>
> **Nothing binding depends on this.** The motion pre-registration's `K = 10`
> (`motion-method-reachability-prereg.md:7-8`) cites this file for the *existence* of temp-0
> nondeterminism — which the raw table establishes, and which 2 flips establish as well as 3 would —
> and separately cites "the temporal finding's fixed→fixed 4/10 → 0/10", an independent K=10
> observation (`subject-validator.md:30`, `temporal-firewall-fix.md:24`, `:68`). The justification
> rests on neither 2 nor 3.
>
> The finding is unchanged: at least one field flips across byte-identical input, so temperature 0 is
> not deterministic in this stack. The count was never load-bearing for that; it is corrected because
> a number in a findings document gets quoted.

| field | outcome across 15 identical runs | kind |
|---|---|---|
| chen · temporal_standardization.method | EXTRACTED ×10 / MISSING ×5 | **state flip (EXTRACTED↔MISSING)** |
| chen · base_pipeline | "CCS (CCS)" ×8 / "CCS" ×7 | value-string flip (both resolve to CCS) |
| chen · surface_projection.surface_registration | MISSING ×15 | stable |
| all oconnor + weber fields | 15/15 each | stable |

Only the temporal_standardization cell crosses the EXTRACTED/MISSING boundary — the kind of flip
that changes a corpus count. The base_pipeline flip is cosmetic (parenthetical only). The other
21 cells were stable at N=15.

## Caveats (these travel with the number — do not quote a rate without them)

- **N=15. The flip *rates* (e.g. "10/15", "≈33%") are point estimates with wide, uncomputed
  confidence intervals.** The finding that is robust is *directional*: at least one field flips,
  so temp-0 determinism is falsified. The magnitude is characterized only to order-of-magnitude.
  Do not cite "33% false-absence" as a system constant; cite "flips observed at N=15; rate not
  yet characterized with error bars."
- Stability at N=15 (the 21 stable cells) is **not** proof of determinism — only that no flip was
  observed in 15 draws. A low-probability flip would need larger N to surface.
- Measured on 3 papers. Generalization to the full corpus is assumed, not shown.
- The stability that *is* observed is genuine, not manufactured: the runs are not identical
  (10/5 and 8/7 splits appear), which rules out Bedrock prompt-caching or a fixed seed pinning
  outputs. Confirmed separately that `temperature=0.0` reaches the API layer (extractor.py:769).
- This variance is **not** a retry/reask artifact — see [retry audit](../adr/max-retries-value-fields-free-string.md):
  0/95 corpus calls fired any reask, so the flips are single-call sampling nondeterminism.

## Consequence

No corpus number should be reported from a single run. Any headline (KB intersection, recall,
false-absence rate) needs K≥10 repeats and should report a modal state with a count or a flip-rate,
not a single state. A v6-vs-v7-style diff is only trustworthy for fields that are per-run stable on
both inputs; a field inside its own noise band must not be read as a real change.

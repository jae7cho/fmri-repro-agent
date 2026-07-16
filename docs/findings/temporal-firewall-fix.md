# Finding: a subject-first firewall converts chen's false positive without regressing true positives

**Harness:** `extractor_mvp/scripts/chen_fix_ab.py` (capture) · **Model (pinned):**
bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0, temp 0 · **same session, back-to-back.**
Raw dump: `extractor_mvp/results/CHEN_FIX_AB.md` + `chen_fix_ab.jsonl` (gitignored).
The prompt change was applied for Run 2/3 then **reverted** — `extractor.py` is back at HEAD, nothing
committed. This doc records a *validated candidate fix* with its exact patch, for deliberate adoption.

> **UPDATE (2026-07-14, post-v0.4.0 adoption).** The patch below is now **applied and staged**
> (not the reverted candidate state described above). Before adoption it was **re-baselined at
> HEAD after v0.4.0**, because v0.4.0 changed the exact layer that produced the numbers in *The
> three measurements* below: a tier-5-recovered span used to drop to MISSING and is now KEPT as
> `EXTRACTED`+`span_recovered`. The original three-measurement numbers are therefore **pre-v0.4.0
> and now historical** — see *Post-v0.4.0 re-baseline* for the current single-session A/B. Treat every
> rate here as a point estimate, not a constant; note that arm 2 shows the baseline variance is NOT
> distinguishable from sampling noise at K=20 (no demonstrated drift) — see *Arm 2* and *Caveats*.

## Verdict: YES — convert chen, no true-positive regression

The scoped prompt change converts chen's temporal_standardization false positive from 70% → 0%
EXTRACTED, and the one genuine true positive (liu_2013) stays 10/10 EXTRACTED on its BOLD-signal
sentence. ~~It additionally corrects part of a *second* false positive (viduarre, ICA components).~~
**[CORRECTED post-v0.4.0]** — this viduarre claim does NOT carry forward: in the 2026-07-14 session
viduarre's false positive did not fire at all (0/10 baseline), so there was nothing for the fix to
correct. See *Post-v0.4.0 re-baseline*. Arm-1's supported claim is the chen conversion + no
true-positive regression, and nothing more.

## Context that matters: the firewall already existed and was being ignored

The baseline stanza ALREADY excludes connectivity-derived normalization, with a near-miss example
("the SFC map was normalized to 0 mean and 1 variance" → NOT this field). So the baseline failure is
not a missing rule — the model **overrides an explicit, near-identical instruction**. The change that
worked was not "add the rule" but restructure it: a mandatory **SUBJECT-FIRST decision rule** (identify
what is being normalized before choosing status) plus a near-miss quoting chen's actual sentence.

## The three measurements (PRE-v0.4.0 — historical)

> These numbers predate v0.4.0's span-recovery consumption. They remain the record of the original
> validation but are NOT the current baseline; see *Post-v0.4.0 re-baseline* below. Retained, not
> deleted, per findings discipline.

Slice sha256[:16] `1a6d8afbec64e926`, identical across Run 1 and Run 2 (asserted).

| run | paper | K | temporal EXTRACTED / MISSING |
|---|---|---|---|
| RUN 1 baseline (today) | chen_2015 | 20 | **14 / 6** (70% EXTRACTED) |
| RUN 2 fixed | chen_2015 | 20 | **0 / 20** (0% EXTRACTED) |
| RUN 3 regression (fixed) | liu_2013 | 10 | **10 / 0** — true positive preserved |
| RUN 3 regression (fixed) | viduarre_2017 | 10 | 4 / 6 — was itself a false positive (see below) |

### Quote-groups side by side (chen, the evidence)

| run | count | verbatim_quote (temporal_standardization_method, EXTRACTED) |
|---|---|---|
| RUN 1 | 9 | "Of note, this surface-based SFC was estimated using the same preprocessed rfMRI data as ReHo but normalized (0 mean and 1 variance)." |
| RUN 1 | 5 | "This surface-based SFC was estimated using the same preprocessed rfMRI data as ReHo but normalized (0 mean and 1 variance)." |
| RUN 2 | 0 | *(no EXTRACTED draws — full conversion to MISSING)* |

Run 2's MISSING draws still list `searched_terms` = normalized / standardized / z-score / unit
variance / voxel — the model **looks at the same sentence and now declines it.** No residual
EXTRACTED draw cites a different sentence → no second binding path left open on chen.

### Run 3 — the regression check, read carefully

- **liu_2013 (genuine true positive): 10/10 EXTRACTED**, all citing *"Finally, for each voxel, the
  fMRI signal was temporally normalized by subtracting its mean and then dividing by its temporal
  standard deviation (SD)."* — a real voxelwise BOLD z-scoring. **Preserved. No regression.**
- **viduarre_2017 was NOT a true positive.** Its v6 EXTRACTED (and the 4/10 that survive the fix)
  cite *"Such time series (… × number of ICA components = 820 × 4 × 1,200 × 50) were finally
  standardized so that, for each scan, subject, and ICA component, the data have a mean of 0 and SD
  of 1."* — ICA-**component** standardization, which the firewall explicitly excludes. So the fix
  moving viduarre 60% toward MISSING is a *second partial correction*, not a regression.

Bleed re-check: `intensity_convention` stayed `fsl_grand_mean_10000` 20/20 in BOTH runs — the fix did
not disturb the adjacent field.

## Post-v0.4.0 re-baseline (2026-07-14, single session)

**Harness:** augmented capture (RAW via the same `completion:response` hook as `chen_fix_ab.py`,
PLUS the FINAL four-state read from `extract()`'s returned `Preprocessing`, incl. `span_recovered`).
Same pinned model (sonnet-4-5, temp 0), same session, back-to-back baseline (HEAD) then fixed
(patch applied). Raw dump gitignored in `results/tempfw_{baseline,fixed}.jsonl`. Per-paper slice
hashes asserted identical across arms: chen `1a6d8afbec64e926`, liu `ee061645c158000b`,
viduarre `9809990c45a78488`, derosa `a08a71f9548c3bb0`.

Why re-baseline: v0.4.0 keeps tier-5-recovered spans as `EXTRACTED`+`span_recovered` (they used to
drop to MISSING). So RAW (model decision — what the prompt can move) and FINAL (post-processed
four-state — what ships) can now diverge, and a case invisible pre-v0.4.0 (derosa) is now live.

| paper | K | BASELINE RAW→FINAL | FIXED RAW→FINAL | note |
|---|---|---|---|---|
| chen_2015 | 20 | 17 ext / 3 miss (0 rec) | **0 ext / 20 miss** | target SFC false positive — converted this session |
| liu_2013 | 10 | 10 ext (0 rec) | **10 ext** | genuine voxelwise BOLD z-score — PRESERVED, no regression |
| viduarre_2017 | 10 | 0 ext / 10 miss | 0 ext / 10 miss | ICA-component FP did NOT manifest this session (non-stationary) |
| derosa_2025 | 10 | 9 ext / 1 miss (**9 rec**) | **10 ext (10 rec)** | NEW; v0.4.0-surfaced; fix does NOT close it |

`intensity_convention` (bleed control): chen `fsl_grand_mean_10000` 20/20 in BOTH arms; liu/viduarre/
derosa `None` 10/10 in BOTH arms. **No bleed.**

### Reading the arms (single-session point estimates — not rates)

- **chen (target):** 17/20 → 0/20 EXTRACTED. The 17 baseline draws split 9 + 8 across two surface
  variants of the SAME binding sentence ("…this surface-based SFC…normalized (0 mean and 1 variance)",
  with/without a leading "Of note,") — one SFC sentence, exactly the shape the pre-v0.4.0 RUN 1 saw
  (9 + 5). So the 0/20 conversion closes the same binding path, not a different one. Directionally
  consistent with the pre-v0.4.0 result (14/20 → 0/20). Fixed MISSING draws still carry `searched_terms`
  = normalized/standardized/z-score/unit variance/voxel and cite nothing else — the model looks at the
  SFC sentence and now declines it. RAW==FINAL here (0 recovery), so the conversion is a genuine
  model-decision change the prompt moved.
- **liu (true positive):** 10/10 → 10/10, all citing *"Finally, for each voxel, the fMRI signal was
  temporally normalized by subtracting its mean and then dividing by its temporal standard deviation
  (SD)."* No regression. (STOP condition clear.)
- **viduarre (ICA-component FP): the false positive NEVER FIRED this session — 0/10 in the BASELINE.**
  **[REVISITED by arm 2 (2026-07-16): it fired 1/10 in the baseline. The claim below that this is
  "the strongest single non-stationarity data point" does NOT survive: across 4/10 (pre-v0.4.0) →
  0/10 (arm-1) → 1/10 (arm-2), no pairwise difference is significant (Fisher p ≥ 0.087). This is a
  low-rate ICA-component OVERRIDE (~0–4/10), not drift; arm-1's 0/10 was a draw from a low-rate
  distribution, not a disappearance. See Arm 2.]**
  This is NOT the fix correcting viduarre (0/10 in both arms because the precondition was already
  absent). The pre-v0.4.0 doc's claim that the fix "additionally corrects part of a second false
  positive (viduarre, ICA components)" (measured 4/10 surviving) **must not carry forward from this
  session** — there was nothing to correct. Two controls make this a clean non-stationarity data
  point rather than an artifact of our own tooling:
  - **Identical input, identical prompt.** viduarre's slice hash is `9809990c45a78488` in BOTH the
    pre-v0.4.0 RUN 3 and this session (the hashes recorded in this doc are the durable artifact a
    reader re-derives; the per-draw raw dumps are local/gitignored). chen's slice was
    `--expect-hash`-asserted `1a6d8afbec64e926` in both arms. And `EXTRACTION_PROMPT` is byte-identical
    between the RUN-3-era base commit `9eed38b` and this session's pre-patch base `c75eccf` (the string
    literal was AST-extracted from both revisions and compared). The reference is pinned to the fixed
    commit `c75eccf`, NOT a moving `HEAD` — the patch landed in `b396772`, so `9eed38b == HEAD` is now
    false by construction; `9eed38b == c75eccf` is the durable assertion. So with the same verbatim
    patch applied to both fixed arms, the ENTIRE prompt is held constant. Same bytes, same prompt, same
    pinned model → session drift, nothing else.
  - **v0.4.0 span-recovery is a no-op here.** viduarre is `span_recovered` 0/10 in BOTH arms (as is
    chen, 0/20), so the baseline cannot be an artifact of v0.4.0's span-recovery change — that layer
    never fires on these cells. (derosa is the contrast: `span_recovered` 9–10/10, genuinely
    v0.4.0-surfaced.)
  The clean measurement is **like-for-like, fixed arm → fixed arm**, and needs no assumption about the
  fix's direction: viduarre **4/10** under the fix (pre-v0.4.0 RUN 3) → **0/10** under the *same* fix
  (this session) — same verbatim patch, same slice hash `9809990c45a78488`, same pinned model, whole
  prompt held constant, only the SESSION differs. That is the strongest single non-stationarity data
  point in this finding: a reason to design arm 2, not evidence for the fix. (A cross-arm reading —
  pre-v0.4.0 fixed 4/10 vs this-session baseline 0/10 — points the same way but is weaker, because it
  would assume the patch is monotonically suppressing; the derosa cell here falsifies that (baseline
  9/10 → fixed 10/10). The fixed→fixed comparison avoids the assumption entirely.)
- **derosa_2025 (NEW — a RESULT, not merely out-of-scope):** 9/10 → 10/10 EXTRACTED, **every EXTRACTED
  draw `span_recovered=True`** (the single baseline non-extract was a *model* MISSING — RAW status
  `missing`, no quote — not a span even tier-5 could recover). All draws cite one sentence:
  *"Activation patterns were standardized prior to further analysis to ensure consistency across parcels
  and sessions."* The subject is **activation patterns** — a parcel-level DERIVED product, not the BOLD
  time series — so EXTRACTED here is a genuine false positive; the cell does not invert to a true
  positive. Pre-v0.4.0 these draws dropped to MISSING (unresolved span) and were invisible; v0.4.0 makes
  them a live EXTRACTED population. **The subject-first fix does not reach it** — this is the SECOND
  derived-subject shape it misses (viduarre-ICA was the first, in the doc's own session), an independent
  confirmation of the doc's own prediction that "the near-miss example is SFC-specific." The 9→10 is one
  draw at K=10 — read it as **no effect**, not the fix worsening derosa.
  Note the two misses are DIFFERENT CLASSES, which "the fix is SFC-shaped" hides: viduarre is an
  OVERRIDE failure — the DECISION RULE explicitly names "ICA/PCA components" and the model extracted
  anyway. derosa is a COVERAGE failure — "activation patterns" is named nowhere in the rule, so there
  was nothing to override. Only one of the two was ever covered. This distinction is what the
  deterministic [subject-validator](subject-validator.md) measures as separate enforcement vs coverage
  lists, and it is why a derived-product denylist is unbounded (derosa is the first not-named shape,
  from a corpus of twenty).

### Honest bounds

- Single session, single draw per arm. chen's 0/20 is a strong signal but a point estimate; the field's
  baseline drifts across sittings (see [variance](variance.md), [chen-temporal-flip](chen-temporal-flip.md)).
  **Not** validated across sessions — re-score over K runs across sessions before treating the
  conversion as a fixed rate.
- STOP conditions were pre-declared: liu regression OR `intensity_convention` movement. Neither
  occurred. Adoption proceeds on that basis.
- **What arm-1 supports — and what it does not.** Arm-1 supports this finding's TITLE precisely —
  *converts chen's false positive without regressing true positives* — and nothing beyond it. It does
  **not** support "subject-first adjudication generalizes": one derived-subject shape converted (the
  SFC shape its near-miss literally quotes), and two derived-subject shapes left untouched (viduarre-ICA
  in the doc's session; derosa activation-patterns here). The broader principle — *restructuring
  adjudication order beats adding rules* — is therefore supported for ONE case and unreplicated for TWO.
  This is a targeted patch for the chen/SFC shape, not a general firewall.
- The activation-pattern and ICA-component paths are deliberately NOT addressed here (see scope
  boundary): closing them needs its own near-miss, which would be a new untested prompt change bundled
  with a validated one. Each earns its own A/B.

## Arm 2 — second-session replication (2026-07-16, 17:06–17:28 ET)

Arm-1 was a single session. This tests whether the conversion REPLICATES. **Independence criterion
(stated, not pretended principled):** the drift mechanism is unknown — provider-side serving changes,
routing, or sampling. "Session" is a PROXY for calendar-time variation, not a controlled variable. So
arm 2 ran on a DIFFERENT calendar day (2026-07-16 vs arm-1's 2026-07-14), fresh process, model pinned
`bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0` temp 0. Date, wall-clock (17:06–17:28 ET), and
pin are recorded here and in the run tags (`ARM2_baseline` / `ARM2_fixed`, appended to
`results/chen_fix_ab.jsonl`) so a later analysis can look for structure we cannot see yet.

**Controls held (only the session varied):** all four `--expect-hash` guards passed → slices
byte-identical to arm-1 (chen `1a6d8afbec64e926`, liu `ee061645c158000b`, viduarre `9809990c45a78488`,
derosa `a08a71f9548c3bb0`). `extractor.py` differs from arm-1 only by the 12-line DECISION RULE
(verified `c75eccf` vs HEAD); the baseline arm ran on `c75eccf`'s pre-patch prompt via a clean
file checkout, the fixed arm on HEAD. Harness: `chen_fix_ab.py` (RAW capture).

| paper | K | arm-1 base→fixed | arm-2 base→fixed | intensity (both arms) |
|---|---|---|---|---|
| chen_2015 | 20 | 17/20 → **0/20** | 14/20 → **0/20** | `fsl_grand_mean_10000` 20/20 |
| liu_2013 | 10 | 10/10 → 10/10 | 10/10 → 10/10 | None |
| viduarre_2017 | 10 | 0/10 → 0/10 | **1/10 → 1/10** | None |
| derosa_2025 | 10 | 9/10 → 10/10 | 8/10 → 10/10 | None |

### Reading (point estimates — never rates)

- **chen fixed arm REPLICATES: 0/20 again → 0/40 EXTRACTED across two sessions** (independent draws,
  identical slice + prompt, sessions apart). The conversion is no longer a single session. Not a rate:
  two point estimates that agree. **The fixed-arm rate's 95% CI upper bound is 8.8%** (0/40,
  Clopper-Pearson two-sided; one-sided 7.2%). Against a ~75% baseline, that separation is enormous and
  needs no drift story at all — it is the result.
- **chen baseline = 14/20 (70%) — this is sampling noise at K=20, NOT drift.** The three
  hash-asserted baseline points (14/20, 17/20, 14/20) pool to **75%** and are homogeneous:
  **χ²=1.60, df=2, p=0.45** — indistinguishable from a single constant rate. Even all five historical
  points (67/100/70/85/70) fail to reject homogeneity (**χ²=9.06, df=4, p=0.060**). The apparent
  "drift" rests on the two points that PREDATE `--expect-hash` (67% = 10/15, 100% = 20/20 — slice
  identity never established): the 100% is a genuine outlier against a 70% run (Fisher **p=0.020**),
  but from a run with no hash assertion — the exact confound we assert hashes against. **Supportable
  claim: baseline ≈ 75%; at K=20 session-to-session variation is not distinguishable from binomial
  sampling noise.**
- **liu preserved 10/10 in both arms; intensity_convention stable in every cell.** Both pre-declared
  STOP gates clear in arm 2 as well.
- **viduarre — arm-1's "strongest non-stationarity" headline does NOT survive.** Arm-1 read the 0/10
  baseline as "the FP never fired." Arm-2 baseline is **1/10**, and NO pairwise comparison across the
  three cells is significant: 4/10 (pre-v0.4.0 fixed) vs 0/10 (arm-1) Fisher **p=0.087**; 4/10 vs 1/10
  **p=0.30**; 0/10 vs 1/10 **p=1.00**. (A 3-way χ²=6.24/p=0.044 is unreliable — expected counts 1.67 <
  5.) So this is a **low-rate ICA-component OVERRIDE (~0–4/10), not drift**: arm-1's 0/10 was a draw
  from a low-rate distribution, not a disappearance. The fix does not suppress it (1/10 → 1/10),
  consistent with an override failure (the rule names ICA/PCA components; the model extracts anyway).
- **derosa 8/10 → 10/10** — replicates the coverage failure; the SFC-shaped fix does not reach the
  activation-pattern shape.

### Honest bounds (arm 2)

Two sessions is two draws, not a rate. chen's 0/40 fixed-arm is a strong replication of the
conversion — the correct statement is "replicated across two sessions, n=40 draws, 0 EXTRACTED," not
"the fix converts chen to 0%." The baseline's five points do NOT demonstrate drift: on the three
hash-controlled points they are homogeneous (p=0.45), and even all five fail to reject a constant rate
(p=0.060) — the correct summary is **baseline ≈ 75%, variance not distinguishable from binomial
sampling noise at K=20** (a third session adds a point, not a rate, and would not by itself settle
drift-vs-noise). What is demonstrated is the SEPARATION: fixed-arm ≤ 8.8% (95%) against a ~75%
baseline. viduarre and derosa remain the two derived-subject shapes the patch does not fully close
(a low-rate override and a coverage gap respectively; see the [subject-validator](subject-validator.md)).

## The exact patch (applied and staged; not committed)

Inserted into the `temporal_standardization_method` stanza of `EXTRACTION_PROMPT` in
`extractor_mvp/src/extractor_mvp/extractor.py`, right after "Canonical values: …":

```
  DECISION RULE (apply BEFORE choosing status): identify the SUBJECT of any "normalized" /
  "standardized" / "z-scored" / "0 mean and 1 variance" / "unit variance" operation. This
  field is "extracted" ONLY when that subject is the voxelwise or vertexwise BOLD TIME SERIES
  itself. If the subject is a measure DERIVED from the signal -- a connectivity estimate
  (FC, SFC, ReHo, seed-connectivity), a correlation/connectivity matrix, a gradient,
  ICA/PCA components, nuisance regressors, classifier features, QC metrics, or a statistical
  map -- the field is "missing", no matter the wording used. When in doubt about the subject,
  choose "missing".
  NEAR-MISS that is MISSING (do NOT extract): "this surface-based SFC was estimated using the
  same preprocessed rfMRI data as ReHo but normalized (0 mean and 1 variance)" -> missing,
  because the SUBJECT normalized is the SFC connectivity map (a derived metric), not the BOLD
  time series.
```

## Caveats (travel with the result)

- **Baseline variance is not distinguishable from sampling noise at K=20 — NOT demonstrated drift.**
  Five chen-baseline points exist: 67% (10/15), 100% (20/20), 70% (14/20), 85% (17/20), 70% (14/20).
  The first two **predate `--expect-hash`**, so their slice identity was never controlled. The three
  hash-asserted points pool to **75%** and are homogeneous (**χ²=1.60, df=2, p=0.45**); all five
  together still fail to reject a constant rate (**χ²=9.06, df=4, p=0.060**). The "drift" impression
  rests on the two uncontrolled points (the 100% is a Fisher **p=0.020** outlier vs a 70% run, but
  from an unhashed slice — the confound `--expect-hash` exists to kill). Supportable claim:
  **baseline ≈ 75%; session-to-session variation is indistinguishable from binomial noise at this K.**
  The demonstrated result is the SEPARATION: the fixed arm is 0/40, 95% CI upper bound **8.8%** — re-
  score more sessions before calling the conversion a fixed rate, but ≤8.8% vs ~75% is already large.
  (See [variance](variance.md), [chen-temporal-flip](chen-temporal-flip.md) for the two pre-hash runs.)
- **The fix is SFC-shaped.** chen (SFC) → fully closed (0/20). The near-miss example is SFC-specific.
  Pre-v0.4.0 viduarre (ICA components) was 4/10 under the fix; post-v0.4.0 it is a **low-rate override**
  (0/10 arm-1, 1/10 arm-2) — no pairwise difference is significant (Fisher p ≥ 0.087), so this is
  low-rate noise, not a closure or a drift. A complete firewall may need the subject-first treatment
  generalized, or a post-hoc validator that checks the cited sentence's subject.
- **derosa_2025 is an unclosed residual of the same family (KNOWN LIMITATION).** Post-v0.4.0 it is a
  live `EXTRACTED`+`span_recovered` population (10/10 fixed) on *"Activation patterns were standardized
  prior to further analysis…"* — a signal-DERIVED subject the rule names in class but the model does
  not bind to the rule. The SFC-shaped near-miss does not reach it. This is NOT addressed here by
  design: adding a second (activation-pattern / ICA) near-miss would be a new untested prompt change
  bundled with the validated one, confounding both arms. It earns its own A/B.
- Adopting this is a prompt change → schema/prompt decision, and per the variance finding it must be
  scored over K runs across sessions, not one, before it's called a fixed rate.

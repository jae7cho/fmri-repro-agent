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
> and now historical** — see *Post-v0.4.0 re-baseline* for the current single-session A/B. Baseline
> is non-stationary across sessions; treat every rate here as a point estimate, not a constant.

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
  This is NOT the fix correcting viduarre (0/10 in both arms because the precondition was already
  absent). The pre-v0.4.0 doc's claim that the fix "additionally corrects part of a second false
  positive (viduarre, ICA components)" (measured 4/10 surviving) **must not carry forward from this
  session** — there was nothing to correct. Two controls make this a clean non-stationarity data
  point rather than an artifact of our own tooling:
  - **Identical input, identical prompt.** viduarre's slice hash is `9809990c45a78488` in BOTH the
    pre-v0.4.0 RUN 3 and this session (the hashes recorded in this doc are the durable artifact a
    reader re-derives; the per-draw raw dumps are local/gitignored). chen's slice was
    `--expect-hash`-asserted `1a6d8afbec64e926` in both arms. And `EXTRACTION_PROMPT` is byte-identical
    between the RUN-3-era base commit `9eed38b` and HEAD (the string literal was AST-extracted from
    both revisions and compared) — so with the same verbatim patch applied to both fixed arms, the
    ENTIRE prompt is held constant. Same bytes, same prompt, same pinned model → session drift, nothing
    else.
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

- **One session.** Run 1's 70% is today's rate; the field's baseline drifts across sessions
  (67% / 100% / 70% over three sittings — see [variance](variance.md) and
  [chen-temporal-flip](chen-temporal-flip.md)). Run 2's 0/20 is a strong signal, but "0%" is a
  single-session point estimate; re-score across sessions before treating the conversion as a
  constant.
- **The fix is SFC-shaped.** chen (SFC) → fully closed (0/20). The near-miss example is SFC-specific.
  Pre-v0.4.0 this partially closed viduarre (ICA components, 4/10 residual); in the post-v0.4.0
  session viduarre's FP did not manifest at all (0/10 both arms), so no closure was measurable there.
  A complete firewall may need the subject-first treatment generalized, or a post-hoc validator that
  checks the cited sentence's subject.
- **derosa_2025 is an unclosed residual of the same family (KNOWN LIMITATION).** Post-v0.4.0 it is a
  live `EXTRACTED`+`span_recovered` population (10/10 fixed) on *"Activation patterns were standardized
  prior to further analysis…"* — a signal-DERIVED subject the rule names in class but the model does
  not bind to the rule. The SFC-shaped near-miss does not reach it. This is NOT addressed here by
  design: adding a second (activation-pattern / ICA) near-miss would be a new untested prompt change
  bundled with the validated one, confounding both arms. It earns its own A/B.
- Adopting this is a prompt change → schema/prompt decision, and per the variance finding it must be
  scored over K runs across sessions, not one, before it's called a fixed rate.

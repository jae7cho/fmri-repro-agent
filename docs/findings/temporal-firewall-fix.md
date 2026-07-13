# Finding: a subject-first firewall converts chen's false positive without regressing true positives

**Harness:** `extractor_mvp/scripts/chen_fix_ab.py` (capture) · **Model (pinned):**
bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0, temp 0 · **same session, back-to-back.**
Raw dump: `extractor_mvp/results/CHEN_FIX_AB.md` + `chen_fix_ab.jsonl` (gitignored).
The prompt change was applied for Run 2/3 then **reverted** — `extractor.py` is back at HEAD, nothing
committed. This doc records a *validated candidate fix* with its exact patch, for deliberate adoption.

## Verdict: YES — convert chen, no true-positive regression

The scoped prompt change converts chen's temporal_standardization false positive from 70% → 0%
EXTRACTED, and the one genuine true positive (liu_2013) stays 10/10 EXTRACTED on its BOLD-signal
sentence. It additionally corrects part of a *second* false positive (viduarre, ICA components).

## Context that matters: the firewall already existed and was being ignored

The baseline stanza ALREADY excludes connectivity-derived normalization, with a near-miss example
("the SFC map was normalized to 0 mean and 1 variance" → NOT this field). So the baseline failure is
not a missing rule — the model **overrides an explicit, near-identical instruction**. The change that
worked was not "add the rule" but restructure it: a mandatory **SUBJECT-FIRST decision rule** (identify
what is being normalized before choosing status) plus a near-miss quoting chen's actual sentence.

## The three measurements

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

## The exact patch (candidate; not committed)

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
- **The fix is SFC-shaped.** chen (SFC) → fully closed (0/20); viduarre (ICA components) → only
  partially closed (4/10 survive). The near-miss example is SFC-specific; the ICA-component path is
  named in the rule but the model still mis-binds it 40% of the time. A complete firewall may need
  the same subject-first treatment generalized, or a post-hoc validator that checks the cited
  sentence's subject.
- Adopting this is a prompt change → schema/prompt decision, and per the variance finding it must be
  scored over K runs across sessions, not one, before it's called a fixed rate.

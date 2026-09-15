> **Moved from `extractor_mvp/results/batch_v7_full/ATTRIBUTION_DIFF.md` on 2026-09-14.** That directory is ignored by a
> bare `*`, so this analysis had no tracked home and appears in no backup archive. Of 18 distinctive sentences here, **none** appears in any tracked file.
> The run artifacts it was computed from stay ignored — only the prose moved.
>
> **A halted pre-registered re-derivation.** The chen canary failed and the corpus re-derivation was
> withheld under the pre-registered rule. A negative result with no tracked home is the shape that
> disappears quietly, which is why it moved first.

# v7 vs v6 attribution diff — HALTED

**Verdict: the chen canary failed and the thesis flip did not occur. Re-derivation of the
corpus numbers (KB intersection, etc.) is WITHHELD** per the pre-registered rule: one lost
chen field halts the whole re-derivation. This document records what the run showed and why
it halts — it is not a clean baseline.

- Run: `batch_v7_full`, 19/19 papers successful, 0 failed. cabral_2017 excluded (N=19).
- Model: `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0` — **identical** to v6_full
  (probed live before the run). **temperature = 0.0.** Decoding is deterministic, so the
  ONLY thing that differs between v6 and v7 for a targeted field is the input text (the
  methods slice). Schema v0.3.0 (a) and the nuisance step (b) add only *untargeted* fields,
  which cannot change a targeted field's state. **Every targeted-field change below is a (c)
  methods_finder slice effect.**

## Targeted-field state changes (8 of 152 compared) — all cause (c)

| paper | field | v6 -> v7 | dir |
|---|---|---|---|
| chen_2015 | surface_projection.surface_registration | EXTRACTED -> MISSING | **LOSS (canary)** |
| chen_2015 | temporal_standardization.method | MISSING -> EXTRACTED | gain |
| cole_2013 | base_pipeline | EXTRACTED -> MISSING | **LOSS** |
| poldrack_2015 | intensity_normalization.convention | MISSING -> EXTRACTED | gain |
| poldrack_2015 | surface_projection.surface_registration | MISSING -> EXTRACTED | gain |
| poldrack_2015 | spatial_normalization.resolution_mm | MISSING -> EXTRACTED | gain |
| viduarre_2017 | temporal_standardization.method | EXTRACTED -> MISSING | LOSS |
| weber_2024 | surface_projection.surface_registration | EXTRACTED -> MISSING | LOSS |

Net: 4 gains, 4 losses. Not a clean recovery — a redistribution.

## 1. chen canary — FAILED, but NOT by slice-cutting

chen lost `surface_projection.surface_registration` (v6 EXTRACTED `freesurfer_recon`, backed
by "...surfaces were reconstructed and spatially normalized ... via a sphere registration").

**Verified: that span text is INSIDE the v7 slice** ([10617, 26692), ratio 0.21; "via a
sphere registration", "spatially normalized to match a group-level standard", "fsaverage5",
"global mean intensity to 10,000" are all present). So the header vocabulary is NOT cutting
methods text — the remedy the guard anticipated ("vocabulary needs another pass") does not
apply. At temperature 0, the SAME model, given a slice that CONTAINS the text, extracted the
field from the whole-document v6 input but not from the 21% v7 slice. The tighter (correct)
slice removed surrounding context the model had been relying on to recognise the field. A
correct slice made extraction WORSE here.

The other three chen values survived unchanged (target_surface=fsaverage5,
intensity convention=fsl_grand_mean_10000, value=10000; base still recognises to ccs — the
name dropped the "(CCS)" parenthetical, EXTRACTED both runs).

## 2. Thesis flip (oconnor / weber -> C-PAC) — DID NOT OCCUR

- oconnor_2017 base_pipeline: MISSING -> **still MISSING**. C-PAC IS in the v7 slice
  ("preprocessing in C-PAC", "Configurable Pipeline for the Analysis of Connectomes" both
  present, slice [7610,37379)). The slice fix succeeded; the MODEL still did not extract it.
- weber_2024 base_pipeline: MISSING -> **still MISSING** ("C-PAC" present in the slice). It
  also LOST surface_registration.

The slice was necessary but not sufficient. The binding constraint on the C-PAC papers is
the **model's extraction** (a false negative on clean, present text), not the methods slice.
"Extraction recall recovery via the slice fix" is **not validated** by this run.

## 3. Conclusion

- The methods_finder change is a correct SLICING improvement (chen 1.00->0.21, oconnor
  0.63->0.56, both verified to contain their key spans). But better slices did NOT translate
  to better extraction: they produced a mix of gains and losses and broke the canary.
- Do NOT promote v7 to baseline. v6_full remains the baseline. No corpus number is
  re-derived from v7.
- The real lever for C-PAC recall is the extractor's model/prompt, not the slice — that is
  the next investigation, and it needs a determinism-controlled design (repeat runs) so
  single-run redistribution is not mistaken for signal.

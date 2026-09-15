> **Moved from `extractor_mvp/results/batch_sfn_v3/delta_v1_v2_v3.md` on 2026-09-14.** That directory is ignored by a
> bare `*`, so this analysis had no tracked home and appears in no backup archive. Its content appears in no tracked file.
> The run artifacts it was computed from stay ignored — only the prose moved.
>
> The v3 column is the honest recount after the v2 coercion recorded in
> [`sfn-v1-v2-delta-coercion.md`](sfn-v1-v2-delta-coercion.md).

# v1 -> v2 -> v3 aggregate delta

| metric | v1 | v2 (coerced) | v3 (honest) |
| --- | --- | --- | --- |
| extracted | 21 | 32 | 17 |
| vlit | 14 | 1 | 18 |
| qunres | 5 | 11 | 8 |
| miss | 79 | 74 | 76 |

## Headline: target_space underspecification (value_not_in_literal preserved)
- v1: 7 MNI/MNI152 flags · v2: **5 coerced to MNI152NLin6Asym (CORRUPTED)** · v3: **all 7 preserved + 2 more caught (power, wheaton)** = 9 honest flags
- power_2014 / wheaton_2004: v1 `EXTRACTED=MNI152NLin6Asym` (coercion; paper says 'atlas space' / 'SPM MNI') -> v3 `value_not_in_literal` (honest)

## Convention gains (spec-extension members), preserved in v3
- liu_2013 `voxel_temporal_zscore`, poldrack_2015 + power_2014 `global_mode_1000`: Extracted with spans
- mueller_2021 `global_median_1000`: member resolved via synonym; quote not in methods slice -> quote_unresolved

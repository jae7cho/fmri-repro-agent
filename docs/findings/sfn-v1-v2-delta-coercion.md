> **Moved from `extractor_mvp/results/batch_sfn_v2/delta_vs_v1.md` on 2026-09-14.** That directory is ignored by a
> bare `*`, so this analysis had no tracked home and appears in no backup archive. Its content appears in no tracked file.
> The run artifacts it was computed from stay ignored — only the prose moved.
>
> **Records that aggregate gains were partly not honest** — the v2 enumerated-members prompt coerced
> underspecified MNI terms into a specific member in 5 of 7 cases. A finding against this project's
> own numbers.

# v1 -> v2 delta (Unicode resolver + enumerated-members prompt)

> WARNING: the v2 n_extracted gains on target_space are largely COERCION — the
> enumerated-members prompt pushed underspecified "MNI"/"MNI152" into the specific
> `MNI152NLin6Asym` member (5 of 7 v1 cases). Aggregate gains are not all honest.

| paper_id | v1_extr | v2_extr | v1_vlit | v2_vlit | v1_qunres | v2_qunres | v1_miss | v2_miss | net |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mueller_2021 | 1 | 3 | 1 | 0 | 1 | 1 | 3 | 2 | +2 |
| vanderwal_2016 | 0 | 2 | 1 | 0 | 0 | 0 | 5 | 4 | +2 |
| weber_2024 | 1 | 3 | 2 | 0 | 0 | 0 | 3 | 3 | +2 |
| agtzidis_2020 | 0 | 1 | 1 | 0 | 1 | 1 | 4 | 4 | +1 |
| chen_2015 | 2 | 3 | 2 | 1 | 0 | 2 | 2 | 0 | +1 |
| derosa_2025 | 0 | 1 | 1 | 0 | 1 | 0 | 4 | 5 | +1 |
| poldrack_2015 | 2 | 3 | 1 | 0 | 1 | 2 | 1 | 0 | +1 |
| power_2014 | 3 | 4 | 1 | 0 | 0 | 0 | 2 | 2 | +1 |
| tang_2025 | 1 | 2 | 1 | 0 | 0 | 0 | 4 | 4 | +1 |
| binder_1999 | 1 | 1 | 0 | 0 | 0 | 0 | 5 | 5 | +0 |
| braun_2015 | 1 | 1 | 0 | 0 | 0 | 0 | 5 | 5 | +0 |
| cabral_2017 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | +0 |
| ciric_2017 | 1 | 1 | 0 | 0 | 0 | 0 | 5 | 5 | +0 |
| cole_2013 | 1 | 1 | 0 | 0 | 0 | 0 | 5 | 5 | +0 |
| liu_2005 | 1 | 1 | 0 | 0 | 0 | 0 | 5 | 5 | +0 |
| oconnor_2017 | 0 | 0 | 1 | 0 | 1 | 2 | 4 | 4 | +0 |
| smith_2013 | 1 | 1 | 1 | 0 | 0 | 0 | 4 | 4 | +0 |
| viduarre_2017 | 1 | 1 | 0 | 0 | 0 | 1 | 5 | 4 | +0 |
| wheaton_2004 | 2 | 2 | 0 | 0 | 0 | 0 | 4 | 4 | +0 |
| liu_2013 | 2 | 1 | 1 | 0 | 0 | 2 | 3 | 3 | -1 |
| **TOTAL** | **21** | **32** | **14** | **1** | **5** | **11** | **79** | **74** | **+11** |

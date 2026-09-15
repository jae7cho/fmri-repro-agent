> **Moved from `extractor_mvp/results/HARD_DROP_AUDIT_v0_4_0.md` on 2026-09-14.** That directory is ignored by a
> bare `*`, so this analysis had no tracked home and appears in no backup archive. Of 3 distinctive sentences here, **none** appears in any tracked file.
> The run artifacts it was computed from stay ignored — only the prose moved.
>
> It **supersedes the corpus-wide headline** in [`span-resolution-hard-drop.md`](span-resolution-hard-drop.md):
> same harness, same model pin, same 19-paper corpus at N=1, but **2 silent drops across 1 paper**
> where the earlier run found 10 across 6. That finding's own raw dump (`HARD_DROP_AUDIT.md`) is a
> different, earlier file and stays ignored. Whether the tracked finding should be amended is not
> settled here — this is the measurement, filed so it stops being invisible.
>
> **One corpus span was removed in the move.** Four cells quoted agtzidis_2020's normalization
> sentence (17 words, twice; truncated to 14, twice). They now read `[span withheld]`. The tracked
> overlap is `ground_truth/target_space_labels_v1.csv`, `agtzidis_2020.supporting_quote`; the full
> span regenerates via `extractor_mvp/scripts/hard_drop_audit.py`. Removing it rather than parking
> the licence question is the same move the review projection made.

# Phase 1 — span-resolution hard-drop audit (measurement only)

Model bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0, temp 0, N=1 over the 19-paper corpus. For each field: RAW model output, whether production's resolve_quote() grounds the quote, and the FINAL four-state. A SILENT DROP = raw extracted + span None + final MISSING_FROM_PAPER.

## Headline

HEADLINE: 2 silent drops (raw=extracted, span=None, final=MISSING) across 1 papers.
By field: {'target_space': 1, 'resolution_mm': 1}
RECOVERABLE mangle (quote present + value in quote): 0 · VALUE-MISMATCH mangle (quote present but value NOT in its own quote — do NOT recover): 0 · genuine-mismatch (quote absent, hallucination-guard): 2 · ambiguous: 0
GENUINE-MISMATCH (quote content absent from source — must keep failing):
  - agtzidis_2020.target_space: 'MNI' quote=[span withheld — see the note at the top of this file]
  - agtzidis_2020.resolution_mm: '3.0' quote=[span withheld — see the note at the top of this file]

## Every silent drop

| paper | field | raw_value | raw_quote (truncated) | why | value_in_quote | artifacts |
|---|---|---|---|---|---|---|
| agtzidis_2020 | target_space | 'MNI' | [span withheld — see the note at the top of this file] | genuine-mismatch (quote_not_found) | True |  |
| agtzidis_2020 | resolution_mm | '3.0' | [span withheld — see the note at the top of this file] | genuine-mismatch (quote_not_found) | False |  |

## All extracted fields (drop or not) — the denominator

| paper | field | span_resolved | final |
|---|---|---|---|
| agtzidis_2020 | base_pipeline_name | True | EXTRACTED (ok) |
| agtzidis_2020 | target_space | False | MISSING_FROM_PAPER (**DROP**) |
| agtzidis_2020 | resolution_mm | False | MISSING_FROM_PAPER (**DROP**) |
| binder_1999 | target_space | True | EXTRACTED (ok) |
| chen_2015 | base_pipeline_name | True | EXTRACTED (ok) |
| chen_2015 | target_space | True | MISSING_FROM_PAPER (ok) |
| chen_2015 | surface_registration | True | MISSING_FROM_PAPER (ok) |
| chen_2015 | target_surface | True | EXTRACTED (ok) |
| chen_2015 | intensity_convention | True | EXTRACTED (ok) |
| chen_2015 | intensity_value | True | EXTRACTED (ok) |
| ciric_2017 | base_pipeline_name | True | EXTRACTED (ok) |
| cole_2013 | target_space | True | EXTRACTED (ok) |
| derosa_2025 | base_pipeline_name | True | EXTRACTED (ok) |
| derosa_2025 | target_space | True | MISSING_FROM_PAPER (ok) |
| derosa_2025 | temporal_standardization_method | True | EXTRACTED (ok) |
| gordon_2014 | base_pipeline_name | True | EXTRACTED (ok) |
| gordon_2014 | target_space | True | MISSING_FROM_PAPER (ok) |
| liu_2013 | base_pipeline_name | True | EXTRACTED (ok) |
| liu_2013 | target_space | True | MISSING_FROM_PAPER (ok) |
| liu_2013 | resolution_mm | True | EXTRACTED (ok) |
| liu_2013 | temporal_standardization_method | True | EXTRACTED (ok) |
| mueller_2021 | base_pipeline_name | True | EXTRACTED (ok) |
| mueller_2021 | intensity_convention | True | EXTRACTED (ok) |
| mueller_2021 | intensity_value | True | EXTRACTED (ok) |
| oconnor_2017 | base_pipeline_name | True | EXTRACTED (ok) |
| oconnor_2017 | target_space | True | MISSING_FROM_PAPER (ok) |
| oconnor_2017 | resolution_mm | True | EXTRACTED (ok) |
| poldrack_2015 | target_space | True | MISSING_FROM_PAPER (ok) |
| poldrack_2015 | resolution_mm | True | EXTRACTED (ok) |
| poldrack_2015 | surface_registration | True | EXTRACTED (ok) |
| poldrack_2015 | target_surface | True | EXTRACTED (ok) |
| poldrack_2015 | intensity_convention | True | EXTRACTED (ok) |
| poldrack_2015 | intensity_value | True | EXTRACTED (ok) |
| power_2014 | target_space | True | MISSING_FROM_PAPER (ok) |
| power_2014 | resolution_mm | True | EXTRACTED (ok) |
| power_2014 | intensity_convention | True | EXTRACTED (ok) |
| power_2014 | intensity_value | True | EXTRACTED (ok) |
| tang_2025 | base_pipeline_name | True | EXTRACTED (ok) |
| tang_2025 | target_space | True | MISSING_FROM_PAPER (ok) |
| tang_2025 | resolution_mm | True | EXTRACTED (ok) |
| vanderwal_2016 | base_pipeline_name | True | EXTRACTED (ok) |
| vanderwal_2016 | target_space | True | MISSING_FROM_PAPER (ok) |
| viduarre_2017 | base_pipeline_name | True | EXTRACTED (ok) |
| weber_2024 | base_pipeline_name | True | EXTRACTED (ok) |
| weber_2024 | target_space | True | MISSING_FROM_PAPER (ok) |
| weber_2024 | surface_registration | True | MISSING_FROM_PAPER (ok) |
| weber_2024 | target_surface | True | MISSING_FROM_PAPER (ok) |
| weber_2024 | intensity_convention | True | MISSING_FROM_PAPER (ok) |
| wheaton_2004 | base_pipeline_name | True | EXTRACTED (ok) |
| wheaton_2004 | target_space | True | MISSING_FROM_PAPER (ok) |

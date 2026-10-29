# The eleven rows after the six follow-ups — coverage_v2 beside coverage_v1: nineteen papers, results (2026-10-28/29)

**DIAGNOSTIC. Not an evaluation.** The nineteen re-run under the six items the author ordered on
2026-10-28 after coverage_v1 (`DESIGN_coverage_expansion.md` B14), with the per-row table **beside**
coverage_v1's, never merged. **No labels and no accuracy figure for the eleven rows (R7)**; every
number is a count of papers or of cells. The three held-out papers entered through the model only and
are read as states and counts.

- **Vintage** `coverage_v2` — `extractor_mvp/results/batch_coverage_v2/` (gitignored): 2026-10-29,
  00:09:38–00:30:18 UTC; started under HEAD `90392e4` (the config commit; the one commit between it
  and the manifest's `44c60db` touched only the re-render script), config
  `configs/batch_coverage_v2_config.yaml` (sha256 `4a5b0f96…`), the same model and settings as
  coverage_v1. **Gate:** `launcher_manifest.json` carries the five prompt hashes —
  `EXTRACTION_PROMPT` `31a050b2…`, `PER_ACQUISITION_EXTRACTION_PROMPT` `04ba3cb7…`,
  `MOTION_METHOD_PROMPT` `b0093774…` (the three unchanged), `TEMPORAL_VOLUME_PROMPT` `18b47abf…`,
  `SPATIAL_PROMPT` `dd46672b…` — the frozen phrase table `85566a83…`, the config's sha256, start, end
  and exit 0; checked before any record was read.
- **Records: 18 of 19.** `status` success 17, `methods_not_found` 1 (liu_2005, as before),
  **`extraction_failed` 1: ciric_2017** — the never-deferred validator (item 2) refused
  `brain_extraction_performed = deferred` on the first completion and on both reasks, and instructor
  raised; the batch records the failure and writes no record. **The cost of item 2, as built:** a
  validator that reasks loses the whole paper when the model holds its answer three times (ciric
  defers brain extraction to Avants et al., 2011b, exactly as in coverage_v1). The v2 column below is
  therefore **over 15 contaminated papers**, v1's over 16. Held for the author: coerce a deferred
  `performed` to missing with a diagnostic instead of reasking, or raise the reask budget for the
  coverage calls; neither was done here, and ciric was not re-run.

## The table — per mandatory row, coverage_v1 (16 contaminated papers) beside coverage_v2 (15)

Row states exclusive in this order: `performed=no`, `addressed`, `deferred`, `unverifiable`, `not
reported` (`not assessed` 0 everywhere). v1 rows sum to 16, v2 rows to 15.

| row | addressed v1 → v2 | performed=no v1 → v2 | deferred v1 → v2 | unverifiable v1 → v2 | not reported v1 → v2 |
|---|---|---|---|---|---|
| Software | 3 → 3 | — | 0 → 0 | 0 → 2 | 13 → 10 |
| T1 stabilization | 5 → 4 | 0 → 0 | 0 → 0 | 0 → 0 | 11 → 11 |
| Brain extraction | 4 → 4 | 0 → 0 | 3 → 1 | 0 → 0 | 9 → 10 |
| Segmentation | 7 → 6 | 0 → 0 | 1 → 1 | 0 → 0 | 8 → 8 |
| Slice time correction | 5 → 5 | 1 → 1 | 0 → 0 | 1 → 0 | 9 → 9 |
| Motion correction | 11 → 11 | — | 4 → 4 | 0 → 0 | 1 → 0 |
| Gradient distortion correction | 3 → 2 | 0 → 0 | 1 → 1 | 0 → 0 | 12 → 12 |
| Distortion correction | 3 → 2 | 0 → 0 | 1 → 1 | 0 → 0 | 12 → 12 |
| Function-structure (intra-subject) coregistration | 10 → 8 | 0 → 0 | 1 → 1 | 1 → 1 | 4 → 5 |
| Intersubject registration | 11 → 13 | — | 1 → 0 | 1 → 0 | 3 → 2 |
| Intensity correction | 3 → 1 | 0 → 0 | 1 → 1 | 0 → 1 | 12 → 12 |
| Artifact and structured noise removal | 14 → 13 | 0 → 0 | 0 → 0 | 0 → 0 | 2 → 2 |
| Volume censoring | 3 → 3 | 1 → 1 | 0 → 0 | 1 → 1 | 11 → 10 |
| Spatial smoothing | 10 → 10 | 1 → 1 | 1 → 0 | 2 → 1 | 2 → 3 |

Read with ciric absent from v2 (in v1 ciric was addressed on T1, segmentation, coregistration,
distortion ×2, intensity correction, artifact, censoring, smoothing, motion; performed=no on slice
timing; deferred on brain extraction): the v2 drops of one on T1 stabilization, segmentation,
artifact and the distortion pair are ciric's row-cells, not movements. What moved: **Intersubject
registration 11 → 13** (agtzidis's target_space and resolution_mm now resolve, ×→/C2 twice, and
binder's); **Motion correction not reported 1 → 0** (agtzidis's operation phrase now resolves, the
cell the corpus run reported unresolved on 10 of 10 draws); **Brain extraction deferred 3 → 1**
(ciric gone, vanderwal's deferral now on a parameter not on `performed`); **Intensity correction
3 → 1** (ciric gone; power's intensity-normalization sentence now unverifiable under the phrase
rule); **Software unverifiable 0 → 2** (cole and poldrack, `base_pipeline_value_unsupported` on the
shared call — a different day's draw of an unchanged prompt, not this build).

**The held-out three, counts only** (42 row-cells summed): v1 addressed 10, performed=no 2,
deferred 1, unverifiable 7, not reported 22; **v2 addressed 10, performed=no 2, deferred 1,
unverifiable 6, not reported 23.**

## Named lines

- **Coverage cells, 15 × 63 = 945 (v2) against 16 × 63 = 1,008 (v1):** extracted 145 (v1 175),
  deferred 16 (10), not stated 707 (738), `step_not_performed` 25 (25), `value_unsupported_by_quote`
  37 (38), `extraction_quote_unresolved` 15 (22).
- **`performed`, 13 × 15 = 195 (v2) against 208 (v1):** yes 56 (68), no 4 (4), deferred **0 (8)**,
  not stated 128 (121), quote unresolved 3 (7), **unsupported by the step's phrases 4 (0)**.
- **The held-out three, 189 cells:** v2 extracted 23, not stated 146, `step_not_performed` 10,
  unsupported 2, unresolved 8 (v1: 22 / 146 / 10 / 2 / 9); `performed` over 39: yes 7, no 2, not
  stated 27, unresolved 3 (v1: 7 / 2 / 26 / 4).
- **Span repairs applied in v2 (tier 6), contaminated papers, listed:** agtzidis ×→/C2 twice on
  five cells (motion method, target_space, resolution_mm, slice-timing `performed`, coregistration
  `performed`); binder fi→ª on four smoothing cells; poldrack >→4 on `scrub.criterion` and
  **<→o twice on `nuisance_regression.filtering_integrated`** (the "<" as "o" leak the author
  named, now observed on a real quote); **the held-out three: 0** repaired spans.
- **`multiple_pipelines` (item 5):** liu_2013 and weber_2024 answered yes on call T (count not
  stated on either), missing on call S; every other contaminated paper missing on both; the held-out
  three: 3 no. The header line renders on those two reports.
- **Wall time** (`wall_time_s`, seconds, v1 → v2): vanderwal 53.87 → 47.45, binder 51.36 → 47.91,
  mueller 55.70 → 49.79, agtzidis 61.71 → 54.17, braun 66.01 → 56.80, cole 59.22 → 60.09, weber
  58.97 → 63.99, power 66.28 → 65.03, derosa 67.82 → 67.17, oconnor 59.31 → 68.46, viduarre 50.03 →
  71.84, gordon 74.77 → 73.14, chen 73.18 → 75.54, liu_2013 60.39 → 79.03, poldrack 84.43 → 82.22;
  ciric 77.50 → (failed, three completions of the spatial call); the held-out three as one group
  176.32 → 183.18; all recorded 1,196.85 → 1,145.82. Launcher clock 20 min 1 s → 20 min 40 s.

## The six items, each replayed before the run (no model call; counts recorded in the commits)

1. **Tier 6** (`3850723`): over every stored result and every recorded draw, 0 previously-resolved
   cells changed; 93 contaminated cells moved (agtzidis, binder, poldrack); 0 held-out.
2. **`performed` never deferred; the phrase table** (`3361c1c`): 3 contaminated cells move to
   unverifiable (power ×2, weber), 8 deferred `performed` cells the validator refuses (ciric 1,
   vanderwal 1, viduarre 6); the held-out three 0 and 0. In the run: the 4 unsupported `performed`
   cells above; the validator's refusal cost ciric.
3. **Alias fixes** (`5ba8d04`): 230 stored terms re-resolve identically; moves chen (csf), three
   Volterra cells, weber (native_surface, a corrected resolution), ciric's detrend; one wrong alias
   found and removed.
4. **Coregistration definitions** (`ec7519a`): no coregistration cell moves on replay.
5. **`multiple_pipelines`** (`a3ce6e3`): no replay (a new field).
6. **Kind prefixes** (`ec7519a`): 30 Rows lines change on the contaminated papers, 4 on the held-out
   three, 0 reports change outside the section.

## The identity gate

Derived unchanged from coverage_v1's (the stored acceptance records carry none of the new fields
and their spans are stored, not re-resolved): `--against da7fe97` (the HEAD before item 1) → **19
identical, 0 changed**; `--against d31e8b7` → 0 identical, 19 changed.

## What was found that was not pre-declared

- **A reask validator can lose a paper.** Item 2 asked for a validator; the codebase's validator
  pattern is a reask with `max_retries=2`; ciric's model answer did not change on reask. One of
  nineteen is the cost on this day.
- **The "<" as "o" leak is real**, on poldrack's filtering sentence, twice in one quote.
- **The phrase rule and the deferral move interact:** vanderwal's brain-extraction deferral moved
  from `performed` to a parameter as the prompt asks, keeping the row deferred.
- **The shared call moved on its own:** Software unverifiable on cole and poldrack from a prompt
  with an unchanged hash — the day-to-day movement the record already carries.

## Status

- No labels, no rates; the held-out three as counts; ciric_2017 absent from coverage_v2 by failure,
  not by exclusion, and not re-run.
- Held for the author: the validator's failure mode (coerce with a diagnostic, or a larger reask
  budget); the count of variants (both yes answers left it unstated); the "¼" as "=" leak seen in
  poldrack, gordon and chen text layers (31, 85, 35 occurrences), outside item 1's rule.

# motion_correction.method — stanza version 6, thirteen papers, results: the adoption rule applied (2026-10-27)

**DIAGNOSTIC. Not an evaluation.** Thirteen papers at K=10 under stanza version 6, against the
readings pre-declared in prereg Amendment 10 (written before the edit and before any call). **No rate,
fraction, percentage or accuracy figure** appears here or may be computed from the projection behind
it (prereg `:9-10`, `:158-159`). Counts are counts of draws. **A new vintage**: never pooled with any
earlier run's draws.

- **Run** 2026-10-27, 13:39:31–14:04:58 UTC. **K** = 10, 13 papers, 130 draws, one session.
- **Model** `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`.
- **Stanza** sha256 `8df070da9cc3f9628d6670c7285740155b05a06dd25972849f0711b056c8ef4f` (7,934
  characters): version 4 plus the package rule in STEP 3 and the two-level output rules in STEP 5,
  from protocol v1.8's text (CALL 1's attribution level), nothing else. **Gate:** the manifest carries
  this hash and `motion_method_prompt_frozen_sha256` equal to it; checked before any record was read.
  No held-out id admitted (`held_out_admitted: []`, licence `None`).
- **Labels** are the v1.8 workbook (`cd98904`; sha256 `894c3bf5…`): `named_tool` 9 (six in the probe
  set, with their attribution level), `deferred` 8, `described_only` 2.
- **Per-draw record** [ground_truth/motion_probe_v6_projection.csv](../../ground_truth/motion_probe_v6_projection.csv)
  — status, heuristic class, state-map row, span offsets, deferral target kind, `model_state`,
  `model_vs_heuristic`, and the new `model_attribution`; **no quote or value text** (53 needles
  derived from the records by script, 0 present in the CSV). The unprojected run is at
  `extractor_mvp/results/motion_probe_v6/` (gitignored).
- **Reasks** 1 of 130 (cole). **Errors** 1 (cole, the binding validator after reask). **Held-out:**
  liu_2005, tang_2025 and wheaton_2004 untouched; not in the probe set.
- **Fitted, by the record:** all thirteen — the package rule is the protocol's, and the protocol's
  worked cases name the probe papers. ciric is post hoc. No count below is independent.

## The adoption rule, applied as written

Amendment 10: *version 6 freezes if every `named_tool` paper — agtzidis, cole, mueller, derosa at the
`package` level; gordon and ciric at the `step` level — returns its level on at least 8 of 10, where
"level" means the raw `motion_correction_binding` equal to the label's level with the raw value on
row 2, and no other paper loses more than 2 matching draws against its version-4 count; otherwise
report and stop.*

| clause 1 paper | label level | draws at the label's level **and** on row 2 | met |
|---|---|---|---|
| ciric_2017 | `step` | **10** of 10 | yes |
| agtzidis_2020 | `package` | **6** of 10 (`package` ×10, but row 2 on 6; the other 4 carry an operation phrase as the value) | **no** |
| cole_2013 | `package` | **4** of 10 | **no** |
| gordon_2014 | `step` | **0** of 10 (`package` on all 10; row 2 on 8) | **no** |
| mueller_2021 | `package` | **0** of 10 (`step` on all 10; row 2 on 8) | **no** |
| derosa_2025 | `package` | **0** of 10 (`ICA-AROMA` as `step` on all 10, routed) | **no** |

| clause 2 paper | label | version-4 count | version 6 | loss |
|---|---|---|---|---|
| power_2014 | `described_only` | 10 | 10 | none |
| binder_1999 | `described_only` | 6 by row | 8 by row | none |
| liu_2013 | `deferred` | 5 (7 on the earlier v4 run) | 10 | none |
| poldrack_2015 | `deferred` | 0 | 8 | none |
| braun_2015 | `deferred` | 10 | 10 | none |
| viduarre_2017 | `deferred` | 10 | 10 | none |
| vanderwal_2016 | `deferred` | 10 | 10 | none |

**Outcome: clause 1 fails on five of six papers; version 6 is not adopted. Report and stop.** Clause 2
was not breached — no paper lost a draw, and three gained — and does not rescue clause 1. **No
stanza is frozen by adoption.** The pin and the recorder's constant carry `8df070da…` as the candidate
Amendment 10 pre-declared, not as an adopted version; what freezes next is the author's ruling, by
amendment.

## Each paper under version 6, against Amendment 10's readings

State-map rows from raw `status` and raw `value` only (Amendment 2 ruling 2); the level is the model's
own `motion_correction_binding`.

| paper | v1.8 label | pre-declared | returned |
|---|---|---|---|
| power_2014 | `described_only` | row 1 ×10 at 3112–3528 | **row 1 ×10**, same span, `described_only` ×10 |
| binder_1999 | `described_only` (confirmed from the text) | row 1 on most, row 3 on some; an `AFNI`/`package` return would be an over-reach | **row 1 ×8, row 3 ×2** (excluded by name), `described_only` ×10, all at 11023–11180; **no `AFNI`**, the over-reach did not occur |
| liu_2013 | `deferred` | row 4 on 5 to 10 of 10 (the recorded cost) | **row 4 ×10**, target kind `pipeline` (6 with the version string, 4 without) |
| derosa_2025 | `named_tool` / `package` / FSL, ICA-AROMA routed | row 2, `FSL`, `package`, quoting the FSL sentence | **`ICA-AROMA` ×10 as `named_tool_step`**, routed by the check ×10; **the package rule did not fire** — FSL was never returned |
| agtzidis_2020 | `named_tool` / `package` / SPM12 | row 2, `SPM12`, `package`; the quote moves to the package sentence | **`package` ×10**; value `SPM12` ×6 with the package sentence resolving at **7020–7085** (a span this paper never resolved before); value an operation phrase ×4 (row 1) with the quote unresolved — a package binding on a non-package value |
| poldrack_2015 | `deferred` (the unreached shape) | row 1 ×10 | **row 4 ×8** — 6 to the pipeline the text describes, target kind `pipeline`; 2 to ref 45, kind `paper` — and row 1 ×2 at 25523–25671. **Not pre-declared:** the shape moved on a majority of draws under an edit not aimed at it |
| ciric_2017 | `named_tool` / `step` / MCFLIRT | row 2, `step`, span 4410–4507 | **row 2 ×10, `step` ×10**, span 4410–4507 |
| braun_2015 | `deferred` | row 4 ×10 | **row 4 ×10**, kind `paper` |
| viduarre_2017 | `deferred` | row 4 ×10 to one of the two citations | **row 4 ×10**: 8 to Glasser et al., 2 to Smith et al. |
| vanderwal_2016 | `deferred` | row 4 ×10 | **row 4 ×10**, kind `pipeline`; the `ANTs` risk absent |
| cole_2013 | `named_tool` / `package` / AFNI | row 2, `AFNI`, `package`; the citation-number artefact tolerated by ruling 5 | **`package`/`AFNI` ×4** (row 2, span 4723–4781, the package sentence, **resolved and kept** — ruling 5 held); `described_only` ×4 on the step-list sentence (3 at 4992–5431, 1 unsupported by its quote); `deferred` ×1 to ref 23 (CALL 11's reading of the same list); **1 error** (no binding after reask) |
| gordon_2014 | `named_tool` / `step` / SPM8 | row 2, `SPM8`, `step` | **`package` on all 10** — the wrong level; value `SPM8` ×8 (row 2) and an operation phrase ×2 (row 1), all at 4860–5140 |
| mueller_2021 | `named_tool` / `package` / SPM12 | row 2, `SPM12`, `package`, quoting the package sentence | **`step` on all 10** — the wrong level; value `SPM12` ×8 **quoted against the realignment sentence**, which does not contain it, so **demoted ×8** (`motion_value_unsupported_by_quote`); an operation phrase ×2 (row 1) at 3894–4058 |

Rows over 130 draws: row 1 ×32, row 2 ×46, row 3 ×2, row 4 ×49, error ×1.

## The attribution level, as the model stated it

- Over the 79 extracted draws: **step 30** (ciric 10 right; derosa 10 and mueller 10 wrong), **package
  24** (agtzidis 10 right; cole 4 right; gordon 10 wrong), `described_only` 25.
- **The level was right where the sentence structure is simplest** (ciric: the tool in the realignment
  clause; agtzidis: one package named for the whole analysis, two sentences away) **and wrong on both
  papers where the level turns on the structure of one sentence**: gordon, where the package is the
  instrument of the realignment sentence itself, came back `package`; mueller, where the package
  governs the procedure set, came back `step`. On derosa the routed tool took the step slot and the
  package rule never applied.
- **The two halves of the package output rule came apart on 6 draws**: a `package` binding with an
  operation phrase as the value (agtzidis 4, gordon 2). The model also returned a `step` binding with
  an operation phrase on mueller (2).
- Model binding against the frozen heuristic, at the state level: **70 agree, 8 disagree, 2
  heuristic-undecided**. The 8 disagreements are exactly those operation-phrase values under a
  `named_tool` binding; 0 disagreements on every earlier run.

## What was found that was not pre-declared

- **poldrack deferred on 8 of 10** — the shape version 5 reached on 3 and version 4 on 0 — under
  edits aimed elsewhere. The only version-6 text about pipelines is STEP 3's sentence that a pipeline
  or wrapper "is a deferral target for step 4, never a value"; six of the eight draws name the
  pipeline the text describes as the target, two the bare number. Reported as found; version 6 is
  not adopted for other reasons.
- **liu_2013 at 10 of 10** for the second stanza in a row (version 5 also), against 5 and 7 under
  version 4.
- **mueller's demotions are the check working on a level error:** the model chose `step`, quoted the
  step sentence, and named the package — the cross-sentence carry the check was built to reject. The
  level and the quote rule are one decision in the stanza; the model split them.
- **cole's package draws survived the citation-number artefact**: 4 of 4 resolved on the package
  sentence and were kept. Before ruling 5 they would have been demoted.
- **derosa**: the exception for a routed step-level tool, written into STEP 3's package bullet, did
  not take; ICA-AROMA still occupied the step slot on every draw.

## Named lines

- Draws 130; reasks 1; errors 1 (cole); unresolved spans 4 (agtzidis, the operation-phrase draws).
- Demoted on the processed layer: unsupported 9 (mueller 8, cole 1); routed 10 (derosa).
- Excluded by name: `undecided` 2 (binder); `unread` 0; `multi_target_unscoreable` 0.
- Wall time per draw, mean: power 4.22 s, binder 17.08 s, liu_2013 15.92 s, derosa 6.32 s,
  agtzidis 13.32 s, poldrack 20.83 s, ciric 7.43 s, braun 11.48 s, viduarre 9.16 s, vanderwal
  4.15 s, cole 19.19 s, gordon 7.61 s, mueller 15.62 s.

## What this shows, and what it does not

- The attribution level is **expressible** — both levels were returned, each correctly on at least one
  paper — and **not reliably assigned** where it depends on one sentence's structure. Reachability, not
  accuracy; the thirteen are fitted.
- No paper lost a draw against version 4, and three deferral cases gained. The rule is a conjunction
  and its first clause failed; the second is reported because the rule names it.
- **No accuracy figure.** Thirteen contaminated papers, all fitted; counts only.

## Status

- Labels unchanged by this document.
- **Held for the author:** which stanza freezes — the restoration of `b0093774…` by amendment, or a
  version 7 under a new amendment — and whether the level belongs in the model's output at all or
  in the scoring map alone (the heuristic classes the state; nothing classes the level). The
  full-corpus run waits on that ruling.

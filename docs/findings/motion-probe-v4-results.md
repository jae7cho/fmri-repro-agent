# motion_correction.method — stanza version 4, ten papers, results (2026-10-26)

**DIAGNOSTIC. Not an evaluation.** Ten papers at K=10 under stanza version 4, against the readings
pre-declared in prereg Amendment 8 (written before the first edit), with the version-3 run as the
regression baseline for the seven papers it covered. **No rate, fraction, percentage or accuracy
figure** appears here or may be computed from the projection behind it (prereg `:9-10`, `:158-159`).
Counts are counts of draws. **A new vintage**: never pooled with any earlier run's draws.

- **Run** 2026-10-26, 22:34–22:47 UTC. **K** = 10, 10 papers, 100 draws.
- **Model** `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`.
- **Stanza** sha256 `b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837` (6,402
  characters): version 3 plus three general edits from CALL 6 and CALL 11 (citation forms; wholesale
  deferral when STEP 1 keeps no passage; "or a named pipeline" in STEP 4's trigger), none naming a
  paper. **Gate:** the manifest carries this hash; checked before any record was read.
- **Resolver vintage** `3cb396e`. **Post-checks on the processed layer:** `motion_guard.py`.
- **Per-draw record** [ground_truth/motion_probe_v4_projection.csv](../../ground_truth/motion_probe_v4_projection.csv)
  — status, heuristic class, state-map row, span offsets, deferral target kind, `model_state`,
  `model_vs_heuristic`; **no quote or value text** (ten needles absent, present in the run records).
  The unprojected run is at `extractor_mvp/results/motion_probe_v4/` (gitignored).
- **Reasks** 0 of 100. **Errors** 0. **Held-out:** liu_2005, tang_2025 and wheaton_2004 untouched.
- **Fitted, by the record:** derosa, poldrack (CALL 10 and the earlier iterations) and, from this
  version, braun, viduarre and vanderwal (Amendment 8). ciric is post hoc. No count below is
  independent.

## The three added shapes — each reached on all ten draws

| paper | label | pre-declared | returned |
|---|---|---|---|
| **braun_2015** | `deferred` | `deferred`, target = refs 47 and 48, through the wholesale branch | **`deferred` ×10**, target kind `paper`, the deferring sentence resolved on every draw |
| **viduarre_2017** | `deferred` | `deferred`, target = Smith et al. / Glasser et al.; FIX is not the value | **`deferred` ×10** to the Glasser citation, target kind `paper`; no value returned, so nothing for the check to route |
| **vanderwal_2016** | `deferred` | `deferred`, target = C-PAC; risk: `ANTs` as `named_tool` from the same sentence | **`deferred` ×10** to the named pipeline, target kind `pipeline`; **the risk did not occur** |

Rows 4 (deferred) were produced on 37 of 100 draws across four papers; before version 3 the state
had never been produced, and version 3 produced it on one paper.

## The seven regression papers against version 3

| paper | label | version 3 | version 4 | movement |
|---|---|---|---|---|
| power_2014 | `described_only` | row 1 ×10 | row 1 ×10, same span (3112–3528) | none |
| binder_1999 | `described_only` | `AFNI` ×6 (demoted by the check), row 1 ×2, row 3 ×2 | **row 1 ×8, row 3 ×2; no `AFNI`**; all ten resolve at 11023–11180 | the cross-sentence carry is gone on this vintage; the heuristic's `undecided` count stays 2 |
| liu_2013 | `deferred` (v1.7.1) | `deferred` ×10 | **`deferred` ×7** (target kind `pipeline`), **row 1 ×3** on the operation sentence (3344–3658) | **a regression of 3 draws** toward `described_only`; reported as found |
| derosa_2025 | `described_only`, fitted | `ICA-AROMA` ×10, routed | `ICA-AROMA` ×10, binding `named_tool`, routed ×10 | none |
| agtzidis_2020 | `described_only` | row 1 ×10, spans unresolved ×10 | row 1 ×10 (the phrase with its reference image), spans unresolved ×10, no `SPM12` | none |
| poldrack_2015 | `deferred` | row 1 ×10 on 25523–25671 | **row 1 ×10 on 25523–25671** | **none — edit (a) did not reach it.** The pre-declared reading (`deferred` to ref 45 through the bare-number form) did not occur on any draw; the v3 risk sentence was not quoted either |
| ciric_2017 | `named_tool` / MCFLIRT | `MCFLIRT` ×10, ESTIMATE span | `MCFLIRT` ×10, span 4410–4507 | none |

## Option (c): the model's binding against the frozen heuristic

Over the 63 extracted draws: **61 agree, 0 disagree, 2 heuristic-undecided** (binder's algorithm
description, which the model calls `described_only`). The 37 deferred draws carry no binding, as the
schema requires.

## What was found that was not pre-declared

- **poldrack is the one deferral shape still unreached.** Edit (a) names the bare-number form the
  text layer produces, and the model still read the realignment sentence as the paper's own
  description on all ten draws. The pipeline there is described, not named ("a pipeline developed at
  … University"), and the citation is a bare number at the end of that clause; braun and viduarre, whose
  citations are also bare numbers or author-year, deferred through the wholesale branch, where no
  passage competes. So the unreached case is narrower than "numbered citation": it is a numbered
  citation on an *unnamed* pipeline beside an operation sentence STEP 1 keeps. Held for the author.
- **liu_2013 moved 3 draws toward `described_only`** under a stanza that was not aimed at it — the same
  lesson as the 2026-10-22 edit, and the reason regression runs on all ten papers. The three draws
  quote the operation sentence (3344–3658) that the seven deferred draws defer past.
- **binder's `AFNI` carry did not appear**, after 6 of 10 under version 3 and 5 and 8 of 10 under
  `378a`. The check would have demoted it; on the raw layer it is simply absent on this vintage.

## Named lines

- Draws 100; reasks 0; errors 0; unresolved spans 10 (agtzidis, the recorded `/C2` exclusion).
- Demoted on the processed layer: derosa 10 (routed). No `motion_value_unsupported_by_quote` on this
  vintage.
- Wall time per draw, mean: power 4.08 s, binder 11.96 s, liu_2013 17.18 s, derosa 5.95 s, agtzidis
  4.91 s, poldrack 5.29 s, ciric 9.07 s, braun 10.86 s, viduarre 4.76 s, vanderwal 3.82 s.

## What this shows, and what it does not

- Three of the four deferral shapes the label pass identified are **reachable** under version 4, each
  on 10 of 10, through the general instructions written for them. The fourth (poldrack) is not, and its
  shape is now stated more precisely than before.
- The regression is **mixed**: no paper moved toward a tool name, one paper (liu_2013) moved three
  draws away from its label, one (binder) moved toward it.
- **No accuracy figure.** Ten contaminated papers, five fitted, one post hoc; counts only.

## Status

- Labels unchanged by this document.
- Held for the author: the poldrack shape; whether liu_2013's three-draw movement is version 4's cost
  or day-to-day movement (a same-day A/B under `ea7b0084…` would separate them, as on 2026-10-25).

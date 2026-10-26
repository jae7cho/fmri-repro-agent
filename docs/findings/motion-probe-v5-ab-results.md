# motion_correction.method — version 5 against version 4, same day: the adoption rule, applied (2026-10-26)

**DIAGNOSTIC. Not an evaluation.** Two stanzas, ten papers, K=10 per arm, 200 draws, run back to back
in one session as pre-registered in prereg Amendment 9 (written before the version-5 edit and before
any call). **No rate, fraction, percentage or accuracy figure** appears here or may be computed from
the two projections behind it (prereg `:9-10`, `:158-159`). Counts are counts of draws. **Two new
vintages**, never pooled with each other or with any earlier run.

## Design, and the gate

- **Arms.** Version 4, `b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837` (6,402
  characters), then version 5, `fb5735fba39457a0f67aebe95fa4668f1df7ae55568f3ad86d1274563863e6d2`
  (6,809 characters); the diff between them is the five introducing-sentence lines in STEP 4. Model
  `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`.
- **Timing.** Version-4 arm 23:15:50–23:29:33 UTC; version-5 arm 23:29:33–23:41:25 UTC.
- **The version-4 arm ran from a detached git worktree at `d1292f6`**, the last commit that pins
  `b0093774…`, with that commit's recorder (its probe table already carried all ten papers). The
  version-5 arm ran from the working tree at `2f0fe2e`. One interpreter served both; an import check
  before the run showed the worktree path yielding a module hashing to `b0093774…` and the working-tree
  path one hashing to `fb5735fb…`. The worktree was removed after the run.
- **Gate (Amendment 9), passed before any per-draw record was read.** Each arm's `manifest.json`
  carries its own hash in `motion_method_prompt_sha256`: version-4 arm → `b0093774…`, version-5 arm →
  `fb5735fb…`. Neither arm is void.
- **Per-draw records** `extractor_mvp/results/motion_probe_ab_2026-10-26_v4v5/{v4,v5}/motion_probe/`
  (gitignored). **Projections**
  [motion_probe_ab_2026-10-26_b009_projection.csv](../../ground_truth/motion_probe_ab_2026-10-26_b009_projection.csv)
  and
  [motion_probe_ab_2026-10-26_fb57_projection.csv](../../ground_truth/motion_probe_ab_2026-10-26_fb57_projection.csv),
  emitted by `motion_probe_projection.py` — status, heuristic class, state-map row, span offsets,
  deferral target kind, `model_state`, `model_vs_heuristic`; **no quote or value text** (fourteen
  needles absent from both CSVs, present in both arms' records).
- **Reasks and errors.** Version-4 arm: 0 reasks, 0 errors. Version-5 arm: 7 draws reasked, 2 ended
  in error, all on binder_1999 (below).
- **Held-out status.** liu_2005, tang_2025 and wheaton_2004 were not loaded, searched or read.
- **Fitted, by the record:** derosa, poldrack, braun, viduarre, vanderwal; ciric post hoc. No count
  below is independent.

## The adoption rule, applied as written

Amendment 9: *version 5 is adopted if poldrack returns `deferred` to ref 45 on at least 6 of 10 and no
other paper loses more than 2 matching draws against its same-day version-4 arm; otherwise version 4
freezes and poldrack's shape is recorded as unreached.* A draw matches on its state-map row (and, for
ciric, its span), against the label as Amendment 8 reads it.

| clause | found | met |
|---|---|---|
| poldrack `deferred` to ref 45 on ≥ 6 of 10 under version 5 | **3 of 10** (target kind `paper`, the bare number); `described_only` ×7 on 25523–25671 | **no** |
| no other paper loses > 2 matching draws vs its version-4 arm today | largest loss: binder_1999, 2 draws by the model's own state (2 errors); by row, no paper lost any | yes |

**Outcome: version 4 freezes.** The rule is a conjunction. Version 5 reached poldrack on 3 draws, the
first draws ever to defer this paper, and that is where it stays: on this arm's record.

## Each paper under both arms, against Amendment 8's readings

State-map rows from raw `status` and raw `value` only (Amendment 2 ruling 2). "Matching" per Amendment 9.

| paper | label (Amendment 8 reading) | version-4 arm today | version-5 arm | matching, v4 → v5 |
|---|---|---|---|---|
| power_2014 | `described_only` ×10 | row 1 ×10, span 3112–3528 | row 1 ×10, same span | 10 → 10 |
| binder_1999 | `described_only`; the `AFNI` carry reported if it happens | row 1 ×6, row 3 ×4 (heuristic `undecided`), all at 11023–11180, model `described_only` ×10; no `AFNI` | row 1 ×8 at 11023–11180, model `described_only` ×8; **2 draws in error** at the binding validator; no `AFNI` | by row 6 → 8; by model state 10 → 8 |
| liu_2013 | `deferred`, target = the FCP scripts (v1.7.1) | **`deferred` ×5** (target kind `pipeline`), row 1 ×5 on the operation sentence 3344–3658 | **`deferred` ×10** (6 with the version string, 4 without; target kind `pipeline` on all) | **5 → 10** |
| derosa_2025 | `described_only`, fitted; routed by the check | `ICA-AROMA` ×10, binding `named_tool`, routed ×10 | `ICA-AROMA` ×10, `named_tool`, routed ×10 | 10 → 10 |
| agtzidis_2020 | `described_only`, the paper's phrase; `SPM12` is a check failure | row 1 ×10, spans unresolved ×10, no `SPM12` | row 1 ×10, spans unresolved ×10, no `SPM12` | 10 → 10 |
| poldrack_2015 | `deferred`, target = ref 45 | row 1 ×10 on 25523–25671 | **`deferred` ×3**, row 1 ×7 on 25523–25671 | 0 → 3 |
| ciric_2017 | `named_tool` / MCFLIRT, ESTIMATE span; post hoc | `MCFLIRT` ×10, span 4410–4507 | `MCFLIRT` ×10, span 4410–4507 | 10 → 10 |
| braun_2015 | `deferred`, refs 47 and 48 | `deferred` ×10, target kind `paper` | `deferred` ×10, target kind `paper` | 10 → 10 |
| viduarre_2017 | `deferred`, Smith et al. / Glasser et al.; FIX is not the value | `deferred` ×10 to Glasser et al. | `deferred` ×10: 6 to Glasser et al., 4 to Smith et al. — both pre-declared targets; no value returned | 10 → 10 |
| vanderwal_2016 | `deferred`, C-PAC; `ANTs` risk | `deferred` ×10 to the named pipeline, kind `pipeline`; risk absent | `deferred` ×10, kind `pipeline`; risk absent | 10 → 10 |

Rows per arm — version 4: row 1 ×41, row 2 ×20, row 3 ×4, row 4 ×35. Version 5: row 1 ×35, row 2
×20, row 4 ×43, no row ×2 (the errors).

## liu_2013: the version-4 count today, beside 7 of 10

Amendment 9 pre-declared two readings for liu_2013's version-4 arm: 10 of 10 today means the
earlier 7 of 10 was within-run variation; 7 again means version 4's cost. **Found: 5 of 10** —
neither. Two days, two counts, both below 10 and not equal to each other: the loss to
`described_only` on the operation sentence (3344–3658) recurs under version 4 and moves between
runs. It is recorded as **the frozen version's cost on this paper**. Version 5 returned `deferred` on
all ten, which the rule as written does not weigh.

## binder_1999 under version 5: the response schema, not the text

Seven of ten first attempts returned `status="extracted"` without `motion_correction_binding`; the
validator (option (c), Amendment 7) rejected them and instructor reasked. Five recovered on the second
attempt (binding `described_only`, the same span as every other draw); **two did not and ended in
error** with no raw status captured. Under version 4 today the same paper had 0 reasks. The eight
draws that completed are row 1 with the heuristic agreeing on all eight, against 4 heuristic-`undecided`
draws under version 4 today: the surface form moved toward the longer operation phrase. The `AFNI`
carry did not appear on either arm.

## Option (c): the model's binding against the frozen heuristic, per arm

- Version 4: 65 extracted draws — **61 agree, 0 disagree, 4 heuristic-undecided** (binder); 35
  deferred draws carry no binding.
- Version 5: 55 extracted draws — **55 agree, 0 disagree, 0 undecided**; 43 deferred; 2 errors.

## What was found that was not pre-declared

- **poldrack moved for the first time** — 3 of 10 to the bare-number target — under the rule written
  for its shape, and not on a majority of draws at temperature 0.
- **liu_2013 at 5 of 10 under version 4**, a third count for the same stanza (10, 7, 5 across three
  runs on three dates: 2026-10-26 version-3 run under `ea7b0084…` was 10; the two version-4 runs 7
  and 5).
- **viduarre's target split** 6/4 between its two pre-declared citations under version 5, against 10
  of 10 on one of them under version 4 today.
- **The binding validator as a cost**: the one edit that made no reference to the binding changed
  how often the model omitted it on one paper.

## Unreached shapes that remain

1. **poldrack's**: an unnamed pipeline cited by a bare number in the sentence that introduces the
   procedure set, followed by an operation sentence STEP 1 keeps. 0 of 10 under the frozen stanza on
   both days it ran. Reachable in principle (3 of 10 under version 5), not under the frozen version.

Not a shape: liu_2013's loss under the frozen stanza, above. No other shape from the label pass
remains unreached: braun, viduarre and vanderwal deferred on 10 of 10 in both arms.

## Named lines

- Draws 200; reasks 7 (version 5, binder); errors 2 (version 5, binder); unresolved spans 10 per arm
  (agtzidis, the recorded `/C2` exclusion).
- Demoted on the processed layer: derosa 10 per arm (routed). No `motion_value_unsupported_by_quote`
  on either vintage.
- Wall time per draw, mean, version 4 / version 5: power 4.03 / 4.04 s, binder 15.88 / 6.86 s,
  liu_2013 16.40 / 15.49 s, derosa 5.67 / 5.83 s, agtzidis 4.53 / 4.62 s, poldrack 5.25 / 9.85 s,
  ciric 13.38 / 4.83 s, braun 10.17 / 10.18 s, viduarre 3.01 / 5.74 s, vanderwal 3.59 / 3.49 s.

## The freeze

Version 4 is the frozen stanza under prereg C11: `b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837`.
The five version-5 lines were removed and the constant is version 4 verbatim (comment lines only
differ from `d1292f6`; live hash checked after the edit). The pin returns to `b0093774…` with a dated
note; the recorder carries `_FROZEN_STANZA_SHA256` and refuses to draw under any other hash before
building a client, writing `motion_method_prompt_frozen_sha256` into its manifest; a test holds the
three values equal and the refusal live. A stanza change now needs a new amendment naming the new hash
in the recorder, in the same commit. Version 5's hash stays on its arm. The prereg carries the dated
freeze note; the freeze is the commit before this document's.

## What this shows, and what it does not

- The adoption rule, written before the edit, decided against the edit on its first clause, with the
  second clause reported as the rule names it. The edit reached its target on 3 draws and cost one
  paper 2 draws through the schema.
- Version 4's instability on liu_2013 is now measured on two days and recorded as a cost of the frozen
  stanza; the version that removed it was not adopted, by the rule.
- **No accuracy figure.** Ten contaminated papers, five fitted, one post hoc; counts only.

## Status

- Labels unchanged by this document.
- The frozen stanza is the one the full-corpus run must carry. That run — 19 papers, the held-out three
  entering for the first time — is the next design question and is not pre-registered here.

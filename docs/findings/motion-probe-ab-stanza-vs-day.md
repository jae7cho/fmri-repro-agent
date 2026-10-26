# motion_correction.method — same-day control: stanza or day? (2026-10-25)

**DIAGNOSTIC. Not an evaluation.** Two stanzas, two papers, K=10 per cell, 40 draws, run back to back in
one session, as pre-registered in prereg Amendment 5 (written before the first call). **No rate,
fraction, percentage or accuracy figure** appears here or may be computed from the two projections
behind it (prereg `:9-10`, `:158-159`). Counts are counts of draws.

## Why

Between the 2026-10-21 run (stanza `56bc6305…`) and the 2026-10-22 run (stanza `378a294f…`),
agtzidis_2020 went from an operation phrase on 9 of 10 to `SPM12` on 10 of 10, and binder_1999 from
`undecided` on 10 of 10 to `AFNI`/`MCW-AFNI` on 5 of 10. The author matched the v2 offsets back to both
texts: in both papers the quote stayed on the step sentence and the value came from another sentence.
Two things had changed between the runs — the stanza and the day — and the project has measured
temperature-0 movement across days before. This run holds the day fixed.

## Design, and the gate

- **Arms.** `56bc` first (agtzidis, binder), then `378a` (agtzidis, binder). Model
  `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`, K=10.
- **Timing.** `56bc` arm 22:49:00–22:50:12 UTC; `378a` arm 22:50:12–22:53:54 UTC. Under five minutes
  end to end.
- **The `56bc` arm ran from a detached git worktree at `3fc366f`**, the last commit at which the pin reads
  `56bc6305…` (its `extractor.py` blob evaluates to that hash). That arm used the recorder and extractor
  module as of that commit; the `378a` arm used the working tree's. One interpreter served both: the
  recorder puts its own `../src` at the head of `sys.path`, and an import check before the run showed the
  worktree path yielding a module hashing to `56bc…` and the working-tree path one hashing to `378a…`.
- **Gate (Amendment 5), passed before any per-draw record was read.** Each arm's `manifest.json` carries
  its own hash in `motion_method_prompt_sha256`:
  `56bc` arm → `56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a`;
  `378a` arm → `378a294f94ca9f0fc6bd45bd42caf4646a007c7d705d05c8b5f584dd66ca8cab`. Neither arm is void.
- **Per-draw records** `extractor_mvp/results/motion_probe_ab_2026-10-25/{56bc,378a}/motion_probe/`
  (gitignored). **Projections**
  [motion_probe_ab_2026-10-25_56bc_projection.csv](../../ground_truth/motion_probe_ab_2026-10-25_56bc_projection.csv)
  and
  [motion_probe_ab_2026-10-25_378a_projection.csv](../../ground_truth/motion_probe_ab_2026-10-25_378a_projection.csv),
  emitted by `motion_probe_projection.py` — status, heuristic class, row, span offsets; **no quote or
  value text** (eight needles absent from both CSVs, present in the run records).
- **Held-out status.** liu_2005, tang_2025 and wheaton_2004 were not loaded, searched or read.

## Result: a stanza effect on both papers

State-map rows are computed from raw `status` and raw `value` only (Amendment 2 ruling 2). Counts of 10.

| paper | arm | rows today | the earlier run under the same stanza | the other arm today |
|---|---|---|---|---|
| **agtzidis_2020** | `56bc` | **row 1 ×10** (one surface form) | v1, 2026-10-21: row 1 ×9, row 2 ×1 | row 2 ×10 |
| **agtzidis_2020** | `378a` | **row 2 ×10** (`SPM12`) | v2, 2026-10-22: row 2 ×10 | row 1 ×10 |
| **binder_1999** | `56bc` | **row 3 ×10** (the algorithm description) | v1: row 3 ×10 | row 2 ×8, row 3 ×2 |
| **binder_1999** | `378a` | **row 2 ×8** (`AFNI`), row 3 ×2 (the bare citation) | v2: row 2 ×5, row 3 ×3, row 1 ×2 | row 3 ×10 |

**Pre-declared reading 1 holds on both papers:** each arm reproduces its own earlier run's modal row, and
the two arms differ from each other on the same day. On the two cells where the earlier runs were not
unanimous, today's arms are *more* separated than before — binder under `378a` has no row-1 draw today
and eight row-2 draws against five; agtzidis under `56bc` has no `SPM12` draw today against one.

So the movement between 2026-10-21 and 2026-10-22 is attributable to the stanza, within what K=10 per
cell can say. "Stanza" means the whole `56bc`→`378a` diff — the longer STEP 3 bullet naming the
structured-noise row and tools, and STEP 4's first rule gaining "and not routed elsewhere". Which of
those sentences did it is **not separable here**; it would take a third arm.

## The quote stayed put; the value moved

The author's finding from the v2 offsets reproduces under same-day conditions.

| paper | arm | quote spans | value in its own quote |
|---|---|---|---|
| agtzidis | `56bc` | all 10 the long form of the realignment clause, **0 of 10 resolved** (the quote runs into the corrupt `×` clause) | n/a — operation phrases |
| agtzidis | `378a` | 7086–7308 ×6, 7188–7308 ×1, 7210–7274 ×1 (8 resolved); 2 unresolved, both the still-longer form that begins at the sentence naming the package | **8 of 8 resolved draws: NOT in the quote**; the 2 unresolved: in the quote |
| binder | both | 11023–11180 ×10, the Cox 1996b sentence, resolved 10 of 10 | `378a`: **8 of 8 `AFNI` draws: NOT in the quote** |

The existing `quote_supports_value` guard (`span_resolver.py:400`), applied to today's tool-name draws,
rejects the same 16 and passes the same 2 as plain substring does.

**Span resolution varied by day while the row did not.** agtzidis under `56bc` resolved 3 of 10 on
2026-10-21 and 0 of 10 today — the model returned the long quote form every time today. Under `378a` it
resolved 9 of 10 on 2026-10-22 and 8 of 10 today. The row is a property of the stanza; how much of the
sentence the model quotes is not stable within a stanza, and nothing here should be read as a fact about
quote length.

## Named lines

- **Draws** 40. **Reasks** 0. **Retries** 0. **Errors** 0. **Unresolved spans** 12 of 40 (agtzidis
  under `56bc` ×10, agtzidis under `378a` ×2), all the recorded `/C2` exclusion.
- **Wall time.** `56bc` arm: min 2.99 s, median 3.57 s, max 3.92 s. `378a` arm: min 3.17 s, median 13.98 s,
  max 16.06 s — binder under `378a` took 13.6–16.1 s per draw, as it did on 2026-10-22 (13.83 s mean),
  against ~3.3 s under `56bc`. The longer stanza costs binder roughly four times the wall time; whether
  that is more reasoning or more output is not recorded by the probe.
- **Ruling 4's trigger** (binder `undecided` ≥ 6 of 10): fires under `56bc` (10 of 10), not under `378a`
  (2 of 10) — on the same day. It is a property of the stanza, which settles what the v1/v2 comparison
  left open.

## What this shows, and what it does not

- The 2026-10-22 stanza edit, made to route derosa's ICA-AROMA, **did not change derosa** (v2: 10 of 10
  `ICA-AROMA`) and **did change agtzidis and binder**, moving both toward naming a package from a
  sentence other than the one quoted. That is now shown with the day held fixed, not inferred across days.
- Nothing here says which of the two papers' labels is right. Under HEAD's `named_tool`/SPM12 label the
  `378a` arm's agtzidis is ten targets; under the author's 2026-10-22 relabel it is ten mismatches. The
  run is about the stanza, not the label.
- **No accuracy figure.** Two papers, both inside the contaminated union; K=10 per cell; counts only.

## Status

- The pinned stanza is `378a294f…`. Whether it is reverted, iterated again, or kept with a value-in-quote
  check in front of it (`docs/design/DELTA_value_in_quote_motion.md`, design only, unstaged) is the
  author's ruling. The held deferral line (Amendment 4 §3) and the derosa routing question are unchanged.
- The worktree used for the `56bc` arm was removed after the run; its commit, `3fc366f`, is in history.

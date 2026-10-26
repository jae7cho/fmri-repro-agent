# motion_correction.method — ciric_2017 under the restored stanza (2026-10-26)

**DIAGNOSTIC. Not an evaluation.** One paper, K=10, under the stanza restored on 2026-10-26, as
pre-registered in prereg Amendment 6 (written before the run). **No rate, fraction, percentage or
accuracy figure** appears here or may be computed from the projection behind it (prereg `:9-10`,
`:158-159`). Counts are counts of draws.

## Why

The same-day control of 2026-10-25 ([motion-probe-ab-stanza-vs-day.md](motion-probe-ab-stanza-vs-day.md))
attributed the agtzidis and binder movement to the 2026-10-22 stanza edit, which had also fixed nothing
it was made for. The author reverted the stanza to `56bc6305…` (commit `8064bf1`), a version already
measured, so no new vintage was created by the revert — with one gap: ciric_2017, the post hoc
replacement control (Amendment 4), had run only under `378a294f…`. This run closes that gap.

## Design, and the gate

- ciric_2017, **K = 10**, from the working tree at `8064bf1`/`5ccd3c5` (the revert and Amendment 6;
  `extractor.py` identical to HEAD, module stanza hashing to `56bc6305…` before the run). Model
  `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`.
- **Gate (Amendment 6), passed before any per-draw record was read:** `manifest.json` carries
  `56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a`.
- **Per-draw records** `extractor_mvp/results/motion_probe_ciric_2026-10-26/motion_probe/` (gitignored).
  **Projection** [motion_probe_ciric_2026-10-26_56bc_projection.csv](../../ground_truth/motion_probe_ciric_2026-10-26_56bc_projection.csv)
  — status, heuristic class, row, span offsets; no quote or value text (four needles absent, present in
  the run record).
- **Held-out status.** liu_2005, tang_2025 and wheaton_2004 were not loaded, searched or read.

## Result: the control passes on all ten draws

Amendment 6's criterion: every draw returns `MCFLIRT` with the ESTIMATE span — a resolved span that
contains the ESTIMATE mention (methods-slice offsets 4475–4482) and none of the three CONSUME mentions
(5533, 6360, 9296).

| draw | value | row | span | contains the ESTIMATE mention | contains a CONSUME mention | value in its own quote |
|---|---|---|---|---|---|---|
| 1–10 | `MCFLIRT` | 2 | 4410–4507, resolved | yes | no | yes |

**10 of 10 pass**, the same span as every draw under `378a` on 2026-10-22 (4410–4507), and the
citation to Jenkinson 2002 was not deferred to on any draw. **This is a control chosen after the first
run**, on a paper in CALL 10's fitting set; it shows the restored stanza emits a bound tool with its
ESTIMATE span, and nothing about how often.

## Named lines

- **Draws** 10. **Reasks** 0. **Retries** 0. **Errors** 0. **Unresolved spans** 0.
- **Wall time** min 3.62 s, mean 4.00 s, max 4.90 s — the shorter stanza's binder-style slowdown
  (13–16 s per draw under `378a`) does not appear on ciric under either stanza (4.22 s mean under `378a`).
- **The existing value-support guard** (`span_resolver.py:400`) passes all ten, as it did under `378a`:
  ciric is the case where the tool is in the quoted step clause.

## What this shows, and what it does not

- ciric_2017 now counts as the restored stanza's positive control: named-tool emission with the
  ESTIMATE span is reachable under `56bc6305…`, on a post hoc control. Evidence, not proof.
- Nothing about agtzidis, binder, derosa or poldrack moves; those are the 2026-10-21 and 2026-10-25
  `56bc` records, unchanged by the revert.
- **No accuracy figure.** One contaminated paper, ten draws, counts only.

## Status

- The pinned stanza is `56bc6305…` again ([test_prompt_pin.py](../../extractor_mvp/tests/test_prompt_pin.py),
  dated note of 2026-10-26). Held for the author: the deferral rule (Amendment 4 §3), option (c) under
  ruling 4 (binder `undecided` 10 of 10 under `56bc` on both days), and the value-in-quote build
  (`docs/design/DELTA_value_in_quote_motion.md` §4).

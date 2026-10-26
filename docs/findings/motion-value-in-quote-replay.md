# The motion value-in-quote post-check, replayed over every recorded draw (2026-10-26)

**Acceptance record for `docs/design/DELTA_value_in_quote_motion.md` §4, built 2026-10-26.** The
post-check (`extractor_mvp/src/extractor_mvp/motion_guard.py`) was replayed, with no model calls, over
all 180 recorded draws of the motion probe — v1 (2026-10-21, 60), v2 (2026-10-22, 70), the same-day
A/B (2026-10-25, 40) and ciric under the restored stanza (2026-10-26, 10) — by
[motion_guard_replay.py](../../extractor_mvp/scripts/motion_guard_replay.py), which mirrors the
production path: a draw whose raw status is not `extracted`, or whose quote did not resolve, is never
seen by the check. **No quote or value text appears here**; draws are named by run, paper and id.

## Totals over 180

| outcome | draws | what they are |
|---|---|---|
| keep | 110 | the value is in its own quote (word forms tolerated) and names no structured-noise tool |
| **unsupported** | **30** | the 30 resolved cross-sentence carries: v2 agtzidis 1, 2, 3, 4, 5, 7, 8, 9, 10; v2 binder 1, 2, 3, 4, 6; A/B `378a` agtzidis 2–9; A/B `378a` binder 1, 2, 3, 4, 6, 7, 8, 9 |
| **routed:ica_aroma** | **20** | every derosa_2025 draw, v1 and v2 — the fitted case, reported as such |
| untouched: span unresolved | 20 | agtzidis v1 ×7 (draws 1, 4, 5, 6, 7, 9, 10), v2 ×1 (draw 6), A/B `56bc` ×10, A/B `378a` ×2 (draws 1, 10) — already `MissingFromPaper` upstream, including the one unresolved tool-name carry (v1 draw 4) and the three host-sentence draws |

**Every other draw is kept.** In particular the **8 inflected operation phrases** — v1 agtzidis 8, v1
poldrack 7, v2 binder 10, v2 poldrack 1, 2, 4, 7, 10 — are kept (the base_pipeline guard's exact-token
rule would reject them); **ciric's 20** (v2 and under `56bc`) are kept; binder's bare-citation values
(v2 draw 5; A/B `378a` draws 5, 10) are kept, as under the old guard. **No other change.** The acceptance
in DELTA §4 is met line for line.

## Per run

| run | paper | keep | unsupported | routed | untouched |
|---|---|---|---|---|---|
| v1 `56bc` | agtzidis | 3 | 0 | 0 | 7 |
| v1 `56bc` | binder, liu_2013, poldrack, power | 10 each | 0 | 0 | 0 |
| v1 `56bc` | derosa | 0 | 0 | 10 | 0 |
| v2 `378a` | agtzidis | 0 | 9 | 0 | 1 |
| v2 `378a` | binder | 5 | 5 | 0 | 0 |
| v2 `378a` | ciric, liu_2013, poldrack, power | 10 each | 0 | 0 | 0 |
| v2 `378a` | derosa | 0 | 0 | 10 | 0 |
| A/B `56bc` | agtzidis | 0 | 0 | 0 | 10 |
| A/B `56bc` | binder | 10 | 0 | 0 | 0 |
| A/B `378a` | agtzidis | 0 | 8 | 0 | 2 |
| A/B `378a` | binder | 2 | 8 | 0 | 0 |
| ciric `56bc` | ciric | 10 | 0 | 0 | 0 |

## What the build changes, and what it does not

- **Raw layer, state-map rows, every prereg count: unchanged.** The check runs after `_process_field`
  on the processed field only (ruling 1); the recorder's raw capture precedes it; rows are computed
  from raw status and value (Amendment 2 ruling 2). The projections and findings of v1, v2, the A/B and
  ciric are as published.
- **Processed layer: re-vintaged for motion.** A demoted draw is `MissingFromPaper` with reason
  `motion_value_unsupported_by_quote` or `motion_value_routed_structured_noise:<tool>`; both are
  members of `cobidas._UNVERIFIABLE_GAP_BASES`, so the motion row renders *examined; the extractor
  could not verify what it found*, never *not reported*.
- **Identity gate against HEAD: 19 identical, 0 changed**, derived before running — no stored JSON in
  `results/batch_a1_acceptance` carries a `motion_correction` step, so the check can touch no stored
  report. **Negative control against `d31e8b7`: 0 identical, 19 changed**, as derived — the two papers
  still identical after `b5ae9c5` are among the five that `2099d04`'s repaired-span tag changed — which
  is the result that distinguishes a live `PYTHONPATH` override from a silently failed one.
- **Mutation-checked** (`tests/test_motion_guard.py`, 35 tests on synthetic strings): disabling the
  unsupported branch, disabling routing, swapping their order, removing inflection tolerance, not
  applying the check in `extract_motion_method`, dropping either reason from the unverifiable set, and
  removing the EXTRACTED-only passthrough guard each fail at least one named test; the suite is green
  with the sources restored.
- **Recorded limit, unchanged:** a tool quoted from its own host sentence passes. CALL 1's job.

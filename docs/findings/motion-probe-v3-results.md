# motion_correction.method — stanza version 3 (rule A and option (c)), results (2026-10-26)

**DIAGNOSTIC. Not an evaluation.** Seven papers at K=10 under stanza version 3, against the readings
pre-declared in prereg Amendment 7, which was written before the first call. **No rate, fraction,
percentage or accuracy figure** appears here or may be computed from the projection behind it (prereg
`:9-10`, `:158-159`). Counts are counts of draws. **A new vintage**: never pooled with the 2026-10-21,
2026-10-22 or 2026-10-25 draws.

- **Run** 2026-10-26, 19:16–19:26 UTC. **K** = 10, 7 papers, 70 draws.
- **Model** `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`.
- **Stanza** `MOTION_METHOD_PROMPT`, sha256 `ea7b0084255454fd38a6de566a5cccf2936b67b09910f6ffa15a79d01c5734a7`
  (5,369 characters), written from protocol v1.7 (CALL 11) with option (c); pinned by
  [test_prompt_pin.py](../../extractor_mvp/tests/test_prompt_pin.py). **Gate:** the manifest carries
  this hash; checked before any record was read.
- **Resolver vintage** `span_resolver.py` at `3cb396e`. **Post-checks in force on the processed
  layer:** `motion_guard.py` (value-in-quote; structured-noise routing).
- **Per-draw record** [ground_truth/motion_probe_v3_projection.csv](../../ground_truth/motion_probe_v3_projection.csv)
  — status, heuristic class, state-map row, span offsets, deferral target kind, and for this vintage
  `model_state` (the binding the model stated) and `model_vs_heuristic`; **no quote or value text**
  (eight needles absent, present in the run records). The unprojected run is at
  `extractor_mvp/results/motion_probe_v3/` (gitignored).
- **Reasks** 0 of 70 — the binding was set correctly on the first completion every time. **Errors** 0.
- **Held-out status.** liu_2005, tang_2025 and wheaton_2004 were not loaded, searched or read.

## The seven results against the pre-declared readings

| paper | label(s) read against | returned (10 draws) | against the reading |
|---|---|---|---|
| **power_2014** | `described_only` | operation phrase ×10, binding `described_only` ×10, heuristic agrees ×10; one span (3112–3528, the whole sentence), resolved 10 of 10 | **matches on all ten** |
| **binder_1999** | `described_only` | `AFNI` ×6 (binding `named_tool`, heuristic `tool_name`); the algorithm description ×2 (binding `described_only`, heuristic `undecided`); an operation phrase ×2 (binding `described_only`, heuristic agrees). The 4 non-AFNI draws resolve at 11023–11180; **the 6 `AFNI` draws are demoted by the value-in-quote check** (`motion_value_unsupported_by_quote`: the package is not in the quoted sentence) | matches on 4 (the heuristic cannot class 2 of them; the model's binding is `described_only` on all 4); **mismatch on 6** — the cross-sentence carry seen under `378a`, now caught by the check rather than scored. Heuristic `undecided` count: 2 |
| **liu_2013** | HEAD `described_only`; pending relabel `deferred` | **`deferred` ×10**, target "the FCP scripts" (target kind `pipeline` ×9, `paper` ×1), the deferring sentence resolved on every draw; binding unset, as the schema requires | **against the pending relabel: matches on all ten** — and **`deferred` is reachable**, for the first time in 250 draws across all vintages. Against the HEAD label: mismatch ×10, pre-declared |
| **derosa_2025** | `described_only` — **fitted** | `ICA-AROMA` ×10, binding **`named_tool`** ×10, heuristic `tool_name`; **all ten routed** by the check (`motion_value_routed_structured_noise:ica_aroma`) | as pre-declared: the check routes whatever the model says. Reported as found: the model now *binds* the denoising tool to the step (`named_tool`), where `56bc` and `378a` had no binding field to show it |
| **agtzidis_2020** | `described_only` (relabel of 2026-10-22) | an operation phrase ×10 (the paper's own words for the operation with its reference image), binding `described_only` ×10, heuristic agrees ×10; **no `SPM12` on any draw**; **spans unresolved 10 of 10** (`extraction_quote_unresolved:quote_not_found`) | **matches on all ten on the raw layer**; no check failure. The span line is the recorded `×`→`/C2` exclusion: every draw quoted the long form through the corrupt clause, as the `56bc` arm did on 2026-10-25 (0 of 10 resolved there too) |
| **poldrack_2015** | `deferred` | operation phrase ×10 (the realignment phrase), binding `described_only` ×10, heuristic agrees; one span, **25523–25671** — the realignment sentence the earlier vintages quoted — resolved 10 of 10; `applywarp` never | **mismatch on all ten, and not through the pre-declared risk.** The risk sentence (session-to-session registration) was not the one quoted on any draw; the model read the realignment sentence itself, which states none of CALL 11's four details, as a description. Reported as found (below) |
| **ciric_2017** | `named_tool` / MCFLIRT — post hoc control | `MCFLIRT` ×10, binding `named_tool` ×10, heuristic agrees; span 4410–4507 ×10 (the ESTIMATE clause), resolved 10 of 10 | **matches on all ten, with the ESTIMATE span** |

## Option (c): the model's binding against the frozen heuristic

Over the 60 extracted draws: **58 agree, 0 disagree, 2 heuristic-undecided** (binder's algorithm
description, which the heuristic cannot class and the model calls `described_only`). The 10 deferred
draws carry no binding, as the schema requires. Amendment 2 ruling 4 is superseded; its `undecided`
count is reported above as a named line (2 of binder's 10) and gates nothing.

## What was found that was not pre-declared

- **poldrack's `described_only` came from the realignment sentence, not the risk sentence.** Amendment 7
  pre-declared that detail (c) might read the session-to-session registration sentence as a stated
  reference image. That did not happen: every draw quoted 25523–25671, which names the operation under
  the cited pipeline and states none of the four details. Under CALL 11 that is the `deferred` case,
  and the stanza's STEP 4 says so; the model did not apply it to this paper while applying it to
  liu_2013 on 10 of 10. The difference between the two texts is that liu_2013 names a pipeline by name
  in the same passage, and poldrack cites a reference number — a shape the next iteration can address;
  not addressed here.
- **binder's `AFNI` returned under version 3** (6 of 10), after being absent under `56bc` on both days
  and present under `378a` (5 and 8 of 10). The value-in-quote check demotes all six on the processed
  layer, so no stored report would carry it; on the raw layer it is the stanza's behaviour and is
  recorded as such.
- **derosa's model binding is `named_tool`.** The model treats the denoising tool as bound to the step.
  Routing happens in code regardless; the binding is reported because (c) exists to show it.
- **agtzidis resolved 0 of 10 spans**, all on the corrupt clause — the long quote form again. The
  reading does not depend on it (rows are computed from the raw layer).

## Named lines

- Draws 70; reasks 0; errors 0; unresolved spans 10 of 70 (agtzidis, all the recorded `/C2` exclusion).
- Demoted on the processed layer by the checks: binder 6 (`motion_value_unsupported_by_quote`), derosa
  10 (`motion_value_routed_structured_noise:ica_aroma`). Both render *examined; could not verify*.
- Wall time per draw, mean: power 5.40 s, binder 16.20 s, liu_2013 15.73 s, derosa 6.83 s, agtzidis
  5.10 s, poldrack 5.87 s, ciric 5.34 s.

## What this shows, and what it does not

- `deferred` **is expressible** (rows 1, 2, 3 and 4 were all produced); the state had never been
  produced before this vintage.
- Option (c) **works as a control**: the model's binding and the heuristic's class never disagreed on a
  classifiable draw, and the model classifies the two draws the heuristic cannot.
- CALL 11 **was applied on one of its two deferral cases and not the other**; the risk pre-declared for
  poldrack is not what happened, and the actual shape is recorded above for the next iteration.
- **No accuracy figure.** Seven contaminated papers, two fitted, one post hoc; counts only.

## Status

- Labels unchanged by this document. liu_2013's relabel to `deferred` and the pass over the six
  deferred rows are the author's, in the workbook.
- Held for the author: the poldrack shape (a numbered citation beside the operation, no named
  pipeline); the scope of detail (c), pre-declared and not yet exercised.

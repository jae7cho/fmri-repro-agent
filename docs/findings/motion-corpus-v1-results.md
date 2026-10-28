# motion_correction.method — the first corpus-wide run under the frozen stanza: nineteen papers, results (2026-10-27)

**DIAGNOSTIC. Not an evaluation.** The run `DESIGN_motion_full_corpus.md` specified and prereg
Amendment 13 released: the recorder over all 19 papers at K=10, then the batch's single draw per
paper, both under the frozen stanza, both gated. Per-paper outcomes **grouped by contamination
class**; the clean three **as states and counts only**; **no corpus-wide rate, fraction, percentage
or interval anywhere** in this document or the projections (prereg `:9-10`, `:158-159`; design doc
§6 items 2–4; Ruling D). Counts are counts of draws. **Two new vintages**, never pooled with any
earlier run's draws or with each other.

- **Stanza** `b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837` (version 4; frozen
  by Amendment 12 — the chain `b0093774…` → `8df070da…` → `d353fb47…` → `b0093774…` is on the pin).
- **R, the recorder** (`extractor_mvp/results/motion_probe_corpus_v1/`, gitignored): 2026-10-27,
  18:53:11–19:22:53 UTC, K=10, 19 papers, **190 draws**, one session, under HEAD `8099063`.
  **Gate:** the manifest carries the stanza hash, `motion_method_prompt_frozen_sha256` equal to it,
  licence `Amendment 13`, `held_out_admitted` = liu_2005, tang_2025, wheaton_2004; checked before any
  record was read.
- **B, the batch** (`extractor_mvp/results/batch_motion_corpus_v1/`, gitignored, as results/ always
  is): 19:22:53–19:31:28 UTC, the same session, `configs/batch_motion_corpus_v1_config.yaml`
  (sha256 `3a8a8cfd…`), 19 `.json` + 19 `.md`, `render_error` empty on all 19, `status` success on
  18 and `methods_not_found` on 1 (liu_2005, below). **Gate:** `batch.py` writes no manifest, so the
  launcher wrote `launcher_manifest.json` beside the output — HEAD `8099063`, the live stanza hash
  `b0093774…`, the config's sha256, the model, start and end, exit 0 — checked before any result was
  read. **Every field B wrote is the new named vintage `motion_corpus_v1`**; this document reports
  the motion field only; the other fields exist and were not read.
- **Model** `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`,
  `max_retries=2`, on both paths; one `ParsedPaper` per paper, sliced by `find_methods_section`.
- **Labels** the v1.8 workbook at `bc18447` (sha256 `350331c8…`, 26,822 bytes): `named_tool` 9,
  `deferred` 8, `described_only` 2; column R `attribution` on every `named_tool` row. For the clean
  three, cells B, C and R were read by id only; D and Q were never read.
- **Projections**
  [ground_truth/motion_probe_corpus_v1_projection.csv](../../ground_truth/motion_probe_corpus_v1_projection.csv)
  (R: status, heuristic class, state-map row, span offsets, deferral target kind, `model_state`,
  `model_vs_heuristic`, derived `attribution`) and
  [ground_truth/batch_motion_corpus_v1_projection.csv](../../ground_truth/batch_motion_corpus_v1_projection.csv)
  (B: the processed layer — status, reason base, span offsets, heuristic class, derived attribution,
  diagnostic base). **No quote or value text in either** (67 needles derived from R's records by
  script, 0 present). Rows for all 19 are emitted by the scripts; the clean three's rows were
  transcribed by nobody.
- **Partition** (design doc §2.5, with cole and gordon in the probe set since Amendment 10):
  **probe thirteen** · **co-adjudicated, not probed** (chen, oconnor, weber) · **clean three**.
  13 + 3 + 3 = 19. Thirteen are fitted; sixteen are contaminated; three are clean for the first and
  only time, their cells spent on this session.

"Match" is the state-map row (raw layer) equal to the label state, plus normalized exact value
equality for `named_tool` (derosa at the processed layer, as Amendment 13 pre-declared); the level
from the processed layer against column R is reported, never scored. The batch's one draw is read
against the states R produced for the same paper: inside that set, or outside.

## Probe thirteen — fitted

| paper | v1.8 label | R: raw rows (of 10) | R: processed layer | match | level vs R | B: one draw | inside R's set |
|---|---|---|---|---|---|---|---|
| power_2014 | `described_only` | row 1 ×10 at 3112–3528 | Extracted ×10 | **10** | — | `described_only`, match | yes |
| binder_1999 | `described_only` | row 1 ×10 at 11023–11180; no row 3 today | Extracted ×10 | **10** | — | `described_only`, match | yes |
| liu_2013 | `deferred` | row 4 ×4 (the scripts, kind `pipeline`), row 1 ×6 at 3344–3658 | Deferred ×4, Extracted ×6 | **4** — below the recorded 5–10 band: a new finding | — | `described_only`, no match | yes |
| derosa_2025 | `named_tool` / FSL / package | row 2 ×10 (raw `ICA-AROMA`) | **`FSL` ×10 by the fallback** on the FSL sentence 8801–9045, reason `motion_value_routed_fallback_to_package` | **10** at the processed layer | package: 10 agree, 0 disagree | `FSL`, match, level package | yes |
| agtzidis_2020 | `named_tool` / SPM12 / package | row 1 ×10 (the operation phrase); quote unresolved ×10 (the `/C2` exclusion) | MissingFromPaper ×10, `extraction_quote_unresolved` | **0** — the pre-declared class, *package attribution unreached by the frozen stanza* | no level ×10 | MISSING (quote unresolved), no match | outside at the raw state; inside at the processed layer |
| poldrack_2015 | `deferred` | **row 4 ×5** (3 to ref 45, kind `paper`; 2 to the pipeline, kind `pipeline`), row 1 ×5 at 25523–25671 | Deferred ×5, Extracted ×5 | **5** — the shape version 4 reached on 0 of 10 on two earlier days; reported as found | — | `described_only`, no match | yes |
| ciric_2017 | `named_tool` / MCFLIRT / step (post hoc) | row 2 ×10, span 4410–4507 | Extracted ×10 | **10** | step: 10 agree | `MCFLIRT`, match, level step | yes |
| braun_2015 | `deferred` | row 4 ×10, kind `paper` | Deferred ×10 | **10** | — | deferred, match | yes |
| viduarre_2017 | `deferred` | row 4 ×10 (5 Glasser et al., 5 Smith et al.), kind `paper` | Deferred ×10 | **10** | — | deferred, match | yes |
| vanderwal_2016 | `deferred` | row 4 ×10, kind `pipeline`; the `ANTs` risk absent | Deferred ×10 | **10** | — | deferred, match | yes |
| cole_2013 | `named_tool` / AFNI / package | **row 2 ×8** (`AFNI`, on a span 4723–5431 that covers the package sentence and the step list), row 1 ×2 (the step list alone, 4782–5431) | Extracted ×10 | **8** — the pre-declared class did **not** occur on 8 of 10 | package: **0 agree, 8 disagree** — the derived level reads the step list's operation phrase inside the long span and says `step`; 2 no level | `described_only` on the step list, no match | yes |
| gordon_2014 | `named_tool` / SPM8 / step | row 2 ×10, span 4860–5140 | Extracted ×10 | **10** — reported as found: version 4's binding test reached the step tool | step: 10 agree | `SPM8`, match, level step | yes |
| mueller_2021 | `named_tool` / SPM12 / package | row 1 ×10 (the operation phrase, 3894–4058) | Extracted ×10 | **0** — the pre-declared class | no level ×10 | `described_only`, no match | yes |

Line: the ten draws all match on 8 of the thirteen (power, binder, derosa, ciric, braun, viduarre,
vanderwal, gordon); cole 8, poldrack 5, liu_2013 4, agtzidis 0, mueller 0. The batch draw matches on
8 of 13 and sits inside the recorder's raw-state set on 12 of 13.

## Co-adjudicated, not probed — chen, oconnor, weber

The first motion draws these three have ever had, under any stanza.

| paper | v1.8 label | R: raw rows (of 10) | match | B: one draw | inside |
|---|---|---|---|---|---|
| chen_2015 | `deferred` (CCS, a wrapper) | row 1 ×10 (the paper's own words, 3812–4144) | **0** | `described_only`, no match | yes |
| oconnor_2017 | `deferred` (CPAC) | row 1 ×10 (19662–19988) | **0** | `described_only`, no match | yes |
| weber_2024 | `deferred` (CPAC); the one `likely_multi_acquisition` flag, which does not route | row 1 ×10 (4797–5068) | **0** | `described_only`, no match | yes |

Not the pre-declared risk (the wrapper returned as a tool: 0 draws) but the other side of it: on all
30 draws the model read the operation sentence as the paper's own assertion and did not connect it
to the wrapper named for the preprocessing. **This is the poldrack shape with a named wrapper** —
the operation listed in the paper's voice under a pipeline named in an introducing sentence — the
shape version 5's introducing-sentence rule targeted and the frozen stanza does not reach. Three of
three such papers; recorded as a named shape, unreached.

## The clean three — states and counts only

Label state `named_tool` on all three (column B), level per column R. Nothing else of theirs
appears here.

| paper | R: state-map rows (of 10) | R: processed layer | match | level vs R | B: one draw | inside |
|---|---|---|---|---|---|---|
| liu_2005 | row 1 ×10 | MissingFromPaper ×10, `extraction_quote_unresolved` | **0 of 10** | no level | `methods_not_found`: no motion field (absent), no match | no |
| tang_2025 | row 4 ×7, row 1 ×3 | Deferred ×7, Extracted ×3 | **0 of 10** | no level | `described_only`, no match | yes |
| wheaton_2004 | row 1 ×8, row 4 ×2 | Extracted ×8, Deferred ×2 | **0 of 10** | no level | `described_only`, no match | yes |

Line: **0 of 30 recorder draws and 0 of 3 batch draws match a clean label**; no clean paper produced
a row-2 draw, so there is no level to compare (0 agree, 0 disagree, 30 without a level). Reasks 0,
errors 0, over the 30.

**liu_2005's interleaved text layer, named beside its result** (Amendment 13; design doc §2.3). On
both paths the paper is sliced by `find_methods_section` from the PDF's own text layer, not from
the de-interleaved slice the target_space pending run used. In the batch the methods finder reported
`methods_found_via: fallback_full_text` and the paper's status is `methods_not_found` — the only
such status in the run; in the recorder every one of its ten quotes failed to resolve. A text layer
the resolver cannot match is a cause the stanza does not own; whether the de-interleaved slice
would change the result is a separate, pre-declared run under a new amendment, not this one.

## liu_2005 on its de-interleaved slice — Amendment 14, beside the corpus line, never pooled

**A separate run, read as states and counts only.** 2026-10-28, 18:54:15–18:56:22 UTC, K=10, the
recorder on `ground_truth/liu_2005_deinterleaved_methods.txt` (sha256 `cfc82ed8…`, recorded in the
manifest) under the frozen stanza `b0093774…`, licence `Amendment 14`, HEAD `9e146a7`; the manifest
gated on all of these before any record was read. Projection
[ground_truth/motion_probe_liu2005_deinterleaved_projection.csv](../../ground_truth/motion_probe_liu2005_deinterleaved_projection.csv),
no text (every raw string of the records derived by script, 0 present).

| | corpus run (the PDF's own text layer) | this run (the de-interleaved slice) |
|---|---|---|
| state-map rows of 10 | row 1 ×10 | row 1 ×9, row 3 ×1 (excluded by name) |
| processed layer | MissingFromPaper ×10, `extraction_quote_unresolved` | Extracted ×9; MissingFromPaper ×1, `motion_value_unsupported_by_quote` (its quote resolved) |
| unresolved spans | 10 of 10 | **0 of 10** |
| matches the label (`named_tool`, level per column R) | 0 of 10 | 0 of 10; no row-2 draw, so no level |
| reasks / errors | 0 / 0 | 0 / 0 |

**Amendment 14's reading (a) holds:** on a text layer the resolver can match, every quote resolves.
The corpus run's ten unresolved quotes were the text layer's, a cause the stanza does not own. The
label does not match on either layer, which is a different fact and is reported as the count it is.
Neither run is pooled with the other; the corpus line above stands as the corpus result.

## Named lines — the whole run, both layers

- **R:** draws 190; reasks 0; errors 0; unresolved spans 20 (agtzidis 10, liu_2005 10); model binding
  against the frozen heuristic over the 142 extracted draws: **142 agree, 0 disagree, 0 undecided**
  (the first run with no `undecided` on binder); rows over 190: row 1 ×104, row 2 ×38, row 4 ×48.
- **The demoted-or-routed count, its own line:** demoted (`motion_value_unsupported_by_quote`) **0**;
  routed and fallen back to the package (`motion_value_routed_fallback_to_package`) **10** (derosa);
  routed without a fallback **0**; the processed layer differs from the raw layer on those 10 draws
  and on the 20 unresolved-quote draws, and nowhere else.
- **The level, derived in code, against column R** over the row-2 draws with a resolved span: ciric
  10 agree, gordon 10 agree, derosa 10 agree, **cole 8 disagree**, agtzidis and mueller no level,
  the clean three no level — **38 agree, 8 disagree, 44 without a level** over the nine `named_tool`
  labels' 90 draws. The 8 disagreements are one span shape: a quote that runs from the package
  sentence into the step list carries an operation phrase, and the derived level reads it as `step`.
- **B:** 19 results; `status` success 18, `methods_not_found` 1 (liu_2005); `render_error` 0;
  `error_message` 0; the batch draw inside the recorder's raw-state set on 17 of 19 (outside:
  agtzidis — processed `absent` against raw `described_only` — and liu_2005).
- **Excluded by name:** `undecided` 0; `unread` 0; `multi_target_unscoreable` 0.
- **Wall time per draw, mean (R):** power 4.90 s, binder 2.93 s, liu_2013 12.00 s, derosa 6.45 s,
  agtzidis 5.13 s, poldrack 21.34 s, ciric 10.88 s, braun 11.17 s, viduarre 5.86 s, vanderwal 4.08 s,
  cole 4.90 s, gordon 6.15 s, mueller 6.19 s, chen 7.19 s, oconnor 4.88 s, weber 4.88 s; the clean
  three as one group mean, 13.76 s.

## The pre-declared error class, accounted

Amendment 13 pre-declared *package attribution unreached by the frozen stanza* for agtzidis, cole
and mueller. It occurred on **agtzidis (10 of 10) and mueller (10 of 10)** and on **cole's 2 of 10**;
on cole's other 8 the frozen stanza returned `AFNI` as a bound tool, which column R calls `package`
and the derived level calls `step` because the quote spans two sentences. derosa's `FSL` at the
processed layer by the fallback occurred on 10 of 10. gordon, reported as found: `SPM8` on 10 of 10.

## What was found that was not pre-declared

- **poldrack deferred on 5 of 10 under version 4**, which had returned `described_only` on 10 of 10
  on both earlier days under the same hash — a third day's count for the same stanza, inside the
  day-to-day movement the record has measured on liu_2013 (10 → 7 → 5 → 10 → 5 → 4 across six runs).
- **liu_2013 at 4 of 10**, below the band Amendment 13 carried.
- **cole's `AFNI` reached on 8 of 10** by a two-sentence quote, where versions 6 and 7 with the
  package rule had reached it on 4 and 0.
- **chen, oconnor and weber in the paper's own voice on 30 of 30**, a named shape unreached.
- **The first run with 0 disagreements and 0 undecided** between the model's binding and the
  heuristic, over 142 extracted draws.

## The identity gate

Derived before the run as **19 identical** (neither run changes code; B writes under its own
`output_dir`) and run after it: `--against HEAD` → 19 identical, 0 changed; the negative control
`--against d31e8b7` → 0 identical, 19 changed. None of the 19 stored acceptance JSONs was touched
(mtimes older than the run).

## What this shows, and what it does not

- Under the frozen stanza, on the nineteen: the deferral shapes it reached in the probe it reaches
  here; the package-attributed labels it was pre-declared not to reach it does not reach, except
  where a two-sentence quote carried the package; the wrapper-named papers are a shape it does not
  reach; and the clean three, which no stanza was iterated on, match on 0 of 30. Reachability, not
  accuracy: thirteen fitted, sixteen contaminated, three clean — **no rate is computed here or may
  be computed from the projections.**
- The batch's single draw agrees with the recorder's distribution on 17 of 19 papers; where it
  differs, the processed layer is the reason, and it is on the record beside the raw one.

## Status

- Labels unchanged by this document. The three clean cells are spent; no second run on them without
  a further amendment.
- **Held for the author:** the wrapper-named shape (chen, oconnor, weber) and liu_2005's text layer,
  both outside what a stanza iteration may now touch; whether the derived level should read only the
  sentence that names the package when a quote spans two sentences (cole); and what the next
  pre-registration, if any, asks of a stanza that is now frozen.

## Rulings — 2026-10-28, by the author, recorded the day they were given

1. **The derived level reads the sentence that contains the value token, not the whole span** — a
   code fix with a replay; no new vintage. (cole's 8 disagreements above were a two-sentence span.)
   **Replayed 2026-10-28, after the fix:** the projection was re-emitted from the same records; cole's 8
   row-2 draws now derive `package`, agreeing with column R, and no other row of the 190 changed. The
   version-7 projection re-emits byte-identical. The level line above becomes **46 agree, 0 disagree,
   44 without a level**; the records are untouched.
2. **liu_2005 gets a recorder run on its de-interleaved slice**, K=10, under prereg Amendment 14,
   reported beside this result and never pooled with it; its clean cell is already spent.
3. **The wrapper-named shape (chen, oconnor, weber) is not a stanza item**: the inference arm handles
   it through `base_pipeline` (`DESIGN_motion_inference_arm.md`).

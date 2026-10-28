# Poster numbers, 2026-11 — every count the poster can use, each with its vintage, hash, rule and source

**Written 2026-10-28 from the sources named on each line; nothing here is recalled.** Every number is
a count of draws or of papers. **No rate, fraction, percentage or interval appears anywhere in this
document, and none may be computed from it** (prereg `motion-method-reachability-prereg.md:9-10`,
`:158-159`). Where a source prints a rate beside a count, only the count is carried here. Vintages
are never pooled. The three held-out papers (liu_2005, tang_2025, wheaton_2004) appear as states and
counts only. `path:line` references are to this repository at the time of writing.

Reading the tables: **vintage** names the stored output a count was read from; **stanza** is the
sha256 of `MOTION_METHOD_PROMPT` where one applies (target_space has no stanza hash on its record;
its vintage is the named CSV); **rule** is the aggregation that produced the count; **source** is
where the count is printed.

---

## 1. The pipeline

### 1.1 States

| count | what | source |
|---|---|---|
| 3 | extraction statuses: `EXTRACTED`, `MISSING_FROM_PAPER`, `DEFERRED_TO_CITATION` | `extractor_mvp/src/extractor_mvp/render.py:44-46` |
| 3 | inference statuses: `NOT_APPLICABLE`, `INFERRED_DEFAULT`, `LEFT_MISSING` | `render.py:45-46` |
| 5 | display states a report renders, by precedence (extracted, inferred default, deferred to citation, missing from paper, left missing) | `render.py:47-54` |
| 6 | state-map rows for `motion_correction.method` (1 `described_only`, 2 `named_tool`, 3 `undecided` — halt, 4 `deferred`, 5 `unread`, 6 `absent`) | prereg `:64-75` |

The provenance contract couples the two stages: `EXTRACTED` requires inference `NOT_APPLICABLE`;
`MISSING_FROM_PAPER` and `DEFERRED_TO_CITATION` require `INFERRED_DEFAULT` or `LEFT_MISSING`
(`DESIGN_motion_inference_arm.md:175-178`, citing `provenance.py:192-202`).

### 1.2 Fields

| count | what | source |
|---|---|---|
| 6 | targeted Layer-2 step fields: `target_space`, `resolution_mm`, `surface_registration`, `target_surface`, `convention`, `value` | `extractor.py:1653-1664` (`_LAYER2_FIELD_IDS`) |
| 7 | entries of `_FIELD_SPECS` (the six above plus `temporal_standardization.method`) | `extractor.py:396` |
| 1 + 1 | `base_pipeline` (name) and `base_pipeline.version` | `cobidas.py:252-255` (base_pipeline always targeted); `extractor.py:710`, `:720` |
| 1 | `motion_correction.method`, targeted since the motion stanza | `extractor.py:1356-1358` |
| **10** | targeted fields in all (7 + 2 + 1) | the four lines above |
| 37 | field rows one stored record carries (the ten above and the filler fields, which are `LEFT_MISSING`, reason `not_targeted_by_mvp`) | derived by script from `results/batch_motion_corpus_v1/papers/power_2014.json`, field ids and statuses only; `render.py:479` for the reason |

### 1.3 COBIDAS D.3 rows covered

| count | what | source |
|---|---|---|
| 16 | D.3 rows in scope for an fMRI-preprocessing protocol | `cobidas.py:48`, `COBIDAS_D3_ROWS` |
| 14 | mandatory rows; 1 unconditional (Software) | `cobidas.py:49`, `:51` |
| 2 | non-mandatory rows (Software citation, Intensity normalization) | `cobidas.py:52`, `:87-93` |
| 2 | AESPA step kinds with no D.3 row (`temporal_filtering`, `temporal_standardization`), never in the denominator | `cobidas.py:105-106` |
| 8 | D.3 rows deliberately out of scope (diffusion, perfusion, resting-state feature, QC), recorded not hidden | `cobidas.py:108-118` |
| **3 of 14** | mandatory rows the extractor can assess: Software (via `base_pipeline.version`), Motion correction, Intersubject registration (`spatial_normalization`, `surface_projection`) | `cobidas.py:51`, `:59`, `:77-83`; one report's coverage block, `results/batch_motion_corpus_v1/papers/power_2014.md` ("Assessed by AESPA: 3", "Not assessed by AESPA: 11") |

**Rule for the per-paper count:** a row is "assessed" when a targeted field maps to it and the
extractor looked (`cobidas.py:285-320`); the Software row follows its own rule and is **not
assessed** when the base pipeline is `NotApplicable` or the extractor found a pipeline name it could
not verify (`cobidas.py:266-283`), so the per-paper count is 3, 2 or 1.

| vintage `batch_motion_corpus_v1` (2026-10-27, stanza `b0093774…`): rows assessed | papers | which |
|---|---|---|
| 3 of 14 | **13** of the 16 contaminated papers | power, binder, liu_2013, derosa, ciric, braun, viduarre, vanderwal, gordon, mueller, chen, oconnor, weber |
| 2 of 14 | 2 | poldrack, cole (no Software row assessed) |
| 1 of 14 | 1 | agtzidis (Software only; 2 rows "targeted but unverifiable") |
| — | 3 | the held-out three: their reports' coverage blocks were not read |

Source: the `Mandatory rows` / `Assessed by AESPA` header lines of the sixteen contaminated papers'
reports under `results/batch_motion_corpus_v1/papers/`, read by explicit path on 2026-10-28 (counts
only; `results/` is gitignored). The Software row is flagged "unconditional violation" on **11** of
those 16 reports and addressed on **3** (liu_2013, derosa, oconnor); on poldrack and cole it is not
assessed.

### 1.4 The software-version finding — **retracted; not a poster number as "0 of 19"**

| claim | status | source |
|---|---|---|
| "0/19 corpus papers naming a base pipeline report its version" | **retracted 2026-09-07**: it restated a hardcoded constant, not a measurement | `docs/DESIGN_cobidas_coverage.md:28-35`; `docs/findings/cobidas-version-criterion.md:64-66` |
| 3 of 19 papers state a separate, exact version string, read from the papers by hand: oconnor (C-PAC 0.4.0), derosa (FSL 5.0.10), liu_2013 (1.1-beta); 4 SPM papers state a version fused into the name | the sayable count | `docs/ground-truth-protocol.md:393-401`; `cobidas-version-criterion.md:66-70`, `:92-96` |
| the count of papers compliant with COBIDAS §4.3 (exact version, not the major number alone) | **unestablished**: no ground-truth labels, no per-tool exactness rule fixed yet | `cobidas-version-criterion.md:101-105`, `:108-110` |
| a count of `base_pipeline.version == EXTRACTED` | a count of papers that stated a separate version string, not of compliance | `cobidas-version-criterion.md:98-99` |

The denominator for compliance is 19 (Software is universal); the descriptive sub-question (papers
naming a pipeline that give an exact version) takes a different denominator, and the two are to be
recorded under separate names (`cobidas-version-criterion.md:112-115`). The poster may say that the
earlier figure was retracted and that three papers state an exact version; it may not say "0 of 19".
oconnor's `0.4.0` is a version C-PAC never released under a tag (checked 2026-10-28 against the
project's GitHub tags: v0.3.9 → v0.3.9.1 → v1.0.0; `motion-inference-arm-v1.md:61-68`).

---

## 2. `target_space` — two vintages, K=3 plurality, braun's single vote

Labels: `ground_truth/target_space_labels_v1.csv`, 19 papers, vintage-independent
(`ground_truth/target_space_tally.md:12-26`): family_specified **10**, deferred **3**, native_volume
**2**, study_specific **2**, absent **1**, canonical **1**.

**Denominator rule:** blind papers = 19 minus the 2 non-blind (mueller_2021, oconnor_2017, used as
worked examples) = **17** (`target_space_tally.md:33-34`, `:62-63`). The tally prints a rate on
these lines; only the counts are carried here.

| vintage | source CSV | rule | correct of 17 blind | source |
|---|---|---|---|---|
| `v040_frozen` | `target_space_predictions_v040_frozen.csv` (frozen pre-0.5.0 output, translated into the v3 map's shape) | K=3, plurality on status (`extractor_status`; per-draw in `status_k3`) | **11** | `target_space_tally.md:27-34` |
| `v050` | `target_space_predictions_v050.csv` (0.5.0 output, `batch_v050_labelset` draws 1/2/3) | K=3, plurality on status, the winning draw supplies the value (`maj_status`; per-draw in `k3_status`) | **10** | `target_space_tally.md:56-63` |

Per-label counts (rows are labels, columns graded predictions; the diagonal is correct):

| label | n | `v040_frozen` correct | `v050` correct | source |
|---|---|---|---|---|
| absent | 1 | 1 | 1 | tally `:47-54`, `:81-88` |
| canonical | 1 | 0 | 0 | |
| deferred | 3 | 1 | 0 | |
| family_specified | 10 | 9 | 9 | |
| native_volume | 2 | 0 | 0 | |
| study_specific | 2 | 0 | 1 | |

(These tables count all 19 papers; the "of 17" lines above exclude the two non-blind.)

**braun's single vote.** `v040_frozen` is the only vintage where any paper's three draws disagreed:
**1 of 19** papers, braun_2015, draws `DEFERRED/MISSING/DEFERRED`, collapsed by plurality to
`DEFERRED`, label `deferred`, blind — correct on one vote. Under `v050` **0 of 19** papers disagreed,
and braun's three draws were unanimously `absent` — wrong (`target_space_tally.md:90-102`,
`:109-118`). Read the margin, not just the winner: where a blind paper's draws split 2–1, the
published count moves by one paper on one vote (`:104-107`).

**What moved between vintages:** 2 of 19 papers — braun (blind) correct → wrong; mueller (non-blind)
wrong → correct. Same total correct over 19; different papers; the blind count differs by one
because only braun reaches the denominator (`target_space_tally.md:109-120`).

**Caveat carried with both vintages:** agtzidis_2020 is `MISSING_FROM_PAPER` on both records
(`extraction_quote_unresolved:quote_not_found`, the `/C2` glyph leak) and is graded correct under
`v050` by `scoring_mode = fallback` from the diagnostic's raw value, so under `v050` the count
measures the report for 16 cells and the diagnostic for 1 (`target_space_tally.md:65-73`,
`:36-39`).

---

## 3. `motion_correction.method`

Model on every run: `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`,
`max_retries=2`; K=10 per paper per arm; one `ParsedPaper` per paper sliced by
`find_methods_section`. Rule for every "match" count: a draw matches when its state-map row (raw
`status` and raw `value` only, prereg Amendment 2 ruling 2) equals the label's state; for
`named_tool` labels, with the label's value (normalized exact equality, the author's ruling of
2026-10-26) and, from v1.8, the level against column R. Each run is its own vintage; nothing is
pooled.

### 3.1 The version chain, v1 → v7

| version | stanza sha256 | run (UTC) | papers × K = draws | purpose (amendment) | outcome | source |
|---|---|---|---|---|---|---|
| 1 | `56bc6305d30cef011f382af74195d3352a6c584ef3abe317c30b807be9b1e21a` | 2026-10-21 | 6 × 10 = 60 | is `described_only` expressible (prereg `:5-10`; Amendment 2's five pre-run rulings) | rows 1, 2, 3 produced; power row 1 ×10, liu_2013 row 1 ×10, derosa `ICA-AROMA` row 2 ×10, poldrack row 1 ×10 (never `applywarp`), agtzidis row 1 ×9 / `SPM12` ×1, binder `undecided` ×10 — ruling 4's trigger fired; the positive control was mis-specified (Amendment 3) | `motion-probe-v1-results.md:9-31`, `:34-38`, `:190-194` |
| 2 | `378a294f94ca9f0fc6bd45bd42caf4646a007c7d705d05c8b5f584dd66ca8cab` | 2026-10-22 | 7 × 10 = 70 | the replacement positive control (ciric) and one C11 iteration (Amendment 4) | ciric `MCFLIRT` ×10 with the ESTIMATE span; ICA-AROMA routing 0 of 10; binder `AFNI` ×5, a new error class; agtzidis `SPM12` 1 → 10, cause not separable from the day | `motion-probe-v2-results.md:13-15`, `:93`, `:113`, `:141-150` |
| same-day control | `56bc…` and `378a…` | 2026-10-25, 22:49–22:54 | 2 papers × 2 arms × 10 = 40 | did the stanza move agtzidis and binder, or the day (Amendment 5) | each arm reproduced its own earlier modal row on the same day: agtzidis row 1 ×10 under `56bc`, row 2 ×10 under `378a`; binder row 3 ×10 under `56bc`, row 2 ×8 / row 3 ×2 under `378a` — a stanza effect; reasks 0, errors 0, unresolved 12 of 40 | `motion-probe-ab-stanza-vs-day.md:3`, `:19-21`, `:41-61`, `:81-92` |
| control under restored `56bc…` | `56bc…` | 2026-10-26 | 1 × 10 = 10 | ciric under the restored stanza (Amendment 6) | 10 of 10 `MCFLIRT`, span 4410–4507, the ESTIMATE mention, no CONSUME mention | `motion-probe-ciric-56bc.md:29-43` |
| 3 | `ea7b0084255454fd38a6de566a5cccf2936b67b09910f6ffa15a79d01c5734a7` | 2026-10-26, 19:16–19:26 | 7 × 10 = 70 | rule A and option (c): the model emits its own binding (Amendment 7) | `deferred` expressible for the first time (liu_2013 ×10); binding vs heuristic never disagreed on a classifiable draw; reasks 0 of 70 | `motion-probe-v3-results.md:9-11`, `:22`, `:71-80` |
| 4 | `b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837` (6,402 chars) | 2026-10-26, 22:34–22:47 | 10 × 10 = 100 | three deferral shapes join the probe (braun, viduarre, vanderwal) (Amendment 8) | each new shape `deferred` ×10; row 4 on 37 of 100 draws; liu_2013 `deferred` 7 / row 1 ×3; poldrack row 1 ×10, unreached; reasks 0 of 100 | `motion-probe-v4-results.md:9-11`, `:20`, `:25-47`, `:54-68` |
| 5 vs 4, same day | `fb5735fba39457a0f67aebe95fa4668f1df7ae55568f3ad86d1274563863e6d2` (6,809) vs `b0093774…` | 2026-10-26, 23:15–23:41 | 10 × 2 × 10 = 200 | the introducing-sentence rule for poldrack, with an adoption rule; then freeze (Amendment 9) | **not adopted**; v4 frozen (`c5bfe6b`) — §3.2 | `motion-probe-v5-ab-results.md:3`, `:11-15`, `:38-51` |
| 6 | `8df070da9cc3f9628d6670c7285740155b05a06dd25972849f0711b056c8ef4f` (7,934) | 2026-10-27, 13:39–14:04 | 13 × 10 = 130 | the attribution level in the model's output; the 13-paper probe set (Amendment 10) | **not adopted** — §3.2; reasks 1 of 130, errors 1 | `motion-probe-v6-results.md:9-11`, `:23`, `:28-60` |
| 7 | `d353fb478cd1fbbe03d079a51b322c749c8b8a3431b58261745ac17b503d5a1d` (7,848) | 2026-10-27, 16:25–16:51 | 13 × 10 = 130 | the level leaves the output; level and routing fallback move into code (Amendment 11) | **not adopted**; v4 restored verbatim and frozen (Amendment 12); reasks 5 of 130, errors 1 | `motion-probe-v7-results.md:9-11`, `:22`, `:59-93` |
| corpus | `b0093774…` (v4, frozen) | 2026-10-27, 18:53–19:31 | 19 × 10 = 190 (recorder) + 19 × 1 (batch) | the first corpus-wide run; the held-out release (Amendment 13) | §3.3 | `motion-corpus-v1-results.md:1-30` |
| liu_2005 slice | `b0093774…` | 2026-10-28, 18:54–18:56 | 1 × 10 = 10 | liu_2005 on its de-interleaved slice, beside the corpus line, never pooled (Amendment 14) | §3.5 | `motion-corpus-v1-results.md:112-132` |

Chain on the pin: `b0093774…` → `8df070da…` → `d353fb47…` → `b0093774…` (prereg `:1134-1140`).

### 3.2 The adoption rules, applied as written

| rule | clause 1 | clause 2 | outcome | source |
|---|---|---|---|---|
| Amendment 9 (v5 vs v4, same day) | poldrack `deferred` to ref 45 on ≥ 6 of 10 under v5: **3 of 10** — not met | no other paper loses > 2 matching draws vs its same-day v4 arm: largest loss binder 2 by the model's own state (2 errors), 0 by row — met | **v4 freezes**; the rule is a conjunction | prereg `:838-841`, `:884-885`; `motion-probe-v5-ab-results.md:38-51` |
| Amendment 10 (v6) | every `named_tool` paper at its level on row 2 on ≥ 8 of 10: ciric 10, agtzidis 6, cole 4, gordon 0, mueller 0, derosa 0 — fails on 5 of 6 | no paper lost a draw vs v4; three gained — not breached | **v6 not adopted**; no stanza frozen by adoption | `motion-probe-v6-results.md:28-60` |
| Amendment 11 (v7) | every `named_tool` paper returns the label's value on ≥ 8 of 10: ciric 10, agtzidis 10, mueller 10, derosa 10 (processed layer), gordon 7, cole 0 — fails on 2 of 6 | no paper loses > 2 vs its v6 count: liu_2013 −5, poldrack −4, cole −4 — fails on 3 | **v7 not adopted; v4 restored and frozen; no further iteration** | prereg `:1101-1110`, `:1134-1140`; `motion-probe-v7-results.md:59-93` |

Same-day controls behind the chain: Amendment 5 (40 draws, two stanzas on one day: a stanza effect)
and Amendment 9 (200 draws, v4 and v5 arms back to back, 23:15–23:41 UTC). Under the Amendment 9
same-day v4 arm, liu_2013 returned `deferred` 5 of 10 against 7 of 10 the day before, recorded as the
frozen version's cost, not within-run variation (prereg `:886-891`).

### 3.3 The corpus run, by contamination class (vintages `motion_probe_corpus_v1` R and `motion_corpus_v1` B)

Stanza `b0093774…`; recorder 2026-10-27 18:53:11–19:22:53 UTC under HEAD `8099063`, licence
Amendment 13; batch 19:22:53–19:31:28 UTC, config sha256 `3a8a8cfd…`. Labels: the v1.8 workbook at
`bc18447` (sha256 `350331c8…`, 26,822 bytes): `named_tool` 9, `deferred` 8, `described_only` 2.
Source for every line below: `motion-corpus-v1-results.md`.

**Probe thirteen, fitted** (`:50-70`) — recorder draws matching the label, of 10:

| all ten | 8 papers: power, binder, derosa, ciric, braun, viduarre, vanderwal, gordon |
|---|---|
| 8 | cole |
| 5 | poldrack |
| 4 | liu_2013 |
| 0 | agtzidis, mueller |

The batch's one draw matches on 8 of 13 and sits inside the recorder's raw-state set on 12 of 13.

**Co-adjudicated, not probed — chen, oconnor, weber** (`:72-87`): their first motion draws under any
stanza; row 1 ×10 on each, the paper's own voice; match **0, 0, 0**; the batch draw `described_only`
on all three, inside the recorder set on 3 of 3. The wrapper returned as a tool: 0 draws. Recorded as
"the poldrack shape with a named wrapper", a named shape, unreached, 3 of 3.

**The clean three, states and counts only** (`:89-102`): label `named_tool` on all three; recorder
match **0 of 30** (liu_2005 0 of 10, row 1 ×10, all ten quotes unresolved; tang_2025 0 of 10, row 4
×7 / row 1 ×3; wheaton_2004 0 of 10, row 1 ×8 / row 4 ×2); batch **0 of 3** (liu_2005
`methods_not_found`, the only such status in the run; the other two `described_only`); no row-2 draw,
so no level (0 agree, 0 disagree, 30 without); reasks 0, errors 0.

**Named lines, the whole run** (`:134-155`, with ruling 1's replay at `:204-210`):

| count | what |
|---|---|
| 190 | recorder draws; reasks 0; errors 0 |
| 20 | unresolved spans (agtzidis 10, liu_2005 10) |
| 142 / 0 / 0 | model binding vs the frozen heuristic over the 142 extracted draws: agree / disagree / undecided — the first run with none |
| 104 / 38 / 48 | state-map rows 1 / 2 / 4 over the 190 |
| 0 | demoted (`motion_value_unsupported_by_quote`) |
| 10 | routed and fallen back to the package (`motion_value_routed_fallback_to_package`), all derosa; routed without a fallback 0 |
| 46 / 0 / 44 | the derived level vs column R over the nine `named_tool` labels' 90 draws: agree / disagree / no level — after ruling 1 (2026-10-28, the level reads the value's sentence; before it, 38 / 8 / 44, cole's 8 on a two-sentence span) |
| 18 / 1 | batch `status` success / `methods_not_found` (liu_2005); `render_error` 0 |
| 17 of 19 | batch draw inside the recorder's raw-state set (outside: agtzidis, liu_2005) |
| 0 / 0 / 0 | excluded by name: `undecided`, `unread`, `multi_target_unscoreable` |

**The pre-declared error class** (`:157-163`): package attribution unreached by the frozen stanza —
agtzidis 10 of 10, mueller 10 of 10, cole 2 of 10 (on cole's other 8 the stanza returned `AFNI`);
derosa `FSL` at the processed layer by the fallback 10 of 10; gordon `SPM8` 10 of 10.

**Identity gate** (`:177-182`): derived before the run as 19 identical; after it `--against HEAD` 19
identical, 0 changed; negative control `--against d31e8b7` 0 identical, 19 changed.

### 3.4 The inference arm, fills per basis (vintage `batch_motion_corpus_v1_inferred`, 2026-10-28, no model call)

Source `motion-inference-arm-v1.md:12-37`; projection
`ground_truth/motion_inference_v1_projection.csv`. Rule: F1 — `deferred`-to-pipeline and `missing`
take the arm proper; `described_only` takes the same inference as a diagnostic on the processed
layer; `named_tool` never. F2 — a recognized pipeline at a certain version wins over the package
basis. Confidence: `version_default` 0.95, `date_inferred_version` 0.75 (stable range only),
`derived` from `base_pipeline.name` 0.70.

| path | basis | papers | which |
|---|---|---|---|
| arm proper | package, `derived` 0.70 | **1** | agtzidis |
| diagnostic | pipeline, `version_default` 0.95 | **1** | liu_2013 (the FCP scripts document) |
| diagnostic | pipeline, `date_inferred_version` 0.75 | **2** | chen, weber |
| diagnostic | package, `derived` 0.70 | **1** | mueller |
| never (`named_tool`) | — | **3** | derosa, gordon, ciric |
| none | — | **7** | power, binder, poldrack, cole (no base pipeline on the record); braun, viduarre (deferred to papers); vanderwal (0.3.x range not stable); oconnor (`0.4.0`, not a C-PAC release) |
| clean three, filled-or-not only | — | **2 of 3** filled | liu_2005 not filled; tang_2025 and wheaton_2004 filled (diagnostic) |

Arm 1, diagnostic 5, never 3, none 7 over the sixteen; 15 of 16 as pre-declared (expected arm 2 /
diagnostic 5; found 1 / 5: vanderwal's conditional fill did not fire, oconnor's version is not a
release). F2's precedence was exercised on 0 papers; every filled paper has 0 alternatives
(`:36-37`, `:55-57`).

### 3.5 liu_2005 beside its slice run (Amendment 14; never pooled)

Slice `ground_truth/liu_2005_deinterleaved_methods.txt` (sha256 `cfc82ed8…`), 2026-10-28
18:54:15–18:56:22 UTC, HEAD `9e146a7`, stanza `b0093774…`, licence Amendment 14. Source
`motion-corpus-v1-results.md:112-132`.

| of 10 draws | corpus run (the PDF's text layer) | the de-interleaved slice |
|---|---|---|
| state-map rows | row 1 ×10 | row 1 ×9, row 3 ×1 (excluded by name) |
| processed layer | MissingFromPaper ×10, `extraction_quote_unresolved` | Extracted ×9; MissingFromPaper ×1, `motion_value_unsupported_by_quote` |
| unresolved spans | 10 | **0** |
| matches the label | 0 | 0 (no row-2 draw, no level) |
| reasks / errors | 0 / 0 | 0 / 0 |

Reading (a) holds: on a text layer the resolver can match, every quote resolves; the label does not
match on either layer, a different fact.

---

## 4. The named limitations

- **Package attribution.** The frozen stanza was pre-declared not to reach a package-level label
  (the tool named for the whole analysis, sentences away from the step); it did not on agtzidis (10 of
  10) and mueller (10 of 10), and on cole's 2 of 10. The level is now derived in code from the
  sentence containing the value (ruling 1, 2026-10-28), not stated by the model: v6 asked the model
  for it and got gordon and mueller backwards (`motion-probe-v6-results.md:84-100`);
  `motion-corpus-v1-results.md:157-163`, `:204-210`.
- **The wrapper shape.** chen, oconnor and weber (CCS, C-PAC) read as the paper's own voice on 30 of
  30 draws; the stanza does not connect the operation sentence to the wrapper named for the
  preprocessing. Ruled not a stanza item: the inference arm handles it through `base_pipeline`
  (`motion-corpus-v1-results.md:82-87`, `:214-216`).
- **Day-to-day movement under one hash.** At temperature 0, the same stanza on different days
  returns different counts: liu_2013 10 → 7 → 5 → 10 → 5 → 4 across six runs; poldrack `described_only`
  10 of 10 on two days then `deferred` 5 of 10 on a third under `b0093774…`; Amendment 11's clause 2
  compared across days and its losses are reported as losses under the rule, not attributed to v7
  alone (`motion-corpus-v1-results.md:167-170`; `motion-probe-v7-results.md:89-93`). The same-day
  control is what separates a stanza effect from a day (`motion-probe-ab-stanza-vs-day.md:41-61`).
- **The text layer.** liu_2005's PDF text layer is interleaved: `methods_not_found` in the batch and
  10 of 10 unresolved quotes in the recorder; on the de-interleaved slice 0 of 10 unresolved. A text
  layer the resolver cannot match is a cause the stanza does not own (`motion-corpus-v1-results.md:104-110`,
  `:129-132`). agtzidis carries the other text-layer defect, the `/C2` glyph leak (10 unresolved in
  the corpus run; `target_space_tally.md:64-73`).
- **The contract conflation.** `described_only` is `EXTRACTED` because it carries the paper's
  phrase in a tool-valued slot, and the provenance contract forbids an inferred default beside an
  `EXTRACTED` field; so every pipeline-basis fill on this corpus went in as a diagnostic on the
  processed layer, the common case, not the exception. The structural fix, a "performed" / "method"
  split, is a schema migration recorded for after 2026-11-09 (`DESIGN_motion_inference_arm.md:22-40`,
  `:175-178`; `motion-inference-arm-v1.md:69-71`, `:92-95`).

---

## 5. Rules of use, restated

- Counts of draws and of papers only. No rate anywhere; none may be computed from these tables.
- Each run is its own vintage; the stanza hash and the date identify it; vintages are never pooled.
- Reachability, not accuracy: thirteen fitted, sixteen contaminated, three clean. The clean three
  appear as states and counts only, and their cells are spent (`motion-corpus-v1-results.md:186-198`).
- `target_space` counts are blind over 17 papers; the two non-blind papers are named wherever they
  enter a table.
- The "0 of 19 report a version" figure is retracted and must not appear.

# DESIGN — the first corpus-wide `motion_correction.method` extraction under the frozen stanza

**Design only. Written 2026-10-26 (late night), after the freeze (`c5bfe6b`) and before any call.**
No code was changed, no model was called, nothing was written under `results/`. Every fact below
carries its locator; every reading in §5 is written before the run it reads.

**Containment, stated first.** liu_2005, tang_2025 and wheaton_2004 remain unread. For this document
the only thing read about them is the `method_state` cell of each, by id, from
`ground_truth/motion_correction_labels_v1.xlsx` (the author's licence for this document), plus one
count from the stored acceptance run (§2.2). No value, quote, note, offset, stored field or text of
theirs was read; `ground_truth/liu_2005_deinterleaved_methods.txt` was not opened. They enter the run
through the model only, and their results are read as states and counts.

## 1. Scope

> **Dated note, 2026-10-26 (late night).** The freeze this document was written under is **lifted and
> moved by prereg Amendment 10 for a definitional change, not tuning**: protocol v1.8 gives
> `named_tool` an attribution level (`step` / `package`), and stanza version 6 expresses it. The
> full-corpus run runs under the version Amendment 10 adopts — `8df070da…` if version 6 freezes —
> and every reading in §5 is re-declared under v1.8 labels before that run. cole, gordon and mueller
> now have v1.8 worked cases (§5.0's first check is settled by the protocol, pending the workbook
> edits); the held-out three's check by the author alone still stands. §2.6's state counts change
> with the workbook edits (agtzidis and derosa become `named_tool`) and are restated then.

- **What this is.** The first extraction of `motion_correction.method` over all 19 papers under the
  frozen stanza `b00937747b00f0f7dc46d6e68d54deca95d860e5b6c3b3e03542f07866f43837` (version 4; prereg
  freeze section after Amendment 9; `scripts/motion_probe.py:132` refuses any other hash before a
  client is built, `:135-142`, `:355`).
- **What it is for.** Diagnostic, not evaluative: `DESIGN_motion_correction_extraction.md` §6 items 2
  and 3 (`:860-864`), Ruling D (`:532-537`), protocol `:648-650` (`DESIGN_motion_correction_extraction.md` still cites it as `protocol:547-550`; that
  locator has drifted and is corrected here, not there). Counts of papers and draws by named
  class. **No corpus-wide rate, fraction or interval anywhere** — not in this document, not in the
  results document, not in a projection header.
- **The corpus.** The 19 ids of `extractor_mvp/configs/batch_a1_acceptance_config.yaml`; cabral_2017
  is excluded by `corpus.py:13-19` (a modelling paper with no methods section) and is not a cell.
- **Motion only — and the batch run is a new named vintage for every field.** `batch.py` runs the
  shared call as well as the motion call, so every field a batch run writes is vintage
  `motion_corpus_v1` (the config of §7 fork 9), not a re-measurement of any committed number;
  **committed numbers stand under their own vintages** (the 2026-10-19 ruling the prompt pin
  records). This design reports the motion field only; the other fields are named as existing and
  not read, not compared.
- **The three clean cells are spent once.** A held-out paper's first draw is the measurement; there
  is no second run on those three without a new amendment, because the second run would be made
  after their first result was seen.

## 2. Facts the design rests on (Part A), each with its locator

### 2.1 The recorder's table is ten papers; extending it to 19 touches five places

`scripts/motion_probe.py`:

- `_PROBE_PAPERS` (`:85-122`) maps id → `{pdf, role}`; `_paper()` (`:223-234`) loads
  `_CORPUS / pdf` (`:80`, the `sfn_batch` folder) through `load_pdf_text` → `find_methods_section`
  → `ParsedPaper`, "exactly as `batch.process_paper` does". Nine entries are missing: chen_2015,
  cole_2013, gordon_2014, mueller_2021, oconnor_2017, weber_2024, liu_2005, tang_2025, wheaton_2004.
  Their PDF names are in the acceptance config and in the corpus folder listing (`Chen_2015.pdf`,
  `Cole_2013.pdf`, `Gordon_2014.pdf`, `Mueller_2021.pdf`, `OConnor_2017.pdf`, `Weber_2024.pdf`,
  `Liu_2005.pdf`, `Tang_2025.pdf`, `Wheaton_2004.pdf`). **Adding them needs ids and file names
  only; no tool reads a line of text to write the table entry.** The text is read only when the run
  loads the PDF for the model. **Done 2026-10-26, on the author's instruction:** all 19 are in the
  table (`:93-165`), roles only, no text read; a test holds the table equal to the acceptance
  config's ids and file names.
- `_HELD_OUT` (`:125`) and the refusal at `:356-366` refuse the three ids before a client is built.
  This is the C11/C26 guard against *iteration*; the stanza is now frozen, so the licence question
  has changed, but the guard has not. **It must be changed by amendment, not deleted** (§7, fork 1).
  **Built 2026-10-26, default-closed:** `_CORPUS_RUN_LICENCE` (`:176`, `None`) and
  `_refuse_unless_licensed` (`:179-193`), called before any client (`:440-441`) for any held-out id
  in `--papers`, including the default list of all 19; `--corpus-run` (`:422-428`) must equal the
  constant, which only the licensing amendment sets, in the same commit. The manifest records the
  licence and the held-out ids admitted (`:371-372`). The out-of-corpus refusal (`:434-438`) is
  unchanged and still precedes the held-out check.
- `--papers` defaults to `sorted(_PROBE_PAPERS)` (`:345-347`): alphabetical, so the held-out three
  would run at positions 8, 15 and 19 of 19, interleaved with the rest.
- The manifest's `papers` list and `pre_registration` string (`:297-299`) name what ran.
- `scripts/motion_probe_projection.py` `_ORDER` (`:48-71`) now lists all 19 in the reporting
  partition's order, the clean three last. **Erratum, 2026-10-26, before the build:** an earlier
  wording of this bullet said a 19-paper run projected with the ten-paper `_ORDER` "would silently
  drop nine". It would not: the script already refused any manifest paper absent from `_ORDER`
  (`:236-238`). What it did not check was a record file on disk for a paper absent from both the
  manifest and `_ORDER`; that check is now at `:218-223`. Both refusals are mutation-tested.
- `tests/test_motion_probe_freeze.py` used liu_2005 as the held-out refusal control; its expectation
  changed with the guard. **Done 2026-10-26:** the control is an out-of-corpus id (cabral_2017),
  and the held-out guard has its own tests in `tests/test_motion_probe_corpus.py`, which stub the
  client and the loader so that no test can read a paper and a missing guard fails at the stub. `tests/test_motion_value_kind.py:134-146` records why the containment is
  procedural, not tested.

The recorder makes **only the motion call** (`:22-28`): no shared prompt, no `target_space` draws,
no report. It records both layers per draw (`:38-43`) and writes `<results-dir>/motion_probe/
<id>.jsonl` plus a manifest (`:451-452`).

### 2.2 The batch path makes the motion call for every paper; no paper takes the multi-acquisition path

- `batch.py:30` imports `extract` from the extractor; `process_paper` (`:212-262`) runs
  `load_pdf_text` → `find_methods_section` (`:253`) → `ParsedPaper` → `extract` (`:261`) → report.
  `extract` is `extract_preprocessing` (`extractor.py:1493-1529`), which makes the motion call first,
  on the same `ParsedPaper` (`:1514`), then the shared call, and assembles the motion step into the
  `Preprocessing` (`:1490`). **Every paper on this path gets the motion call.**
- The per-acquisition path (`extract_preprocessing_for_acquisition`, `:1532`) "reuses the shared
  prompt and so gets no motion call — a cost ruling A records" (`:1506-1509`). It is reached only by
  `multi_acquisition_batch.py`, a separate driver with its own config and output
  (`results/batch_multi_acq/`: cho, greene, marek, weber, yang — a different corpus). **The 19-paper
  batch has never been run through it.**
- `likely_multi_acquisition` (`batch.py:41`, `:127-128`: two or more of five dataset names in the
  slice) is a **flag, not a route**: it lands in the JSON and `summary.csv` and changes nothing
  about which extractor runs. In the stored acceptance run, **one of the sixteen** contaminated
  papers carries it (weber_2024), and **0 of the held-out three** (a count, from the flag only).
- **Where a new run writes.** `BatchConfig.output_dir` (`batch_config.py:23`, default
  `results/batch`); `run_batch` writes `<output_dir>/papers/<id>.json` and `.md`, `summary.csv`,
  `summary.md` (`batch.py:363-400`). A new run is a new config with a new `output_dir`. The
  acceptance run's `output_dir` is `results/batch_a1_acceptance` (its config, line 2); a new config
  must not name it. `results/.gitignore` is `*`: nothing under `results/` is tracked, so an
  overwrite there leaves no diff (`rerender_reports.py:21-23`).
- **The identity gate reads only the directory it is given.** `rerender_reports.py` takes
  `--results-dir` (required, `:323-328`) and `--against` (default `HEAD`, `:329`), reads
  `<results-dir>/papers/*.json`, renders under both refs, and never writes into `papers/`
  (`:21-23`). The standing invocation passes `batch_a1_acceptance` (DEVLOG `:3080-3082`;
  `DESIGN_motion_correction_extraction.md` §3f `:361-394`). A run into another directory is
  invisible to the gate unless someone passes that directory.
- The stored acceptance run is from 2026-09-07 (DEVLOG `:1299-1316`), 19 `.json` + 19 `.md`, all
  `status: success` on the sixteen (a count; the three not read), model
  `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0` — the same model string the recorder pins
  (`motion_probe.py:79`). **No stored JSON anywhere carries a `motion_correction` step** (DEVLOG
  `:3080`; §3f). So the batch run would be the first motion data on the nine non-probe papers in
  any form, and the first *report* carrying a live motion row for any paper. The row is live:
  `cobidas.py:59` defines it, `:161-167` classes the two motion post-check reasons, and
  `render.py:497-501`, `:554-560` word them.

### 2.3 liu_2005's de-interleaved slice is used by two scripts, neither on the run paths

- `ground_truth/liu_2005_deinterleaved_methods.txt` is tracked. It is read by
  `scripts/run_pending_target_space.py` (`:6`, `:31`, `:80-81`: the slice is fed directly as the
  paper text, bypassing `find_methods_section`, for the target_space pending run) and by
  `scripts/glyph_leak_prediction.py` (`:46`, `_TEXT_OVERRIDE`).
- `batch.process_paper` and `motion_probe._paper` contain no override (grep over `batch.py`,
  `batch_config.py`, `batch_utils.py`, `methods_finder.py`, `pdf_loader.py`,
  `multi_acquisition_batch.py`: no match). Both slice the PDF's own text with
  `find_methods_section`.
- **The motion call receives exactly the slice the main call receives**: `extract_preprocessing`
  passes one `ParsedPaper` to both (`extractor.py:1514`, `:1517-1523`), and the recorder builds the
  same `ParsedPaper` the batch would (`motion_probe.py:224`). On both run paths that is the
  interleaved slice, not the de-interleaved one. Whether that slice is adequate for liu_2005 is a
  property of its stored acceptance result and of its text, neither of which was read; it is a
  fork (§7, fork 7), not a fact.

### 2.4 The scoring map: what exists, what is undefined

**Exists**, in prose, in the prereg; no CSV (there is a `target_space_scoring_map.csv`, no motion
one) and no code (no `score` function touches motion).

- **State map** (prereg `:68-75`): row 1 `extracted` + `operation_phrase` → `described_only`; row 2
  `extracted` + `tool_name` → `named_tool`; row 3 `extracted` + `undecided` → halt, adjudicate, count;
  row 4 `deferred` with target `paper`/`pipeline`/`dataset_doc` → `deferred`; row 5 `deferred` to
  `supplement` → `unread`; row 6 `missing` → `absent`. `value_kind` is the frozen heuristic on the raw
  `value` (`:66`, `:92-104`; `scripts/motion_value_kind.py`), computed from the raw layer (Amendment 2
  ruling 2).
- **Correctness rule** (`:125-136`): a cell is correct only when (1) predicted state == label state;
  (2) for `named_tool`, `value` matches `method_value` "by tool identity, not string identity — SPM12
  vs SPM 12 is a match; FSL vs MCFLIRT is not"; (3) `span_role == estimate`. `unread`, `undecided` and
  `multi_target_unscoreable` are excluded from both numerator and denominator and reported as named
  lines.
- **The model's own binding** (`motion_correction_binding`, Amendment 7, option (c)) is recorded and
  compared with the heuristic; disagreements are counted. The *scored* state is the heuristic's row;
  the binding is a reported comparison, not a second scorer.

**Undefined when first written; each ruled in §2.4a the same night. The table is kept as the record
of what was open:**

| state | model state | value | what is undefined |
|---|---|---|---|
| `named_tool` | row 2 | equality with `method_value` by "tool identity" | **which aliases.** The prereg gives one example pair and names no table. `motion_correction.method` has **no synonym table** (`synonym_resolver.py:276-280`; `SYNONYMS_BY_FIELD` holds `convention`, `surface_registration`, `target_space`, `target_surface` only) and resolves by **exact, case-sensitive Literal membership** (`extractor.py:550-552`; `:1371-1375` opts out of the bare-id lookup; Literal `mcflirt, spm_realign, afni_3dvolreg, ants, other`, `preprocessing.py:686`). So `resolved` is `None` and `resolution="unrecognized"` for every tool the model names in the paper's spelling — `MCFLIRT`, `AFNI`, `SPM8`, `SPM12` all included — and **the only layer that carries tool identity is the raw `value` (= `verbatim`).** Also undefined: **version** (is SPM8 a match for a label of SPM12? the example is same-version) and **program-within-suite** (is `3dvolreg` a match for a label of `AFNI`?). The four contaminated `named_tool` labels are MCFLIRT, AFNI, SPM8, SPM12, so three of four hit this gap. |
| `described_only` | row 1 | none (state only) | the span clause (3) applies: no code assigns `span_role`, the workbook has no `span_role` column (its columns are `method_state`, `method_value`, `method_quote`, then the bullet 2–7 pairs, `notes`), so the only mechanism is a comparison of the draw's span with the label's `method_quote` — unbuilt, and for a held-out paper runnable only by script that prints a state. |
| `deferred` | row 4 | — | **state only, or target too.** Rule (1) is state-only; Amendments 8–9 read targets ("to ref 45", "C-PAC", target kind) but the correctness rule has no target clause. The stored `deferral_ref` and target kind exist per draw, so either rule is computable. |
| routed / unsupported (processed layer `missing` with a motion reason) | raw row 1 or 2 | — | **which layer scores.** The row is computed from the raw layer; the report shows the processed layer (`not_covered`, `render.py:500-501`). derosa's routed `ICA-AROMA` is raw row 2 against a `described_only` label — reading 2's error class (`:149-152`) — while the processed layer declined it, which is the behaviour the check was built for. agtzidis's unresolved quote is raw row 1 (a match) and processed `missing`. The prereg scores the raw row; the report shows the other. |
| `absent` / `stated_not_performed` | row 6 / none | — | **not exercised**: no label in the corpus (§2.6), so every `missing` from the model is a mismatch by construction, never a correct absence. |

### 2.4a Scoring rulings — ruled by the author, 2026-10-26, recorded before any value is seen

Each open line of the table above is ruled as follows, dated, so that no scoring rule is written
after the model's values are seen.

1. **`named_tool`: value = normalized exact equality with the label's `method_value`.** A state
   match with a value mismatch is **its own named line, described in words, never a match.** **No
   tool table at scoring time** — which spelling names which tool is a knowledge-base fact, not a
   scoring rule. *Normalization, proposed here for ratification and not ruled:* case-fold and strip
   internal whitespace and hyphens, which makes the prereg's one example pair (`:130-131`) equal and
   nothing else.
2. **`deferred` and `described_only` match on state only**, with the deferral target **reported, not
   scored.**
3. **`span_role` is reported for ciric only**, where the mention table exists; for every other paper
   the clause is not evaluated, and the results document says so.
4. **Layers.** The recorder scores the raw layer, as the probe did; the batch reports the processed
   layer; **the count of draws the check demoted or routed is its own line.**
5. **Every `missing` is a mismatch by construction** (§2.6).
6. **liu_2005's interleaved text layer is named beside its result** as a possible cause the stanza
   does not own (§2.3), whatever the result is.

**Ratified 2026-10-26 (late night), by the author: all seven decisions of the version-6 build, with
two adjustments, both applied before the commit.** (a) The `named_tool` value is the **package name
token as written** (SPM12, SPM8, AFNI, FSL); a version written separately is recorded in the quote,
not in the value, or normalized equality would fail on a separately written version — protocol
v1.8, the stanza's STEP 5 and Amendment 10 say so. (b) The matcher tolerates a **letter-ending value
followed by a digit run in the quote**, under-claim only (`DELTA_value_in_quote_motion.md` §4 ruling
5): the text layer attaches citation numbers to words, and a demoted cole report would have been
wrong; the replay over all 550 recorded motion draws and the step-field replay move nothing. Also
ruled: **clause 1 of Amendment 10's adoption rule covers every `named_tool` paper**, gordon and ciric
included, neither of which has a clause-2 count; **binder and power are `described_only`, confirmed
from their text** (power names no listed package; binder names MCW-AFNI once for a different step),
with a package-level return on either pre-declared as an over-reach; and the five list entries stand.

### 2.5 Contamination classes, derived from the record

| class | source | members | n |
|---|---|---|---|
| co-adjudicated | protocol §7 `:736-742`, re-derived from the workbook's Notes flags (v1.7.1); the flag reads `co-adjudicated` on 13 rows and `Co-adjudicated` on liu_2013's (checked by substring, case-insensitive) | agtzidis_2020, binder_1999, braun_2015, chen_2015, ciric_2017, derosa_2025, liu_2013, mueller_2021, oconnor_2017, poldrack_2015, power_2014, vanderwal_2016, viduarre_2017, weber_2024 | 14 |
| CALL 10 derivation set | protocol `:598-636` worked cases, ids only | agtzidis_2020, chen_2015, ciric_2017, cole_2013, gordon_2014, liu_2013, poldrack_2015 | 7 |
| overlap of the two | `:643-647` | agtzidis, chen, ciric, liu_2013, poldrack | 5 |
| **union** | 14 + 7 − 5 | the 14 plus cole_2013 and gordon_2014 | **16 of 19** |
| probe set, fitted | `motion_probe.py:85-122`, prereg Amendments 4 and 8 | power, binder, liu_2013, derosa, agtzidis, poldrack, ciric, braun, viduarre, vanderwal — all ten inside the 14 | 10 |
| clean on both axes | `:644-646` | liu_2005, tang_2025, wheaton_2004 — with the protocol's own qualifier that tang_2025 was label-adjudicated in the session that produced CALL 10 | 3 |

**The reporting partition** (§4) is therefore: probe ten · co-adjudicated, not probed (chen,
mueller, oconnor, weber) · CALL 10 only (cole, gordon) · clean three. 10 + 4 + 2 + 3 = 19.

### 2.6 Label states: none is `absent` or `stated_not_performed`

From the `Labels` sheet, `method_state` by id (all 19; the held-out three by state only):
`deferred` 8 (braun, chen, liu_2013, oconnor, poldrack, vanderwal, viduarre, weber),
`named_tool` 7 (ciric, cole, gordon, mueller, liu_2005, tang_2025, wheaton_2004),
`described_only` 4 (agtzidis, binder, derosa, power). 8 + 7 + 4 = 19; `absent` 0,
`stated_not_performed` 0. The sheet's one extra row is an instruction banner with no id.

**Consequence the author asked to be stated:** the stanza's STEP 1 limitation — a kept-nothing case
goes to the wholesale deferral branch, and `stated_not_performed` has no extractor state (prereg
`:77-80`) — **costs nothing on this corpus.** No cell can be correctly `missing`; every `missing` the
run produces is an extraction outcome to count, not a vocabulary gap to excuse.

## 3. The two runs — a fork for the author

| | **R — the recorder, K=10 over 19** | **B — the batch, one draw over 19** |
|---|---|---|
| what runs | `motion_probe.py`: the motion call only, ten draws per paper, both layers recorded, manifest gated on the frozen hash | `batch.py` with a new config: the motion call then the shared call, per paper, once; `_assemble`, the cobidas row and the report |
| calls | 190 draws + reasks (the A/B's arms ran 100 draws in 13:43 and 11:52, so roughly 25 minutes) | 38 calls + reasks; the acceptance run's duration is not recorded |
| output | `<new>/motion_probe/<id>.jsonl` + manifest; a projection (status, row, offsets, target kind, binding; no text) | `<new>/papers/<id>.json` with the motion step, `<id>.md` with the live motion row, `summary.csv`/`.md` |
| what it supports | the **distribution** per paper — the diagnostic the probe runs produced, now on 19; stability of each cell at K=10; the state-map rows and named lines of §4; the reading of every pre-declared cost in §5 | **the reports the poster shows** — the first rendered motion row on real papers; the JSON a future stability runner compares against |
| what it cannot support | no report, no cobidas row, no exercise of `_assemble` or `render` on a live motion step | a single draw per paper is a sample reported as a value (`DESIGN_kdraw_stability.md` §6, `:495`, `:513`; Ruling E `:539-551`): no stability claim, and a cell that differs from its label on one draw is one draw |
| side effects | none on the stored acceptance run; nine new papers' text goes to the model, three of them for the first and only time | every other field re-extracted under the current code: a new vintage for all of them, which this design does not report |
| prerequisites | the licensing amendment, which sets `_CORPUS_RUN_LICENCE` (§7, fork 1; the guard is built and default-closed); the table and `_ORDER`, extended 2026-10-26; the needle check scripted from the records, not hand-listed; **§5.0's label checks** | the config, written 2026-10-26 and not run: `configs/batch_motion_corpus_v1_config.yaml`, an exact mirror of the acceptance config with `output_dir` `results/batch_motion_corpus_v1`; nothing else in code; **§5.0's label checks** |

**Both, R first, then B**, is the recommendation. R is the instrument every earlier number came
from, so its 19-paper distribution is comparable in kind to the probe runs and carries the held-out
three as states and counts in the format already built for that. B then produces the deliverable,
and each paper's one batch draw is read **against its own R distribution** — inside the set of
states R produced for that paper, or outside it — which turns a single draw into a count with a
denominator of one and a reference. Running B alone would put the three clean cells' only
measurement on one draw each; running R alone leaves the poster without a report. The author's
estimate of about 25 minutes for R is consistent with the A/B's pace.

**Ordering constraint.** B's one draw per paper is made *after* R's ten are stored, which means the
same paper's text has been sent eleven times by the end; nothing in either run reads the other's
output while running, so no result conditions on another, but the two are one session for the
day-effect reason recorded in `motion-probe-ab-stanza-vs-day.md`: back to back, same day, in that order.

## 4. Reporting rule

1. **Every table names its vintage and the stanza hash:** run name, date, model, K, and
   `b0093774…` in the header; the projection's header carries the same and
   `motion_method_prompt_frozen_sha256` from the manifest (`motion_probe.py:311`).
2. **Rows are papers, grouped by the partition of §2.5**, in this order: probe ten; co-adjudicated,
   not probed; CALL 10 only; **the clean three on their own line**, with tang_2025's qualifier in the
   same sentence as the line.
3. **Per paper, from R:** the label state; the state-map row per draw as counts (`row 1 ×n …`); the
   model's binding against the heuristic (agree / disagree / undecided counts); the processed-layer
   outcome per draw (Extracted / Deferred / Missing with its reason) as counts; and **match**: the
   number of draws whose row equals the label state, with the value clause for `named_tool` applied
   under §2.4a ruling 1 (a state match with a value mismatch is its own named line, in words), the
   span clause evaluated for ciric only (ruling 3), and the count of draws the check demoted or
   routed as its own line (ruling 4). **For the held-out three the row reads: label state, matching draws of 10, and
   nothing else** — no value, no offset, no target, no reason string, no binding detail; those live
   in the projection and the records, written by script, transcribed by nobody.
4. **Per paper, from B:** the one draw's row and processed outcome, and whether that state is inside
   the paper's R set. For the held-out three: inside / outside, nothing else.
5. **Counts only.** Each line reports *n of the line's n* (e.g. "clean three: 2 of 3 match on all
   ten draws"); **no line reports anything "of 19"**, and no fraction, rate, percentage or interval
   appears in the document or the projection. The excluded classes — `undecided` (row 3), `unread`
   (row 5), `multi_target_unscoreable` — are named lines with counts, never folded.
6. **Named lines for the run:** draws, reasks, errors, unresolved spans, routed, unsupported,
   `missing`, by paper where the paper is contaminated and as totals for the held-out line.
7. **The projection is emitted by the script for all 19 rows in its existing format** (offsets
   included, as for every prior row; without the corpus an offset recovers nothing). The needle
   check is scripted: every raw `value`, `verbatim_quote`, `ref_string` and deferral sentence in the
   records is asserted absent from the CSV, and the script prints counts only.

## 5. Pre-declared readings, written before any run

Readings are the label and the record. "Match" means the state-map row equals the label state
(and, for `named_tool`, the value clause under fork 2). The same-day A/B's version-4 arm
(`motion_probe_ab_2026-10-26_b009_projection.csv`) and the version-4 run
(`motion_probe_v4_projection.csv`) are the reference for the ten; the six never-run contaminated
papers have labels and no record.

### 5.0 Precondition — two label checks before any run (the author, 2026-10-26)

A rule or a label written after the model's values are seen is not pre-registered, so both checks
precede the first call. **If any label changes, the reading below is re-declared for that paper
before the run, and §2.6's counts are restated.** No paper sentence is reproduced in this section.

1. **cole_2013, gordon_2014, mueller_2021 against CALL 1 v1.6, then CALL 11.** Flagged on
   2026-10-22 and never checked; the author's check, from the sentences the author has identified.
   The candidate states as the author listed them — **cole:** two packages named for the
   preprocessing as a whole, the step listed in the paper's voice under a citation to a standard,
   none of the four details; v1.6 leaves the package unbound (the agtzidis shape with two packages),
   and CALL 11 then reads `deferred` to the cited standard, or `described_only` if the paper's voice
   is read as its own assertion with the citation as comparison; a relabel supersedes CALL 10's cole
   row. **gordon:** the package is the instrument of the realignment sentence itself, not of "the
   analysis"; if that binds, `named_tool` SPM8 stands, and if not, `described_only`, since the
   reference image is stated; not `deferred` either way. **mueller:** the agtzidis shape exactly —
   package for the procedure set, step in the paper's voice, none of the four details, so
   `described_only` under v1.6; the workbook note's reading binds SPM12 through tool vocabulary,
   which the protocol keeps off labels; and an earlier sentence defers the preprocessing to a prior
   paper with a brief reproduction, which CALL 11 reads as `deferred` unless the reproduction carries
   a detail. Three candidate states; the author's.
> **Status, 2026-10-26 (late night).** Check 1 is settled by protocol v1.8's worked cases, and the
> workbook is done by the author: sha256 `894c3bf523a38f5076bb250465629eb63ee38489687f478218145d37c9afbabe`,
> 22,355 bytes, verified in the working tree; a new column R `attribution` (step / package), 17 cells
> changed (agtzidis back to `named_tool` SPM12 `package`; derosa `named_tool` FSL `package`; cole
> `package`; gordon `step`; mueller `package`; ciric `step`; dated notes on all six; `co-adjudicated`
> flags on cole and gordon). States now read `named_tool` 9, `deferred` 8, `described_only` 2. The
> held-out three's rows are untouched and their R cells are **pending the author** (0 of 3 filled, a
> count). Committed alone after the protocol commit. Check 2 stands.

2. **The held-out three, by the author alone.** All three carry `named_tool` and need the same v1.6
   check. Nothing in this repository proposes a reading for them: anything proposed here would
   contaminate them. tang_2025's sentences are already quoted in the protocol's v1.4 amendment, so
   that check needs no PDF; this document does not cite the passage.

If a label changes, the workbook note says it was a **protocol-consistency relabel by the author
alone, before the run**, and §5.2 or §5.3 is re-declared for that paper.

### 5.1 The ten probe papers (fitted; the frozen stanza was iterated on them)

| paper | label | reading under `b0093774…` | the known cost, carried |
|---|---|---|---|
| power_2014 | `described_only` | row 1 ×10 at 3112–3528 | — |
| binder_1999 | `described_only` | row 1 on most draws, **row 3 (`undecided`) on some**, all at 11023–11180; model binding `described_only` on all extracted draws | **unclassable by the heuristic on part of its draws** (4 of 10 on 2026-10-26's arm; 0 to 4 across runs): those draws are excluded by name, not matched or mismatched. An `AFNI` draw is a check failure, demoted and counted. |
| liu_2013 | `deferred` | row 4 (target kind `pipeline`) on **between 5 and 10 of 10**; the rest row 1 on the operation sentence 3344–3658 | **below 10 is the frozen version's recorded cost** (7, then 5, on two days). Fewer than 5 deferred is a new finding, reported as found. |
| derosa_2025 | `described_only` | raw row 2 (`ICA-AROMA`, binding `named_tool`) ×10; processed layer routed ×10 | the row is a mismatch under reading 2's error class and the processed layer declined it: both reported; which scores is fork 5 |
| agtzidis_2020 | `described_only` | raw row 1 ×10; spans unresolved ×10 (the recorded `/C2` exclusion); processed layer `missing` | a `SPM12` draw is a check failure; which layer scores is fork 6 |
| poldrack_2015 | `deferred` | **row 1 ×10** at 25523–25671 | **unreached under the frozen stanza** (0 of 10 on both days). Any `deferred` draw is a new finding, reported, and changes nothing about the freeze. |
| ciric_2017 | `named_tool` / MCFLIRT | row 2 ×10, value `MCFLIRT`, span 4410–4507 (the ESTIMATE clause); `resolved` is `None` because the member is `mcflirt` | post hoc, said in the same sentence as any count |
| braun_2015 | `deferred` | row 4 ×10, target kind `paper` | — |
| viduarre_2017 | `deferred` | row 4 ×10, target one of the two pre-declared citations (split 6/4 on one arm); no value returned | — |
| vanderwal_2016 | `deferred` | row 4 ×10, target kind `pipeline`; the `ANTs` host-sentence risk has not occurred in 20 draws and remains the risk | — |

### 5.2 The six contaminated papers never run under the motion call

| paper | class | label | reading | risk, by the record's rules |
|---|---|---|---|---|
| chen_2015 | co-adjudicated, CALL 10 | `deferred`, value `CCS` | row 4, target kind `pipeline` | `CCS` returned as a tool (row 2): it is tool-shaped for the heuristic, and CALL 1 v1.1 rules a pipeline wrapping an unnamed tool `deferred` — a row-2 draw is the mismatch class to name |
| mueller_2021 | co-adjudicated | `named_tool`, value `SPM12` — **pending §5.0** | row 2, value naming SPM12 | a value naming only `SPM` or a version other than 12 — the alias/version gap (fork 2); routed if the model names a structured-noise tool instead |
| oconnor_2017 | co-adjudicated | `deferred`, value `CPAC` | row 4, target kind `pipeline` | as vanderwal: a host-sentence tool named beside the pipeline |
| weber_2024 | co-adjudicated | `deferred`, value `CPAC` | row 4, target kind `pipeline` | the one paper flagged `likely_multi_acquisition`; the flag does not route, so the reading is the same; a slice that spans two datasets' pipelines is the thing to look for in the target |
| cole_2013 | CALL 10 only | `named_tool`, value `AFNI` — **pending §5.0** | row 2, value naming AFNI or its program | `3dvolreg` against a label of `AFNI` is the program-within-suite gap (fork 2); `resolved` will be `None` either way |
| gordon_2014 | CALL 10 only | `named_tool`, value `SPM8` — **pending §5.0** | row 2, value naming SPM8 | version gap (fork 2) |

### 5.3 The clean three — read from the workbook by id only

All three carry the label state **`named_tool`**. The pre-declared reading for each is **"matches
its label"**: row 2 on every draw with a value equal to the workbook's `method_value` under fork 2's
rule, evaluated by script, reported as matching draws of 10 and nothing else. Anything other than
that is reported as the row and the count it is, by paper id, with no value, offset or text. Two
pre-declared conditions on the reading, written now because they are properties of the path, not
of the papers:

- **A `missing` draw on any of the three is a mismatch**, by §2.6; if its reason is
  `extraction_quote_unresolved` on liu_2005, that is recorded as the slice question (fork 7) and
  not re-run under this design.
- **No held-out paper takes the multi-acquisition path** (the flag is 0 of 3, and the flag does not
  route), so every one of the three receives the motion call in both R and B.
- **liu_2005's interleaved text layer is named beside its result** (§2.4a ruling 6), whatever the
  result is; it is a possible cause the stanza does not own, and naming it is not a re-run.
- **The labels themselves are checked first** (§5.0.2), by the author alone.

### 5.4 The gate, derived before the run (§6 item 1 of the design doc)

Nothing in R or B changes code, and neither writes under `batch_a1_acceptance`. So, after the run:
`rerender_reports.py --results-dir extractor_mvp/results/batch_a1_acceptance --against HEAD` →
**19 identical, 0 changed**, read from stdout (exit code is 0 either way, `:252`); the negative
control `--against d31e8b7` → **0 identical, 19 changed**, the value derived and observed on
2026-10-26 (DEVLOG `:3080-3082`; `rerender_reports.py:38` records the older 16/3 at a 2026-10-01
HEAD, superseded). A failed `PYTHONPATH` override also yields 19 identical (`:31-36`), so the
control is run, not optional. Any other pair means code moved between the freeze and the run, and
the run is read against that commit, not against the freeze.

## 6. What the results document must carry

The vintage and hash in every table (§4.1); the partition with the clean three's own line and
tang_2025's qualifier (§4.2); the diagnostic-not-evaluative label and the contamination union with
its arithmetic (16 = 14 + 7 − 5), per `DESIGN_motion_correction_extraction.md` §6.3; the three
excluded classes as named lines (§6.7); the named lines of §2.4a — value mismatches in words, the
demoted-or-routed count, ciric's `span_role`; the §2.6 statement that no cell can be correctly `missing`;
the frozen version's costs as costs, not findings (§5.1); and, for the held-out three, states and
counts only. No rate. No draw of theirs is ever pooled with the sixteen's in any number.

## 7. Open forks — not settled here

1. **Built 2026-10-26, default-closed; the amendment still decides.** *Admitting the held-out three through the recorder.* The guard at `motion_probe.py:125`,
   `:356-366` refuses them unconditionally. Proposed mechanism, to be ruled and then amended: a
   `--corpus-run <amendment-id>` flag whose value must equal a constant naming the amendment that
   licenses the run, accepted only when the live hash equals `_FROZEN_STANZA_SHA256` (already
   enforced), with the refusal otherwise unchanged and tested. The amendment states that the three
   cells are spent on that run and that no second recorder run on them follows without a further
   amendment.
2. **RULED 2026-10-26 (§2.4a, ruling 1).** *The `named_tool` value rule.* Which layer (raw `value`, since `resolved` is `None` for every
   paper-spelled tool), which aliases (none exist for this field), whether version differs
   (SPM8 ≠ SPM12?) and whether a program names its suite (`3dvolreg` = `AFNI`?). Three of the four
   contaminated `named_tool` labels sit in this gap; the three clean ones may. A rule written after
   seeing the clean three's values is not pre-registered, so this is ruled before R.
3. **RULED (§2.4a, ruling 2: state only, target reported).** *`deferred`: state only, or target too.* Both are computable from the records.
4. **RULED (§2.4a, ruling 3: ciric only).** *`span_role`.* Unbuilt; no label column. Either built as a quote-overlap check against
   `method_quote` (for the held-out three, run by script, printing a state) or declared *not
   evaluated* for this run, with the correctness rule's clause (3) recorded as unmet.
5. **RULED (§2.4a, ruling 4).** *Which layer scores a routed or unsupported draw* (derosa): the raw row (mismatch, reading 2) or
   the processed decline.
6. **RULED (§2.4a, ruling 4).** *Which layer scores an unresolved quote* (agtzidis): raw row 1 or processed `missing`.
7. **Partly ruled (§2.4a, ruling 6: the layer is named beside the result); the path choice stays open.** *liu_2005's slice.* Standard path for all 19 (recommended: one path, no paper-specific
   intervention on a held-out cell) versus the de-interleaved slice the target_space pending run fed
   directly. If the standard path yields `missing` with an unresolved quote on liu_2005, a second,
   pre-declared run on that slice is a new amendment, after the first result is on record as what it is.
8. **Ruling E.** Scores wait on stability. R at K=10 is the stability measurement for this field; B's
   reports are not scores; the per-paper match table of §4.3 is a count by class and not a rate. Whether
   that table is a "score" in Ruling E's sense is the author's call, and it decides whether §4.3's
   match column appears in the first results document or waits.
9. **Done 2026-10-26.** *Names and model.* The vintage is `motion_corpus_v1`: config
   `configs/batch_motion_corpus_v1_config.yaml` (an exact mirror of the acceptance config, only
   `output_dir` differs: `results/batch_motion_corpus_v1`), written and not run; recorder
   `--results-dir …/results/motion_probe_corpus_v1`; model as pinned on both paths
   (`claude-sonnet-4-5-20250929-v1:0`, `temperature=0.0`, `max_retries=2`); K=10.
10. **B's other fields.** A batch run re-vintages every field. This design reports none of them;
    whether any of them is ever read from this run is a separate decision, and the results document
    says they exist and were not read.
11. **Corrected and done 2026-10-26** (§2.1's erratum). *The projection's `_ORDER`* lists all 19 in
    the partition's order; a manifest paper or a record file outside it is refused, never dropped.
12. **The licensing amendment**, still to be written by the author: the three cells are spent on one
    run; `_CORPUS_RUN_LICENCE` is set to the amendment's id in the same commit; no second recorder
    run on them without a further amendment; the run follows §5.0.

First staged 2026-10-26 with everything unbuilt. The same night, after the author's rulings: the
table, the guard, the projection order and the config were built and tested (forks 1, 9, 11), and
forks 2–6 were ruled (§2.4a). The run waits on §5.0 and on the licensing amendment (fork 12).

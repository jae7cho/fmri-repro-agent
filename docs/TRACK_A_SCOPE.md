# Track A — build scope: wiring the COBIDAS completeness checker

**Scoped 2026-08-26.** Target date **2026-10-31** (SfN poster 2026-11-14, less two weeks for printing
and slack). Open-source academic tool; no rendering, figures, or poster design in scope — see
**Deferred** at the end, which is the list to consult before starting anything not named here.

**Framing.** Track A wires an existing capability; it does not build a new one.
`render.to_cobidas_coverage` (render.py:607) over the 16-row D.3 registry (cobidas.py:50) already emits
the completeness report. Its only callers are `tests/`. Track A is plumbing, one bug, and one guard.

**Track B (the motion extraction arc, the reachability probe, scoring) is unchanged and is NOT on this
critical path.** 15 of 19 spec steps having no extractor does not block this deliverable, because
`to_cobidas_coverage` takes its denominator from the standard rather than from the steps present, and
renders an unextracted step as *"no fields assessed by current extractor"* — a true and useful statement.
Each field Track B later extracts upgrades one row from not-assessed to assessed.

## Status, updated 2026-09-07

- **A2 landed** (`d90507b`). `to_report` is the only sanctioned report surface, the coverage
  section is pinned by a surface-parametrized test over `REPORT_SURFACES` (`render.py:725`),
  and the two field views are documented as partial.
- **A3 landed** (`c9c2951`). The Software header and body now share one coverage condition
  (`render.py:793`). The bug described below is fixed; that section is retained as the record
  of what was wrong.
- **A1 code landed** (`214b55c`). `run_batch` writes `papers/{paper_id}.md` (`batch.py:323`).
  Its acceptance criterion, 19 rendered reports with `render_error` empty on every row, was met
  by the corpus run of 2026-09-07.
- A4 and A5 are open. A5's design must also settle whether `_tally` (`batch.py:99`) should
  count `base_pipeline`: its docstring says it buckets the targeted fields, `base_pipeline` is
  targeted (`cobidas.py:161-162`), and it iterates `preprocessing.steps` only (`batch.py:111`),
  so `n_deferred` reads 0 corpus-wide while two papers defer their base pipeline.

Source line numbers throughout this document were accurate when it was scoped on 2026-08-26.
Several have since moved. Verify at HEAD before relying on any of them.

---

## A2 — make the coverage-section guard STRUCTURAL (do this first)

**Why first.** The safety property that makes this tool honest is currently held by a single line:
`render.py:602`, which staples `to_cobidas_coverage` onto `to_protocol`. `to_text` (render.py:350) and
`to_bullets` (render.py:379) iterate **present steps only**, so on their own they omit motion entirely and
print `Completeness: 8 not reported in source · 19 not covered by extractor` — a header in which a step
that was never examined is invisible. A2 must land **before A1**, because A1 creates the first non-test
caller and the convention has no defence against a second one.

> **Correction, 2026-09-07.** `to_text` and `to_bullets` were renamed to `to_field_table`
> (`render.py:357`) and `to_field_bullets` (`render.py:412`) in `d90507b`. Neither emits a
> `Completeness:` line. That header is emitted only by `to_protocol` (`render.py:677`), so the
> illustration above describes no surface at HEAD. The safety property is also no longer held
> by a single line: `REPORT_SURFACES` (`render.py:725`) makes it structural, which is what A2
> delivered.

**Done when:** a field-rendering view either carries the catalog-driven coverage section or cannot be
called in a report context — enforced by structure, not by comment. A test asserts that a report produced
without the coverage section fails rather than renders.

**Do not change:** `to_cobidas_coverage`'s static-registry denominator (cobidas.py:154), or the behaviour
pinned by `test_never_emitted_kind_row_is_not_covered` (`covered_by_extractor is False` for a
never-emitted kind). That is the property being protected. **Corrected 2026-09-07:** this
originally cited `tests/test_cobidas.py:115`, which now falls inside
`test_software_coverage_over_every_base_pipeline_state`, a different test. The denominator
itself is `COBIDAS_D3_ROWS` (`cobidas.py:50`), pinned by
`test_registry_denominator_is_static_not_steps_present`.

**Size:** small. Structural, not algorithmic.

---

## A1 — wire `render` into `batch.py`

**Why.** `render.py`'s only importers are `tests/`. `batch.py` already holds a live `Preprocessing`
(batch.py:213) and already writes per-paper files (batch.py:279). This is one import, one call, one write.
It is the single highest-value change in Track A: it converts the existing corpus run into per-paper
completeness reports with no new logic.

**Done when:** `run_batch` writes a rendered report per paper alongside `papers/{paper_id}.json`, and a
corpus run over the existing PDFs produces 19 reports.

**Size:** small.

---

## A3 — fix the Software header/body disagreement

**The bug.** When `base_pipeline` is itself missing or deferred, there is no `base_pipeline.version` row,
so `assess_coverage` receives `None` and places `software` in *not-assessed*
(`covered = version_extraction_status is not None`, cobidas.py:157). The `"(incl. Software — unconditional
violation)"` suffix gates on `mand_not_reported` (render.py:638-642) and therefore does not fire — while
the body section still prints the Software violation, because it gates only on `software.addressed`
(render.py:667). Header tally and body contradict each other. Verified divergent at HEAD.

**Why it matters here:** it is in the report's summary line, so it ships as a visible defect on the one
panel people will read first.

**Done when:** header and body agree in the missing-`base_pipeline` case, with a test pinning it.

**Size:** small. Decide deliberately which of the two readings is correct — that is a semantic call about
whether an unassessable Software row is a violation or an unknown, and it belongs to the author, not to
the fix.

---

## A4 — a PDF → report entry point

**Why.** There is no `[project.scripts]` in either `pyproject.toml`. `demo.py` is text-in by construction
(`--text`, demo.py:56) and never imports `render`. `batch.py` is PDF-in and never imports `render`. Every
link of the chain exists and is already sequenced in `_process_paper` (batch.py:155-215):
`load_pdf_text` → `find_methods_section` → `ParsedPaper` → `extract` → *(new)* `render`.

**Done when:** one command takes a PDF path and writes a completeness report. Not a service, not a web
interface — a command-line entry point.

**Size:** medium. Mostly assembly; `demo.py` is the wrong host.

**Open decision, needs answering before A4 is useful at the poster:** live demonstration versus
pre-generated example reports. A live run needs a laptop, network, API credentials and per-run cost at the
venue, and inherits the latency of a real extraction. Pre-generated reports for a handful of recognisable
papers carry the same explanatory weight with none of that risk. **Recommendation: pre-generated, with the
command shown.** Decide early — it changes whether A4 needs polish or merely needs to work.

---

## A5 — corpus-level COBIDAS table

**Why.** Nothing in `render.py` is cross-paper. `batch.py`'s `SUMMARY_COLUMNS` (batch.py:43-60) carry
extractor-performance counts (`n_extracted`, `n_deferred`, …) and no D.3 content, and `_tally`
(batch.py:100-102) explicitly skips untargeted fields — so the existing corpus table measures the tool,
not the literature. `RowCoverage` (cobidas.py:129) is already the right per-paper unit to aggregate over.

**Status: SHOULD, not MUST.** The poster's cross-paper panels come from the committed target_space and
motion label sets, not from this. A5 makes the *tool* produce a corpus finding; it is not needed to
present one.

**Size:** medium. Aggregation over existing structures, no new logic.

---

## Poster-number hardening (adjacent to Track A, same window)

Two small items that remove a class of embarrassment where the repo and the presented numbers disagree.

- **`score_target_space.py` counts only error classes** (its sole `Counter`, :159). No committed code
  tallies `target_space_state`. The published volumetric distribution — `family_specified 10 / deferred 3 /
  native_volume 2 / study_specific 2 / canonical 1 / absent 1 = 19` — exists **only as inline prose** in
  the protocol and DEVLOG. Add the tally so it regenerates from `target_space_labels_v1.csv`.
- **The scorer writes no file.** It is report-only to stdout (score_target_space.py:1), so every rate in
  `target_space_README.md` was hand-transcribed and nothing checks the prose against a rerun.

**Two traps to encode as assertions while doing this:**
1. Read `target_space_labels_v1.csv` (19 rows), **never** `target_space_labels_v1.xlsx` (21 rows — two
   `(EXAMPLE)` rows duplicate oconnor and mueller, inflating `canonical` to 2 and `study_specific` to 3;
   stripped at derive_target_space_csv.py:56-58).
2. The accuracy figure has **two vintages**: `v040_frozen` gives blind 11/17, and the 0.5.0 re-extraction
   gives 10/17, moved entirely by braun on model non-stationarity. Any emitted rate must name its
   prediction vintage on its face.

---

## Explicitly OUT of scope, with reasons — the list to check before starting anything

**Rendering, figures, panel design, poster layout.** Deferred by decision on 2026-08-26: compute and
commit everything first, render once. Nothing in this document produces a figure.

**A6 — uncertainty machinery (K-draw / self-consistency).** No K-draw, voting, or resampling exists
anywhere; `_CONFIDENCE = 0.8` (extractor.py:74) is a hardcoded MVP placeholder that never reaches output;
temp-0 nondeterminism is documented in `docs/findings/variance.md`. This is the **trust question** and the
first thing an outside user will hit. It is deferred because it is the *same machinery* as Track B's
pre-registered K-draw variance step, and should be built once, for both. If Track A finishes early, this
is the highest-value addition — and measuring stability on **attestation** judgements specifically is the
open empirical question, since attestation may be far more stable than value extraction.

**A7 — sub-fields dropped in rendering.** `Deferral.target_kind`, `Extracted.span_recovered`,
`Extracted.confidence`, `InferredDefault.alternative_inferences`, and every span after `spans[0]`
(render.py:184). The `target_kind` case crosses the frozen provenance boundary — `provenance.Deferral` has
no `"supplement"`, so extractor.py:602 and :726 flatten it before the `Preprocessing` is built.
**Consequence: prereg amendment 1's rule "deferred + supplement ⇒ unread" cannot be rendered today.** Not
poster-blocking; record it as a known limitation.

**The surface completeness distribution.** Does not exist at any stage — no instrument, no labels, no
scoring-map rows, no counts. The protocol ratifies a **two-distribution** deliverable
(target_space protocol :269-276) and only the volumetric axis is built. Building the surface axis is a
labelling effort on the scale of the motion arc, not a computation. **Present the volumetric axis and say
the surface axis is pending** rather than presenting one distribution as the whole finding. The joint
statement (:271-275) depends on it and is deferred with it.

**The motion extraction arc** (build `motion_correction.method`, run the reachability probe, the stanza,
K-draw, scoring). Track B, unchanged, off this critical path.

**The three stale-token defects in the instrument** — Glossary B20 still opens `(v1.4 — …)` while its tail
records v1.5; Labels row 22 legend says `CALLs 1–8` (should be 1–10); CALL 10's body stamp reads
`**Added v1.5.**` with no date where CALLs 6–9 all carry one. Cosmetic, but they are provenance claims in a
versioned instrument. Batch them into one commit whenever the workbook is next touched.

---

## Order and gate

**A2 → A1 → A3 → A4**, then A5 and the hardening items if time allows.

A2 before A1 is the only ordering I would defend as non-negotiable: wiring creates the first non-test
caller of the renderer, and the property that makes the report safe is currently one line of convention.

Standing constraints apply unchanged: Claude Code stages, the author commits; explicit pathspecs, never
`git add -A`; DEVLOG last with real hashes; commits blocked Mon–Fri 09:00–17:00 ET; verify at HEAD before
asserting anything about file contents.

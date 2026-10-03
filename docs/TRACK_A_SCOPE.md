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

> **Correction, 2026-09-12.** A1 (`214b55c`) landed after this was scoped and invalidated the
> central premise. `batch.py` DOES import `render` — `batch.py:34` is
> `from extractor_mvp.render import to_report` — and `_process_paper`, now at `batch.py:163`
> rather than :155-215, already runs the whole chain and writes `papers/{paper_id}.md`
> (`batch.py:323`). The `*(new)*` on `render` above is no longer new.
>
> What survives: there is still no `[project.scripts]` in either `pyproject.toml`, and
> `demo.py` is still text-in (`--text` required, `demo.py:56`) and still never imports
> `render`.
>
> So the remaining gap is not assembly. It is single-PDF ergonomics and an installed entry
> point: `batch.py` reaches the chain only through a `BatchConfig` listing papers.
>
> **Re-estimated: small, not medium.** Measured by building and running it — roughly 30
> non-blank lines plus a `[project.scripts]` table, reusing eight existing functions untouched
> through one call to `_process_paper`. Verified that nothing on the path needs `BatchConfig`,
> the papers list, the citation resolver or the summary writers: the exclusion gate
> (`batch.py:300`), the resolver build (`:292`) and all three writers (`:345-347`) are in
> `run_batch`, outside the per-paper call. What remains is six small gaps — an argv surface
> (`batch.main`'s `--config` is `required=True`, `batch.py:407`), the `.md` write and `mkdir`
> (both in `run_batch`, `batch.py:290-291`, `:322-323`), a `paper_id` default, a model default
> (no such constant exists), and the fact that `_process_paper` is private and the name is
> taken twice in the package (`batch.py:163`, `multi_acquisition_batch.py:94`) — plus three
> judgment calls that are decisions rather than work: exit semantics for a single paper,
> `python -m` versus a console script, and whether `_process_paper` gets promoted.
>
> **Blocked on a packaging defect, which is separate work.** `pypdf` is dev-only
> (`extractor_mvp/pyproject.toml:29`; absent from `dependencies`, `:13-22`), and
> `pdf_loader.py:22-28` imports it inside a `try` that returns `("", "failed")`. An installed
> console script would therefore fail on EVERY PDF with `"pypdf returned no text"`
> (`batch.py:185`), a message that blames the PDF, and `pdf_creation_date` would return `None`,
> silently disabling KB version inference. Move `pypdf` to runtime before A4.

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

> ## RULED 2026-10-01 — the 2026-08-26 deferral is superseded. Text above retained.
>
> **Rendering happens in November, from whatever state exists then.** The 2026-08-26 deferral was
> "compute everything first, render once", which left the start of rendering contingent on a
> computation set never declared finished — so it was standing by default rather than by decision.
> It is now decided: no further condition gates rendering, and November's state is the input.
>
> *Source and date.* Ruled by the author in conversation and written down here on 2026-10-01.
> Deliberately **not backdated** to the conversation: the record's date is the date it became
> checkable, and a ruling nobody can find is not a ruling — which is how this one came to be
> contradicted by `DEVLOG.md:2371` saying the question was "still standing by default". That entry is
> corrected forward rather than edited.
>
> ### The constraint that ships with it: do NOT demo any of the five missing-base papers
>
> Demo reports are regenerated by **replay from stored per-paper JSON**
> (`extractor_mvp/scripts/rerender_reports.py`), and the base_pipeline diagnostic (`2018bd3`) changes
> only what a NEW extraction records. Stored JSONs carry the pre-fix reason, so replay prints the
> pre-fix sentence. Measured at HEAD, replaying all five:
>
> | paper | stored reason | replayed line |
> |---|---|---|
> | binder_1999, cole_2013, liu_2005, **poldrack_2015**, power_2014 | `no_base_pipeline_named` | `Base pipeline: no base pipeline named in source — you must specify` |
>
> For **poldrack_2015** that sentence is **false**. It is the one paper with independent cross-vintage
> evidence of being a quote-drop rather than a genuine absence — `predictions_v040_frozen.csv` has it
> `EXTRACTED` 3/3 as `"Washington University pipeline"`. So a replayed poldrack report puts on the
> poster the exact false statement the base arm was built to remove.
>
> **Two ways out, and they are the only two:** pick demo papers from outside those five, or re-extract
> the ones you want to show. Re-extraction is a paid run and re-extracts `target_space` on a model this
> project has measured as non-stationary, so it is not free — which is why the first option is the
> default and this constraint is recorded before panel selection rather than discovered during it.

**A6 — uncertainty machinery (K-draw / self-consistency).** No K-draw, voting, or resampling exists
anywhere; `_CONFIDENCE = 0.8` (extractor.py:74) is a hardcoded MVP placeholder that never reaches
*rendered* output — it IS on all 601 EXTRACTED arms in the stored per-paper JSON, measured 2026-10-01,
and A7 below correctly lists it as dropped in rendering;
temp-0 nondeterminism is documented in `docs/findings/variance.md`. This is the **trust question** and the
first thing an outside user will hit. It is deferred because it **shares machinery with** Track B's
pre-registered K-draw reachability probe, and should be built once, for both. (Corrected 2026-10-01:
this previously said "the *same machinery* as Track B's pre-registered K-draw **variance step**". The
pre-registration contains no variance step — 0 hits for `stability`, `flip` and `K-draw` against a
control of 4 for `variance` in `variance.md`. What it binds is a K=10 reachability probe with no
accuracy figure, so a stability number reported for motion is an amendment, not an implementation. See
`docs/design/DESIGN_kdraw_stability.md` §1.) If Track A finishes early, this
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

**Tracking the demo reports, and the license question under it.** Deferred 2026-09-12. The 19
per-paper reports live under the `*`-ignored `extractor_mvp/results/`, so the demo artifact has no
tracked home. Tracking them was ruled on the premise that the `.md` are derived summaries while only
the `.json` carry verbatim text. **That premise is false and the ruling is void:** both carry quotes.
Measured over the corpus — `.json` 55 quotes / 1454 words / longest 86 words; `.md` 50 quotes / 574
words / longest 17 words, every fragment hard-capped at 80 characters by `_SPAN_QUOTE_MAX`
(`render.py:118`, truncated `:328-331`, emitted `:338` and `:580-581`). Three papers carry none.

**Re-measured independently 2026-09-14, and it holds — do not re-derive this in October.** A
different method, matching each report's text against every corpus string of 12+ words stored in
`results/*.json`, finds spans in **15 of the 19** reports. That is confirmation by a second route,
not a new number: it counts reference-string MATCHES, and one sentence stored with and without
trailing punctuation matches twice, so its raw total of 58 is an upper bound and NOT a quote count.
The 50 quotes / 574 words / longest 17 above remains the clean measurement. The question is settled
as *the same licence question as the JSONs, in a narrower form* — narrower because of the 80-char
cap, not different in kind. The 2026-09-12 premise that the reports were quote-free is void twice
over now, by two methods.

If the license question is taken up later, **frame it for the reports, not the JSONs** — they are
different questions. The reports raise scholarly quotation of 80-character fragments with attribution
adjacent, which may resolve favourably across the whole corpus; the JSONs raise verbatim sentences,
which probably splits by publication year (the corpus spans 1999-2025, so older papers are likely
all-rights-reserved). A partial track buys a partial guarantee, which is worse than a clearly-scoped
one. Nothing built depends on this: `scripts/rerender_reports.py` regenerates the reports on demand
and the identity gate works on any machine holding the run.

**STANDING CONDITION, not a task: the stored reports are stale.** 16 of 19 under
`extractor_mvp/results/batch_a1_acceptance/papers/` no longer match what HEAD's renderer produces —
`59e732b` moved braun_2015 and viduarre_2017 (a coverage count, not wording) and `f44771a` moved the
other 14. Only derosa_2025, liu_2013 and oconnor_2017 are current. Nothing regenerates them
automatically, so anyone reaching for a demo report before 2026-10-31 gets output the tool no longer
produces. Regeneration is free, deterministic, and makes no model call:

```
extractor_mvp/.venv/bin/python extractor_mvp/scripts/rerender_reports.py \
  --results-dir "$PWD/extractor_mvp/results/batch_a1_acceptance" --emit-to <dir>
```

Regenerate by REPLAY, never by re-running `aespa-report`. Replay is deterministic from stored JSON;
re-extraction is a different code path with model calls, and any nondeterminism would land in the
artifact the identity gate depends on. That the tool is real and that the artifacts are reproducible
are separate claims and the docs keep them apart.

**The published configs carry 313 absolute paths, which makes their commit message's claim too
strong.** `0982b84` tracked them on the grounds that "a config is the input that makes a run
reproducible". With `/Users/cwook/...` on every `path:` and `output_dir:` line — 313 lines across
21 files, now public — they make a run **identifiable, not reproducible**, which is the weaker
claim. Worth fixing before a reader arrives expecting the stronger one.

The fix is cheap and needs no new code: `load_batch_config` already resolves relative `path`,
`output_dir` and `citation_cache_dir` against the config file's own directory
(`batch_config.py:48`, `:52`, `:56-58`), so the paths can simply be relative.

But it buys portability of the CONFIG, not of the RUN. Zero PDFs are tracked — `git ls-files`
finds none — and the corpus lives outside the repository at `../tested_lit/`. A cloner with
relative configs still cannot run one without supplying the papers, so the honest claim even
after the fix is that the configs record which inputs a run used, not that anyone can repeat it.

**The same fact from the test side: five tests can run on exactly one machine.**
`extractor_mvp/tests/test_methods_finder.py:12` is
`_CORPUS = Path("/Users/cwook/Documents/neurorepro/tested_lit/sfn_batch")`, with a `skipif` on
`_CORPUS.exists()`. That those five never run in CI is **fine and is now stated** — the corpus is
not in the repository, on the licensing grounds already ruled on, and `CONTRIBUTING.md` tabulates
CI's `326 passed, 7 skipped, 2 deselected` against this laptop's `331 passed, 2 skipped`. What is
not fine is the hardcoded path: it makes the tests unrunnable by anyone *who holds a corpus*, which
is a different and larger set than "nobody". An environment variable naming the corpus directory,
skipped when unset, fixes it and keeps the CI skip exactly as it is.

Grouped with the config item above because it is one fact seen twice. Absolute paths put state
outside anything a checkout controls, so a `git worktree` isolates nothing from them — which is why
a scratchpad reproduction of CI matched its *collection* output character-for-character and its
*pass counts* wrongly (`2026-10-02` DEVLOG, `252ea37`). **A sandbox is isolated only with respect to
the paths it controls.**

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

# DESIGN — K-draw stability (opt-in)

*A new capability: measure how much the extractor's output moves across repeated draws of the same
paper at a fixed prompt, pin and temperature. **Nothing here is implemented.** Two rulings are
settled (§2); the forks in §4 are open and the rulings are the author's. Drafted 2026-10-01; every
locator verified at HEAD `20f3694`, and every number derived from files on disk with its derivation
shown.*

---

## 1. Scope, and what this is not

**In scope.** A mode that runs the existing extraction path K times over the same input and records
how the per-field results compare across those draws.

**It is NOT a correctness measure.** See §2, ruling 1. Agreement across draws is agreement, not
accuracy; the corpus already contains a field the extractor reports identically on every draw and
gets wrong (`target_space` on viduarre: `MISSING_FROM_PAPER` 3/3, label `deferred`).

**It is NOT the variance step of the motion pre-registration — because that step does not exist.**
This needs stating plainly, because a doc of record says otherwise. `docs/TRACK_A_SCOPE.md:201-202`
describes this work as "the *same machinery* as Track B's **pre-registered K-draw variance step**".
Measured against the pre-registration itself
(`docs/findings/motion-method-reachability-prereg.md`, 162 lines, v1 `ccf8a35` plus the append-only
Amendment 1 `44f285f`, unchanged since):

| pattern | hits in the prereg | positive control |
|---|---|---|
| `stability` | **0** | — |
| `flip` | **0** | — |
| `K-draw` | **0** | — |
| `variance` | 2 | `variance.md` 4 |
| `K=10` | 1 (`:7`) | — |

What the prereg actually binds is a **reachability probe**: `motion_correction.method` only, six named
papers, **K = 10** per paper cited to `variance.md` (`:7`), per-draw recording, an asymmetric
any-single-draw unreachability rule, and no accuracy figure — `:23` and `:160`, "40 clean draws are
evidence *for* reachability and not proof".

So the two share machinery (repeated draws at a fixed pin) and are not the same step. **A stability
number reported for motion would be an amendment to a committed pre-registration, not an
implementation of it**, and must be flagged as one. `TRACK_A_SCOPE.md:201-202` should be corrected to
say "shares machinery with" rather than naming a step the prereg does not contain.

**Also not in scope:** changing the default path (§2, ruling 2), the `_build_version_pf` arm of
`DELTA_base_pipeline_diagnostic.md` §10, and any figure or panel work.

---

## 2. The two rulings, settled

### Ruling 1 — the measured quantity is STABILITY, never "confidence"

The word must not appear for this quantity anywhere in the feature, its output, or its documentation.

**Why, in one paragraph.** Stability is agreement across repeated draws of one unchanged input. It is
a property of the *sampler*, not of the *answer*. A model that is wrong in the same way every time is
maximally stable and entirely incorrect, and this corpus contains that case: viduarre's
`target_space` is `MISSING_FROM_PAPER` on 3 of 3 draws against a `deferred` label. Calling agreement
"confidence" would license exactly the inference the project exists to refuse — treating the absence
of disagreement as evidence of presence of correctness. The honest reading runs one way only: low
stability is a reason to distrust a number; high stability is not a reason to trust it.

### Ruling 2 — opt-in

The default path runs exactly as today: one draw. Stability runs only when explicitly requested.

**The consequence to record:** with the mode off, no committed number can move, because mode off
means no new runs. That holds, and it is what lets the feature be built this close to freeze — §5's
acceptance makes "the default path did not move" a checkable property rather than an assurance.

**But the premise an earlier draft gave for it was false, and the correction matters more than the
fork it sits next to.** That draft said the SfN figures "are computed from single-draw artifacts".
They are not. **Both published rates are K=3 runs collapsed to one status per paper before grading**
— the frozen CSV's own header says `status = K=3 MAJORITY` and `score_target_space.py:173` reads that
column; `score_v050_reextraction.py:183-185` takes the plurality, resolves a three-way tie toward
`draw_1` by insertion order, and lets the winning draw supply the graded value.

So fork 3's collapse is **not a risk this feature would introduce — it is a present defect already
inside 11/17 and 10/17**, whose rule was unstated at the point of use. And the margin is thin:
braun_2015 is the only paper in either vintage whose draws disagreed (`DEFERRED/MISSING/DEFERRED`),
it is blind, and re-scoring the frozen vintage with that one plurality the other way yields
10/17 — identical to v050. The entire published vintage difference rests on one 2-1 vote.

Disclosed rather than left standing: `20bbd2a` puts the aggregation rule on the face of every rate in
the tally and README, surfaces the contested cell, and appends Amendment 2 to the 0.5.0
pre-registration narrowing the non-stationarity attribution (braun 1/3→3/3 is Fisher p = 0.400;
mueller 0/3→3/3 is p = 0.100 and is non-blind; K=3's attainable floor is 0.100, so no K=3 comparison
can reach significance). **This feature is therefore repairing a defect it discovered in the numbers
it was designed around**, which is the strongest available argument for fork 3's ruling below.

---

## 3. What already exists

### 3a. `_CONFIDENCE` — a placeholder that does reach an artifact

`extractor.py:74`: `_CONFIDENCE = 0.8  # placeholder for MVP; calibration is post-abstract`.

Written at exactly three sites — `extractor.py:454` (`_extracted_pf`, every step field), `:672`
(`_build_version_pf`), `:771` (`_build_base_pipeline`) — which are the only production constructions
of `Extracted` (`:453`, `:669`, `:768`). Nothing reads it inside the extractor. The field is
`provenance.py:54`, `confidence: float = Field(ge=0.0, le=1.0)`: required, no default, no comment, and
no validator beyond the bounds. The spec's only confidence validator is `InferredDefault._ceiling`
(`provenance.py:152-165`), which never reads `Extracted.confidence`.

**HALT — a doc of record is imprecise, and it matters here.** `TRACK_A_SCOPE.md:199` says the
placeholder "never reaches output". Measured over `extractor_mvp/results/**/*.json`: **601 of 601
EXTRACTED arms carry `confidence: 0.8`, across 283 of 360 files.** The claim holds for *human-facing*
surfaces — the gathering pass showed by perturbation that `to_report`, `to_field_table`,
`to_field_bullets` and `to_cobidas_coverage` are byte-identical when the value is changed, with
controls proving each view can see other fields — and fails for the stored artifact. The same
document distinguishes these three paragraphs later: `:206-208` (A7) lists `Extracted.confidence`
among "sub-fields dropped in **rendering**", which is true. So `:199` needs the word "rendered", not a
retraction.

One indirect path exists and has never fired: `citation_resolver.py:124` and `:204` read
`pf.extraction.confidence` and compute `InferredDefault.confidence = min(0.8 × 0.70, 0.60)`, which
renders as `source_confidence=0.80`. Zero of 360 stored JSON files contain `source_confidence` — the
resolver is disabled in every tracked config.

### 3b. Temperature is explicitly 0, and there is a second variance source

`extractor.py:984-990` passes `temperature=0.0` and `max_retries=2`. There is **no** `seed`, `top_p`
or `top_k` anywhere in `extractor.py`. So "temp-0 nondeterminism" is an accurate description of the
premise, not a loose one.

**But `max_retries=2` means a draw is not necessarily one sample.** Instructor reasks on a validation
failure, so a single draw is 1 or 2 completions. `docs/findings/reask-measurement-validity.md` exists
about exactly this, and the gathering pass found **no reask has ever been observed** (0 of 95 logged
calls). This is a live input to fork 1: at fixed prompt, pin and temperature there are already *two*
things that can vary, and a stability number must say which it measured.

### 3c. Existing repeated draws

Three sets of three draws each, same paper IDs within a set: `batch_v040_labelset/draw_1..3` (18
papers), `batch_v050_labelset/draw_1..3` (19), `batch_v6_run1..3` (20).

### 3d. The existing aggregation, read from the code

`score_v050_reextraction.py:182-185`:

```python
statuses = [r["status"] for r in recs]
maj = Counter(statuses).most_common(1)[0][0]
stable = len(set(statuses)) == 1
rec = next(r for r in recs if r["status"] == maj)
```

So, precisely: **plurality on STATUS only**, not unanimity. `stable` is a separate honest flag for
status unanimity. The winning draw then supplies value and diagnostic (`:185`). A three-way tie
resolves to **draw_1**, because `Counter.most_common` breaks ties by first insertion and `statuses` is
built in draw order — demonstrated, not inferred.

Two columns are emitted side by side (`:214-215`): `k3_status`, the `"/"`-joined per-draw record — a
**distribution** — and `maj_status`, the collapsed **winner**. That pairing is the existing precedent
for fork 3.

### 3e. Observed cross-draw agreement, and why the denominator is a design question

Derived here by comparing every `ProvenancedField` across the three draws of each set on
`(status, inference reason, value)`, excluding cells whose reason is `not_targeted_by_mvp`:

| set | targeted cells | full agreement | status agreement | untargeted (excluded) |
|---|---|---|---|---|
| v040 | 157 | 152 | 154 | 342 |
| v050 | 164 | 161 | 161 | 361 |
| v6run | 170 | 166 | 168 | 160 |

**The denominator is not well defined, and that is fork 2 arriving as arithmetic.** An independent
derivation in the same pass, using a different rule for what counts as a targeted cell, got 144 / 152
/ 160 — while agreeing with this one *exactly* on the untargeted counts (342 / 361 / 160) and almost
exactly on the number of disagreeing cells (5 / 3 / 5 against 5 / 3 / 4). The robust finding is
**3 to 5 disagreeing targeted cells per three-draw set**; any *fraction* presupposes a ruling on the
unit. Two methods disagreeing by 13 cells on the same data is the reason §4's fork 2 is not an
implementation detail.

**Rule of three, stated so no one over-reads the above.** With K=3 and zero observed flips on a cell,
the 95% upper bound on that cell's per-draw flip probability is 3/3 = **1.0** — completely
uninformative. Agreement at K=3 bounds nothing about a cell that happened to agree. It can only
*exhibit* instability where instability occurs, never bound it where it does not.

### 3f. Prior variance findings

`docs/findings/variance.md` and `variance-harness-findings.md`: N=15 repeats, temperature 0, input
held byte-identical (slice computed once and reused), on chen_2015 / oconnor_2017 / weber_2024. The
headline is that the extractor is **not run-to-run deterministic at temperature 0**. The gathering
pass reports a discrepancy worth checking before either file is cited as a count: the raw N=15 table
shows **2 flipped cells and 22 stable**, where both documents state 3 of 24. Flagged, not resolved.

### 3g. Cost, derived

Per-paper wall time, from consecutive per-paper JSON mtimes within a draw (each draw is serial, so a
gap is one paper):

**Pooled over 9 draws: N=162 gaps, mean 11.87 s, median 11.35 s, range 8.09–19.62 s.**

`batch.py`'s loop is serial and the batch makes one `create()` per paper (`extractor.py:984`), so:

| K | calls | wall at the mean | worst case if every call reasks |
|---|---|---|---|
| 3 | 57 | 677 s ≈ **11.3 min** | 114 calls |
| 10 | 190 | 2255 s ≈ **37.6 min** | 380 calls |

No dollar amount or token count is recorded anywhere in the repo for the extractor. The three v050
draws were run as concurrent processes, so wall time is reducible by running draws in parallel; the
call count is not.

---

## 4. THE FORKS — RULED 2026-10-01

All six ruled on the same day the facts landed. Each ruling's reason is recorded because the reason is
the transferable part; the forks are kept in place rather than collapsed into a spec so that a later
reader can see what was chosen against.

| fork | ruling |
|---|---|
| 1 what varies | **production path, reask included, reask recorded per draw** |
| 2 unit | **keep the full per-draw field; report status agreement and value agreement as separate counts** |
| 2 denominator | **"targeted" = the repo's existing predicate, `_UNTARGETED_REASON`** |
| 3 shape | **distribution only; the stability record carries no winner** |
| 4 site | **separate results artifact with emitted provenance** |
| 5 `_CONFIDENCE` | **comment at the definition now; rename at the next spec bump** |
| 6 K | **required argument when the mode is on, no default; counts, never a rate unless K ≥ 3/p** |

**Fork 1 — production path, reask included, reask recorded per draw.** It measures what a user's
report actually came from, which is the only thing a stability number about this tool can honestly
claim. Recording the reask per draw keeps the mixture decomposable, which is what removes the
measurement-validity objection `reask-measurement-validity.md` raised: a mixed measurement whose
components are separable is not a confounded measurement. No reask has been observed in 95 calls, so
this costs nothing today and is cheap only while that remains true.

**Fork 2 — the full per-draw field, with status agreement and value agreement as separate counts.** A
single `stable` flag spanning both would be the fourth collapse in this repository's recorded series.
Keeping the whole record also means span-level agreement can be computed later without a re-run, which
is the difference between a decision and a commitment.

**Fork 2, denominator — the existing `_UNTARGETED_REASON` predicate** (`cobidas.py`, read by
`_row_covered_by_extractor`). One definition of "targeted" across coverage and stability. The 13-cell
gap in §3e came from a second rule invented on the spot during measurement, which is exactly the
failure a shared predicate prevents.

**Fork 3 — distribution only; no winner in the stability record.** `score_v050_reextraction.py:185`
makes one draw's value authoritative on the strength of a status vote — the collapse with a value
attached. The existing `k3_status`/`maj_status` pair shows the distribution costs one column; the
ruling is that the stability artifact carries the first and not the second. Nothing downstream may
consume a winner from it.

**Fork 4 — a separate results artifact with emitted provenance.** The prediction-CSV precedent already
has the discipline: a header emitted rather than hand-written, recomputed at emit time, failing loudly
when its inputs are absent. It avoids a spec bump whose precedent was a 16k-line diff, and unlike an
appended key it cannot be silently dropped by `parse_any_version`.

**Fork 5 — comment at the definition now, rename at the next spec bump.** Rename and remove both break
things today with no migration path (§3f's enumeration). A comment costs nothing and removes the
misleading reading for anyone who looks; the rename rides a bump that is paying the schema cost anyway.

**Fork 6 — K required when the mode is on, no default.** Zero flips in K draws bounds the flip
probability at 3/K, so claiming "under 10%" needs **K = 30 per cell**. Report counts; report a rate
only when K is large enough for the bound to mean something. No default, because a default is how a
statistical choice gets made by whoever implements first.

---

## 4a. The forks as they stood, with the evidence each ruling was made against

### Fork 1 — what varies across draws

The quantity reported is *defined* by what is held fixed.

- **Sampling only.** Fixed prompt, pin, temperature; repeat the call. Measures the sampler's
  nondeterminism at temperature 0 — which §3b confirms is real. Cheapest, and the narrowest claim.
- **Sampling plus reask.** The same, but a draw is whatever the production path returns, reask
  included. This is what the *default path* actually does, so it is what a stability number about
  production behaviour would have to measure. Cost: the number is then a mixture of two mechanisms,
  and `reask-measurement-validity.md` exists because that mixture was already a measurement-validity
  question once. No reask has been observed in 95 calls, so today the two choices are empirically
  indistinguishable — which makes this cheap to decide now and expensive to decide after a reask
  appears in a published number.
- **Other perturbations** (prompt paraphrase, slice boundary, model pin): each measures robustness to
  that perturbation, not stability. Naming them here only to exclude them from the word "stability".

### Fork 2 — unit of stability

A field can agree on status and disagree on value. §3e shows this is not hypothetical: v040's status
agreement (154) exceeds its full agreement (152).

- **Status-level.** Detects four-state movement, which is the thing the provenance model exists to
  preserve. Cannot detect a paper whose value changed while staying `EXTRACTED`.
- **Value-level.** Detects the above. Requires a comparison rule for structured values
  (`SpecifiedTerm`, `PipelineRef`) and a decision about whether a differing `verbatim` with the same
  `resolved` counts as a flip.
- **Span-level.** Detects a different sentence being cited for the same value — which bears directly
  on the span-resolution work, since a recovered span and a clean one are different evidence.
  Strictest, and the only unit that would catch a quote drifting under a stable answer.

Whichever is chosen fixes the denominator in §3e. Until then there is no stability *fraction*, only a
count.

### Fork 3 — output shape: distribution or winner

**Stated plainly: a majority vote on status collapses the four-state distinctions the provenance model
exists to preserve.** A 2–1 `EXTRACTED` / `MISSING_FROM_PAPER` split becomes `EXTRACTED`, and the
disagreement — the only thing the extra draws bought — is discarded. This repository has recorded that
collapse-two-facts-into-one-bucket defect three times: the reason-partition DELTA, the Software row's
`addressed` boolean carrying two questions, and the `Not assessed by AESPA` count in
`DELTA_base_pipeline_diagnostic.md` §4a. **A stability feature that introduced it would be the
fourth, inside the feature meant to measure honesty.**

`k3_status` is the useful precedent and it does **both** (§3d): it emits the full per-draw
distribution *and* a collapsed `maj_status`, plus a `stable` unanimity flag. So the existing code
already demonstrates that keeping the distribution costs one extra column. The open question is not
whether to keep it but what, if anything, downstream may consume the winner — and `:185`'s
"winning draw supplies value and diagnostic" is the part that would need ruling, since it makes one
draw's value authoritative on the strength of a status vote.

### Fork 4 — where the record lives

The frozen boundary is real. `ProvenancedField` has two arms, three states each, and five legal pairs
enforced by `couple_stages` (`provenance.py:191-201`); there is no free slot for K draws. An unknown
key is **silently dropped** — `model_config` is `{}`, so pydantic ignores extras, and
`parse_any_version` strips non-schema keys, which `rerender_reports.py:140` depends on. So a record
that is merely *appended* to the JSON would vanish on the next parse without an error.

Candidates, with costs, none chosen:

| site | cost | what reads it today |
|---|---|---|
| a new field on `Extracted` | a spec version bump. Precedent `2560bb11`: 26 files, +16413/−135, of which the exported schema JSON is +15917. Plus 44 hard-coded version lines in 8 files, 3 of which are historical comments a bump must *not* edit. | the migrator, the schema, the examples, `parse_any_version` |
| a sibling record in the per-paper JSON | no spec change, but it is dropped by `parse_any_version` unless the wrapper is versioned — and the wrapper is currently unversioned, gitignored and migrator-blind | nothing |
| a sidecar file beside the per-paper JSON | no spec contact at all; needs its own join key and provenance header | nothing |
| a separate results artifact (like the prediction CSVs) | precedent exists and is good — emitted header, recomputed verification | the scorers, by explicit path |

Note for whoever rules this: `span_recovered` was an additive field on `Extracted` and the gathering
pass reports **299 of 601** on-disk EXTRACTED arms lack it, holding only for the 155 v050 arms. An
additive spec field does not retrofit; the old artifacts simply do not have it.

### Fork 5 — what happens to `_CONFIDENCE`

Under ruling 1, a field named "confidence" that is never computed is a misleading artifact — and
§3a shows it is not inert: it is on 601 stored arms and it feeds the citation resolver's ceiling
arithmetic.

- **Leave it.** Zero work. A stability feature then ships alongside a field whose name claims the
  thing ruling 1 forbids, in the same JSON.
- **Rename it** (e.g. `extraction_prior`). Every constructor passing `confidence=` is rejected —
  verified — so the 601 stored arms, `examples/spec.json` (59 keys), the frozen v0.1.0 document and
  the dict fixtures all fail validation without a migration, and `migrations.py` does not touch
  confidence.
- **Remove it.** `citation_resolver.py:124`/`:204` raise `AttributeError`, caught at `batch.py:236`,
  so the paper silently becomes `extraction_failed` — and no CI test reaches those lines; only the
  live test does. `test_examples_reproducible` fails its byte-identity check.

The cheapest honest option may be none of the three: leave the field and **document it at its
definition** as a placeholder that is not a confidence, which costs one comment and removes the
misleading reading for anyone who looks. Stated as an option, not a recommendation.

### Fork 6 — K: fixed or parameterised, and the default when on

- The prereg binds **K=10** for its own probe (`:7`), citing `variance.md`.
- §3e's rule-of-three shows K=3 cannot bound a flip rate; it can only exhibit flips.
- §3g prices K=3 at 57 calls / ~11 min and K=10 at 190 calls / ~38 min, serial, reducible by running
  draws concurrently as the v050 run did.

If a *rate* is ever to be reported rather than a count, K must be large enough for the bound to mean
something, and that is a statistical choice with a cost attached — not a default to be picked by
whoever implements it first.

---

## 4b. Two sub-decisions the forks left open — RULED 2026-10-03

Both arrived in the implementation prompt rather than from this document, which is why they are
written here before any code: a decision that lives only in a prompt is one the code embodies and
the record does not, and this project has had that exact gap once already — the render ruling sat
unrecorded while `DEVLOG.md:2371` asserted the opposite. Ruled by the author in conversation;
recorded 2026-10-03, the day they became checkable, not backdated.

### Sub-decision 1 — value agreement is EXACT equality of the serialized value

§4a's fork 2 left this open in as many words: value-level comparison "requires a comparison rule for
structured values (`SpecifiedTerm`, `PipelineRef`) and a decision about whether a differing
`verbatim` with the same `resolved` counts as a flip." **It counts.**

*Why exact.* Fork 2 keeps the full per-draw field, so every looser rule — `resolved`-only,
case-insensitive, whitespace-normalised — stays computable later from the stored record with no
re-run. Strictness is therefore free in optionality and costly only in the direction of reporting
*more* disagreement than a looser rule would. Between two numbers computable from the same record,
the one that cannot understate movement is the one to publish. Every normalisation is itself a
looseness ruling, and applying one inside a comparison applies it invisibly.

*What "serialized value" means, scoped precisely.* The comparison is over `Extracted.value` **only**,
as `model_dump(mode="json")` with deterministic key order, and with **no** normalisation of any kind.
Three fields of `Extracted` are deliberately excluded, and each exclusion is a ruling:

| excluded | why |
|---|---|
| `spans` | span agreement is a **separate unit** (§4a, fork 2), and folding it into value agreement would be the collapse this document is most alert to. `SpecifiedTerm.verbatim` is *inside* the value and is not the quote; the quote is `Extracted.spans`. So exact value equality does **not** collapse value into span. |
| `confidence` | it is the uncalibrated placeholder of §3a and fork 5. A stability number that moved when it changed would be a stability number partly about a non-quantity. |
| `span_recovered` | not comparable across vintages: **299 of 601** stored EXTRACTED arms lack it (§4a, fork 4's closing note), so including it would read absence as disagreement. |

`SpecifiedTerm` is `{verbatim, resolved, resolution}` and `PipelineRef` is `{name, version}` — all
value content, all compared. Two draws returning the same `resolved` under different `verbatim`
therefore register as a **value** disagreement and a **status** agreement, which is exactly the
status/value split fork 2 ruled for.

### Sub-decision 2 — the artifact is run output, gitignored, beside its draws

Not `ground_truth/`. Stability is a property of a run, not of a label, and the per-run artifact
belongs with the draws it was computed from.

**The stated reason needs one correction, because `ground_truth/` is not labels-only.** Measured:
`ground_truth/predictions_v040_frozen.csv` is **tracked** and is not a label — its own emitted header
calls it a "durable snapshot of a NON-reproducible run … the record the first Tier-A/Tier-B number was
computed against", while `extractor_mvp/results/batch_v040_labelset/predictions_v040.csv` is the
untracked run output (`extractor_mvp/results/.gitignore:7` matches `*`), carrying a bare column row
and no provenance block. So the directory already holds run-derived tracked artifacts, and "not a
label" does not by itself exclude it. The ruling stands on the narrower ground: *the default artifact
of an opt-in mode that has never been run is run output.*

**And the precedent fork 4 cites is two-stage, which adds a condition.** Emit into gitignored
`results/`; promote to a tracked snapshot with its emitted header when a number is computed against
it. That is precisely what makes 11/17 and 10/17 auditable today. Therefore:

> **No stability number may be published from a gitignored artifact.** Reporting one anywhere a
> reader can meet it — poster, abstract, README, findings doc — requires first promoting that
> specific artifact to a tracked snapshot carrying its emitted provenance header, in the manner of
> `predictions_v040_frozen.csv`. Publishing a figure whose only record is in an ignored directory
> would repeat, with stability, what `20bbd2a` had to repair for the aggregation rule.

One refinement to fork 4 as ruled: the provenance header goes on the artifact **at emit time**, not
only on promotion. The frozen CSV shows this project writes the header at the point a number is
computed against the file; writing it when the file is created is strictly better, costs nothing, and
means the gitignored copy is self-describing if anyone finds one on disk.

---

## 5. Acceptance, stated now so it cannot drift

Any later implementation must show all of these:

1. **With the mode off, nothing moves.** The re-render identity gate
   (`extractor_mvp/scripts/rerender_reports.py`) shows **19/19 byte-identical**, and the negative
   control against `d31e8b7` returns the value recorded in that script's docstring **at that HEAD** —
   note the docstring now records 16/3 with its derivation and the fact that the figure drifts by
   construction (`20f3694`). If the two-fixed-ref fix has landed by then, use the fixed pair instead,
   which is the point of it.
2. **No stability output is presented as, named as, or aggregated into a correctness figure.** No
   output field, column, log line or document may call it confidence. A stability number must not
   enter a blind-rate denominator, a Wilson interval, or any accuracy table.
3. **No number is computed from the motion reachability probe in violation of §1.** The prereg binds
   no accuracy figure and no variance step; if stability is reported for motion, the amendment is
   written first, dated, append-only, with the superseded text retained — the pattern Amendment 1
   itself used.
4. **The distribution survives.** Whatever fork 3 is ruled, the per-draw record must be recoverable
   from the artifact. A feature that emits only a winner has discarded what the extra calls paid for.
5. **The denominator is stated wherever a fraction is**, and it is `_UNTARGETED_REASON`'s — per fork
   2's ruling, and because §3e contains two defensible denominators differing by 13 cells, one of
   which was invented during measurement.
6. **Every rate the repo publishes names its aggregation**, not only its vintage. Already true as of
   `20bbd2a`; the acceptance records it so a later rate cannot be added without it.
7. **K is passed explicitly.** A run with the mode on and no K is an error, not a default.
8. **Value agreement is exact and scoped.** The comparison reads `Extracted.value` only, with no
   normalisation, and excludes `spans`, `confidence` and `span_recovered` — §4b, sub-decision 1. A
   test must show that two draws agreeing on `resolved` under differing `verbatim` register as value
   disagreement with status agreement, or the split is not implemented.
9. **No stability number is published from a gitignored artifact** — §4b, sub-decision 2. The emitted
   provenance header is written at emit time, so the check is that the artifact in `results/` already
   carries it.

---

## 6. What this enables, and the order

Recorded order: **stability before further labelled rows** — motion's extraction side, then
smoothing.

The reason is that an unstable field's labels are fine and its *scores* are not. Labelling is a
one-time cost against the papers; scoring is a measurement against the extractor, and a score
computed from one draw of an unstable field is a sample reported as a value. The corpus has already
paid for this once: braun moved correct→error between vintages at an identical pin, taking the blind
rate 11/17 → 10/17, and that movement was discovered by re-extraction rather than predicted by any
stability measure. Knowing which fields move is what makes the next labelled row's score worth
computing.

**And the design pass already produced the argument's best instance, for later use.** Tracing which
column the published rates read (§2) found that the tool's own headline vintage difference — the
six-point drop a reader meets first — rests on a **single 2-1 plurality vote** on one paper, and that
the paper's earlier draws already contained the outcome the later vintage produced. That was found by
designing the stability feature, before building any of it, by asking what the numbers were aggregates
*of*. It is the case for keeping the distribution, demonstrated on the number people will read first
rather than argued in the abstract — which is what makes it worth presenting rather than merely
recording.
